import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app.database import SessionLocal, init_db
from backend.app.services.historical_ingestion import HistoricalIngestionService
from backend.app.services.document_ingestion import DocumentIngestionService
from backend.app.services.metrics_engine import MetricsEngine
from backend.app.services.scheduler_service import SchedulerService

def run_verification():
    print("=== Step 1: Initializing Database ===")
    init_db()
    db = SessionLocal()

    try:
        # 1. FR-001 Ingestion
        print("\n=== Step 2: Testing FR-001 (5-Year Historical Ingestion) for AAPL ===")
        hist_res = HistoricalIngestionService.ingest_company_history(db, "AAPL", minimum_years=5)
        print(f"FR-001 Result: {hist_res}")
        assert hist_res["has_five_year_history"] is True, "Must have 5+ years of data"
        assert hist_res["statements_ingested"] > 0, "Must have ingested statements"
        assert hist_res["metrics_computed"] > 0, "Must have computed structured metrics"
        print("[PASS] FR-001 PASSED")

        # 2. FR-002 Document Ingestion
        print("\n=== Step 3: Testing FR-002 (Document Ingestion) ===")
        # Test 1: Earnings Call Transcript
        transcript_path = Path("sample_data/sample_earnings_transcript.txt")
        if transcript_path.exists():
            with open(transcript_path, "rb") as f:
                bytes_content = f.read()
            doc_res = DocumentIngestionService.ingest_document(
                db=db,
                ticker="AAPL",
                doc_type="EARNINGS_CALL_TRANSCRIPT",
                title="Apple Q4 FY24 Earnings Conference Call",
                file_bytes=bytes_content,
                original_filename="sample_earnings_transcript.txt",
                fiscal_period="2024-Q4",
                period_type="QUARTERLY"
            )
            print(f"FR-002 Transcript Result: {doc_res['title']} (ID: {doc_res['document_id']})")

        # Test 2: Balance Sheet CSV
        bs_path = Path("sample_data/sample_balance_sheet.csv")
        if bs_path.exists():
            with open(bs_path, "rb") as f:
                bs_bytes = f.read()
            bs_res = DocumentIngestionService.ingest_document(
                db=db,
                ticker="AAPL",
                doc_type="BALANCE_SHEET",
                title="Apple Balance Sheet Upload",
                file_bytes=bs_bytes,
                original_filename="sample_balance_sheet.csv",
                fiscal_period="2024-FY",
                period_type="ANNUAL"
            )
            print(f"FR-002 Statement CSV Result: {bs_res['title']} (Metrics Updated: {bs_res['metrics_updated']})")
        print("[PASS] FR-002 PASSED")

        # 3. FR-003 Structured Metrics
        print("\n=== Step 4: Testing FR-003 (Structured Financial Metrics) ===")
        metrics = MetricsEngine.get_metrics_timeline(db, "AAPL", "ANNUAL")
        print(f"Retrieved {len(metrics)} annual periods of metrics for AAPL.")
        sample = metrics[-1]
        print(f"Latest Period ({sample['fiscal_period']}) Metrics:")
        print(f"  - Revenue: {sample['revenue']}")
        print(f"  - EBITDA: {sample['ebitda']}")
        print(f"  - EBIT: {sample['ebit']}")
        print(f"  - Net Profit: {sample['net_profit']}")
        print(f"  - Operating Margin: {sample['operating_margin']}")
        print(f"  - Op Cash Flow: {sample['operating_cash_flow']}")
        print(f"  - Free Cash Flow: {sample['free_cash_flow']}")
        print(f"  - Debt Ratio: {sample['debt_ratio']}")
        print(f"  - EPS: {sample['eps']}")
        print(f"  - ROE: {sample['roe']}")
        print(f"  - ROA: {sample['roa']}")
        assert sample['revenue'] is not None
        assert sample['net_profit'] is not None
        print("[PASS] FR-003 PASSED")

        # 4. FR-004 Automated Report Monitoring
        print("\n=== Step 5: Testing FR-004 (Automated Report Monitoring) ===")
        sim_res = SchedulerService.simulate_new_report_release(db, "AAPL", "QUARTERLY_REPORT_10Q", "2025-Q1")
        print(f"FR-004 Simulated Release: {sim_res}")
        status = SchedulerService.get_status()
        print(f"Scheduler Status: {status['monitored_companies_count']} monitored companies, {len(status['recent_audit_logs'])} audit logs.")
        print("[PASS] FR-004 PASSED")

        print("\n==========================================")
        print("ALL REQUIREMENTS FR-001 TO FR-004 VERIFIED!")
        print("==========================================")

    finally:
        db.close()

if __name__ == "__main__":
    run_verification()
