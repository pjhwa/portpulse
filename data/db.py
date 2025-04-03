# data/db.py
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
                volume INTEGER,
                PRIMARY KEY (date, ticker)
            )
            """)
        conn.close()

def save_prices(df: pd.DataFrame, ticker: str, db_path="portpulse.db"):
    ensure_db(db_path)

    if df.empty:
        print(f"[red]⚠ {ticker} 데이터프레임이 비어 있습니다. 저장을 중단합니다.[/red]")
        return

    # 입력 데이터프레임 디버깅 출력
    #print(f"[debug] {ticker} 입력 데이터프레임: {df.tail(1)}")

    # 데이터프레임 복사 후 열 이름 소문자 변환
    df = df.copy()
    df.columns = [col.lower() for col in df.columns]

    # 필수 열 확인 및 보완 (기존 값 보존)
    required = ['open', 'high', 'low', 'close', 'adjclose', 'volume']
    for col in required:
        if col not in df.columns:
            if col == 'adjclose' and 'close' in df.columns:
                df['adjclose'] = df['close']
            elif col == 'close' and 'adjclose' in df.columns:
                df['close'] = df['adjclose']
            else:
                df[col] = 0.0

    # 데이터 유효성 확인
    if df['close'].isna().all() or df['close'].eq(0).all():
        print(f"[red]⚠ 경고: {ticker}의 'close' 값이 모두 NaN 또는 0입니다. 저장을 중단합니다.[/red]")
        #print(f"[debug] {ticker} 처리 후 데이터프레임: {df.tail(5)}")
        return

    #print(f"[green]✔ {ticker} 저장 완료[/green]")

    # 인덱스를 'date' 열로 변환
    df = df.reset_index()
    if 'date' not in df.columns:
        if 'Date' in df.columns:
            df = df.rename(columns={'Date': 'date'})
        elif 'index' in df.columns:
            df = df.rename(columns={'index': 'date'})
        else:
            print(f"[red]⚠ {ticker} 데이터프레임에 날짜 열이 없습니다: {df.columns.tolist()}[/red]")
            return

    df['date'] = pd.to_datetime(df['date']).dt.strftime("%Y-%m-%d")
    df['ticker'] = ticker
    df = df[['date', 'ticker'] + required]

    # SQLite 연결
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    for _, row in df.iterrows():
        cursor.execute("""
            INSERT OR REPLACE INTO prices (date, ticker, open, high, low, close, adjclose, volume)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            row['date'], row['ticker'], row['open'], row['high'], row['low'],
            row['close'], row['adjclose'], row['volume']
        ))
    conn.commit()
    conn.close()
    #print(f"[debug] {ticker} 데이터 저장 후 확인: {df.tail(1)}")

def load_prices(ticker: str, start: str = "2022-07-01", db_path="portpulse.db"):
    ensure_db(db_path)
    try:
        conn = sqlite3.connect(db_path)
        query = f"SELECT * FROM prices WHERE ticker = ? AND date >= ?"
        df = pd.read_sql(query, conn, params=(ticker, start))
        conn.close()

        if df.empty:
            #print(f"[yellow]⚠ {ticker} 데이터가 데이터베이스에 없습니다. 기간: {start} 이후[/yellow]")
            return None

        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values("date")
        df.set_index('date', inplace=True)

        if df['close'].isna().all() or df['close'].eq(0).all():
            print(f"[red]⚠ {ticker} 데이터가 유효하지 않습니다 (모두 0/NaN).[/red]")
            #print(f"[debug] {ticker} 로드된 데이터: {df.tail(5)}")
            return None

        return df
    except Exception as e:
        print(f"[red]데이터 로드 오류: {e}[/red]")
        return None
