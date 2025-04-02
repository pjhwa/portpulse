# 🧠 PortPulse: TSLA/TSLL 포트폴리오 최적화 전략

**PortPulse**는 시장 지표와 기술적 분석을 활용하여 TSLA/TSLL 포트폴리오 비중을 자동 조정하고, 수익률을 극대화하는 전략을 제공합니다. Streamlit 기반 대시보드, 백테스트, 전략 최적화 및 리포트 기능을 포함합니다.

---

## 🚀 주요 기능

| 기능 | 설명 |
|------|------|
| 📊 포트폴리오 전략 분석 | RSI, MACD, Bollinger Bands, ATR, VIX, 금리, Fear & Greed Index 기반 비중 제안 |
| 🧪 시뮬레이션 | 사용자 정의 날짜 범위 기반 전략 백테스트 |
| 📈 성과 비교 | PortPulse 전략 vs TSLA vs TSLL vs SPY vs QQQ 수익률 비교 |
| 🔍 자동 최적화 | Sharpe, CAGR, Max Drawdown 기반 자동 임계값 튜닝 |
| 📄 PDF 리포트 | 전략 분석 결과를 리포트로 생성 및 다운로드 가능 |
| ☁️ 대시보드 | Streamlit 웹 UI를 통한 인터랙티브 분석 도구 |

---

## 🧱 설치 및 실행

```bash
# 필요한 라이브러리 설치
pip install -r requirements.txt

# 대시보드 실행
streamlit run dashboard.py
```

---

## 📂 주요 파일 구조

```text
.
├── dashboard.py              # Streamlit 대시보드
├── main.py                   # CLI 진입점 (옵션 기반 실행 가능)
├── core/
│   ├── backtest.py           # 백테스트 로직
│   ├── fetch.py              # 데이터 수집 및 정규화
│   ├── indicators.py         # 기술적 지표 계산
│   ├── signal.py             # 포트폴리오 비중 결정 로직
│   ├── optimize.py           # 전략 자동 최적화
├── data/
│   └── db.py                 # SQLite 데이터 저장소
├── report_utils.py           # PDF 리포트 생성
├── email_utils.py            # 이메일 전송 기능
├── requirements.txt          # 종속성 정의
```

---

## 📊 사용 예시

- 시뮬레이션:
  > 📅 `2023-01-01 ~ 2024-12-31` 기간 수익률 비교 및 전략 비중 분석

- 결과:
  > CAGR 12.5%, Sharpe 1.4, Max Drawdown 18.3%

---

## 📧 이메일 리포트

- PDF 보고서 자동 생성
- 이메일 전송 기능 지원 (`email_utils.py`)

---

## 🌐 GitHub

[🔗 GitHub Repository](https://github.com/pjhwa/portpulse)

---

## 📎 참고

- TSLL: TSLA 2배 레버리지 ETF
- 데이터 소스: Yahoo Finance (yfinance), CNN Fear & Greed Index, VIX 등
