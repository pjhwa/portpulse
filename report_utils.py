# report_utils.py
from fpdf import FPDF
import datetime

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

    def output_report(self, filename="portpulse_strategy_report.pdf"):
        self.output(filename)


def generate_pdf_report(date_str, weights, explanation, metrics):
    pdf = PDFReport()
    pdf.add_page()
    pdf.add_section("📅 분석일자", date_str)
    pdf.add_section("💼 포트폴리오 비중", f"TSLA: {weights[0]*100:.1f}%, TSLL: {weights[1]*100:.1f}%")
    pdf.add_section("📊 전략 설명", explanation)
    summary = f"CAGR: {metrics['CAGR']*100:.2f}%\nSharpe: {metrics['Sharpe']:.2f}\nMax Drawdown: {metrics['MaxDrawdown']*100:.2f}%"
    pdf.add_section("📈 성과 요약", summary)
    pdf.output_report()
    return "portpulse_strategy_report.pdf"
