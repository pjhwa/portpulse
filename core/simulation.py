# core/simulation.py
import pandas as pd
from datetime import datetime
from core.fetch import fetch_price_data, fetch_vix_data, fetch_fear_greed_index
from core.indicators import add_all_indicators
from core.backtest import run_backtest, compute_performance_metrics
from core.signal import custom_decide_allocation_extended
from data.thresholds import load_latest_thresholds, get_default_thresholds
from rich.table import Table
from rich.console import Console

console = Console()

def simulate_with_saved_thresholds(start, end):
    """저장된 최적화된 임계값을 사용하여 시뮬레이션을 실행합니다."""
    thresholds = load_latest_thresholds()
    if thresholds is None:
        thresholds = get_default_thresholds()

    tsla_df, tsll_df = fetch_price_data(start=start.isoformat(), end=end.isoformat())
    tsla_df = add_all_indicators(tsla_df)
    vix_df = fetch_vix_data()
    fear_greed_val = fetch_fear_greed_index()  # 시뮬레이션 시작 전에 한 번만 가져옴

    daily_records = []

    def allocation_fn(today):
        vix_val = vix_df.get(today.name, None)
        # Use .loc to assign directly to tsla_df
        tsla_df.loc[today.name, 'fear_greed'] = fear_greed_val if fear_greed_val is not None else 50
        today_with_fear_greed = tsla_df.loc[today.name]  # Get updated Series
        w_tsla, w_tsll = custom_decide_allocation_extended(today_with_fear_greed, thresholds)
        score = compute_signal_score(today_with_fear_greed, thresholds)
        daily_records.append({
            'date': today.name,
            'w_tsla': w_tsla,
            'w_tsll': w_tsll,
            'score': score
        })
        return w_tsla, w_tsll

    strat_vals, _, _ = run_backtest(tsla_df, tsll_df, allocation_fn=allocation_fn)
    perf = compute_performance_metrics(strat_vals)
    perf["Final Value"] = strat_vals.iloc[-1] if not strat_vals.empty else 0.0
    pd.DataFrame(daily_records).to_csv(f"simulation_{start}_{end}.csv")
    return strat_vals, perf

def simulate_with_default_thresholds(start, end):
    """기본 임계값을 사용하여 시뮬레이션을 실행합니다."""
    thresholds = get_default_thresholds()
    tsla_df, tsll_df = fetch_price_data(start=start.isoformat(), end=end.isoformat())
    tsla_df = add_all_indicators(tsla_df)
    vix_df = fetch_vix_data()
    fear_greed_val = fetch_fear_greed_index()  # 시뮬레이션 시작 전에 한 번만 가져옴

    daily_records = []

    def allocation_fn(today):
        vix_val = vix_df.get(today.name, None)
        # Use .loc to assign directly to tsla_df
        tsla_df.loc[today.name, 'fear_greed'] = fear_greed_val if fear_greed_val is not None else 50
        today_with_fear_greed = tsla_df.loc[today.name]  # Get updated Series
        w_tsla, w_tsll = custom_decide_allocation_extended(today_with_fear_greed, thresholds)
        score = compute_signal_score(today_with_fear_greed, thresholds)
        daily_records.append({
            'date': today.name,
            'w_tsla': w_tsla,
            'w_tsll': w_tsll,
            'score': score
        })
        return w_tsla, w_tsll

    strat_vals, _, _ = run_backtest(tsla_df, tsll_df, allocation_fn=allocation_fn)
    perf = compute_performance_metrics(strat_vals)
    perf["Final Value"] = strat_vals.iloc[-1] if not strat_vals.empty else 0.0
    pd.DataFrame(daily_records).to_csv(f"simulation_default_{start}_{end}.csv")
    return strat_vals, perf

def compute_signal_score(df_row, thresholds):
    """신호 점수를 계산하는 함수"""
    score = 0
    # RSI 신호 (thresholds가 flat dictionary이므로 키를 직접 사용)
    if df_row['rsi_daily'] < thresholds['rsi_daily_low']:
        score += 2
    elif df_row['rsi_daily'] > thresholds['rsi_daily_high']:
        score -= 2
    # 추가 지표에 대한 신호 점수 계산 필요 시 확장
    return score

def run_simulation_mode(start, end, thresholds):
    """시뮬레이션 모드를 실행하고 결과를 출력합니다."""
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

    initial_value = 100.0  # 초기 투자 금액
    opt_return = (perf_opt['Final Value'] / initial_value - 1) * 100
    def_return = (perf_def['Final Value'] / initial_value - 1) * 100
    console.print(f"\n[bold green]Optimized 수익률: {opt_return:.2f}%[/bold green]")
    console.print(f"[bold yellow]Default 수익률: {def_return:.2f}%[/bold yellow]")

if __name__ == "__main__":
    start_date = datetime(2024, 9, 1).date()
    end_date = datetime(2025, 3, 31).date()
    run_simulation_mode(start_date, end_date)
