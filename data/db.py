# core/fetch.py
import yfinance as yf
import pandas as pd
import requests
from data.db import load_prices, save_prices, ensure_db
from rich import print

ensure_db()

def fetch_price_data(start="2023-03-01", end=None):
    ensure_db()
    tsla = load_prices("TSLA", start)
    tsll = load_prices("TSLL", start)

    if tsla is None:
        try:
            tsla = yf.Ticker("TSLA").history(start=start, end=end, auto_adjust=True)
            if tsla.empty or tsla['Close'].isna().all():
                print(f"[red]⚠ TSLA 데이터 로드 실패: 데이터가 비어 있거나 모두 NaN입니다.[/red]")
                raise ValueError("TSLA 데이터가 유효하지 않습니다.")
            #print(f"[debug] TSLA yfinance 데이터: {tsla.tail(1)}")
            save_prices(tsla, "TSLA")
        except Exception as e:
            print(f"[red]⚠ TSLA 데이터 가져오기 오류: {e}[/red]")
            raise RuntimeError(f"TSLA 데이터를 가져올 수 없습니다: {e}")

    if tsll is None:
        try:
            tsll = yf.Ticker("TSLL").history(start=start, end=end, auto_adjust=True)
            if tsll.empty or tsll['Close'].isna().all():
                print(f"[red]⚠ TSLL 데이터 로드 실패: 데이터가 비어 있거나 모두 NaN입니다.[/red]")
                raise ValueError("TSLL 데이터가 유효하지 않습니다.")
            #print(f"[debug] TSLL yfinance 데이터: {tsll.tail(1)}")
            save_prices(tsll, "TSLL")
        except Exception as e:
            print(f"[red]⚠ TSLL 데이터 가져오기 오류: {e}[/red]")
            raise RuntimeError(f"TSLL 데이터를 가져올 수 없습니다: {e}")

    # 열 이름 표준화 및 중복 인덱스 제거
    for df in [tsla, tsll]:
        # yfinance 데이터의 열 이름을 소문자로 변환
        df.columns = [col.lower() for col in df.columns]
        if 'close' not in df.columns:
            print(f"[yellow]⚠ {df.name if hasattr(df, 'name') else 'DataFrame'}에 'close' 열이 없습니다. 열: {df.columns.tolist()}[/yellow]")
            raise ValueError("'close' 열이 없는 데이터프레임")
        df.index = pd.to_datetime(df.index)
        df.index.name = 'date'
        if df.index.duplicated().any():
            print(f"[yellow]⚠ {df.name if hasattr(df, 'name') else 'DataFrame'}에서 중복 인덱스 발견. 중복 제거합니다.[/yellow]")
            df = df[~df.index.duplicated(keep='last')]

    return tsla, tsll

def fetch_vix_data():
    try:
        vix = yf.Ticker("^VIX").history(period="6mo")
        if vix.empty:
            print(f"[red]⚠ VIX 데이터 로드 실패: 데이터가 비어 있습니다.[/red]")
            return pd.Series()
        vix.columns = [col.lower() for col in vix.columns]
        vix_data = vix['close']
        return vix_data
    except Exception as e:
        print(f"[red]⚠ VIX 데이터 가져오기 오류: {e}[/red]")
        return pd.Series()

def fetch_fear_greed_index():
    try:
        res = requests.get("https://api.alternative.me/fng/?limit=1&format=json")
        val = int(res.json()['data'][0]['value'])
        return val
    except:
        return None

def fetch_interest_rate():
    try:
        fed = yf.download("^TNX", period="7d", interval="1d", progress=False, auto_adjust=False)
        if 'close' in fed.columns and not fed.empty:
            fed.columns = [col.lower() for col in fed.columns]
            return fed['close'].iloc[-1] / 10
        return 4.0
    except Exception as e:
        print(f"[red]⚠ 금리 데이터 가져오기 오류: {e}[/red]")
        return 4.0
