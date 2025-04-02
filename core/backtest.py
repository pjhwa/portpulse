# backtest.py
import pandas as pd
import numpy as np
from rich.console import Console
from rich.table import Table

def run_backtest(tsla_df, tsll_df, allocation_fn=None):
    """
    백테스트를 수행하여 전략 수익률, TSLA 단독 보유, TSLL 단독 보유 수익곡선을 반환합니다.
    """
    portfolio = []
    tsla_only = []
    tsll_only = []

    for i in range(1, len(tsla_df)):
        today = tsla_df.iloc[i - 1]
        tomorrow = tsla_df.iloc[i]
        tsll_price = tsll_df.loc[tomorrow.name]["Close"]

        if allocation_fn:
            w_tsla, w_tsll = allocation_fn(today)
        else:
            w_tsla = 1.0
            w_tsll = 0.0

        total_return = (
            w_tsla * (tomorrow["Close"] / today["Close"]) +
            w_tsll * (tsll_price / tsll_df.loc[today.name]["Close"])
        )

        portfolio.append(portfolio[-1] * total_return if portfolio else 100.0)
        tsla_only.append(tsla_only[-1] * (tomorrow["Close"] / today["Close"]) if tsla_only else 100.0)
        tsll_only.append(tsll_only[-1] * (tsll_price / tsll_df.loc[today.name]["Close"]) if tsll_only else 100.0)

    dates = tsla_df.index[1:]
    return pd.Series(portfolio, index=dates), pd.Series(tsla_only, index=dates), pd.Series(tsll_only, index=dates)

def compute_performance_metrics(equity_curve):
    """
    수익곡선을 기반으로 CAGR, Volatility, Sharpe, Max Drawdown을 계산합니다.
    """
    returns = equity_curve.pct_change().dropna()
    cagr = (equity_curve.iloc[-1] / equity_curve.iloc[0]) ** (252 / len(equity_curve)) - 1
    volatility = returns.std() * np.sqrt(252)
    sharpe = returns.mean() / returns.std() * np.sqrt(252)
    drawdown = 1 - equity_curve / equity_curve.cummax()
    max_dd = drawdown.max()
    return {
        "CAGR": cagr,
        "Volatility": volatility,
        "Sharpe": sharpe,
        "MaxDrawdown": max_dd
    }

def print_performance_table(strategy_curve, tsla_curve, tsll_curve):
    """
    전략 vs TSLA vs TSLL 성과 비교표를 콘솔에 출력합니다.
    """
    console = Console()
    table = Table(title="Performance Summary: Dynamic Strategy vs TSLA vs TSLL")

    table.add_column("Metric")
    table.add_column("Dynamic Strategy", justify="right")
    table.add_column("TSLA Only", justify="right")
    table.add_column("TSLL Only", justify="right")

    strat_metrics = compute_performance_metrics(strategy_curve)
    tsla_metrics = compute_performance_metrics(tsla_curve)
    tsll_metrics = compute_performance_metrics(tsll_curve)

    for key in ["CAGR", "Volatility", "Sharpe", "MaxDrawdown"]:
        table.add_row(
            key,
            f"{strat_metrics[key]*100:.2f}%" if key != "Sharpe" else f"{strat_metrics[key]:.2f}",
            f"{tsla_metrics[key]*100:.2f}%" if key != "Sharpe" else f"{tsla_metrics[key]:.2f}",
            f"{tsll_metrics[key]*100:.2f}%" if key != "Sharpe" else f"{tsll_metrics[key]:.2f}"
        )

    console.print(table)
