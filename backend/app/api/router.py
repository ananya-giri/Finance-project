from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.company import Company
from backend.app.models.unstructured_doc import UnstructuredDocument
from backend.app.models.update_log import UpdateLog
from backend.app.models.structured_metrics import StructuredMetric
from backend.app.api.schemas import (
    CompanyResponse,
    IngestHistoryRequest,
    StructuredMetricItem,
    DocumentItem,
    UpdateLogItem,
    SchedulerStatusResponse
)
from backend.app.services.historical_ingestion import HistoricalIngestionService
from backend.app.services.document_ingestion import DocumentIngestionService, SUPPORTED_DOC_TYPES
from backend.app.services.metrics_engine import MetricsEngine
from backend.app.services.scheduler_service import SchedulerService

router = APIRouter(prefix="/api", tags=["financial-engine"])

@router.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "Fintech Financial Intelligence & Data Management Platform",
        "supported_requirements": ["FR-001", "FR-002", "FR-003", "FR-004"]
    }

# ============================================================================
# FR-001: 5-Year Historical Financial Data Management
# ============================================================================

@router.get("/companies", response_model=List[CompanyResponse])
def get_companies(db: Session = Depends(get_db)):
    """List all tracked companies and their 5-year history completeness status."""
    return db.query(Company).order_by(Company.ticker.asc()).all()

@router.post("/companies/ingest-historical")
def ingest_historical_data(req: IngestHistoryRequest, db: Session = Depends(get_db)):
    """
    FR-001: Ingest historical financial data of companies for a minimum of 5 years.
    Automatically fetches Income Statements, Balance Sheets, Cash Flows,
    calculates all 10 FR-003 metrics, and verifies 5-year history.
    """
    try:
        result = HistoricalIngestionService.ingest_company_history(
            db=db,
            ticker_symbol=req.ticker,
            minimum_years=req.minimum_years
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to ingest historical data: {str(e)}")

# ============================================================================
# FR-002: Document & Statement Ingestion Hub (All 7 Supported Types)
# ============================================================================

@router.get("/documents/supported-types")
def get_supported_doc_types():
    """Returns the list of 7 supported document types specified in FR-002."""
    return SUPPORTED_DOC_TYPES

@router.post("/documents/upload")
async def upload_document(
    ticker: str = Form(...),
    doc_type: str = Form(..., description="INCOME_STATEMENT, BALANCE_SHEET, CASH_FLOW, ANNUAL_REPORT, QUARTERLY_REPORT, INVESTOR_PRESENTATION, EARNINGS_CALL_TRANSCRIPT"),
    title: Optional[str] = Form(None),
    fiscal_period: Optional[str] = Form(None),
    period_type: str = Form("ANNUAL"),
    period_date: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    FR-002: Ingest Income Statements, Balance Sheets, Cash Flow Statements,
    Annual Reports, Quarterly Reports, Investor Presentations, and Earnings Call Transcripts.
    """
    try:
        file_bytes = await file.read()
        p_date = date.fromisoformat(period_date) if period_date else None
        
        result = DocumentIngestionService.ingest_document(
            db=db,
            ticker=ticker,
            doc_type=doc_type,
            title=title or file.filename,
            file_bytes=file_bytes,
            original_filename=file.filename,
            fiscal_period=fiscal_period,
            period_type=period_type,
            period_date=p_date
        )
        return result
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Document ingestion failed: {str(e)}")

@router.get("/documents", response_model=List[DocumentItem])
def list_documents(
    ticker: Optional[str] = None,
    doc_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List ingested documents with metadata and extracted text snippets."""
    query = db.query(UnstructuredDocument)
    if ticker:
        query = query.filter(UnstructuredDocument.ticker == ticker.upper())
    if doc_type:
        query = query.filter(UnstructuredDocument.doc_type == doc_type.upper())
    return query.order_by(UnstructuredDocument.uploaded_at.desc()).all()

# ============================================================================
# FR-003: Structured Financial Metrics Engine (All 10 Core Metrics)
# ============================================================================

@router.get("/metrics/{ticker}", response_model=List[StructuredMetricItem])
def get_company_metrics(
    ticker: str,
    period_type: str = Query("ANNUAL", description="ANNUAL or QUARTERLY"),
    db: Session = Depends(get_db)
):
    """
    FR-003: Retrieves stored structured financial metrics:
    - Revenue
    - EBITDA
    - EBIT
    - Net Profit
    - Operating Margin
    - Cash Flow (Operating & Free Cash Flow)
    - Debt Ratio (Debt-to-Assets, Debt-to-Equity)
    - EPS
    - ROE
    - ROA
    """
    timeline = MetricsEngine.get_metrics_timeline(db, ticker, period_type.upper())
    if not timeline:
        # Check if company exists; if so but no metrics, return empty
        comp = db.query(Company).filter(Company.ticker == ticker.upper()).first()
        if not comp:
            raise HTTPException(status_code=404, detail=f"Company {ticker} not found. Please ingest first.")
    return timeline

@router.get("/metrics/{ticker}/summary")
def get_metrics_summary(ticker: str, db: Session = Depends(get_db)):
    """Executive high-level summary of financial health and 5-year growth rates."""
    comp = db.query(Company).filter(Company.ticker == ticker.upper()).first()
    if not comp:
        raise HTTPException(status_code=404, detail=f"Company {ticker} not found.")

    annual_metrics = db.query(StructuredMetric).filter(
        StructuredMetric.company_id == comp.id,
        StructuredMetric.period_type == "ANNUAL"
    ).order_by(StructuredMetric.period_end_date.asc()).all()

    if not annual_metrics:
        return {"ticker": comp.ticker, "summary": "No historical annual data ingested yet."}

    latest = annual_metrics[-1]
    oldest = annual_metrics[0]
    years_span = max(1, len(annual_metrics) - 1)

    cagr_revenue = None
    if oldest.revenue and latest.revenue and oldest.revenue > 0 and latest.revenue > 0:
        cagr_revenue = round(((latest.revenue / oldest.revenue) ** (1 / years_span) - 1) * 100, 2)

    return {
        "ticker": comp.ticker,
        "company_name": comp.name,
        "sector": comp.sector,
        "industry": comp.industry,
        "years_covered": len(annual_metrics),
        "has_five_year_history": comp.has_five_year_history,
        "period_range": f"{oldest.fiscal_period} to {latest.fiscal_period}",
        "latest_metrics": {
            "period": latest.fiscal_period,
            "revenue": latest.revenue,
            "ebitda": latest.ebitda,
            "ebit": latest.ebit,
            "net_profit": latest.net_profit,
            "operating_margin_pct": round(latest.operating_margin * 100, 2) if latest.operating_margin is not None else None,
            "operating_cash_flow": latest.operating_cash_flow,
            "free_cash_flow": latest.free_cash_flow,
            "debt_ratio": latest.debt_ratio,
            "eps": latest.eps,
            "roe_pct": round(latest.roe * 100, 2) if latest.roe is not None else None,
            "roa_pct": round(latest.roa * 100, 2) if latest.roa is not None else None
        },
        "revenue_5yr_cagr_pct": cagr_revenue,
        "status": "HEALTHY" if (latest.operating_margin or 0) > 0.15 else "MODERATE"
    }

# ============================================================================
# FR-004: Automated Report Monitoring & Scheduler
# ============================================================================

@router.get("/scheduler/status", response_model=SchedulerStatusResponse)
def get_scheduler_status():
    """FR-004: Returns current status of automated report watcher and audit summary."""
    return SchedulerService.get_status()

@router.post("/scheduler/check-now")
def trigger_immediate_check(ticker: Optional[str] = None, db: Session = Depends(get_db)):
    """FR-004: Immediately checks for newly available reports across tracked companies."""
    results = SchedulerService.run_update_check(db, ticker)
    return {"status": "SUCCESS", "message": "Manual check completed", "results": results}

@router.post("/scheduler/simulate-new-report")
def simulate_new_report(ticker: str, report_type: str = "QUARTERLY_REPORT_10Q", quarter: Optional[str] = None, db: Session = Depends(get_db)):
    """
    FR-004: Simulates a new quarterly or annual filing publication
    to test automated detection, ingestion, and metric recalculation.
    """
    return SchedulerService.simulate_new_report_release(db, ticker, report_type, quarter)

@router.post("/scheduler/interval")
def set_scheduler_interval(minutes: int = Query(..., ge=1, le=1440)):
    """Configure automated polling interval in minutes."""
    SchedulerService.set_interval(minutes)
    return {"status": "SUCCESS", "poll_interval_minutes": minutes}

@router.get("/scheduler/logs", response_model=List[UpdateLogItem])
def get_update_logs(limit: int = 50, db: Session = Depends(get_db)):
    """FR-004: Audit log of automated checks, new reports detected, and metrics updates."""
    return db.query(UpdateLog).order_by(UpdateLog.created_at.desc()).limit(limit).all()
