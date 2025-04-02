# core/signal.py
import math

def sigmoid(x):
    return 1 / (1 + math.exp(-x))


def decide_allocation(rsi, macd, macd_signal, macd_hist, price, bb_upper, bb_lower, atr,
                      vix=None, fear_greed=None, interest_rate=None):
    score = 0
    weights = []

    # RSI 기준
    if rsi is not None:
        if rsi < 30:
            score += 1
            weights.append("[RSI] 과매도(+1)")
        elif rsi > 70:
            score -= 1
            weights.append("[RSI] 과매수(-1)")

    # MACD
    if macd is not None and macd_signal is not None:
        if macd > macd_signal:
            score += 1
            weights.append("[MACD] 상승 모멘텀(+1)")
        else:
            score -= 1
            weights.append("[MACD] 하락 모멘텀(-1)")

    # Bollinger Bands
    if price is not None and bb_upper is not None and bb_lower is not None:
        if price < bb_lower:
            score += 1
            weights.append("[Bollinger] 하단 이탈(+1)")
        elif price > bb_upper:
            score -= 1
            weights.append("[Bollinger] 상단 돌파(-1)")

    # ATR 변동성
    if atr is not None and price is not None:
        atr_pct = (atr / price) * 100
        if atr_pct > 5:
            score -= 1
            weights.append(f"[ATR] 변동성 과다({atr_pct:.1f}%) → -1")
        elif atr_pct < 2:
            score += 1
            weights.append(f"[ATR] 변동성 안정({atr_pct:.1f}%) → +1")

    # VIX
    if vix is not None:
        if vix > 25:
            score -= 1
            weights.append(f"[VIX] 공포 수준({vix:.1f}) → -1")
        elif vix < 15:
            score += 1
            weights.append(f"[VIX] 안정 수준({vix:.1f}) → +1")

    # Fear & Greed Index
    if fear_greed is not None:
        if fear_greed >= 70:
            score += 1
            weights.append(f"[FGI] 탐욕({fear_greed}) → +1")
        elif fear_greed <= 30:
            score -= 1
            weights.append(f"[FGI] 공포({fear_greed}) → -1")

    # 금리
    if interest_rate is not None:
        if interest_rate > 4.0:
            score -= 1
            weights.append(f"[금리] 고금리({interest_rate:.2f}%) → -1")
        elif interest_rate < 2.0:
            score += 1
            weights.append(f"[금리] 저금리({interest_rate:.2f}%) → +1")

    # 비중 결정: sigmoid(스코어)
    tsll_weight = sigmoid(score)
    tsla_weight = 1.0 - tsll_weight
    return tsla_weight, tsll_weight


def explain_allocation_reason(rsi, macd, macd_signal, macd_hist, price, bb_upper, bb_lower, atr,
                               w_tsla, w_tsll, vix=None, fear_greed=None, interest_rate=None):
    messages = []

    if rsi is not None:
        if rsi < 30:
            messages.append(f"RSI({rsi:.1f}) → 과매도 상태 → 매수(+1)")
        elif rsi > 70:
            messages.append(f"RSI({rsi:.1f}) → 과매수 상태 → 매도(-1)")
        else:
            messages.append(f"RSI({rsi:.1f}) → 중립")

    if macd is not None and macd_signal is not None:
        if macd > macd_signal:
            messages.append(f"MACD({macd:.2f}) > Signal({macd_signal:.2f}) → 상승 모멘텀(+1)")
        else:
            messages.append(f"MACD({macd:.2f}) <= Signal({macd_signal:.2f}) → 하락 모멘텀(-1)")

    if price is not None and bb_upper is not None and bb_lower is not None:
        if price < bb_lower:
            messages.append(f"가격({price:.2f}) < BB 하단({bb_lower:.2f}) → 반등 기대(+1)")
        elif price > bb_upper:
            messages.append(f"가격({price:.2f}) > BB 상단({bb_upper:.2f}) → 과열 우려(-1)")
        else:
            messages.append("가격이 Bollinger 밴드 내 → 중립")

    if atr is not None and price is not None:
        atr_pct = (atr / price) * 100
        if atr_pct > 5:
            messages.append(f"ATR 변동성 {atr_pct:.1f}% → 과다 변동성(-1)")
        elif atr_pct < 2:
            messages.append(f"ATR 변동성 {atr_pct:.1f}% → 안정된 시장(+1)")

    if vix is not None:
        messages.append(f"VIX = {vix:.1f} → {'공포 (-1)' if vix > 25 else '안정 (+1)' if vix < 15 else '중립'}")

    if fear_greed is not None:
        messages.append(f"Fear & Greed Index = {fear_greed} → {'탐욕 (+1)' if fear_greed >= 70 else '공포 (-1)' if fear_greed <= 30 else '중립'}")

    if interest_rate is not None:
        messages.append(f"미국 10Y 금리 = {interest_rate:.2f}% → {'저금리(+1)' if interest_rate < 2 else '고금리(-1)' if interest_rate > 4 else '중립'}")

    messages.append(f"\n➡ 내일 비중 제안: TSLA {w_tsla*100:.1f}%, TSLL {w_tsll*100:.1f}%")
    return "\n".join(messages)
