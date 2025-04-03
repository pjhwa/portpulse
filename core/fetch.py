# core/fetch.py
import yfinance as yf
import pandas as pd
import requests
from data.db import load_prices, save_prices, ensure_db

# DB 초기화 (최초 1회 실행)
ensure_db()

def fetch_price_data(start="2022-07-01", end=None):
    ensure_db()
    tsla = load_prices("TSLA", start)
    tsll = load_prices("TSLL", start)

    if tsla is None:
        tsla = yf.Ticker("TSLA").history(start=start, end=end, auto_adjust=True)
        save_prices(tsla, "TSLA")
    if tsll is None:
        tsll = yf.Ticker("TSLL").history(start=start, end=end, auto_adjust=True)
        save_prices(tsll, "TSLL")

    # 열 이름 표준화
    for df in [tsla, tsll]:
        if 'Close' not in df.columns:
            if 'close' in df.columns:
                df['Close'] = df['close']
            elif 'AdjClose' in df.columns:
                df['Close'] = df['AdjClose']
            else:
                raise ValueError(f"Cannot find 'Close' column in {df.columns}")
        df.index = pd.to_datetime(df.index)
        df.index.name = 'Date'

    # 디버깅 출력
    #print(f"TSLA columns: {tsla.columns.tolist()}")
    #print(f"TSLL columns: {tsll.columns.tolist()}")

    return tsla, tsll

def fetch_vix_data():
    vix = yf.Ticker("^VIX").history(period="6mo")
    vix_data = vix['Close']
    return vix_data

def fetch_fear_greed_index():
    try:
        res = requests.get("https://api.alternative.me/fng/?limit=1&format=json")
        val = int(res.json()['data'][0]['value'])
        return val
    except:
        return None

def fetch_interest_rate():
    fed = yf.download("^TNX", period="7d", interval="1d", progress=False, auto_adjust=False)
    if 'Close' in fed.columns and not fed.empty:
        return fed['Close'].iloc[-1] / 10  # ^TNX 단위는 x10
    return 4.0  # fallback
