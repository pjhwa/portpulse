# core/fetch.py
import yfinance as yf
import pandas as pd
import requests
from data.db import load_prices, save_prices, init_db

# DB 초기화
init_db()

def fetch_price_data(start="2022-07-01", end=None):
    # DB 우선 조회
    tsla = load_prices("TSLA", start)
    tsll = load_prices("TSLL", start)

    if tsla is None:
        tsla = yf.Ticker("TSLA").history(start=start, end=end, auto_adjust=False)
        if not tsla.empty:
            tsla["AdjClose"] = tsla["Adj Close"] if "Adj Close" in tsla.columns else tsla["Close"]
            save_prices(tsla, "TSLA")

    if tsll is None:
        tsll = yf.Ticker("TSLL").history(start=start, end=end, auto_adjust=False)
        if not tsll.empty:
            tsll["AdjClose"] = tsll["Adj Close"] if "Adj Close" in tsll.columns else tsll["Close"]
            save_prices(tsll, "TSLL")

    return tsla, tsll

def fetch_vix_data():
    vix = yf.Ticker("^VIX").history(period="6mo")
    return vix['Close']

def fetch_fear_greed_index():
    try:
        res = requests.get("https://api.alternative.me/fng/?limit=1&format=json")
        val = int(res.json()['data'][0]['value'])
        return val
    except:
        return None

def fetch_interest_rate():
    try:
        fed = yf.Ticker("^TNX").history(period="6mo")
        return float(fed['Close'].iloc[-1]) / 10
    except:
        return None
