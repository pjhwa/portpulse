# db.py
import sqlite3
import pandas as pd
from datetime import datetime

DB_FILE = "portpulse.db"

def init_db():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
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
    ''')
    conn.commit()
    conn.close()

def save_prices(df, ticker):
    from data.db import DB_FILE

    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    df = df.copy()

    # ✅ 모든 컬럼을 소문자로 통일
    df.columns = [col.lower() for col in df.columns]

    # ✅ 누락된 'close' 컬럼을 'adjclose'로 보완
    if 'close' not in df.columns and 'adjclose' in df.columns:
        df['close'] = df['adjclose']

    # ✅ 필수 컬럼 확인
    cols = ['open', 'high', 'low', 'close', 'adjclose', 'volume']
    missing = [col for col in cols if col not in df.columns]
    if missing:
        print(f"[에러] {ticker} 저장 실패. 누락된 컬럼: {missing}")
        return

    # ✅ 날짜 컬럼 생성 및 정리
    df['date'] = df.index.astype(str)
    df['ticker'] = ticker
    df[cols] = df[cols].astype(float)
    df = df[['date', 'ticker'] + cols]

    df.to_sql("prices", conn, if_exists="append", index=False)
    conn.close()

def load_prices(ticker, start_date=None):
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    q = f"SELECT * FROM prices WHERE ticker = ?"
    if start_date:
        q += f" AND date >= ?"
        df = pd.read_sql(q, conn, params=(ticker, start_date))
    else:
        df = pd.read_sql(q, conn, params=(ticker,))
    if df.empty:
        return None
    df['date'] = pd.to_datetime(df['date'], utc=True)
    df.set_index('date', inplace=True)
    return df
