# portpulse.py

import argparse
from datetime import datetime
from core.fetch import fetch_price_data, fetch_vix_data, fetch_fear_greed_index, fetch_interest_rate
from core.indicators import add_technical_indicators
from core.signal import decide_allocation, explain_allocation_reason
from core.backtest import run_backtest, compute_performance_metrics, print_performance_table
from core.optimize import run_optimization
from rich import print


def analyze_today():
    print("[bold cyan]\n📊 오늘의 시장 지표 및 기술 지표 기반 분석\n[/bold cyan]")
    tsla_df, tsll_df = fetch_price_data()
    tsla_df = add_technical_indicators(tsla_df)
    latest_date = tsla_df.index[-1]
    latest = tsla_df.loc[latest_date]
    price = latest['AdjClose']
    rsi = latest['RSI']
    macd = latest['MACD']
    macd_signal = latest['MACD_signal']
    macd_hist = latest['MACD_hist']
    bb_upper = latest['BB_upper']
    bb_lower = latest['BB_lower']
    atr = latest['ATR']

    vix_data = fetch_vix_data()
    vix = vix_data.get(latest_date, None)
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
    print("\n[bold green]💡 제안된 내일 포트폴리오 비중:[/bold green]")
    print(f"TSLA: {w_tsla*100:.1f}%  |  TSLL: {w_tsll*100:.1f}%")


def run_backtest_mode():
    print("\n[bold cyan]📈 백테스트 모드 실행 중...\n[/bold cyan]")
    tsla_df, tsll_df = fetch_price_data()
    tsla_df = add_technical_indicators(tsla_df)
    strategy_vals, tsla_vals, tsll_vals = run_backtest(tsla_df, tsll_df)
    strat_metrics = compute_performance_metrics(strategy_vals)
    tsla_metrics = compute_performance_metrics(tsla_vals)
    tsll_metrics = compute_performance_metrics(tsll_vals)
    print_performance_table(strat_metrics, tsla_metrics, tsll_metrics)


def run_simulation_mode(start, end):
    print(f"\n[bold cyan]🧪 시뮬레이션 모드 실행 중: {start} ~ {end}[/bold cyan]\n")
    tsla_df, tsll_df = fetch_price_data(start=start, end=end)
    tsla_df = add_technical_indicators(tsla_df)
    strategy_vals, tsla_vals, tsll_vals = run_backtest(tsla_df, tsll_df)
    strat_metrics = compute_performance_metrics(strategy_vals)
    tsla_metrics = compute_performance_metrics(tsla_vals)
    tsll_metrics = compute_performance_metrics(tsll_vals)
    print_performance_table(strat_metrics, tsla_metrics, tsll_metrics)


def main():
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
