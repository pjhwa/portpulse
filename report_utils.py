# report_utils.py
from fpdf import FPDF
import datetime
import os

class PDFReport(FPDF):
    def header(self):
        self.set_font("Arial", "B", 12)
        self.cell(0, 10, "PortPulse Daily Strategy Report", 0, 1, "C")
        self.set_font("Arial", "", 10)
        self.cell(0, 10, f"Generated on: {datetime.date.today()}", 0, 1, "R")
        self.ln(5)

    def add_section(self, title, content):
        self.set_font("Arial", "B", 11)
        self.cell(0, 10, title, ln=True)
        self.set_font("Arial", "", 10)
        self.multi_cell(0, 8, content)
        self.ln(4)

    def add_image(self, image_path):
        if os.path.exists(image_path):
            self.image(image_path, x=10, w=190)
            self.ln(10)

    def output_report(self, filename=None):
        if filename is None:
            today = datetime.date.today().strftime("%Y-%m-%d")
            os.makedirs("reports", exist_ok=True)
            filename = f"reports/{today}_portpulse_strategy_report.pdf"
        self.output(filename)

def generate_pdf_report(date_str, weights, explanation, metrics, equity_chart_path=None):
    pdf = PDFReport()
    pdf.add_page()
    pdf.add_section("📅 분석일자", date_str)
    pdf.add_section("💼 포트폴리오 비중", f"TSLA: {weights[0]*100:.1f}%, TSLL: {weights[1]*100:.1f}%")
    pdf.add_section("📊 전략 설명", explanation)
    summary = f"CAGR: {metrics['CAGR']*100:.2f}%\nSharpe: {metrics['Sharpe']:.2f}\nMax Drawdown: {metrics['MaxDrawdown']*100:.2f}%"
    pdf.add_section("📈 성과 요약", summary)

    if equity_chart_path and os.path.exists(equity_chart_path):
        pdf.add_section("📉 수익 곡선 비교 (PortPulse vs TSLA/TSLL/시장)", "아래는 전략과 벤치마크 비교 수익 곡선입니다.")
        pdf.add_image(equity_chart_path)

    pdf.output_report()
    return "portpulse_strategy_report.pdf"
