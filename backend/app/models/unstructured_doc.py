from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.database import Base

class UnstructuredDocument(Base):
    """
    FR-002: Supports ingestion of:
    - Annual Reports
    - Quarterly Reports
    - Investor Presentations
    - Earnings Call Transcripts
    (Also supports direct uploads of Income Statements, Balance Sheets, Cash Flow Statements)
    """
    __tablename__ = "unstructured_documents"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    ticker = Column(String(20), index=True, nullable=False)
    
    # Document Classification
    doc_type = Column(String(50), nullable=False) 
    # e.g.: ANNUAL_REPORT, QUARTERLY_REPORT, INVESTOR_PRESENTATION, EARNINGS_CALL_TRANSCRIPT,
    #       INCOME_STATEMENT_FILE, BALANCE_SHEET_FILE, CASH_FLOW_FILE
    
    title = Column(String(255), nullable=False)
    fiscal_period = Column(String(30), nullable=True)  # e.g. '2024-FY', '2025-Q2'
    
    # File details
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size_bytes = Column(Integer, default=0)
    mime_type = Column(String(100), default="application/octet-stream")
    
    # Parsed Content snippet (first 1000 chars) & full text storage
    content_snippet = Column(Text, nullable=True)
    text_length = Column(Integer, default=0)
    
    # Metadata for RAG and downstream intelligence (FR-013 ready: Source, Date, Industry, Geography, Confidence)
    metadata_json = Column(Text, nullable=True)
    
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    company = relationship("Company", back_populates="documents")
