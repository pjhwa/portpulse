# core/optimize.py
import itertools
import pandas as pd
import matplotlib.pyplot as plt
from core.fetch import fetch_price_data, fetch_vix_data
from core.indicators import add_technical_indicators
from core.backtest import run_backtest, compute_performance_metrics, print_performance_table
from core.signal import decide_allocation
from rich import print

# 유연한 평가 기준 지원: Sharpe, CAGR, MDD

# 튜닝 가능한 할당 함수

def custom_decide_allocation(rsi, macd, macd_signal, macd_hist, price, bb_upper, bb_lower, atr,
                             rsi_low, rsi_high, atr_low, atr_high, use_bb=True, vix=None):
    score = 0
    if rsi is not None:
        if rsi <= rsi_low:
            score += 1
        elif rsi >= rsi_high:
            score -= 1
    if macd is not None and macd_signal is not None:
        if macd > macd_signal:
            score += 1
        else:
            score -= 1
    if use_bb and price is not None and bb_upper is not None and bb_lower is not None:
        if price < bb_lower:
            score += 1
        elif price > bb_upper:
            score -= 1
    if atr is not None and price is not None:
        atr_pct = (atr / price) * 100
        if atr_pct < atr_low:
            score += 1
        elif atr_pct > atr_high:
            score -= 1
    if vix is not None:
        if vix > 25:
            score -= 1
        elif vix < 15:
            score += 1
    w_tsll = max(0.0, min(score / 5, 1.0)) if score > 0 else 0.0
    w_tsla = 1.0 - w_tsll
    return w_tsla, w_tsll


def run_optimization(metric="sharpe"):
    print("\n[bold cyan]🧠 자동 튜닝 최적화 실행 중...[/bold cyan]")
    tsla_df, tsll_df = fetch_price_data()
    tsla_df = add_technical_indicators(tsla_df)
    vix_df = fetch_vix_data()

    # ⬆ 2단계: 확장된 튜닝 범위
    rsi_lows = [20, 25, 30, 35, 40]
    rsi_highs = [60, 65, 70, 75, 80]
    atr_lows = [1.0, 1.5, 2.0, 2.5, 3.0]
    atr_highs = [4.0, 5.0, 6.0, 7.0, 8.0]
    bb_flags = [True, False]

    best_config = None
    best_value = float('-inf')
    best_results = None
    best_curve = None

    for (rsi_lo, rsi_hi, atr_lo, atr_hi, use_bb) in itertools.product(rsi_lows, rsi_highs, atr_lows, atr_highs, bb_flags):
        if rsi_lo >= rsi_hi or atr_lo >= atr_hi:
            continue

        def alt_decider(rsi, macd, macd_signal, macd_hist, price, bb_upper, bb_lower, atr, date=None):
            vix_val = vix_df.loc[date] if date in vix_df.index else None
            return custom_decide_allocation(rsi, macd, macd_signal, macd_hist, price, bb_upper, bb_lower, atr,
                                            rsi_lo, rsi_hi, atr_lo, atr_hi, use_bb, vix=vix_val)

        strat_vals, tsla_vals, tsll_vals = run_backtest(tsla_df, tsll_df, allocation_fn=alt_decider)
        metrics = compute_performance_metrics(strat_vals)

        metric_val = {
            "sharpe": metrics["Sharpe"],
            "cagr": metrics["CAGR"],
            "mdd": -metrics["MaxDrawdown"]
        }.get(metric.lower(), metrics["Sharpe"])

        if metric_val is not None and metric_val > best_value:
            best_value = metric_val
            best_config = {
                'RSI_low': rsi_lo, 'RSI_high': rsi_hi,
                'ATR_low': atr_lo, 'ATR_high': atr_hi,
                'Use_Bollinger': use_bb
            }
            best_results = (metrics, compute_performance_metrics(tsla_vals), compute_performance_metrics(tsll_vals))
            best_curve = strat_vals

    print("\n[bold green]✅ 최적화 완료![/bold green]")
    print(f"[bold]최고 성과 조건 (metric = {metric.upper()}):[/bold]")
    for k, v in best_config.items():
        print(f" - {k}: {v}")

    print("\n[bold]최종 전략 성능:[/bold]")
    print_performance_table(*best_results)

    pd.Series(best_curve).to_csv("best_equity_curve.csv")
    summary_df = pd.DataFrame([{
        **best_config,
        **best_results[0],
        "OptimizeMetric": metric,
        "BestValue": best_value
    }])
    summary_df.to_csv("best_strategy_summary.csv", index=False)

    plt.figure(figsize=(10, 5))
    plt.plot(best_curve.index, best_curve.values, label="Optimized Strategy", linewidth=2)
    plt.title("Best Strategy Equity Curve")
    plt.xlabel("Date")
    plt.ylabel("Portfolio Value")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig("equity_curve.png")
    pd.Series(tsla_vals).to_csv("best_tsla_curve.csv")
    pd.Series(tsll_vals).to_csv("best_tsll_curve.csv")

    import yfinance as yf
    start, end = tsla_df.index[0], tsla_df.index[-1]
    spy = yf.Ticker("SPY").history(start=start, end=end)['Close']
    qqq = yf.Ticker("QQQ").history(start=start, end=end)['Close']
    spy = spy / spy.iloc[0] * 100
    qqq = qqq / qqq.iloc[0] * 100
    spy.to_csv("best_spy_curve.csv")
    qqq.to_csv("best_qq_curve.csv")
    print("\n📁 결과 저장됨: best_strategy_summary.csv, equity_curve.png")
