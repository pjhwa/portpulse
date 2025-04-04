# core/backtest.py
import pandas as pd
import numpy as np
from rich.console import Console
from rich.table import Table

def run_backtest(tsla_df, tsll_df, allocation_fn=None):
    """
    백테스트를 수행하여 전략 수익률, TSLA 단독 보유, TSLL 단독 보유 수익곡선을 반환합니다.

    Parameters:
    - tsla_df: TSLA 주가 데이터프레임
    - tsll_df: TSLL 주가 데이터프레임
    - allocation_fn: 비중 결정 함수 (기본값: None, TSLA 100%)

    Returns:
    - 전략 포트폴리오, TSLA 단독, TSLL 단독의 수익 시리즈
    """
    # 공통 날짜 인덱스 추출
    common_dates = tsla_df.index.intersection(tsll_df.index)
    tsla_df = tsla_df.loc[common_dates]
    tsll_df = tsll_df.loc[common_dates]

    portfolio = []
    tsla_only = []
    tsll_only = []

    for i in range(1, len(common_dates)):
        today = common_dates[i - 1]
        tomorrow = common_dates[i]

        today_data = tsla_df.loc[today]
        tomorrow_data = tsla_df.loc[tomorrow]
        tsll_price_today = tsll_df.loc[today]["close"]  # 소문자 'close'로 변경
        tsll_price_tomorrow = tsll_df.loc[tomorrow]["close"]  # 소문자 'close'로 변경

        if allocation_fn:
            w_tsla, w_tsll = allocation_fn(today_data)
        else:
            w_tsla = 1.0  # 기본: TSLA 100%
            w_tsll = 0.0

        total_return = (
            w_tsla * (tomorrow_data["close"] / today_data["close"]) +  # 소문자 'close'로 변경
            w_tsll * (tsll_price_tomorrow / tsll_price_today)
        )

        if portfolio:
            portfolio.append(portfolio[-1] * total_return)
        else:
            portfolio.append(100.0)  # 초기 자산 100으로 설정

        if tsla_only:
            tsla_only.append(tsla_only[-1] * (tomorrow_data["close"] / today_data["close"]))  # 소문자 'close'로 변경
        else:
            tsla_only.append(100.0)

        if tsll_only:
            tsll_only.append(tsll_only[-1] * (tsll_price_tomorrow / tsll_price_today))
        else:
            tsll_only.append(100.0)

    return (pd.Series(portfolio, index=common_dates[1:]),
            pd.Series(tsla_only, index=common_dates[1:]),
            pd.Series(tsll_only, index=common_dates[1:]))

def compute_performance_metrics(equity_curve):
    """
    수익곡선을 기반으로 성과 지표를 계산합니다.
    - CAGR: 연평균 복리 수익률
    - Volatility: 연간 변동성
    - Sharpe: 샤프 비율
    - MaxDrawdown: 최대 손실률
    - CumulativeReturn: 누적 수익률
    - MaxReturn: 최대 수익률
    """
    returns = equity_curve.pct_change().dropna()
    cagr = (equity_curve.iloc[-1] / equity_curve.iloc[0]) ** (252 / len(equity_curve)) - 1
    volatility = returns.std() * np.sqrt(252)
    sharpe = returns.mean() / returns.std() * np.sqrt(252) if returns.std() != 0 else 0
    drawdown = 1 - equity_curve / equity_curve.cummax()
    max_dd = drawdown.max()
    cumulative_return = (equity_curve.iloc[-1] / equity_curve.iloc[0]) - 1
    max_return = (equity_curve.max() / equity_curve.iloc[0]) - 1

    return {
        "CAGR": cagr,
        "Volatility": volatility,
        "Sharpe": sharpe,
        "MaxDrawdown": max_dd,
        "CumulativeReturn": cumulative_return,
        "MaxReturn": max_return
    }

def print_performance_table(strat_metrics, tsla_metrics, tsll_metrics):
    """
    전략 vs TSLA vs TSLL 성과 비교표를 콘솔에 출력합니다.
    인자:
        strat_metrics (dict): 전략의 성과 지표 딕셔너리
        tsla_metrics (dict): TSLA의 성과 지표 딕셔너리
        tsll_metrics (dict): TSLL의 성과 지표 딕셔너리
    """
    console = Console()
    table = Table(title="Performance Summary: Dynamic Strategy vs TSLA vs TSLL")
    table.add_column("Metric")
    table.add_column("Dynamic Strategy", justify="right")
    table.add_column("TSLA Only", justify="right")
    table.add_column("TSLL Only", justify="right")

    metrics_keys = ["CAGR", "Volatility", "Sharpe", "MaxDrawdown", "CumulativeReturn", "MaxReturn"]
    for key in metrics_keys:
        table.add_row(
            key,
            f"{strat_metrics[key]*100:.2f}%" if key != "Sharpe" else f"{strat_metrics[key]:.2f}",
            f"{tsla_metrics[key]*100:.2f}%" if key != "Sharpe" else f"{tsla_metrics[key]:.2f}",
            f"{tsll_metrics[key]*100:.2f}%" if key != "Sharpe" else f"{tsll_metrics[key]:.2f}"
        )
    console.print(table)
