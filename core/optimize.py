# core/optimize.py
import itertools
import multiprocessing
from tqdm import tqdm
from utils import normalize_adjclose
from core.fetch import fetch_price_data, fetch_vix_data, fetch_fear_greed_index
from core.indicators import add_all_indicators
from core.backtest import run_backtest, compute_performance_metrics
from core.signal import custom_decide_allocation_extended
from data.db import save_best_thresholds
from data.thresholds import get_default_thresholds
from rich import print

def backtest_worker(params, tsla_df, tsll_df, vix_df, fear_greed, default_thresholds, metric_key, min_return):
    """
    멀티프로세스에서 실행할 백테스트 작업 함수

    Parameters:
    - params: 임계값 조합 (rsi_lo, rsi_hi, atr_lo, atr_hi, bb_lo, bb_hi)
    - tsla_df, tsll_df: 주가 데이터프레임
    - vix_df, fear_greed: 시장 지표 데이터
    - default_thresholds: 기본 임계값 딕셔너리
    - metric_key: 최적화 기준 메트릭 (Sharpe, CAGR, MaxDrawdown)
    - min_return: 최소 누적 수익률

    Returns:
    - (thresholds, metrics, score) 또는 None (조건 미달 시)
    """
    rsi_lo, rsi_hi, atr_lo, atr_hi, bb_lo, bb_hi = params
    thresholds = default_thresholds.copy()
    thresholds.update({
        'rsi_daily_low': rsi_lo,
        'rsi_daily_high': rsi_hi,
        'atr_low': atr_lo,
        'atr_high': atr_hi,
        'bb_width_low': bb_lo,
        'bb_width_high': bb_hi,
    })

    def allocation_fn(today):
        today = today.copy()
        vix_val = vix_df.get(today.name, None)
        fear_greed_val = fear_greed.get(today.name, None)
        today['fear_greed'] = fear_greed_val
        return custom_decide_allocation_extended(today, thresholds)

    strat_vals, _, _ = run_backtest(tsla_df, tsll_df, allocation_fn=allocation_fn)
    metrics = compute_performance_metrics(strat_vals)

    # 메트릭에 따라 점수 계산
    if metric_key in ["Sharpe", "CAGR"]:
        score = metrics[metric_key]
    else:  # MaxDrawdown
        score = -metrics[metric_key]

    # 최소 수익률 조건 확인
    if metrics["CumulativeReturn"] >= min_return:
        return (thresholds, metrics, score)
    return None

def run_optimization_and_save(metric="sharpe", min_return=0.0):
    print("\n[bold cyan]🧠 백테스트 기반 임계값 최적화 실행 중...[/bold cyan]")

    # 데이터 로드
    tsla_df, tsll_df = fetch_price_data(start="2020-01-01")  # 5년 데이터로 확장
    tsla_df = normalize_adjclose(tsla_df)
    tsll_df = normalize_adjclose(tsll_df)
    tsla_df = add_all_indicators(tsla_df)
    vix_df = fetch_vix_data()
    fear_greed = fetch_fear_greed_index()

    # 초기 임계값 범위
    rsi_daily_lows = [10, 15, 20, 25, 30, 35, 40]
    rsi_daily_highs = [50, 55, 60, 65, 70, 75, 80]
    atr_lows = [0.5, 1.0, 1.5, 2.0, 2.5]
    atr_highs = [3.0, 4.0, 5.0, 6.0, 7.0]
    bb_width_lows = [0.01, 0.03, 0.05, 0.07, 0.09]
    bb_width_highs = [0.10, 0.15, 0.20, 0.25, 0.30]

    default_thresholds = get_default_thresholds()
    search_space = list(itertools.product(rsi_daily_lows, rsi_daily_highs, atr_lows, atr_highs, bb_width_lows, bb_width_highs))

    # Define the metric key mapping
    metric_key_map = {
        "sharpe": "Sharpe",
        "cagr": "CAGR",
        "mdd": "MaxDrawdown"
    }

    # Validate the metric
    if metric.lower() not in metric_key_map:
        raise ValueError(f"Invalid metric: {metric}. Allowed metrics are {list(metric_key_map.keys())}")
    metric_key = metric_key_map[metric.lower()]

    # args_list 생성: 모든 인자를 포함
    args_list = [
        (params, tsla_df, tsll_df, vix_df, fear_greed, default_thresholds, metric_key, min_return)
        for params in search_space
    ]

    # 멀티프로세스 설정
    num_processes = max(1, multiprocessing.cpu_count() // 2)  # CPU 코어 수의 절반 사용

    # 병렬 처리 및 진행률 바 적용
    with multiprocessing.Pool(processes=num_processes) as pool:
        results = []
        # imap_unordered를 tqdm으로 감싸고, 진행률을 실시간으로 표시
        for result in tqdm(pool.starmap(backtest_worker, args_list),
                          total=len(args_list),
                          desc="Grid Search 진행 중"):
            results.append(result)

    # None 결과 필터링 및 상위 결과 추출
    valid_results = [res for res in results if res is not None]
    if valid_results:
        best_result = max(valid_results, key=lambda x: x[2])  # x[2]는 score
        best_config, best_metrics, best_value = best_result

        # 상위 5개 전략 저장
        top_strategies = sorted(valid_results, key=lambda x: x[2], reverse=True)[:5]
    else:
        best_config = None
        best_metrics = None
        best_value = float('-inf')

    # 누적 수익률이 음수일 경우 재탐색
    if not best_config or best_metrics["CumulativeReturn"] < min_return:
        print("[yellow]⚠ 누적 수익률이 최소 기준 미달입니다. 임계값 범위를 확장하여 재탐색합니다.[/yellow]")
        rsi_daily_lows = [5, 10, 15, 20, 25, 30, 35, 40, 45]  # 확장된 범위
        rsi_daily_highs = [45, 50, 55, 60, 65, 70, 75, 80, 85]
        atr_lows = [0.3, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
        atr_highs = [3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0]
        bb_width_lows = [0.005, 0.01, 0.03, 0.05, 0.07, 0.09, 0.11]
        bb_width_highs = [0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40]

        search_space = list(itertools.product(rsi_daily_lows, rsi_daily_highs, atr_lows, atr_highs, bb_width_lows, bb_width_highs))
        args_list = [
            (params, tsla_df, tsll_df, vix_df, fear_greed, default_thresholds, metric_key, min_return)
            for params in search_space
        ]

        with multiprocessing.Pool(processes=num_processes) as pool:
            results = []
            # imap_unordered를 tqdm으로 감싸고, 진행률을 실시간으로 표시
            for result in tqdm(pool.starmap(backtest_worker, args_list),
                              total=len(args_list),
                              desc="재탐색 진행 중"):
                results.append(result)

        valid_results = [res for res in results if res is not None]
        if valid_results:
            best_result = max(valid_results, key=lambda x: x[2])
            best_config, best_metrics, best_value = best_result
            top_strategies = sorted(valid_results, key=lambda x: x[2], reverse=True)[:5]

    # 결과 출력
    if best_config:
        print("\n[bold green]✅ 최적화 완료![/bold green]")
        for k, v in best_config.items():
            if k not in ['metric', 'score', 'cagr', 'cumulative_return', 'max_return']:
                print(f" - {k}: {v}")
        print(f" - Metric: {metric}")
        print(f" - Score: {best_value:.2f}")
        print(f" - CAGR: {best_metrics['CAGR']*100:.2f}%")
        print(f" - 누적 수익률: {best_metrics['CumulativeReturn']*100:.2f}%")
        print(f" - 최대 수익률: {best_metrics['MaxReturn']*100:.2f}%")
        save_best_thresholds(best_config, db_path="data/portpulse.db")

        print("\n[bold cyan]📊 상위 5개 전략[/bold cyan]")
        for i, (thresholds, metrics) in enumerate(top_strategies):
            print(f"전략 {i+1}:")
            print(f" - RSI Daily Low: {thresholds['rsi_daily_low']}, High: {thresholds['rsi_daily_high']}")
            print(f" - ATR Low: {thresholds['atr_low']}, High: {thresholds['atr_high']}")
            print(f" - BB Width Low: {thresholds['bb_width_low']}, High: {thresholds['bb_width_high']}")
            print(f" - {metric_key}: {metrics[metric_key]:.2f}")
            print(f" - CAGR: {metrics['CAGR']*100:.2f}%")
            print(f" - 누적 수익률: {metrics['CumulativeReturn']*100:.2f}%")
    else:
        print("[red]❌ 최적화 실패: 유효한 설정을 찾지 못했습니다.[/red]")

if __name__ == "__main__":
    run_optimization_and_save(metric="sharpe", min_return=0.05)
