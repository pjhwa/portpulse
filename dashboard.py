# main.py
import schedule
import time
from datetime import datetime
from core.fetch import fetch_price_data, fetch_vix_data, fetch_fear_greed_index, fetch_interest_rate
from core.indicators import add_technical_indicators
from core.signal import decide_allocation, explain_allocation_reason
from core.backtest import run_backtest, compute_performance_metrics
from report_utils import generate_pdf_report
from email_utils import send_email_report
import matplotlib.pyplot as plt
import yfinance as yf

SENDER = "your_email@gmail.com"
PASSWORD = "your_app_password"
RECIPIENT = "recipient@example.com"


def run_daily_strategy():
    tsla_df, tsll_df = fetch_price_data()
    tsla_df = add_technical_indicators(tsla_df)
    latest = tsla_df.iloc[-1]
    date = tsla_df.index[-1]
    vix = fetch_vix_data().get(date)
    fear = fetch_fear_greed_index()
    rate = fetch_interest_rate()

    w_tsla, w_tsll = decide_allocation(
        latest['RSI'], latest['MACD'], latest['MACD_signal'], latest['MACD_hist'],
        latest['AdjClose'], latest['BB_upper'], latest['BB_lower'], latest['ATR'],
        vix=vix, fear_greed=fear, interest_rate=rate
    )

    explanation = explain_allocation_reason(
        latest['RSI'], latest['MACD'], latest['MACD_signal'], latest['MACD_hist'],
        latest['AdjClose'], latest['BB_upper'], latest['BB_lower'], latest['ATR'],
        w_tsla, w_tsll, vix=vix, fear_greed=fear, interest_rate=rate
    )

    strat_vals, tsla_vals, tsll_vals = run_backtest(tsla_df, tsll_df)
    metrics = compute_performance_metrics(strat_vals)

    # 📈 벤치마크: SPY, QQQ
    spy = yf.Ticker("SPY").history(start=tsla_df.index[0], end=tsla_df.index[-1])['Close']
    qqq = yf.Ticker("QQQ").history(start=tsla_df.index[0], end=tsla_df.index[-1])['Close']
    spy = spy / spy.iloc[0] * 100
    qqq = qqq / qqq.iloc[0] * 100

    # 📈 수익 곡선 비교 시각화
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(strat_vals.index, strat_vals.values, label="PortPulse 전략", linewidth=2)
    ax.plot(tsla_vals.index, tsla_vals.values, label="TSLA 단독 투자", linestyle="--")
    ax.plot(tsll_vals.index, tsll_vals.values, label="TSLL 단독 투자", linestyle=":")
    ax.plot(spy.index, spy.values, label="SPY (S&P 500)", linestyle="-.")
    ax.plot(qqq.index, qqq.values, label="QQQ (NASDAQ)", linestyle="--", alpha=0.7)
    ax.set_title("PortPulse vs TSLA vs TSLL vs SPY vs QQQ 수익 곡선")
    ax.set_xlabel("Date")
    ax.set_ylabel("Portfolio Value (정규화)")
    ax.legend()
    ax.grid(True)
    fig.tight_layout()
    fig.savefig("portpulse_equity_curve.png")

    # 📄 PDF 보고서 생성 시 그래프 포함
    report_path = generate_pdf_report(
        date.strftime("%Y-%m-%d"),
        (w_tsla, w_tsll),
        explanation,
        metrics,
        equity_chart_path="portpulse_equity_curve.png"
    )

    send_email_report(
        sender_email=SENDER,
        sender_password=PASSWORD,
        recipient_email=RECIPIENT,
        subject="PortPulse 전략 보고서 📤",
        body="첨부된 PDF는 오늘자 PortPulse 포트폴리오 전략 리포트입니다.",
        attachment_path=report_path
    )
    print("✅ PortPulse 전략 실행 및 이메일 전송 완료")


schedule.every().day.at("09:00").do(run_daily_strategy)

print("⏳ PortPulse 스케줄러 대기 중... (매일 09:00 실행)")
while True:
    schedule.run_pending()
    time.sleep(60)
