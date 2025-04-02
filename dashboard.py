# dashboard.py
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import date
from core.optimize import run_optimization
from core.fetch import fetch_price_data, fetch_vix_data, fetch_fear_greed_index, fetch_interest_rate
from core.indicators import add_technical_indicators
from core.signal import decide_allocation, explain_allocation_reason
from core.backtest import run_backtest, compute_performance_metrics

st.set_page_config(page_title="PortPulse 전략 대시보드", layout="wide")

st.title("🚀 PortPulse 전략 대시보드")

st.sidebar.header("⚙️ 전략 설정")

# 사용자 최적화 기준 선택 및 실행
opt_metric = st.sidebar.selectbox("최적화 기준 선택", ["sharpe", "cagr", "mdd"], index=0)
if st.sidebar.button("🔍 전략 최적화 실행 (PortPulse AI)"):
    with st.spinner("최적화 실행 중..."):
        run_optimization(metric=opt_metric)
        st.success("✅ 최적화 완료!")

# 사용자 시뮬레이션 기간 입력 및 실행
st.sidebar.markdown("---")
st.sidebar.subheader("📅 시뮬레이션 기간 설정")
def_date = (date(2023, 1, 1), date.today())
sim_start = st.sidebar.date_input("시작일", def_date[0])
sim_end = st.sidebar.date_input("종료일", def_date[1])

if st.sidebar.button("🧪 시뮬레이션 실행"):
    st.subheader("📈 사용자 지정 시뮬레이션 결과 (PortPulse)")
    tsla_df, tsll_df = fetch_price_data(start=sim_start, end=sim_end)
    tsla_df = add_technical_indicators(tsla_df)
    strategy_vals, tsla_vals, tsll_vals = run_backtest(tsla_df, tsll_df)
    metrics = compute_performance_metrics(strategy_vals)
    st.write("CAGR:", f"{metrics['CAGR']*100:.2f}%")
    st.write("Sharpe:", f"{metrics['Sharpe']:.2f}")
    st.write("Max Drawdown:", f"{metrics['MaxDrawdown']*100:.2f}%")

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(strategy_vals.index, strategy_vals.values, label="PortPulse Strategy")
    ax.set_title("Simulated Equity Curve")
    ax.grid(True)
    ax.legend()
    st.pyplot(fig)

# 오늘의 분석
st.markdown("---")
st.subheader("📊 오늘의 포트폴리오 전략 분석 (PortPulse AI)")
tsla_df, tsll_df = fetch_price_data()
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

# 전략 요약 보기
st.markdown("---")

st.subheader("📑 최적화 전략 요약 (PortPulse)")
try:
    summary_df = pd.read_csv("best_strategy_summary.csv")
    st.dataframe(summary_df.T, use_container_width=True)
    st.download_button("📥 전략 요약 다운로드", data=summary_df.to_csv(index=False), file_name="portpulse_strategy_summary.csv")
except FileNotFoundError:
    st.warning("최적화 결과 없음: 먼저 최적화를 실행해주세요.")

# 수익곡선 시각화 및 저장
try:
    equity_df = pd.read_csv("best_equity_curve.csv", index_col=0, parse_dates=True)
    st.subheader("📈 PortPulse 전략 수익 곡선")
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(equity_df.index, equity_df.values, label="PortPulse Strategy", color="green")
    ax.set_title("Equity Curve")
    ax.set_xlabel("Date")
    ax.set_ylabel("Portfolio Value")
    ax.grid(True)
    ax.legend()
    st.pyplot(fig)

    # PNG 다운로드
    from io import BytesIO
    buf = BytesIO()
    fig.savefig(buf, format="png")
    st.download_button("📸 수익 곡선 다운로드 (PNG)", data=buf.getvalue(), file_name="portpulse_equity_curve.png")

except FileNotFoundError:
    st.warning("수익 곡선 데이터가 없습니다.")

st.markdown("---")
st.caption("© 2025 PortPulse 전략 최적화 도구 | Streamlit AI 대시보드")
