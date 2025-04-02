# dashboard.py
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import date
import yfinance as yf
from core.optimize import run_optimization
from core.fetch import fetch_price_data, fetch_vix_data, fetch_fear_greed_index, fetch_interest_rate
from core.indicators import add_technical_indicators
from core.signal import decide_allocation, explain_allocation_reason
from core.backtest import run_backtest, compute_performance_metrics

st.set_page_config(page_title="PortPulse 전략 대시보드", layout="wide")

st.title("🚀 PortPulse 전략 대시보드")

st.sidebar.header("⚙️ 전략 설정")

opt_metric = st.sidebar.selectbox("최적화 기준 선택", ["sharpe", "cagr", "mdd"], index=0)
if st.sidebar.button("🔍 전략 최적화 실행 (PortPulse AI)"):
    with st.spinner("최적화 실행 중..."):
        run_optimization(metric=opt_metric)
        import numpy as np
        from core.fetch import fetch_price_data
        from core.indicators import add_technical_indicators
        from core.backtest import run_backtest
        import yfinance as yf

        tsla_df, tsll_df = fetch_price_data()
        if "AdjClose" not in tsla_df.columns:
            if "Adj Close" in tsla_df.columns:
                tsla_df["AdjClose"] = tsla_df["Adj Close"]
            elif "Close" in tsla_df.columns:
                tsla_df["AdjClose"] = tsla_df["Close"]

        tsla_df = add_technical_indicators(tsla_df)
        strategy_vals, tsla_vals, tsll_vals = run_backtest(tsla_df, tsll_df)

        tsla_vals.to_csv("best_tsla_curve.csv")
        tsll_vals.to_csv("best_tsll_curve.csv")

        start, end = tsla_df.index[0], tsla_df.index[-1]
        spy = yf.Ticker("SPY").history(start=start, end=end)['Close']
        qqq = yf.Ticker("QQQ").history(start=start, end=end)['Close']
        spy = spy / spy.iloc[0] * 100
        qqq = qqq / qqq.iloc[0] * 100
        spy.to_csv("best_spy_curve.csv")
        qqq.to_csv("best_qq_curve.csv")
        st.success("✅ 최적화 완료!")

st.sidebar.markdown("---")
st.sidebar.subheader("📅 시뮬레이션 기간 설정")
def_date = (date(2023, 1, 1), date.today())
sim_start = st.sidebar.date_input("시작일", def_date[0])
sim_end = st.sidebar.date_input("종료일", def_date[1])

if st.sidebar.button("🧪 시뮬레이션 실행"):
    st.subheader("📈 사용자 지정 시뮬레이션 결과 (PortPulse)")
    tsla_df, tsll_df = fetch_price_data(start=sim_start, end=sim_end)
    if "AdjClose" not in tsla_df.columns:
        if "Adj Close" in tsla_df.columns:
            tsla_df["AdjClose"] = tsla_df["Adj Close"]
        elif "Close" in tsla_df.columns:
            tsla_df["AdjClose"] = tsla_df["Close"]
        else:
            st.error("TSLA 데이터에 AdjClose 컬럼이 없어 분석을 진행할 수 없습니다.")
            st.stop()
    tsla_df = add_technical_indicators(tsla_df)
    strategy_vals, tsla_vals, tsll_vals = run_backtest(tsla_df, tsll_df)
    metrics = compute_performance_metrics(strategy_vals)

    st.write("CAGR:", f"{metrics['CAGR']*100:.2f}%")
    st.write("Sharpe:", f"{metrics['Sharpe']:.2f}")
    st.write("Max Drawdown:", f"{metrics['MaxDrawdown']*100:.2f}%")

    spy = yf.Ticker("SPY").history(start=sim_start, end=sim_end)['Close']
    qqq = yf.Ticker("QQQ").history(start=sim_start, end=sim_end)['Close']
    spy = spy / spy.iloc[0] * 100
    qqq = qqq / qqq.iloc[0] * 100

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(strategy_vals.index, strategy_vals.values, label="PortPulse 전략")
    ax.plot(tsla_vals.index, tsla_vals.values, label="TSLA Only", linestyle="--")
    ax.plot(tsll_vals.index, tsll_vals.values, label="TSLL Only", linestyle=":")
    ax.plot(spy.index, spy.values, label="SPY", linestyle="-.", alpha=0.8)
    ax.plot(qqq.index, qqq.values, label="QQQ", linestyle="--", alpha=0.6)
    ax.set_title("전략 수익 곡선 비교")
    ax.legend()
    ax.grid(True)
    st.pyplot(fig)

st.markdown("---")
st.subheader("📊 오늘의 포트폴리오 전략 분석 (PortPulse AI)")
tsla_df, tsll_df = fetch_price_data()
if tsla_df is not None and 'AdjClose' not in tsla_df.columns:
    if 'Adj Close' in tsla_df.columns:
        tsla_df['AdjClose'] = tsla_df['Adj Close']
    elif 'Close' in tsla_df.columns:
        tsla_df['AdjClose'] = tsla_df['Close']
if "AdjClose" not in tsla_df.columns:
    if "Adj Close" in tsla_df.columns:
        tsla_df["AdjClose"] = tsla_df["Adj Close"]
    elif "Close" in tsla_df.columns:
        tsla_df["AdjClose"] = tsla_df["Close"]
    else:
        st.error("TSLA 데이터에 AdjClose 컬럼이 없어 분석을 진행할 수 없습니다.")
        st.stop()
tsla_df = add_technical_indicators(tsla_df)
latest = tsla_df.iloc[-1]
latest_date = tsla_df.index[-1]
vix_data = fetch_vix_data()
fear_greed = fetch_fear_greed_index()
interest_rate = fetch_interest_rate()

w_tsla, w_tsll = decide_allocation(
    latest['RSI'], latest['MACD'], latest['MACD_signal'], latest['MACD_hist'],
    latest['AdjClose'], latest['BB_upper'], latest['BB_lower'], latest['ATR'],
    vix=vix_data.get(latest_date), fear_greed=fear_greed, interest_rate=interest_rate
)

explanation = explain_allocation_reason(
    latest['RSI'], latest['MACD'], latest['MACD_signal'], latest['MACD_hist'],
    latest['AdjClose'], latest['BB_upper'], latest['BB_lower'], latest['ATR'],
    w_tsla, w_tsll, vix=vix_data.get(latest_date), fear_greed=fear_greed, interest_rate=interest_rate
)

st.markdown(f"**📅 분석일자:** {latest_date.date()}")
st.markdown(f"**💼 PortPulse 제안 비중:** TSLA {w_tsla*100:.1f}% | TSLL {w_tsll*100:.1f}%")
st.text(explanation)

st.markdown("---")
st.subheader("📑 최적화 전략 요약 (PortPulse)")
try:
    summary_df = pd.read_csv("best_strategy_summary.csv")
    summary_df = summary_df.apply(pd.to_numeric, errors='coerce')
    st.dataframe(summary_df.T, use_container_width=True)
    st.download_button("📥 전략 요약 다운로드", data=summary_df.to_csv(index=False), file_name="portpulse_strategy_summary.csv")
except FileNotFoundError:
    st.warning("최적화 결과 없음: 먼저 최적화를 실행해주세요.")

try:
    equity_df = pd.read_csv("best_equity_curve.csv", index_col=0, parse_dates=True)
    st.subheader("📈 PortPulse 전략 수익 곡선")
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(equity_df.index, equity_df.values, label="Optimized Strategy", color="green")
    try:
        tsla_df = pd.read_csv("best_tsla_curve.csv", index_col=0, parse_dates=True)
        tsll_df = pd.read_csv("best_tsll_curve.csv", index_col=0, parse_dates=True)
        spy_df = pd.read_csv("best_spy_curve.csv", index_col=0, parse_dates=True)
        qqq_df = pd.read_csv("best_qq_curve.csv", index_col=0, parse_dates=True)
        ax.plot(tsla_df.index, tsla_df.values, label="TSLA Only", linestyle="--")
        ax.plot(tsll_df.index, tsll_df.values, label="TSLL Only", linestyle=":")
        ax.plot(spy_df.index, spy_df.values, label="SPY", linestyle="-.", alpha=0.8)
        ax.plot(qqq_df.index, qqq_df.values, label="QQQ", linestyle="--", alpha=0.6)
    except Exception as e:
        st.warning(f"비교용 수익 곡선 데이터를 불러올 수 없습니다: {e}")
    ax.set_title("Equity Curve")
    ax.set_xlabel("Date")
    ax.set_ylabel("Portfolio Value")
    ax.grid(True)
    ax.legend()
    st.pyplot(fig)

    from io import BytesIO
    buf = BytesIO()
    fig.savefig("portpulse_equity_comparison.png")
    fig.savefig(buf, format="png")
    st.download_button("📸 수익 곡선 다운로드 (PNG)", data=buf.getvalue(), file_name="portpulse_equity_curve.png")

except FileNotFoundError:
    st.warning("수익 곡선 데이터가 없습니다.")

st.markdown("---")
st.caption("© 2025 PortPulse 전략 최적화 도구 | Streamlit AI 대시보드")
