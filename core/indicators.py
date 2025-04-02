# indicators.py
import pandas as pd

def compute_RSI(series, period=14):
    """
    상대강도지수(RSI)를 계산합니다.

    Parameters:
    - series: 가격 시계열 (종가 또는 조정 종가)
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
    df.index = pd.to_datetime(df.index)
    high_low = df['high'] - df['low']
    high_close = (df['high'] - df['close'].shift()).abs()
    low_close = (df['low'] - df['close'].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return atr

def add_technical_indicators(df):
    df = df.copy()
    df.index = pd.to_datetime(df.index)
    df.columns = [col.lower() for col in df.columns]  # ✅ 컬럼명 통일

    # 👉 ATR 계산을 위한 Close 컬럼 보완
    if "close" not in df.columns and "adjclose" in df.columns:
        df["close"] = df["adjclose"]

    # adjclose 컬럼이 DataFrame일 가능성 대비 처리
    if 'adjclose' in df.columns:
        # 인덱스를 datetime 형식으로 변환 및 정렬
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()

        adj_series = df['adjclose']
        if not isinstance(adj_series, pd.Series):
            adj_series = adj_series.iloc[:, 0]
        df['rsi'] = compute_RSI(adj_series)
        macd, signal, hist = compute_MACD(adj_series)
        df['macd'] = macd
        df['macd_signal'] = signal
        df['macd_hist'] = hist
        upper, lower = compute_Bollinger_Bands(adj_series)
        df['bb_upper'] = upper
        df['bb_lower'] = lower

        # compute_ATR에 사용할 컬럼 소문자로 변환 보장
        df.columns = [col.lower() for col in df.columns]

        df.index = pd.to_datetime(df.index)

        # 인덱스가 문자열이면 datetime으로 변환
        if df.index.dtype == 'object':
            try:
                df.index = pd.to_datetime(df.index)
            except Exception as e:
                print("[경고] DataFrame 인덱스 datetime 변환 실패:", e)

            for col in ['high', 'low', 'close']:
                if col in df.columns:
                    col_data = df[col]
                    # DataFrame이면 첫 번째 컬럼만 사용
                    if isinstance(col_data, pd.DataFrame):
                        col_data = col_data.iloc[:, 0]
                    # Series가 아닌 경우 강제로 변환
                    elif not isinstance(col_data, pd.Series):
                        col_data = pd.Series(col_data, index=df.index)

                    col_data = pd.to_numeric(col_data, errors='coerce')
                    df[col] = col_data

                    # Shift 후에도 Series인지 확인
                    if col == 'close':
                        shifted = col_data.shift()
                        if not isinstance(shifted, pd.Series):
                            shifted = pd.Series(shifted, index=df.index)
                        df['close_shifted'] = shifted  # 임시 컬럼으로 저장

        # ATR 계산 전에 필요한 열이 존재하는지 확인
        required_cols = ['high', 'low', 'close']
        if all(col in df.columns for col in required_cols):
            df['atr'] = compute_ATR(df)
        else:
            raise KeyError(f"ATR 계산에 필요한 컬럼이 없습니다: {required_cols}")
    else:
        raise KeyError("'adjclose' 컬럼이 존재하지 않습니다.")

    return df
