# ✅ portpulse.py
import argparse
from datetime import datetime
from core.fetch import fetch_price_data, fetch_vix_data, fetch_fear_greed_index, fetch_interest_rate
from core.indicators import add_technical_indicators
from core.signal import decide_allocation, explain_allocation_reason
from core.backtest import run_backtest, compute_performance_metrics, print_performance_table
from core.optimize import run_optimization
from rich import print
from rich.table import Table
from rich.console import Console
from rich.text import Text
from core.portfolio import load_trade_log, get_current_holdings, get_initial_holdings
from core.portfolio import ensure_database

# ✅ 누락 컬럼 보완 함수 포함
def normalize_adjclose(df):
    # 열 이름을 소문자로 통일 (fetch_price_data와의 일관성 유지)
    df.columns = [col.lower() for col in df.columns]

    # 'adjclose' 열이 없는 경우 보완
    if "adjclose" not in df.columns:
        if "close" in df.columns:
            df["adjclose"] = df["close"]
        elif "adj close" in df.columns:
            df["adjclose"] = df["adj close"]
        else:
            raise ValueError("Cannot find a suitable column to set as 'adjclose'")

    # 'close' 열이 없는 경우 'adjclose'로 보완
    if "close" not in df.columns and "adjclose" in df.columns:
        df["close"] = df["adjclose"]

    return df

def analyze_today():
    console = Console()
    print("\n[bold cyan]📊 오늘의 시장 지표 및 기술 지표 기반 분석[/bold cyan]\n")
    tsla_df, tsll_df = fetch_price_data()
    tsla_df = tsla_df.rename(columns=str.lower)
    tsll_df = tsll_df.rename(columns=str.lower)

    tsla_df = normalize_adjclose(tsla_df)
    tsll_df = normalize_adjclose(tsll_df)

    # 데이터프레임이 비어 있는지 확인
    if tsla_df.empty:
        print(f"[red]⚠ TSLA 데이터가 비어 있습니다. 분석을 중단합니다.[/red]")
        return
    if tsll_df.empty:
        print(f"[red]⚠ TSLL 데이터가 비어 있습니다. 분석을 중단합니다.[/red]")
        return

    tsla_df = add_technical_indicators(tsla_df)

    latest_date = tsla_df.index[-1]
    latest = tsla_df.loc[latest_date]
    price = latest['adjclose']
    rsi = latest['rsi']
    macd = latest['macd']
    macd_signal = latest['macd_signal']
    macd_hist = latest['macd_hist']
    bb_upper = latest['bb_upper']
    bb_lower = latest['bb_lower']
    atr = latest['atr']

    vix_data = fetch_vix_data()
    vix = vix_data.get(latest_date, None) if not vix_data.empty else None
    fear_greed = fetch_fear_greed_index()
    interest_rate = fetch_interest_rate()

    w_tsla, w_tsll = decide_allocation(
        rsi, macd, macd_signal, macd_hist,
        price, bb_upper, bb_lower, atr,
        vix=vix, fear_greed=fear_greed, interest_rate=interest_rate
    )

    explanation = explain_allocation_reason(
        rsi, macd, macd_signal, macd_hist,
        price, bb_upper, bb_lower, atr,
        w_tsla, w_tsll, vix=vix, fear_greed=fear_greed, interest_rate=interest_rate
    )

    print(f"[bold yellow]📅 분석 기준일: {latest_date.date()}[/bold yellow]\n")
    print(explanation)

    trade_log = load_trade_log()
    current = get_current_holdings(trade_log)
    initial = get_initial_holdings(trade_log)
    tsla_price = tsla_df.iloc[-1]['adjclose']  # 소문자
    tsll_price = tsll_df.iloc[-1]['adjclose']  # 소문자

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
    print("\n[bold cyan]📈 백테스트 모드 실행 중...[/bold cyan]\n")
    tsla_df, tsll_df = fetch_price_data()
    tsla_df = normalize_adjclose(tsla_df)  # TSLA 데이터프레임 정규화
    tsll_df = normalize_adjclose(tsll_df)  # TSLL 데이터프레임 정규화
    tsla_df = add_technical_indicators(tsla_df)

    def allocation_fn(today):
        return decide_allocation(
            today['RSI'], today['MACD'], today['MACD_signal'], today['MACD_hist'],
            today['AdjClose'], today['BB_upper'], today['BB_lower'], today['ATR']
        )

    # 백테스트 실행
    strategy_vals, tsla_vals, tsll_vals = run_backtest(tsla_df, tsll_df, allocation_fn=allocation_fn)

    # 성과 지표 계산
    strat_metrics = compute_performance_metrics(strategy_vals)
    tsla_metrics = compute_performance_metrics(tsla_vals)
    tsll_metrics = compute_performance_metrics(tsll_vals)

    # 결과 출력
    print_performance_table(strat_metrics, tsla_metrics, tsll_metrics)

def run_simulation_mode(start, end):
    print(f"\n[bold cyan]🧪 시뮬레이션 모드 실행 중: {start} ~ {end}[/bold cyan]\n")
    tsla_df, tsll_df = fetch_price_data(start=start, end=end)
    tsla_df = normalize_adjclose(tsla_df)
    tsla_df = add_technical_indicators(tsla_df)
    strategy_vals, tsla_vals, tsll_vals = run_backtest(tsla_df, tsll_df)
    strat_metrics = compute_performance_metrics(strategy_vals)
    tsla_metrics = compute_performance_metrics(tsla_vals)
    tsll_metrics = compute_performance_metrics(tsll_vals)
    print_performance_table(strat_metrics, tsla_metrics, tsll_metrics)


def main():
    ensure_database("portpulse.db")
    parser = argparse.ArgumentParser(description="PortPulse 포트폴리오 전략 분석 도구")
    parser.add_argument("--backtest", action="store_true", help="백테스트 실행")
    parser.add_argument("--simulate", nargs=2, metavar=("START_DATE", "END_DATE"),
                        help="시뮬레이션 실행 (예: --simulate 2023-01-01 2024-01-01)")
    parser.add_argument("--optimize", action="store_true", help="자동 최적화 실행")
    parser.add_argument("--metric", type=str, default="sharpe", help="최적화 기준 (sharpe, cagr, mdd)")
    args = parser.parse_args()

    if args.backtest:
        run_backtest_mode()
    elif args.simulate:
        try:
            start_date = datetime.strptime(args.simulate[0], "%Y-%m-%d").date()
            end_date = datetime.strptime(args.simulate[1], "%Y-%m-%d").date()
            run_simulation_mode(start_date, end_date)
        except Exception:
            print("[red]날짜 형식이 올바르지 않습니다. YYYY-MM-DD 형식으로 입력하세요.[/red]")
    elif args.optimize:
        run_optimization(metric=args.metric)
    else:
        analyze_today()


if __name__ == "__main__":
    main()
