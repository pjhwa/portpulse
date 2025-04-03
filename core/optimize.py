# core/optimize.py
import itertools
import pandas as pd
import numpy as np
from tqdm import tqdm
from datetime import datetime
from core.fetch import fetch_price_data, fetch_vix_data, fetch_fear_greed_index
from core.indicators import add_all_indicators
from core.backtest import run_backtest, compute_performance_metrics
from core.signal import custom_decide_allocation_extended
from data.thresholds import save_best_thresholds, get_default_thresholds
from rich import print

def run_optimization_and_save(metric="sharpe", optimization_method="grid"):
    """
    백테스트 기반으로 임계값을 최적화하고 결과를 저장하는 함수

    Parameters:
    - metric (str): 최적화 기준 지표 ("sharpe", "cagr", "mdd" 등)
    - optimization_method (str): 최적화 방법 ("grid" 또는 "bayesian")
    """
    print("\n[bold cyan]🧠 백테스트 기반 임계값 최적화 실행 중...[/bold cyan]")

    # 데이터 로드
    tsla_df, tsll_df = fetch_price_data()
    tsla_df = add_all_indicators(tsla_df)
    vix_df = fetch_vix_data()
    fear_greed = fetch_fear_greed_index()

    # 임계값 범위 설정 (Grid Search용)
    rsi_daily_lows = [20, 25, 30, 35]
    rsi_daily_highs = [60, 65, 70, 75]
    atr_lows = [1.0, 1.5, 2.0]
    atr_highs = [4.0, 5.0, 6.0]
    bb_width_lows = [0.03, 0.05, 0.07]
    bb_width_highs = [0.10, 0.15, 0.20]

    # 검색 공간 생성
    search_space = list(itertools.product(rsi_daily_lows, rsi_daily_highs, atr_lows, atr_highs, bb_width_lows, bb_width_highs))

    best_config = None
    best_value = float('-inf')
    best_metrics = None

    # Grid Search 실행
    default_thresholds = get_default_thresholds()  # Load default thresholds
    for params in tqdm(search_space, desc="Grid Search 진행 중"):
        rsi_lo, rsi_hi, atr_lo, atr_hi, bb_lo, bb_hi = params
        thresholds = default_thresholds.copy()  # Start with default thresholds
        thresholds.update({
            'rsi_daily_low': rsi_lo,
            'rsi_daily_high': rsi_hi,
            'atr_low': atr_lo,
            'atr_high': atr_hi,
            'bb_width_low': bb_lo,
            'bb_width_high': bb_hi,
        })

        def allocation_fn(today):
            today = today.copy()  # Create a copy to avoid SettingWithCopyWarning
            vix_val = vix_df.get(today.name, None)
            fear_greed_val = fear_greed.get(today.name, None)
            today['fear_greed'] = fear_greed_val
            return custom_decide_allocation_extended(today, thresholds)

        strat_vals, _, _ = run_backtest(tsla_df, tsll_df, allocation_fn=allocation_fn)
        metrics = compute_performance_metrics(strat_vals)

        # 선택된 메트릭에 따라 점수 계산
        score = {
            "sharpe": metrics["Sharpe"],
            "cagr": metrics["CAGR"],
            "mdd": -metrics["MaxDrawdown"]
        }.get(metric, metrics["Sharpe"])

        if score > best_value:
            best_value = score
            best_config = thresholds.copy()
            best_config.update({"metric": metric, "score": score})
            best_metrics = metrics

    # 최적화 결과 출력 및 저장
    if best_config:
        print("\n[bold green]✅ 최적화 완료![/bold green]")
        for k, v in best_config.items():
            print(f" - {k}: {v}")
        save_best_thresholds(best_config)
    else:
        print("[red]❌ 최적화 실패: 유효한 설정을 찾지 못했습니다.[/red]")

# Bayesian Optimization 예시 (선택적)
from skopt import gp_minimize

def bayesian_optimize(metric="sharpe"):
    """
    Bayesian Optimization을 사용한 임계값 최적화 함수

    Parameters:
    - metric (str): 최적화 기준 지표

    Returns:
    - dict: 최적화된 임계값
    """
    def objective(params):
        thresholds = {
            'rsi_daily_low': params[0],
            'rsi_daily_high': params[1],
            'atr_low': params[2],
            'atr_high': params[3],
            'bb_width_low': params[4],
            'bb_width_high': params[5],
        }
        strat_vals, _, _ = run_backtest(tsla_df, tsll_df, lambda x: custom_decide_allocation_extended(x, thresholds))
        metrics = compute_performance_metrics(strat_vals)
        return -metrics[metric]  # 최소화 문제로 변환

    # 검색 공간 정의
    space = [(20, 35), (60, 75), (1.0, 2.0), (4.0, 6.0), (0.03, 0.07), (0.10, 0.20)]
    res = gp_minimize(objective, space, n_calls=50)
    best_thresholds = {
        'rsi_daily_low': res.x[0],
        'rsi_daily_high': res.x[1],
        'atr_low': res.x[2],
        'atr_high': res.x[3],
        'bb_width_low': res.x[4],
        'bb_width_high': res.x[5],
    }
    return best_thresholds

if __name__ == "__main__":
    run_optimization_and_save(metric="sharpe", optimization_method="grid")
