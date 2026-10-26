from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.company import Company
from backend.app.models.unstructured_doc import UnstructuredDocument
from backend.app.models.update_log import UpdateLog
from backend.app.models.structured_metrics import StructuredMetric
from backend.app.models.market_intelligence import EconomicIndicator, MarketIntelligenceEvent
from backend.app.models.multi_agent import OrchestrationRun, AgentExecutionTrace
from backend.app.api.schemas import (
    CompanyResponse,
    IngestHistoryRequest,
    StructuredMetricItem,
    DocumentItem,
    UpdateLogItem,
    SchedulerStatusResponse,
    EconomicIndicatorItem,
    MarketEventItem,
    CreateMarketEventRequest,
    ClassifyEventRequest,
    ClassifyEventResponse,
    MarketIntelligenceDashboardResponse,
    RAGSearchRequest,
    RAGSearchResponse,
    RAGRecommendRequest,
    RAGRecommendResponse,
    RAGStatusResponse,
    RAGIndexAllResponse,
    AgentMetadataItem,
    AgentRunRequest,
    AgentResultResponse,
    OrchestrationRunRequest,
    OrchestrationRunResponse,
    OrchestrationHistoryItem
)
from backend.app.services.historical_ingestion import HistoricalIngestionService
from backend.app.services.document_ingestion import DocumentIngestionService, SUPPORTED_DOC_TYPES
from backend.app.services.metrics_engine import MetricsEngine
from backend.app.services.scheduler_service import SchedulerService
from backend.app.services.market_intelligence import MarketIntelligenceService
from backend.app.services.rag_service import RAGService
from backend.app.services.agents import AgentRegistry, AgentContext, OrchestratorAgent
import json


router = APIRouter(prefix="/api", tags=["financial-engine"])

@router.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "Fintech Financial Intelligence & Data Management Platform",
        "supported_requirements": [
            "FR-001", "FR-002", "FR-003", "FR-004",
            "FR-005", "FR-006", "FR-007", "FR-008", "FR-009",
            "FR-010", "FR-011", "FR-012", "FR-013", "FR-014",
            "FR-015", "FR-016", "FR-017", "FR-018", "FR-019",
            "FR-020", "FR-021", "FR-022", "FR-023"
        ]
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

# ============================================================================
# Section 2.2 External Market Intelligence Collection (FR-005 to FR-009)
# ============================================================================

@router.get("/market-intelligence/overview", response_model=MarketIntelligenceDashboardResponse)
def get_market_intelligence_overview(db: Session = Depends(get_db)):
    """
    Overview scorecard for Section 2.2:
    Indicators count, categories breakdown, events distribution across impact categories (FR-009).
    """
    return MarketIntelligenceService.get_dashboard_summary(db)

@router.get("/market-intelligence/indicators", response_model=List[EconomicIndicatorItem])
def get_economic_indicators(
    category: Optional[str] = Query(None, description="EXCHANGE_RATE, INFLATION_RATE, INTEREST_RATE, COMMODITY_PRICE, STOCK_INDEX, INDUSTRY_GROWTH"),
    db: Session = Depends(get_db)
):
    """
    FR-005 & FR-006: Retrieves external economic indicators across all 6 core categories.
    """
    # Seed indicators if empty
    count = db.query(EconomicIndicator).count()
    if count == 0:
        MarketIntelligenceService.collect_all_indicators(db)

    query = db.query(EconomicIndicator)
    if category and category.upper() != "ALL":
        query = query.filter(EconomicIndicator.category == category.upper())
    return query.order_by(EconomicIndicator.category.asc(), EconomicIndicator.name.asc()).all()

@router.post("/market-intelligence/indicators/sync")
def sync_economic_indicators(db: Session = Depends(get_db)):
    """
    FR-005 & FR-006: Triggers continuous / live collection of external economic indicators.
    """
    res = MarketIntelligenceService.collect_all_indicators(db)
    return res

@router.get("/market-intelligence/events", response_model=List[MarketEventItem])
def get_market_events(
    impact_category: Optional[str] = Query(None, description="FINANCIAL, REGULATORY, POLITICAL, ENVIRONMENTAL, SUPPLY_CHAIN, COMPETITIVE"),
    event_type: Optional[str] = Query(None, description="TARIFF_CHANGE, TRADE_RESTRICTION, SANCTION, IMPORT_EXPORT_CURB, TAX_POLICY, GOVERNMENT_REGULATION, NEWS_ARTICLE, MARKET_REPORT"),
    severity: Optional[str] = Query(None, description="CRITICAL, HIGH, MEDIUM, LOW"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """
    FR-007, FR-008 & FR-009: Retrieves geopolitical/regulatory events, news, and market reports
    filtered by impact category and event type.
    """
    MarketIntelligenceService.seed_initial_events_if_empty(db)
    query = db.query(MarketIntelligenceEvent)

    if impact_category and impact_category.upper() != "ALL":
        query = query.filter(MarketIntelligenceEvent.impact_category == impact_category.upper())
    if event_type and event_type.upper() != "ALL":
        query = query.filter(MarketIntelligenceEvent.event_type == event_type.upper())
    if severity and severity.upper() != "ALL":
        query = query.filter(MarketIntelligenceEvent.severity == severity.upper())

    return query.order_by(MarketIntelligenceEvent.event_date.desc()).limit(limit).all()

@router.post("/market-intelligence/events", response_model=MarketEventItem)
def create_market_event(req: CreateMarketEventRequest, db: Session = Depends(get_db)):
    """
    FR-007 & FR-008: Ingests a new geopolitical, regulatory, or market intelligence event.
    Automatically applies FR-009 classification if impact_category is omitted.
    """
    import json
    from datetime import datetime

    impact_cat = req.impact_category
    sev = req.severity
    sent = req.sentiment
    conf = 0.88
    sectors = req.affected_sectors or []
    tickers = req.affected_tickers or []

    # If category not provided, auto-classify using FR-009 engine
    if not impact_cat:
        classified = MarketIntelligenceService.classify_external_event(f"{req.title}. {req.summary}")
        impact_cat = classified["impact_category"]
        sev = classified["severity"]
        sent = classified["sentiment"]
        conf = classified["confidence_score"]
        if not sectors:
            sectors = classified["affected_sectors"]
        if not tickers:
            tickers = classified["affected_tickers"]

    new_event = MarketIntelligenceEvent(
        title=req.title,
        summary=req.summary,
        event_type=req.event_type.upper(),
        impact_category=impact_cat.upper(),
        severity=sev.upper(),
        sentiment=sent.upper(),
        confidence_score=conf,
        source=req.source or "Intelligence Network",
        source_url=req.source_url,
        affected_sectors=json.dumps(sectors),
        affected_tickers=json.dumps(tickers),
        event_date=datetime.utcnow()
    )
    db.add(new_event)
    db.commit()
    db.refresh(new_event)
    return new_event

@router.post("/market-intelligence/classify", response_model=ClassifyEventResponse)
def classify_market_event(req: ClassifyEventRequest):
    """
    FR-009: Live NLP & Heuristic Event Impact Classifier.
    Analyzes any text input and classifies it into:
    - FINANCIAL
    - REGULATORY
    - POLITICAL
    - ENVIRONMENTAL
    - SUPPLY_CHAIN
    - COMPETITIVE
    Returns detected event type, severity, sentiment, affected sectors, and suggested actions.
    """
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")
    return MarketIntelligenceService.classify_external_event(req.text)

@router.get("/market-intelligence/news", response_model=List[MarketEventItem])
def get_market_news_and_reports(
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    FR-008: Retrieves relevant financial news articles and analytical market reports.
    """
    MarketIntelligenceService.seed_initial_events_if_empty(db)
    query = db.query(MarketIntelligenceEvent).filter(
        MarketIntelligenceEvent.event_type.in_(["NEWS_ARTICLE", "MARKET_REPORT"])
    )
    return query.order_by(MarketIntelligenceEvent.event_date.desc()).limit(limit).all()

@router.post("/market-intelligence/news/sync")
def sync_market_news(db: Session = Depends(get_db)):
    """
    FR-008: Triggers live collection of recent market news and analytical reports.
    """
    count = MarketIntelligenceService.collect_live_market_news(db)
    return {"status": "SUCCESS", "articles_collected": count}

@router.get("/market-intelligence/impact-matrix")
def get_impact_matrix(db: Session = Depends(get_db)):
    """
    FR-009: Generates an impact category distribution matrix across severities.
    """
    MarketIntelligenceService.seed_initial_events_if_empty(db)
    events = db.query(MarketIntelligenceEvent).all()
    categories = ["FINANCIAL", "REGULATORY", "POLITICAL", "ENVIRONMENTAL", "SUPPLY_CHAIN", "COMPETITIVE"]
    matrix = {cat: {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "TOTAL": 0} for cat in categories}

    for ev in events:
        cat = ev.impact_category
        sev = ev.severity
        if cat in matrix and sev in matrix[cat]:
            matrix[cat][sev] += 1
            matrix[cat]["TOTAL"] += 1

    return matrix

# ============================================================================
# Section 2.3 Knowledge Management and RAG (FR-010 to FR-014)
# ============================================================================

@router.get("/rag/status", response_model=RAGStatusResponse)
def get_rag_status(db: Session = Depends(get_db)):
    """
    FR-010: Returns persistent vector storage status, chunk counts,
    and verified embedding model specifications (BAAI/bge-small-en-v1.5).
    """
    return RAGService.get_rag_status(db)

@router.post("/rag/index/{document_id}")
def index_document(document_id: int, force: bool = Query(False), db: Session = Depends(get_db)):
    """
    FR-010: Explicitly trigger persistent vector indexing for a document.
    Calculates SHA-256 hashes and guarantees idempotency.
    """
    try:
        return RAGService.index_document(db=db, document_id=document_id, force=force)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Indexing failed: {str(e)}")

@router.post("/rag/index-all", response_model=RAGIndexAllResponse)
def index_all_documents(force: bool = Query(False), db: Session = Depends(get_db)):
    """
    FR-010: Indexes / synchronizes all unstructured documents in the knowledge base.
    Guarantees idempotency via SHA-256 content hashing to avoid duplicate chunks.
    """
    try:
        return RAGService.index_all_unindexed(db=db, force=force)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backfill indexing failed: {str(e)}")

@router.post("/rag/search", response_model=RAGSearchResponse)
def search_semantic_evidence(req: RAGSearchRequest, db: Session = Depends(get_db)):
    """
    FR-011, FR-012, FR-013: Semantic Evidence Retrieval.
    - Symmetrically computes query vector via BAAI/bge-small-en-v1.5 (384 dimensions).
    - Filters by ticker, doc_type, fiscal_period, industry, geography, and confidence score (FR-013).
    - Ranks by cosine similarity and suppresses near-duplicates (FR-011).
    - Preserves verifiable provenance and source attribution (FR-012).
    """
    try:
        return RAGService.search_evidence(
            db=db,
            query=req.query,
            ticker=req.ticker,
            doc_type=req.doc_type,
            fiscal_period=req.fiscal_period,
            industry=req.industry,
            geography=req.geography,
            min_confidence=req.min_confidence,
            min_similarity=req.min_similarity or 0.35,
            top_k=req.top_k or 5
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Semantic retrieval failed: {str(e)}")

@router.post("/rag/recommend", response_model=RAGRecommendResponse)
def generate_grounded_recommendation(req: RAGRecommendRequest, db: Session = Depends(get_db)):
    """
    FR-014: Grounded Financial Recommendations & RAG Synthesis.
    - Synthesizes actionable recommendations strictly grounded in retrieved evidence.
    - References verifiable citations [Citation 1, Citation 2, ...].
    - Guardrail against hallucinations: Returns explicit INSUFFICIENT_EVIDENCE if no
      verified evidence passes the relevance threshold.
    """
    try:
        return RAGService.generate_grounded_recommendation(
            db=db,
            query=req.query,
            ticker=req.ticker,
            doc_type=req.doc_type,
            fiscal_period=req.fiscal_period,
            industry=req.industry,
            geography=req.geography,
            min_confidence=req.min_confidence,
            min_similarity=req.min_similarity if req.min_similarity is not None else 0.68,
            top_k=req.top_k or 4
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Recommendation synthesis failed: {str(e)}")


# ============================================================================
# Section 2.4: Multi-Agent Orchestration (FR-015 to FR-023)
# ============================================================================

@router.get("/agents", response_model=List[AgentMetadataItem])
def list_agents():
    """
    FR-015: The platform shall support multiple specialized AI agents.
    Returns the metadata, capabilities, roles, and status of all registered agents:
    - FR-016: Financial Analysis Agent
    - FR-017: Economic Intelligence Agent
    - FR-018: Geopolitical Risk Agent
    - FR-019: Industry Intelligence Agent
    - FR-020: Forecasting Agent
    - FR-021: Recommendation Agent
    - FR-022: Explainability Agent
    - FR-023: Orchestrator Agent
    """
    return AgentRegistry.list_agents()

@router.get("/agents/{agent_id}", response_model=AgentMetadataItem)
def get_agent_details(agent_id: str):
    """Retrieve metadata and capabilities for a specific specialized agent."""
    agent = AgentRegistry.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Specialized agent '{agent_id}' not found.")
    return agent.get_metadata()

@router.post("/agents/{agent_id}/run", response_model=AgentResultResponse)
def run_individual_agent(agent_id: str, req: AgentRunRequest, db: Session = Depends(get_db)):
    """
    FR-015 to FR-022: Executes an individual specialized AI agent on demand.
    Allows ad-hoc analytical deep dives for a company ticker.
    """
    agent = AgentRegistry.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Specialized agent '{agent_id}' not found.")
    
    ctx = AgentContext(ticker=req.ticker, db=db, parameters=req.parameters or {})
    result = agent.run(ctx)
    return AgentResultResponse(
        agent_id=result.agent_id,
        agent_name=result.agent_name,
        status=result.status,
        confidence_score=result.confidence_score,
        execution_time_ms=result.execution_time_ms,
        summary=result.summary,
        data=result.data,
        key_insights=result.key_insights,
        error=result.error
    )

@router.post("/orchestration/run", response_model=OrchestrationRunResponse)
def run_orchestration(req: OrchestrationRunRequest, db: Session = Depends(get_db)):
    """
    FR-023: The Orchestrator Agent shall coordinate all agents.
    Coordinates parallel data discovery, forward forecasting, strategic recommendation formulation,
    and transparent causal explainability.
    """
    orchestrator = AgentRegistry.get_agent("ORCHESTRATOR") or OrchestratorAgent()
    ctx = AgentContext(ticker=req.ticker, db=db, parameters=req.parameters or {})
    
    result = orchestrator.run(ctx)
    if result.status == "FAILED":
        raise HTTPException(status_code=500, detail=f"Multi-agent orchestration failed: {result.error}")
    
    dossier = result.data
    return OrchestrationRunResponse(
        run_id=dossier.get("run_id", "unknown"),
        ticker=dossier.get("ticker", req.ticker),
        status=dossier.get("status", "COMPLETED"),
        consensus_stance=dossier.get("consensus_stance", "HOLD"),
        conviction_score=dossier.get("conviction_score", 75.0),
        total_execution_ms=dossier.get("total_execution_ms", 0),
        timestamp=dossier.get("timestamp", ""),
        executive_summary=dossier.get("executive_summary", ""),
        agent_findings=dossier.get("agent_findings", {}),
        inter_agent_messages=dossier.get("inter_agent_messages", []),
        orchestrator_metadata=dossier.get("orchestrator_metadata", {})
    )

@router.get("/orchestration/runs", response_model=List[OrchestrationHistoryItem])
def get_orchestration_history(
    ticker: Optional[str] = Query(None, description="Optional filter by ticker symbol"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Returns chronological audit logs and dossiers of previous multi-agent orchestration runs."""
    q = db.query(OrchestrationRun)
    if ticker:
        q = q.filter(OrchestrationRun.ticker == ticker.upper().strip())
    runs = q.order_by(OrchestrationRun.created_at.desc()).limit(limit).all()
    return runs

@router.get("/orchestration/runs/{run_id}")
def get_orchestration_run_detail(run_id: str, db: Session = Depends(get_db)):
    """Retrieves full serialized multi-agent dossier and granular agent execution traces for a run ID."""
    run = db.query(OrchestrationRun).filter(OrchestrationRun.run_id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail=f"Orchestration run '{run_id}' not found.")
    
    traces = db.query(AgentExecutionTrace).filter(AgentExecutionTrace.run_id == run_id).all()
    
    parsed_dossier = {}
    if run.full_dossier_json:
        try:
            parsed_dossier = json.loads(run.full_dossier_json)
        except Exception:
            parsed_dossier = {"raw": run.full_dossier_json}
    
    return {
        "run_id": run.run_id,
        "ticker": run.ticker,
        "status": run.status,
        "consensus_stance": run.consensus_stance,
        "confidence_score": run.confidence_score,
        "executive_summary": run.executive_summary,
        "total_execution_ms": run.total_execution_ms,
        "created_at": run.created_at,
        "dossier": parsed_dossier,
        "traces": [
            {
                "agent_id": t.agent_id,
                "agent_name": t.agent_name,
                "status": t.status,
                "confidence_score": t.confidence_score,
                "execution_time_ms": t.execution_time_ms,
                "error_message": t.error_message,
                "created_at": t.created_at
            }
            for t in traces
        ]
    }

@router.get("/orchestration/latest/{ticker}")
def get_latest_orchestration_for_ticker(ticker: str, db: Session = Depends(get_db)):
    """Retrieves the latest available multi-agent dossier for a specific company."""
    t_clean = ticker.upper().strip()
    run = (
        db.query(OrchestrationRun)
        .filter(OrchestrationRun.ticker == t_clean)
        .order_by(OrchestrationRun.created_at.desc())
        .first()
    )
    if not run:
        return {"status": "NO_PREVIOUS_RUN", "ticker": t_clean, "dossier": None}
    
    parsed_dossier = {}
    if run.full_dossier_json:
        try:
            parsed_dossier = json.loads(run.full_dossier_json)
        except Exception:
            pass
            
    return {
        "status": "FOUND",
        "run_id": run.run_id,
        "ticker": run.ticker,
        "consensus_stance": run.consensus_stance,
        "confidence_score": run.confidence_score,
        "created_at": run.created_at,
        "dossier": parsed_dossier
    }

