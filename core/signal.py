# core/signal.py
import pandas as pd
import numpy as np

def decide_allocation(rsi, macd, signal, hist, price, bb_upper, bb_lower, atr,
                      vix=None, fear_greed=None, interest_rate=None):
    """
    다양한 기술 및 시장 지표를 기반으로 TSLA/TSLL 포트폴리오 비중을 결정합니다.
    """
    weights = {
        "rsi": 1.0,
        "macd": 1.0,
        "bollinger": 1.0,
        "atr": 1.0,
        "vix": 1.0,
        "interest": 1.0,
        "sentiment": 1.0
    }

    score = 0.0

    # RSI
    if rsi < 30:
        score += weights["rsi"]
    elif rsi > 70:
        score -= weights["rsi"]

    # MACD
    if macd > signal:
        score += weights["macd"]
    else:
        score -= weights["macd"]

    # Bollinger Bands
    if price < bb_lower:
        score += weights["bollinger"]
    elif price > bb_upper:
        score -= weights["bollinger"]

    # ATR
    if atr > 0.05 * price:
        score -= weights["atr"]

    # VIX
    if vix and vix > 25:
        score -= weights["vix"]

    # ✅ 금리 → Series가 아닌 단일 float 값으로 비교
    if interest_rate is not None:
        if isinstance(interest_rate, pd.Series):
            interest_rate = interest_rate.iloc[-1]

        if interest_rate > 4.0:
            score -= weights["interest"]

    # Fear & Greed
    if fear_greed:
        if fear_greed > 60:
            score += weights["sentiment"]
        elif fear_greed < 40:
            score -= weights["sentiment"]

    # Normalize to [-4, 4] then apply sigmoid scaling
    score = max(min(score, 4), -4)
    tsll_weight = 1 / (1 + np.exp(-score))  # sigmoid: (-∞, ∞) → (0, 1)
    tsla_weight = 1 - tsll_weight

    return tsla_weight, tsll_weight

def explain_allocation_reason(rsi, macd, signal, hist, price, bb_upper, bb_lower, atr,
                               w_tsla, w_tsll, vix=None, fear_greed=None, interest_rate=None):
    """
    포트폴리오 비중 결정에 대한 상세한 해석을 텍스트로 반환합니다.
    """
    lines = []

    if rsi < 30:
        lines.append(f"RSI({rsi:.1f})는 과매도 → 매수(+1)")
    elif rsi > 70:
        lines.append(f"RSI({rsi:.1f})는 과매수 → 매도(-1)")
    else:
        lines.append(f"RSI({rsi:.1f})는 중립")

    if macd > signal:
        lines.append(f"MACD({macd:.2f}) > Signal({signal:.2f}) → 상승 모멘텀(+1)")
    else:
        lines.append(f"MACD({macd:.2f}) ≤ Signal({signal:.2f}) → 하락 모멘텀(-1)")

    if price < bb_lower:
        lines.append("주가가 Bollinger 밴드 하단 이하 → 반등 기대(+1)")
    elif price > bb_upper:
        lines.append("주가가 Bollinger 밴드 상단 이상 → 과열 우려(-1)")
    else:
        lines.append("주가가 Bollinger 밴드 내 중립 영역에 있음")

    if atr > 0.05 * price:
        lines.append(f"ATR 변동성({atr:.2f}) 높음 → 리스크 회피(-1)")
    else:
        lines.append(f"ATR({atr:.2f}) 안정적")

    if vix:
        if vix > 25:
            lines.append(f"VIX({vix:.1f}) 높음 → 시장 불안(-1)")
        else:
            lines.append(f"VIX({vix:.1f}) 안정적")

    if interest_rate is not None:
        if isinstance(interest_rate, pd.Series):
            interest_rate = interest_rate.iloc[-1]

        if interest_rate > 4.0:
            lines.append(f"금리({interest_rate:.1f}%) 높음 → 보수적 접근(-1)")
        else:
            lines.append(f"금리({interest_rate:.1f}%) 양호")

    if fear_greed:
        if fear_greed > 60:
            lines.append(f"Fear & Greed Index({fear_greed}) 탐욕 구간 → 매수(+1)")
        elif fear_greed < 40:
            lines.append(f"Fear & Greed Index({fear_greed}) 공포 구간 → 매도(-1)")
        else:
            lines.append(f"Fear & Greed Index({fear_greed}) 중립")

    lines.append(f"\n➡ 제안 비중: TSLA {w_tsla*100:.1f}%, TSLL {w_tsll*100:.1f}%")
    return "\n".join(lines)
