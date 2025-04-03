# ✅ data/db.py 수정: 누락된 컬럼 보완 후 저장하도록 개선
import os
import sqlite3
import pandas as pd
from datetime import datetime
from rich import print
from rich.text import Text

def ensure_db(path="portpulse.db"):
    if not os.path.exists(path):
        print(f"[yellow]⚠ 데이터베이스가 존재하지 않습니다. 새로 생성합니다: {path}[/yellow]")
        conn = sqlite3.connect(path)
        with conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS prices (
                date TEXT,
                ticker TEXT,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                adjclose REAL,
                volume INTEGER
            )
            """)
        conn.close()

def save_prices(df: pd.DataFrame, ticker: str, db_path="portpulse.db"):
    ensure_db(db_path)

    # ✅ 열 이름 표준화
    rename_map = {
        'Open': 'open', 'High': 'high', 'Low': 'low',
        'Close': 'close', 'Adj Close': 'adjclose', 'Volume': 'volume'
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    required = ['open', 'high', 'low', 'close', 'adjclose', 'volume']
    missing = [col for col in required if col not in df.columns]

    for col in missing:
        if col == 'adjclose' and 'close' in df.columns:
            df['adjclose'] = df['close']
        elif col == 'close' and 'adjclose' in df.columns:
            df['close'] = df['adjclose']
        else:
            df[col] = 0.0

    # ✅ 모든 가격 값이 0인지 확인
    if df[required].sum().sum() == 0:
        print(f"[red]⚠ 경고: {ticker}의 가격 데이터가 모두 0입니다. 저장을 중단합니다.[/red]")
        return

    if not missing:
        print(f"[green]✔ {ticker} 저장 완료[/green]")
    else:
        print(f"[yellow]⚠ {ticker} 데이터에 누락된 컬럼 {missing}을 보완하여 저장합니다.[/yellow]\n")

    df = df.reset_index()
    df['date'] = pd.to_datetime(df['Date']).dt.strftime("%Y-%m-%d")
    df['ticker'] = ticker
    df = df[['date', 'ticker'] + required]

    conn = sqlite3.connect(db_path)
    df.to_sql("prices", conn, if_exists="append", index=False)
    conn.close()

def load_prices(ticker: str, start: str = "2023-01-01", db_path="portpulse.db"):
    ensure_db(db_path)
    try:
        conn = sqlite3.connect(db_path)
        query = f"SELECT * FROM prices WHERE ticker = ? AND date >= ?"
        df = pd.read_sql(query, conn, params=(ticker, start))
        conn.close()

        if df.empty:
            return None

        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values("date")

        # 종가 누락 보안
        if 'adjclose' not in df.columns and 'close' in df.columns:
            df['adjclose'] = df['close']
        elif 'close' not in df.columns and 'adjclose' in df.columns:
            df['close'] = df['adjclose']

        df.set_index('date', inplace=True)
        return df
    except Exception as e:
        print(f"[red]데이터 로드 오류: {e}[/red]")
        return None
