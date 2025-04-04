# portpulse.py
import argparse
from datetime import datetime
from utils import normalize_adjclose
from core.fetch import fetch_price_data, fetch_vix_data, fetch_fear_greed_index, fetch_interest_rate
from core.indicators import add_all_indicators
from core.signal import custom_decide_allocation_extended, explain_allocation_reason
from core.backtest import run_backtest, compute_performance_metrics, print_performance_table
from core.optimize import run_optimization_and_save
from core.simulation import simulate_with_saved_thresholds, simulate_with_default_thresholds
from core.portfolio import load_trade_log, get_current_holdings, get_initial_holdings, ensure_database
from data.thresholds import load_latest_thresholds
from rich import print
from rich.table import Table
from rich.console import Console
from rich.text import Text

def analyze_today():
    console = Console()
    print("\n[bold cyan]📊 오늘의 시장 지표 및 기술 지표 기반 분석[/bold cyan]\n")
    tsla_df, tsll_df = fetch_price_data()
    tsla_df = tsla_df.rename(columns=str.lower)
    tsll_df = tsll_df.rename(columns=str.lower)

    tsla_df = normalize_adjclose(tsla_df)
    tsll_df = normalize_adjclose(tsll_df)

    if tsla_df.empty or tsll_df.empty:
        print(f"[red]⚠ 데이터가 비어 있습니다. 분석을 중단합니다.[/red]")
        return

    tsla_df = add_all_indicators(tsla_df)

    latest_date = tsla_df.index[-1]
    latest = tsla_df.loc[latest_date]
    price = latest['adjclose']
    vix_data = fetch_vix_data()
    vix = vix_data.get(latest_date, None) if not vix_data.empty else None
    fear_greed = fetch_fear_greed_index()
    interest_rate = fetch_interest_rate()

    # 임계값 로드 (최적화된 값이 없으면 기본값 사용)
    thresholds = load_latest_thresholds()
    if thresholds is None:
        thresholds = get_default_thresholds()
    else:
        print("\n[bold green]📈 최적화된 성과 지표[/bold green]")
        if 'cagr' in thresholds:
            print(f" - CAGR: {thresholds['cagr']*100:.2f}%")
        if 'cumulative_return' in thresholds:
            print(f" - 누적 수익률: {thresholds['cumulative_return']*100:.2f}%")
        if 'max_return' in thresholds:
            print(f" - 최대 수익률: {thresholds['max_return']*100:.2f}%")

    w_tsla, w_tsll = custom_decide_allocation_extended(latest, thresholds)
    explanation = explain_allocation_reason(latest, w_tsla, w_tsll, thresholds)

    print(f"[bold yellow]📅 분석 기준일: {latest_date.date()}[/bold yellow]\n")
    print(explanation)

    trade_log = load_trade_log()
    current = get_current_holdings(trade_log)
    initial = get_initial_holdings(trade_log)
    tsla_price = tsla_df.iloc[-1]['adjclose']
    tsll_price = tsll_df.iloc[-1]['adjclose']

    print("\n[bold green]📊 현재 포트폴리오 분석[/bold green]")

    print("[bold]* 초기 투자 자산[/bold]")
    initial_cost = 0.0
    table_initial = Table(show_header=True, header_style="bold", title="")
    table_initial.add_column("Ticker", justify="center")
    table_initial.add_column("수량", justify="right")
    table_initial.add_column("단가", justify="right")
    table_initial.add_column("금액", justify="right")

    for ticker in ["TSLA", "TSLL"]:
        shares = initial[ticker]["shares"]
        price = initial[ticker]["price"]
        value = shares * price
        initial_cost += value
        table_initial.add_row(ticker, str(shares), f"${price:.2f}", f"${value:,.2f}")

    console.print(table_initial)

    print("[bold]* 현재 자산 구성 및 수익률[/bold]")
    total_value = 0.0
    asset_rows = []
    for ticker in ["TSLA", "TSLL"]:
        shares = current[ticker]["shares"]
        cost = current[ticker]["cost"]
        price = tsla_price if ticker == "TSLA" else tsll_price
        value = price * shares
        pnl = (price - cost) / cost * 100 if cost > 0 else 0
        total_value += value
        asset_rows.append((ticker, shares, cost, value, pnl))

    table_current = Table(show_header=True, header_style="bold", title="")
    table_current.add_column("Ticker", justify="center")
    table_current.add_column("수량", justify="right")
    table_current.add_column("평균단가", justify="right")
    table_current.add_column("평가금액", justify="right")
    table_current.add_column("수익률", justify="right")
    table_current.add_column("비중", justify="right")

    for ticker, shares, cost, value, pnl in asset_rows:
        weight = (value / total_value) * 100 if total_value > 0 else 0
        table_current.add_row(ticker, str(shares), f"${cost:.2f}", f"${value:,.2f}", f"{pnl:.2f}%", f"{weight:.1f}%")

    console.print(table_current)

    print(f"\n💰 총 평가액: ${total_value:,.2f}")
    if initial_cost > 0:
        overall_pnl = (total_value - initial_cost) / initial_cost * 100
        color = "green" if overall_pnl >= 0 else "red"
        pnl_text = Text(f"📈 전체 포트폴리오 수익률: {overall_pnl:.2f}%", style=color)
        console.print(pnl_text)

    if total_value == 0:
        print("[yellow]\n보유 자산 없음 → 리밸런싱 제안 생략[/yellow]")
        return

    print("\n[bold green]📌 제안된 내일 포트폴리오 비중[/bold green]")
    print(f"TSLA: {w_tsla*100:.1f}%  |  TSLL: {w_tsll*100:.1f}%")

    print("\n[bold green]🔁 리밸런싱 제안[/bold green]")
    target_tsla_amt = total_value * w_tsla
    target_tsll_amt = total_value * w_tsll
    current_tsla_amt = tsla_price * current["TSLA"]["shares"]
    current_tsll_amt = tsll_price * current["TSLL"]["shares"]
    delta_tsla = target_tsla_amt - current_tsla_amt
    delta_tsll = target_tsll_amt - current_tsll_amt

    if delta_tsll < -1:
        print(f"TSLL {-delta_tsll / tsll_price:.0f}주 매도 권장")
    if delta_tsla < -1:
        print(f"TSLA {-delta_tsla / tsla_price:.0f}주 매도 권장")
    if delta_tsll > 1:
        print(f"TSLL {delta_tsll / tsll_price:.0f}주 매수 권장")
    if delta_tsla > 1:
        print(f"TSLA {delta_tsla / tsla_price:.0f}주 매수 권장")

def run_backtest_mode():
    run_optimization_and_save(metric="sharpe")

def run_simulation_mode(start, end, thresholds):
    console = Console()
    console.print(f"\n[bold cyan]🧪 시뮬레이션 모드 실행 중: {start} ~ {end}, 임계값: {thresholds}[/bold cyan]\n")
    strat_opt, perf_opt = simulate_with_saved_thresholds(start, end)
    strat_def, perf_def = simulate_with_default_thresholds(start, end)

    table = Table(title="Simulation Summary: Optimized vs Default")
    table.add_column("Metric")
    table.add_column("Optimized", justify="right")
    table.add_column("Default", justify="right")

    for key in ["Final Value", "CAGR", "Sharpe", "MaxDrawdown"]:
        table.add_row(
            key,
            f"{perf_opt[key]:.2f}" if isinstance(perf_opt[key], float) else str(perf_opt[key]),
            f"{perf_def[key]:.2f}" if isinstance(perf_def[key], float) else str(perf_def[key])
        )
    console.print(table)

    initial_value = 100.0
    opt_return = (perf_opt['Final Value'] / initial_value - 1) * 100
    def_return = (perf_def['Final Value'] / initial_value - 1) * 100
    print(f"\n[bold green]Optimized 수익률: {opt_return:.2f}%[/bold green]")
    print(f"[bold yellow]Default 수익률: {def_return:.2f}%[/bold yellow]")

def main():
    ensure_database("data/portpulse.db")
    parser = argparse.ArgumentParser(description="PortPulse 포트폴리오 전략 분석 도구")
    parser.add_argument("--backtest", action="store_true", help="백테스트 실행")
    parser.add_argument("--simulate", nargs=2, metavar=("START_DATE", "END_DATE"), help="시뮬레이션 실행 (YYYY-MM-DD 형식)")
    parser.add_argument("--optimize", action="store_true", help="자동 최적화 실행")
    parser.add_argument("--metric", type=str, default="sharpe", choices=["sharpe", "cagr", "mdd"], help="최적화 기준 (sharpe, cagr, mdd)")
    parser.add_argument("--min-return", type=float, default=0.0, help="최소 누적 수익률 (기본값: 0.0%)")
    args = parser.parse_args()

    if args.backtest:
        #run_backtest_mode()
        run_optimization_and_save(metric=args.metric, min_return=args.min_return)
    elif args.simulate:
        try:
            # 날짜 형식 변환
            start_date = datetime.strptime(args.simulate[0], "%Y-%m-%d").date()
            end_date = datetime.strptime(args.simulate[1], "%Y-%m-%d").date()
            # 최신 임계값 로드, 없으면 기본값 사용
            thresholds = load_latest_thresholds()
            if thresholds is None:
                print("[yellow]⚠ 최적화된 임계값이 없습니다. 기본값을 사용합니다.[/yellow]")
                thresholds = get_default_thresholds()
            # 시뮬레이션 실행
            run_simulation_mode(start_date, end_date, thresholds)
        except ValueError:
            print("[red]날짜 형식이 올바르지 않습니다. YYYY-MM-DD 형식으로 입력하세요.[/red]")
    elif args.optimize:
        #run_optimization_and_save(metric=args.metric)
        run_optimization_and_save(metric=args.metric, min_return=args.min_return)
    else:
        analyze_today()

if __name__ == "__main__":
    main()
