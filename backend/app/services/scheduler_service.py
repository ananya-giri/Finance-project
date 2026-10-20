import logging
from datetime import datetime, timedelta, date
from typing import Dict, Any, List, Optional
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session

from backend.app.database import SessionLocal
from backend.app.models.company import Company
from backend.app.models.update_log import UpdateLog
from backend.app.services.historical_ingestion import HistoricalIngestionService
from backend.app.services.metrics_engine import MetricsEngine
from backend.app.config import AUTO_UPDATE_POLL_INTERVAL_MINUTES

logger = logging.getLogger("scheduler_service")

class SchedulerService:
    """
    FR-004 Implementation:
    Automated Report Monitoring and Data Update Engine.
    Continuously monitors companies for newly available quarterly (10-Q)
    or annual (10-K) reports and automatically updates financial statements
    and structured metrics.
    """
    _scheduler: Optional[BackgroundScheduler] = None
    _is_running: bool = False
    _last_run: Optional[datetime] = None
    _poll_interval_minutes: int = AUTO_UPDATE_POLL_INTERVAL_MINUTES

    @classmethod
    def start(cls):
        if cls._scheduler is None:
            cls._scheduler = BackgroundScheduler(daemon=True)
            cls._scheduler.add_job(
                cls._scheduled_poll_job,
                "interval",
                minutes=cls._poll_interval_minutes,
                id="financial_report_watcher",
                replace_existing=True
            )
        if not cls._scheduler.running:
            cls._scheduler.start()
            cls._is_running = True
            logger.info(f"Financial Report Watcher started. Polling every {cls._poll_interval_minutes} minutes.")

    @classmethod
    def stop(cls):
        if cls._scheduler and cls._scheduler.running:
            cls._scheduler.shutdown(wait=False)
            cls._is_running = False
            logger.info("Financial Report Watcher stopped.")

    @classmethod
    def get_status(cls) -> Dict[str, Any]:
        next_run = None
        if cls._scheduler and cls._scheduler.running:
            job = cls._scheduler.get_job("financial_report_watcher")
            if job and job.next_run_time:
                next_run = job.next_run_time.isoformat()

        db = SessionLocal()
        try:
            total_monitored = db.query(Company).filter(Company.auto_sync_enabled == True).count()
            recent_logs = db.query(UpdateLog).order_by(UpdateLog.created_at.desc()).limit(5).all()
            logs_summary = [{
                "id": l.id,
                "ticker": l.ticker,
                "event_type": l.event_type,
                "status": l.status,
                "report_type_detected": l.report_type_detected,
                "period_detected": l.fiscal_period_detected,
                "details": l.details,
                "timestamp": l.created_at.isoformat()
            } for l in recent_logs]
        finally:
            db.close()

        return {
            "scheduler_active": cls._is_running,
            "poll_interval_minutes": cls._poll_interval_minutes,
            "last_check_timestamp": cls._last_run.isoformat() if cls._last_run else None,
            "next_scheduled_run": next_run,
            "monitored_companies_count": total_monitored,
            "recent_audit_logs": logs_summary
        }

    @classmethod
    def set_interval(cls, minutes: int):
        cls._poll_interval_minutes = max(1, minutes)
        if cls._scheduler and cls._scheduler.running:
            cls._scheduler.reschedule_job(
                "financial_report_watcher",
                trigger="interval",
                minutes=cls._poll_interval_minutes
            )
            logger.info(f"Rescheduled watcher interval to {cls._poll_interval_minutes} minutes.")

    @classmethod
    def _scheduled_poll_job(cls):
        logger.info("Auto-update check running for tracked companies...")
        cls._last_run = datetime.utcnow()
        db = SessionLocal()
        try:
            cls.run_update_check(db)
        except Exception as e:
            logger.error(f"Error during scheduled poll: {e}")
        finally:
            db.close()

    @classmethod
    def run_update_check(cls, db: Session, target_ticker: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Executes report availability check across monitored companies.
        """
        cls._last_run = datetime.utcnow()
        query = db.query(Company).filter(Company.auto_sync_enabled == True)
        if target_ticker:
            query = query.filter(Company.ticker == target_ticker.upper())

        companies = query.all()
        results = []

        for comp in companies:
            comp.last_checked_for_updates = datetime.utcnow()
            try:
                # Ingest / check live updates
                ingest_res = HistoricalIngestionService.ingest_company_history(db, comp.ticker)
                
                log = UpdateLog(
                    company_id=comp.id,
                    ticker=comp.ticker,
                    event_type="SCHEDULED_CHECK",
                    status="SUCCESS",
                    report_type_detected="SEC_FILING_QUARTERLY_OR_ANNUAL",
                    fiscal_period_detected=comp.latest_fiscal_period,
                    details=f"Automated check completed. Data refreshed. Latest fiscal period: {comp.latest_fiscal_period}."
                )
                db.add(log)
                db.commit()

                results.append({
                    "ticker": comp.ticker,
                    "status": "SUCCESS",
                    "details": f"Refreshed: {comp.latest_fiscal_period}",
                    "has_five_year_history": comp.has_five_year_history
                })
            except Exception as e:
                db.rollback()
                log = UpdateLog(
                    company_id=comp.id,
                    ticker=comp.ticker,
                    event_type="ERROR",
                    status="ERROR",
                    details=f"Check failed: {str(e)}"
                )
                db.add(log)
                db.commit()
                results.append({
                    "ticker": comp.ticker,
                    "status": "ERROR",
                    "details": str(e)
                })

        return results

    @classmethod
    def simulate_new_report_release(
        cls,
        db: Session,
        ticker: str,
        report_type: str = "QUARTERLY_REPORT_10Q",
        quarter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Simulates the release of a brand-new quarterly or annual report for demonstration
        and validation of FR-004.
        """
        ticker = ticker.upper().strip()
        comp = db.query(Company).filter(Company.ticker == ticker).first()
        if not comp:
            HistoricalIngestionService.ingest_company_history(db, ticker)
            comp = db.query(Company).filter(Company.ticker == ticker).first()

        now = datetime.utcnow()
        current_year = now.year
        target_period = quarter or f"{current_year}-Q3"

        # Generate realistic new financial numbers showing growth
        simulated_metrics = {
            "revenue": 95000000000.0,
            "ebit": 29000000000.0,
            "ebitda": 33000000000.0,
            "net_profit": 24500000000.0,
            "operating_cash_flow": 31000000000.0,
            "free_cash_flow": 27500000000.0,
            "total_assets": 360000000000.0,
            "total_debt": 110000000000.0,
            "total_equity": 65000000000.0,
            "eps": 1.64
        }

        # Store simulated metrics
        metric = MetricsEngine.calculate_and_store_metrics(
            db=db,
            company=comp,
            period_type="QUARTERLY" if "Q" in target_period else "ANNUAL",
            fiscal_period=target_period,
            period_end_date=date.today(),
            data=simulated_metrics,
            source=f"AUTO_DETECTED_{report_type}"
        )

        comp.latest_fiscal_period = target_period
        comp.last_synced_at = now

        # Add audit log
        log = UpdateLog(
            company_id=comp.id,
            ticker=comp.ticker,
            event_type="NEW_REPORT_DETECTED",
            status="UPDATED",
            report_type_detected=report_type,
            fiscal_period_detected=target_period,
            details=f"FR-004 Auto-Update Triggered: New {report_type} published. Ingested financials, updated all 10 core metrics for {target_period}."
        )
        db.add(log)
        db.commit()

        return {
            "status": "UPDATED",
            "ticker": comp.ticker,
            "report_type": report_type,
            "fiscal_period": target_period,
            "metrics_updated": [
                "revenue", "ebitda", "ebit", "net_profit", "operating_margin",
                "operating_cash_flow", "free_cash_flow", "debt_ratio", "eps", "roe", "roa"
            ],
            "timestamp": now.isoformat()
        }
