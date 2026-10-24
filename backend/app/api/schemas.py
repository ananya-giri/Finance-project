from datetime import datetime, date
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class CompanyResponse(BaseModel):
    id: int
    ticker: str
    name: str
    sector: Optional[str] = None
    industry: Optional[str] = None
    country: Optional[str] = None
    currency: Optional[str] = "USD"
    years_of_data_available: int
    has_five_year_history: bool
    latest_fiscal_year: Optional[int] = None
    latest_fiscal_period: Optional[str] = None
    last_synced_at: Optional[datetime] = None
    auto_sync_enabled: bool

    class Config:
        from_attributes = True

class IngestHistoryRequest(BaseModel):
    ticker: str = Field(..., description="Stock ticker symbol, e.g. AAPL, MSFT, TSLA")
    minimum_years: int = Field(5, description="Minimum historical years to ingest (FR-001)")

class StructuredMetricItem(BaseModel):
    id: int
    fiscal_period: str
    period_end_date: str
    year: int
    # 10 Core FR-003 Metrics:
    revenue: Optional[float] = None
    ebitda: Optional[float] = None
    ebit: Optional[float] = None
    net_profit: Optional[float] = None
    operating_margin: Optional[float] = None
    operating_cash_flow: Optional[float] = None
    free_cash_flow: Optional[float] = None
    debt_ratio: Optional[float] = None
    debt_to_equity: Optional[float] = None
    eps: Optional[float] = None
    roe: Optional[float] = None
    roa: Optional[float] = None
    # Auxiliary indicators:
    gross_margin: Optional[float] = None
    current_ratio: Optional[float] = None
    source: Optional[str] = None
    updated_at: Optional[str] = None

class DocumentItem(BaseModel):
    id: int
    ticker: str
    doc_type: str
    title: str
    fiscal_period: Optional[str] = None
    file_name: str
    file_size_bytes: int
    mime_type: str
    content_snippet: Optional[str] = None
    text_length: int
    metadata_json: Optional[str] = None
    uploaded_at: datetime

    class Config:
        from_attributes = True

class UpdateLogItem(BaseModel):
    id: int
    ticker: Optional[str] = None
    event_type: str
    status: str
    report_type_detected: Optional[str] = None
    fiscal_period_detected: Optional[str] = None
    details: str
    created_at: datetime

    class Config:
        from_attributes = True

class SchedulerStatusResponse(BaseModel):
    scheduler_active: bool
    poll_interval_minutes: int
    last_check_timestamp: Optional[str] = None
    next_scheduled_run: Optional[str] = None
    monitored_companies_count: int
    recent_audit_logs: List[Dict[str, Any]]

# ============================================================================
# FR-005 to FR-009: Market Intelligence Schemas
# ============================================================================

class EconomicIndicatorItem(BaseModel):
    id: int
    category: str
    name: str
    symbol: str
    current_value: float
    previous_value: Optional[float] = None
    unit: str
    change_24h: Optional[float] = 0.0
    change_pct_24h: Optional[float] = 0.0
    frequency: str
    source: str
    historical_sparkline: Optional[str] = None
    last_updated: datetime

    class Config:
        from_attributes = True

class MarketEventItem(BaseModel):
    id: int
    title: str
    summary: str
    event_type: str
    impact_category: str
    severity: str
    sentiment: str
    confidence_score: float
    source: str
    source_url: Optional[str] = None
    affected_sectors: Optional[str] = "[]"
    affected_tickers: Optional[str] = "[]"
    event_date: datetime
    created_at: datetime

    class Config:
        from_attributes = True

class CreateMarketEventRequest(BaseModel):
    title: str
    summary: str
    event_type: str = Field(..., description="TARIFF_CHANGE, TRADE_RESTRICTION, SANCTION, IMPORT_EXPORT_CURB, TAX_POLICY, GOVERNMENT_REGULATION, NEWS_ARTICLE, MARKET_REPORT")
    impact_category: Optional[str] = Field(None, description="FINANCIAL, REGULATORY, POLITICAL, ENVIRONMENTAL, SUPPLY_CHAIN, COMPETITIVE (leave empty for auto-classification)")
    severity: Optional[str] = "MEDIUM"
    sentiment: Optional[str] = "NEUTRAL"
    source: Optional[str] = "Intelligence Network"
    source_url: Optional[str] = None
    affected_sectors: Optional[List[str]] = []
    affected_tickers: Optional[List[str]] = []

class ClassifyEventRequest(BaseModel):
    text: str = Field(..., description="Headline, policy draft, news article, or regulatory memo")

class ClassifyEventResponse(BaseModel):
    title: str
    summary: str
    detected_event_type: str
    impact_category: str
    impact_description: str
    confidence_score: float
    severity: str
    sentiment: str
    affected_sectors: List[str]
    affected_tickers: List[str]
    suggested_actions: List[str]

class MarketIntelligenceDashboardResponse(BaseModel):
    total_indicators_tracked: int
    categories_breakdown: Dict[str, int]
    total_events: int
    impact_category_distribution: Dict[str, int]
    severity_distribution: Dict[str, int]
    latest_critical_events: List[MarketEventItem]
    continuous_collection_active: bool

# ============================================================================
# FR-010 to FR-014: Knowledge Management & RAG Schemas
# ============================================================================

class RAGSearchRequest(BaseModel):
    query: str = Field(..., description="Semantic search query or question")
    ticker: Optional[str] = Field(None, description="Filter by company ticker (e.g. AAPL)")
    doc_type: Optional[str] = Field(None, description="Filter by document type (e.g. EARNINGS_CALL_TRANSCRIPT, BALANCE_SHEET)")
    fiscal_period: Optional[str] = Field(None, description="Filter by fiscal period (e.g. 2024-FY, 2024-Q4)")
    industry: Optional[str] = Field(None, description="Filter by company industry")
    geography: Optional[str] = Field(None, description="Filter by geography/country")
    min_confidence: Optional[float] = Field(None, description="Minimum metadata confidence score (0.0 - 1.0)")
    min_similarity: Optional[float] = Field(0.35, description="Minimum cosine similarity threshold (default 0.35)")
    top_k: Optional[int] = Field(5, description="Maximum number of distinct evidence passages")

class EvidenceItem(BaseModel):
    chunk_id: int
    document_id: int
    title: str
    file_name: str
    ticker: str
    doc_type: str
    fiscal_period: Optional[str] = None
    chunk_index: int
    text: str
    similarity_score: float
    metadata: Dict[str, Any]

class RAGSearchResponse(BaseModel):
    query: str
    results_count: int
    distinct_documents_count: int
    evidence: List[EvidenceItem]

class CitationItem(BaseModel):
    citation_id: str
    document_id: int
    title: str
    file_name: str
    ticker: str
    doc_type: str
    fiscal_period: Optional[str] = None
    chunk_index: int
    similarity_score: float
    confidence_score: float
    excerpt: str

class RAGRecommendRequest(BaseModel):
    query: str = Field(..., description="Financial question or analysis prompt to evaluate")
    ticker: Optional[str] = Field(None, description="Target company ticker (optional)")
    doc_type: Optional[str] = Field(None, description="Target document type filter")
    fiscal_period: Optional[str] = Field(None, description="Target fiscal period filter")
    industry: Optional[str] = Field(None, description="Target industry filter")
    geography: Optional[str] = Field(None, description="Target geography filter")
    min_confidence: Optional[float] = Field(None, description="Minimum metadata confidence score (0.0 - 1.0)")
    min_similarity: Optional[float] = Field(0.68, description="Minimum cosine similarity threshold for grounded evidence (default 0.68)")
    top_k: Optional[int] = Field(4, description="Maximum evidence items to synthesize")

class RAGRecommendResponse(BaseModel):
    status: str
    query: str
    target_ticker: Optional[str] = None
    recommendation: str
    key_findings: List[str]
    grounded: bool
    citations: List[CitationItem]
    evidence_count: int
    average_similarity: float
    insufficient_evidence_reason: Optional[str] = None

class RAGStatusResponse(BaseModel):
    status: str
    embedding_model: str
    vector_dimension: int
    total_documents_count: int
    indexed_documents_count: int
    total_chunks_stored: int
    indexed_tickers: List[str]
    persistence_type: str

class RAGIndexDetailItem(BaseModel):
    status: str
    document_id: int
    ticker: Optional[str] = None
    title: Optional[str] = None
    chunks_count: Optional[int] = 0
    message: Optional[str] = None
    error: Optional[str] = None

class RAGIndexAllResponse(BaseModel):
    status: str
    message: str
    total_documents: int
    newly_indexed: int
    unchanged_count: int
    skipped_count: int
    failed_count: int
    total_chunks_stored: int
    details: List[RAGIndexDetailItem]
