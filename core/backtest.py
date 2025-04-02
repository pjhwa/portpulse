# core/backtest.py
import math
import pandas as pd
import numpy as np
from core.signal import decide_allocation
from rich.table import Table
from rich import print

def run_backtest(tsla_df, tsll_df, allocation_fn=None):
    if allocation_fn is None:
        from core.signal import decide_allocation as allocation_fn
    combined = pd.DataFrame({
        'TSLA': tsla_df['AdjClose'],
        'TSLL': tsll_df['AdjClose']
    }).dropna()
    dates = combined.index
    strategy = [1.0]
    tsla_only = [1.0]
    tsll_only = [1.0]
    w_tsla, w_tsll = 1.0, 0.0
    for i in range(1, len(dates)):
        today = dates[i]
        yday = dates[i-1]
        tsla_ret = combined.loc[today, 'TSLA'] / combined.loc[yday, 'TSLA'] - 1
        tsll_ret = combined.loc[today, 'TSLL'] / combined.loc[yday, 'TSLL'] - 1
        prev = strategy[-1]
        strategy.append(prev * (1 + w_tsla * tsla_ret + w_tsll * tsll_ret))
        tsla_only.append(tsla_only[-1] * (1 + tsla_ret))
        tsll_only.append(tsll_only[-1] * (1 + tsll_ret))
        if today in tsla_df.index:
            row = tsla_df.loc[today]
            w_tsla, w_tsll = decide_allocation(row['RSI'], row['MACD'], row['MACD_signal'], row['MACD_hist'],
                                               row['AdjClose'], row['BB_upper'], row['BB_lower'], row['ATR'])
    return pd.Series(strategy, index=dates), pd.Series(tsla_only, index=dates), pd.Series(tsll_only, index=dates)

def compute_performance_metrics(series):
    rets = series.pct_change().dropna()
    cagr = (series.iloc[-1] / series.iloc[0]) ** (252/len(series)) - 1
    vol = rets.std() * np.sqrt(252)
    sharpe = (rets.mean() / rets.std()) * np.sqrt(252) if rets.std() > 0 else None
    dd = (series / series.cummax() - 1).min()
    return {"CAGR": cagr, "Volatility": vol, "Sharpe": sharpe, "MaxDrawdown": abs(dd)}

def print_performance_table(s, t, l):
    def fmt(x, pct=False): return f"{x*100:.2f}%" if x is not None and pct else f"{x:.2f}"
    table = Table(title="Performance Summary: Dynamic Strategy vs TSLA vs TSLL", title_style="bold cyan")
    table.add_column("Metric")
    table.add_column("Dynamic Strategy")
    table.add_column("TSLA Only")
    table.add_column("TSLL Only")
    for metric in ["CAGR", "Volatility", "Sharpe", "MaxDrawdown"]:
        table.add_row(metric, fmt(s[metric], pct=True), fmt(t[metric], pct=True), fmt(l[metric], pct=True))
    print(table)
