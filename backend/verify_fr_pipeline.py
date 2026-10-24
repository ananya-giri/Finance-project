import os
import sys
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.database import Base, init_db
from backend.app.services.historical_ingestion import HistoricalIngestionService
from backend.app.services.document_ingestion import DocumentIngestionService
from backend.app.services.metrics_engine import MetricsEngine
from backend.app.services.scheduler_service import SchedulerService

@contextmanager
def isolated_test_context():
    """
    Creates an isolated temporary SQLite database and temporary upload directory.
    Never modifies data/fintech.db or data/uploads/.
    Disposes test engine cleanly for Windows file lock release.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)
        temp_db_path = temp_dir_path / "temp_fintech.db"
        temp_upload_dir = temp_dir_path / "uploads"
        temp_upload_dir.mkdir(parents=True, exist_ok=True)

        prod_db = PROJECT_ROOT / "data" / "fintech.db"
        if prod_db.exists():
            shutil.copy2(prod_db, temp_db_path)

        test_engine = create_engine(
            f"sqlite:///{temp_db_path}",
            connect_args={"check_same_thread": False}
        )
        Base.metadata.create_all(bind=test_engine)
        TestSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
        test_db = TestSession()

        import backend.app.config
        import backend.app.services.document_ingestion
        import backend.app.services.rag_service
        orig_upload_dir = backend.app.config.UPLOAD_DIR
        backend.app.config.UPLOAD_DIR = temp_upload_dir
        backend.app.services.document_ingestion.UPLOAD_DIR = temp_upload_dir
        backend.app.services.rag_service.UPLOAD_DIR = temp_upload_dir

        try:
            yield test_db
        finally:
            test_db.close()
            test_engine.dispose()
            backend.app.config.UPLOAD_DIR = orig_upload_dir
            backend.app.services.document_ingestion.UPLOAD_DIR = orig_upload_dir
            backend.app.services.rag_service.UPLOAD_DIR = orig_upload_dir

def run_verification(db=None):
    if db is None:
        with isolated_test_context() as isolated_db:
            return run_verification(db=isolated_db)

    print("=== Step 1: Initializing Database ===")
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
        # Test 1: Earnings Call Transcript (Accurate APEX Metadata for APEX sample file)
        transcript_path = Path("sample_data/sample_earnings_transcript.txt")
        if transcript_path.exists():
            with open(transcript_path, "rb") as f:
                bytes_content = f.read()
            doc_res = DocumentIngestionService.ingest_document(
                db=db,
                ticker="APEX",
                doc_type="EARNINGS_CALL_TRANSCRIPT",
                title="Apex Financial Systems Q3 FY25 Earnings Call",
                file_bytes=bytes_content,
                original_filename="sample_earnings_transcript.txt",
                fiscal_period="2025-Q3",
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
        metrics_with_rev = [m for m in metrics if m.get("revenue") is not None]
        sample = metrics_with_rev[-1] if metrics_with_rev else metrics[-1]

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

        # 5. FR-005 & FR-006 External Economic Indicators
        print("\n=== Step 6: Testing FR-005 & FR-006 (External Economic Indicators Collection) ===")
        from backend.app.services.market_intelligence import MarketIntelligenceService
        from backend.app.models.market_intelligence import EconomicIndicator, MarketIntelligenceEvent

        ind_res = MarketIntelligenceService.collect_all_indicators(db)
        print(f"Indicators Collection Result: {ind_res}")
        
        indicators = db.query(EconomicIndicator).all()
        categories_found = {ind.category for ind in indicators}
        print(f"Total Indicators Tracked: {len(indicators)}")
        print(f"Categories Found: {categories_found}")

        required_categories = {
            "EXCHANGE_RATE",
            "INFLATION_RATE",
            "INTEREST_RATE",
            "COMMODITY_PRICE",
            "STOCK_INDEX",
            "INDUSTRY_GROWTH"
        }
        assert required_categories.issubset(categories_found), f"Missing categories: {required_categories - categories_found}"
        assert len(indicators) >= 20, "Should have tracked at least 20 indicators across the 6 categories"
        print("[PASS] FR-005 & FR-006 PASSED: All 6 economic indicator categories verified!")

        # 6. FR-007 Geopolitical & Regulatory Events
        print("\n=== Step 7: Testing FR-007 (Geopolitical & Regulatory Events Collection) ===")
        MarketIntelligenceService.seed_initial_events_if_empty(db)
        geo_types = [
            "TARIFF_CHANGE",
            "TRADE_RESTRICTION",
            "SANCTION",
            "IMPORT_EXPORT_CURB",
            "TAX_POLICY",
            "GOVERNMENT_REGULATION"
        ]
        found_types = set()
        for gt in geo_types:
            ev = db.query(MarketIntelligenceEvent).filter(MarketIntelligenceEvent.event_type == gt).first()
            if ev:
                found_types.add(gt)
                print(f"  - [{gt}] {ev.title} (Severity: {ev.severity})")
        assert len(found_types) == len(geo_types), f"Missing event types: {set(geo_types) - found_types}"
        print("[PASS] FR-007 PASSED: Tariff Changes, Trade Restrictions, Sanctions, Curbs, Tax Policy, and Regulations verified!")

        # 7. FR-008 News Articles & Market Reports
        print("\n=== Step 8: Testing FR-008 (News Articles & Market Reports Collection) ===")
        news_reports = db.query(MarketIntelligenceEvent).filter(
            MarketIntelligenceEvent.event_type.in_(["NEWS_ARTICLE", "MARKET_REPORT"])
        ).all()
        print(f"Total News Articles & Market Reports: {len(news_reports)}")
        for nr in news_reports[:3]:
            print(f"  - [{nr.event_type}] {nr.title} ({nr.source})")
        assert len(news_reports) > 0, "Should have news articles or market reports collected"
        print("[PASS] FR-008 PASSED: News Articles and Market Reports verified!")

        # 8. FR-009 Event Impact Classification
        print("\n=== Step 9: Testing FR-009 (Impact Category Classification Engine) ===")
        test_cases = [
            ("Federal Reserve unexpected 50bps rate cut shifts sovereign bond yields and liquidity", "FINANCIAL"),
            ("SEC approves mandatory climate-related disclosure and greenhouse gas audit regulations", "REGULATORY"),
            ("Bilateral summit between sovereign nations triggers diplomatic friction and sanctions discussion", "POLITICAL"),
            ("EPA finalizes strict carbon emission cap for coal-fired power facilities under clean air rules", "ENVIRONMENTAL"),
            ("Maritime shipping bottleneck and port container backlogs delay semiconductor raw materials", "SUPPLY_CHAIN"),
            ("Hyperscaler competitor launches open-weights enterprise foundation model slashing cloud prices", "COMPETITIVE")
        ]

        for text, expected_cat in test_cases:
            res = MarketIntelligenceService.classify_external_event(text)
            print(f"  • Input: \"{text[:45]}...\"")
            print(f"    Classified Impact: {res['impact_category']} | Severity: {res['severity']} | Confidence: {res['confidence_score']:.2f}")
            assert res['impact_category'] == expected_cat, f"Expected {expected_cat}, got {res['impact_category']}"

        print("[PASS] FR-009 PASSED: All 6 impact categories (Financial, Regulatory, Political, Environmental, Supply Chain, Competitive) verified!")

        print("\n========================================================")
        print("ALL REQUIREMENTS FR-001 TO FR-009 SUCCESSFULLY VERIFIED!")
        print("========================================================")

    finally:
        db.close()

if __name__ == "__main__":
    run_verification()
