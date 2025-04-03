# data/thresholds.py
import sqlite3
import os
from datetime import datetime
from rich import print

DB_PATH = "portpulse.db"

def ensure_threshold_table():
    """thresholds 테이블이 존재하지 않으면 생성합니다."""
    if not os.path.exists(DB_PATH):
        print(f"[yellow]⚠ 데이터베이스 파일 없음. 생성 중: {DB_PATH}[/yellow]")
    conn = sqlite3.connect(DB_PATH)
    with conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS thresholds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_saved TEXT,
            indicator TEXT,
            threshold_type TEXT,
            value REAL,
            metric TEXT,
            score REAL
        )
        """)
    conn.close()

def save_best_thresholds(config):
    """최적화된 임계값을 데이터베이스에 저장합니다."""
    ensure_threshold_table()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    for indicator, thresholds in config.items():
        if isinstance(thresholds, dict):
            for threshold_type, value in thresholds.items():
                cursor.execute("""
                    INSERT INTO thresholds (date_saved, indicator, threshold_type, value, metric, score)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    datetime.today().strftime("%Y-%m-%d"),
                    indicator,
                    threshold_type,
                    value,
                    config.get('metric', 'unknown'),
                    config.get('score', 0.0)
                ))
    conn.commit()
    conn.close()
    print("[green]📌 최적 임계값 저장 완료[/green]")

def load_latest_thresholds():
    """가장 높은 점수를 가진 최신 임계값을 로드합니다."""
    ensure_threshold_table()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT indicator, threshold_type, value
        FROM thresholds
        ORDER BY score DESC
        LIMIT 1
    """)
    rows = cursor.fetchall()
    conn.close()
    if rows:
        thresholds = {}
        for row in rows:
            indicator, threshold_type, value = row
            if indicator not in thresholds:
                thresholds[indicator] = {}
            thresholds[indicator][threshold_type] = value
        return thresholds
    print("[yellow]⚠ 최적화된 임계값이 없습니다. 기본값을 사용합니다.[/yellow]\n")
    return get_default_thresholds()

def get_default_thresholds():
    """기본 임계값을 반환합니다. (flat dictionary)"""
    return {
        'rsi_daily_low': 30,
        'rsi_daily_mid': 40,
        'rsi_daily_high': 70,
        'rsi_weekly_low': 30,
        'rsi_weekly_high': 70,
        'rsi_short_low': 20,
        'rsi_short_high': 80,
        'atr_low': 1.5,
        'atr_high': 5.0,
        'bb_width_low': 0.05,
        'bb_width_high': 0.15,
        'stoch_k_low': 20,
        'stoch_k_high': 80,
        'fear_greed_low': 20,
        'fear_greed_high': 80,
        # 추가 지표의 기본 임계값을 여기에 정의
    }
