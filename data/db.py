# data/db.py
import os
import sqlite3
import pandas as pd
from datetime import datetime
from rich import print

def ensure_db(path="data/portpulse.db"):
    """데이터베이스가 존재하지 않으면 생성합니다."""
    if not os.path.exists(path):
        print(f"[yellow]⚠ 데이터베이스가 존재하지 않습니다. 새로 생성합니다: {path}[/yellow]")
        conn = sqlite3.connect(path)
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
        conn.execute("""
        CREATE TABLE IF NOT EXISTS indicators (
            date TEXT,
            ticker TEXT,
            indicator TEXT,
            value REAL,
            PRIMARY KEY (date, ticker, indicator)
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS thresholds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_saved TEXT,
            indicator TEXT,
            threshold_type TEXT,
            value REAL,
            metric TEXT,
            score REAL,
            cagr REAL,
            cumulative_return REAL,
            max_return REAL
        )
        """)
        conn.close()

def save_prices(df: pd.DataFrame, ticker: str, db_path="data/portpulse.db"):
    """주가 데이터를 데이터베이스에 저장합니다."""
    ensure_db(db_path)
    df = df.copy()
    df.columns = [col.lower() for col in df.columns]
    required = ['open', 'high', 'low', 'close', 'adjclose', 'volume']
    for col in required:
        if col not in df.columns:
            if col == 'adjclose' and 'close' in df.columns:
                df['adjclose'] = df['close']
            elif col == 'close' and 'adjclose' in df.columns:
                df['close'] = df['adjclose']
            else:
                df[col] = 0.0
    df = df.reset_index()
    df['date'] = pd.to_datetime(df['date']).dt.strftime("%Y-%m-%d")
    df['ticker'] = ticker
    df = df[['date', 'ticker'] + required]
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

def load_prices(ticker: str, start: str = "2022-07-01", db_path="data/portpulse.db"):
    """데이터베이스에서 주가 데이터를 로드합니다."""
    ensure_db(db_path)
    conn = sqlite3.connect(db_path)
    query = f"SELECT * FROM prices WHERE ticker = ? AND date >= ?"
    df = pd.read_sql(query, conn, params=(ticker, start))
    conn.close()
    if df.empty:
        return None
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values("date")
    df.set_index('date', inplace=True)
    return df

def save_indicators(df: pd.DataFrame, ticker: str, db_path="data/portpulse.db"):
    """지표 데이터를 데이터베이스에 저장합니다."""
    ensure_db(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    for date, row in df.iterrows():
        for indicator in row.index:
            cursor.execute("""
                INSERT OR REPLACE INTO indicators (date, ticker, indicator, value)
                VALUES (?, ?, ?, ?)
            """, (date.strftime("%Y-%m-%d"), ticker, indicator, row[indicator]))
    conn.commit()
    conn.close()

def load_indicators(ticker: str, start: str = "2022-07-01", db_path="data/portpulse.db"):
    """데이터베이스에서 지표 데이터를 로드합니다."""
    ensure_db(db_path)
    conn = sqlite3.connect(db_path)
    query = f"SELECT * FROM indicators WHERE ticker = ? AND date >= ?"
    df = pd.read_sql(query, conn, params=(ticker, start))
    conn.close()
    if df.empty:
        return None
    df = df.pivot(index='date', columns='indicator', values='value')
    df.index = pd.to_datetime(df.index)
    return df

def save_best_thresholds(config, db_path="data/portpulse.db"):
    ensure_db(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    metric = config.get('metric', 'unknown')
    score = config.get('score', 0.0)
    cagr = config.get('cagr', 0.0)
    cumulative_return = config.get('cumulative_return', 0.0)
    max_return = config.get('max_return', 0.0)
    date_saved = datetime.today().strftime("%Y-%m-%d")

    for key, value in config.items():
        if key not in ['metric', 'score', 'cagr', 'cumulative_return', 'max_return']:
            parts = key.split('_')
            if len(parts) >= 2:
                threshold_type = parts[-1]
                indicator = '_'.join(parts[:-1])
                cursor.execute("""
                    INSERT INTO thresholds (date_saved, indicator, threshold_type, value, metric, score, cagr, cumulative_return, max_return)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (date_saved, indicator, threshold_type, float(value), metric, float(score), cagr, cumulative_return, max_return))
    conn.commit()
    conn.close()
    print("[green]📌 최적 임계값 및 성과 지표 저장 완료[/green]")

def load_latest_thresholds(db_path="data/portpulse.db"):
    ensure_db(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT indicator, threshold_type, value, cagr, cumulative_return, max_return
        FROM thresholds
        WHERE score = (SELECT MAX(score) FROM thresholds)
        LIMIT 1
    """)
    rows = cursor.fetchall()
    conn.close()
    if rows:
        thresholds = {}
        for row in rows:
            indicator, threshold_type, value, cagr, cumulative_return, max_return = row
            if indicator not in thresholds:
                thresholds[indicator] = {}
            thresholds[indicator][threshold_type] = value
            thresholds['cagr'] = cagr
            thresholds['cumulative_return'] = cumulative_return
            thresholds['max_return'] = max_return
        return thresholds
    print("[yellow]⚠ 최적화된 임계값이 없습니다. 기본값을 사용합니다.[/yellow]")
    return None

if __name__ == "__main__":
    sample_config = {
        'rsi_daily_low': 20,
        'metric': 'sharpe',
        'score': 0.24,
        'cagr': 0.15,
        'cumulative_return': 0.50,
        'max_return': 0.75
    }
    save_best_thresholds(sample_config)
