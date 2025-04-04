# core/portfolio.py
import pandas as pd
from rich.table import Table
from rich.console import Console
from rich.text import Text
import os
import sqlite3

def ensure_database(file_path="data/portpulse.db"):
    if not os.path.exists(file_path):
        print(f"[yellow]⚠ 데이터베이스 파일이 존재하지 않습니다. 새로 생성합니다: {file_path}[/yellow]")
        conn = sqlite3.connect(file_path)
        conn.close()

def load_trade_log(file_path="trade_log.csv"):
    try:
        df = pd.read_csv(file_path, parse_dates=["Date"])
        df = df.sort_values("Date")
        return df
    except FileNotFoundError:
        print(f"[red]⚠ trade_log.csv 파일을 찾을 수 없습니다: {file_path}[/red]")
        return pd.DataFrame(columns=["Date", "Ticker", "Action", "Shares", "Price"])

def get_initial_holdings(trade_log):
    initial = {"TSLA": {"shares": 0, "price": 0.0}, "TSLL": {"shares": 0, "price": 0.0}}
    for _, row in trade_log.iterrows():
        if row["Action"].lower() == "hold":
            ticker = row["Ticker"]
            initial[ticker] = {"shares": row["Shares"], "price": row["Price"]}
    return initial

def get_current_holdings(trade_log):
    holdings = {"TSLA": {"shares": 0, "cost": 0.0}, "TSLL": {"shares": 0, "cost": 0.0}}
    for _, row in trade_log.iterrows():
        ticker = row["Ticker"]
        action = row["Action"].lower()
        shares = row["Shares"]
        price = row["Price"]

        if ticker not in holdings:
            holdings[ticker] = {"shares": 0, "cost": 0.0}

        if action in ("buy", "hold"):
            total_cost = holdings[ticker]["cost"] * holdings[ticker]["shares"] + price * shares
            holdings[ticker]["shares"] += shares
            holdings[ticker]["cost"] = total_cost / holdings[ticker]["shares"]
        elif action == "sell":
            holdings[ticker]["shares"] -= shares
            if holdings[ticker]["shares"] <= 0:
                holdings[ticker] = {"shares": 0, "cost": 0.0}
    return holdings
