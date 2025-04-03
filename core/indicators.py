# core/indicators.py
import pandas as pd

def compute_RSI(series, period=14):
    """
    상대강도지수(RSI)를 계산합니다.

    Parameters:
    - series: 주가 시계열 (종가 또는 조정 종가)
    - period: 계산 기간 (기본값: 14)

    Returns:
    - RSI 시리즈 (0~100 범위)
    """
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def compute_MACD(series, short=12, long=26, signal=9):
    """
    MACD, 시그널선, 히스토그램 계산
    """
    ema_short = series.ewm(span=short, adjust=False).mean()
    ema_long = series.ewm(span=long, adjust=False).mean()
    macd = ema_short - ema_long
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    hist = macd - signal_line
    return macd, signal_line, hist

def compute_Bollinger_Bands(series, period=20, num_std=2):
    """
    볼린저 밴드 상단/하단 계산
    """
    ma = series.rolling(window=period).mean()
    std = series.rolling(window=period).std()
    upper = ma + num_std * std
    lower = ma - num_std * std
    return upper, lower

def compute_ATR(df, period=14):
    """
    평균 진폭(ATR)을 계산합니다.

    Parameters:
    - df: 시세 데이터프레임 (High, Low, Close 포함)
    - period: 계산 기간 (기본값: 14)

    Returns:
    - ATR 시리즈
    """
    high_low = df['high'] - df['low']
    high_close = (df['high'] - df['close'].shift()).abs()
    low_close = (df['low'] - df['close'].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return atr

def add_technical_indicators(df):
    df = df.copy()

    # 👉 ATR 계산을 위한 Close 컬럼 보완
    if "Close" not in df.columns and "AdjClose" in df.columns:
        df["Close"] = df["AdjClose"]

    df['RSI'] = compute_RSI(df['AdjClose'])
    macd, signal, hist = compute_MACD(df['AdjClose'])
    df['MACD'] = macd
    df['MACD_signal'] = signal
    df['MACD_hist'] = hist
    upper, lower = compute_Bollinger_Bands(df['AdjClose'])
    df['BB_upper'] = upper
    df['BB_lower'] = lower
    df['ATR'] = compute_ATR(df)
    return df
