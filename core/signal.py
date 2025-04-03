# core/signal.py
import pandas as pd
import numpy as np

# 기본 임계값 설정 (flat dictionary)
DEFAULT_THRESHOLDS = {
    'rsi_daily_low': 30,
    'rsi_daily_mid': 40,
    'rsi_daily_high': 70,
    'rsi_weekly_low': 30,
    'rsi_weekly_high': 70,
    'rsi_short_low': 20,
    'rsi_short_high': 80,
    'sma5_sma50_cross': 0,
    'macd_hist_positive': 0,
    'macd_short_hist_positive': 0,
    'bb_width_low': 0.05,
    'bb_width_high': 0.15,
    'atr_low': 1.5,
    'atr_high': 5.0,
    'stoch_k_low': 20,
    'stoch_k_high': 80,
    'fear_greed_low': 20,
    'fear_greed_high': 80,
}

def compute_signal(indicator_value, thresholds, indicator_type):
    """
    지표 값과 임계값을 기반으로 매수/매도 신호를 계산합니다.
    반환 값: 2 (강한 매수), 1 (약한 매수), 0 (중립), -1 (약한 매도), -2 (강한 매도)

    Parameters:
    - indicator_value: 지표의 현재 값
    - thresholds: 지표별 임계값 딕셔너리
    - indicator_type: 지표 유형 (예: 'rsi', 'sma_cross')
    """
    # If the indicator value is missing, return a neutral signal
    if indicator_value is None:
        return 0

    if indicator_type == 'rsi':
        if indicator_value < thresholds['low']:
            return 2  # 강한 매수
        elif 'mid' in thresholds and indicator_value < thresholds['mid']:
            return 1  # 약한 매수
        elif indicator_value > thresholds['high']:
            return -2  # 강한 매도
        elif 'mid' in thresholds and indicator_value > thresholds['mid']:
            return -1  # 약한 매도
        else:
            return 0  # 중립
    elif indicator_type == 'sma_cross':
        if indicator_value > 0:
            return 1  # 매수
        elif indicator_value < 0:
            return -1  # 매도
        else:
            return 0  # 중립
    elif indicator_type == 'macd_hist':
        if indicator_value > 0:
            return 1  # 매수
        else:
            return -1  # 매도
    elif indicator_type == 'bb_width':
        if indicator_value < thresholds['low']:
            return 1  # 낮은 변동성, 매수
        elif indicator_value > thresholds['high']:
            return -1  # 높은 변동성, 매도
        else:
            return 0  # 중립
    elif indicator_type == 'atr':
        atr_pct = indicator_value / thresholds['price']
        if atr_pct < thresholds['low']:
            return 1  # 낮은 변동성, 매수
        elif atr_pct > thresholds['high']:
            return -1  # 높은 변동성, 매도
        else:
            return 0  # 중립
    elif indicator_type == 'stoch_k':
        if indicator_value < thresholds['low']:
            return 2  # 강한 매수
        elif indicator_value > thresholds['high']:
            return -2  # 강한 매도
        else:
            return 0  # 중립
    elif indicator_type == 'fear_greed':
        if indicator_value < thresholds['low']:
            return 2  # 공포 상태, 강한 매수
        elif indicator_value > thresholds['high']:
            return -2  # 탐욕 상태, 강한 매도
        else:
            return 0  # 중립
    else:
        return 0  # 알 수 없는 지표 유형, 중립

def custom_decide_allocation_extended(df_row, thresholds, indicator_weights=None):
    """
    여러 지표와 임계값을 기반으로 배분을 결정합니다.

    Parameters:
    - df_row: 현재 날짜의 데이터가 포함된 pandas Series
    - thresholds: 각 지표의 임계값 딕셔너리 (flat)
    - indicator_weights: 각 지표의 가중치 딕셔너리 (기본값: 모든 지표 동일 가중치)

    Returns:
    - w_tsla: TSLA의 배분 비율
    - w_tsll: TSLL의 배분 비율
    """
    if indicator_weights is None:
        indicator_weights = {
            'rsi_daily': 1.0,
            'rsi_weekly': 1.0,
            'rsi_short': 1.0,
            'sma5_sma50_cross': 1.0,
            'macd_hist': 1.0,
            'macd_short_hist': 1.0,
            'bb_width': 1.0,
            'atr': 1.0,
            'stoch_k': 1.0,
            'fear_greed': 1.0,
        }

    score = 0.0

    # RSI 일봉
    rsi_daily_signal = compute_signal(df_row['rsi_daily'], {
        'low': thresholds['rsi_daily_low'],
        'mid': thresholds['rsi_daily_mid'],
        'high': thresholds['rsi_daily_high']
    }, 'rsi')
    score += indicator_weights['rsi_daily'] * rsi_daily_signal

    # RSI 주봉
    rsi_weekly_signal = compute_signal(df_row['rsi_weekly'], {
        'low': thresholds['rsi_weekly_low'],
        'high': thresholds['rsi_weekly_high']
    }, 'rsi')
    score += indicator_weights['rsi_weekly'] * rsi_weekly_signal

    # 단기 RSI
    rsi_short_signal = compute_signal(df_row['rsi_short'], {
        'low': thresholds['rsi_short_low'],
        'high': thresholds['rsi_short_high']
    }, 'rsi')
    score += indicator_weights['rsi_short'] * rsi_short_signal

    # SMA 교차
    sma_cross_signal = 1 if df_row['sma5'] > df_row['sma50'] else -1 if df_row['sma5'] < df_row['sma50'] else 0
    score += indicator_weights['sma5_sma50_cross'] * sma_cross_signal

    # MACD 히스토그램
    macd_hist_signal = 1 if df_row['macd_hist'] > 0 else -1
    score += indicator_weights['macd_hist'] * macd_hist_signal

    # 단기 MACD 히스토그램
    macd_short_hist_signal = 1 if df_row['macd_hist_short'] > 0 else -1
    score += indicator_weights['macd_short_hist'] * macd_short_hist_signal

    # 볼린저 밴드 폭
    bb_width_signal = compute_signal(df_row['bb_width'], {
        'low': thresholds['bb_width_low'],
        'high': thresholds['bb_width_high']
    }, 'bb_width')
    score += indicator_weights['bb_width'] * bb_width_signal

    # ATR
    atr_signal = compute_signal(df_row['atr'], {
        'low': thresholds['atr_low'],
        'high': thresholds['atr_high'],
        'price': df_row['adjclose']
    }, 'atr')
    score += indicator_weights['atr'] * atr_signal

    # 스토캐스틱 오실레이터
    stoch_k_signal = compute_signal(df_row['stoch_k'], {
        'low': thresholds['stoch_k_low'],
        'high': thresholds['stoch_k_high']
    }, 'stoch_k')
    score += indicator_weights['stoch_k'] * stoch_k_signal

    # 공포-탐욕 지수
    if 'fear_greed' in df_row:
        fear_greed_signal = compute_signal(df_row['fear_greed'], {
            'low': thresholds['fear_greed_low'],
            'high': thresholds['fear_greed_high']
        }, 'fear_greed')
        score += indicator_weights['fear_greed'] * fear_greed_signal

    # 점수 정규화 및 배분 비율 계산
    max_score = sum(indicator_weights.values()) * 2  # 최대 신호값이 2라고 가정
    min_score = -max_score
    normalized_score = (score - min_score) / (max_score - min_score)
    w_tsll = max(0.0, min(normalized_score, 1.0))
    w_tsla = 1.0 - w_tsll

    return w_tsla, w_tsll

def explain_allocation_reason(df_row, w_tsla, w_tsll, thresholds):
    """
    배분 결정 이유를 설명합니다.

    Parameters:
    - df_row: 현재 날짜의 데이터가 포함된 pandas Series
    - w_tsla: TSLA의 배분 비율
    - w_tsll: TSLL의 배분 비율
    - thresholds: 각 지표의 임계값 딕셔너리 (flat)

    Returns:
    - 설명 문자열
    """
    lines = []

    # RSI 일봉 설명
    if df_row['rsi_daily'] < thresholds['rsi_daily_low']:
        lines.append(f"RSI Daily ({df_row['rsi_daily']:.1f}) < {thresholds['rsi_daily_low']} → 강한 매수")
    elif df_row['rsi_daily'] < thresholds['rsi_daily_mid']:
        lines.append(f"RSI Daily ({df_row['rsi_daily']:.1f}) < {thresholds['rsi_daily_mid']} → 약한 매수")
    elif df_row['rsi_daily'] > thresholds['rsi_daily_high']:
        lines.append(f"RSI Daily ({df_row['rsi_daily']:.1f}) > {thresholds['rsi_daily_high']} → 강한 매도")
    elif df_row['rsi_daily'] > thresholds['rsi_daily_mid']:
        lines.append(f"RSI Daily ({df_row['rsi_daily']:.1f}) > {thresholds['rsi_daily_mid']} → 약한 매도")

    # 추가 지표에 대한 설명은 필요 시 확장 가능
    lines.append(f"\n➡ 제안된 배분: TSLA {w_tsla*100:.1f}%, TSLL {w_tsll*100:.1f}%")
    return "\n".join(lines)

# 예제 실행
if __name__ == "__main__":
    # 샘플 데이터 (실제 데이터로 대체 필요)
    sample_row = pd.Series({
        'rsi_daily': 25,
        'rsi_weekly': 35,
        'rsi_short': 15,
        'sma5': 100,
        'sma50': 95,
        'macd_hist': 0.5,
        'macd_hist_short': 0.2,
        'bb_width': 0.04,
        'atr': 1.2,
        'stoch_k': 18,
        'fear_greed': 15,
        'adjclose': 100.0
    })

    thresholds = DEFAULT_THRESHOLDS
    w_tsla, w_tsll = custom_decide_allocation_extended(sample_row, thresholds)
    explanation = explain_allocation_reason(sample_row, w_tsla, w_tsll, thresholds)
    print(explanation)
