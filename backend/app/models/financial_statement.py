from datetime import datetime
from sqlalchemy import Column, Integer, String, Date, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.database import Base

class FinancialStatement(Base):
    __tablename__ = "financial_statements"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    ticker = Column(String(20), index=True, nullable=False)
    
    # FR-002: Income Statements, Balance Sheets, Cash Flow Statements
    statement_type = Column(String(30), nullable=False)  # INCOME_STATEMENT, BALANCE_SHEET, CASH_FLOW
    period_type = Column(String(20), nullable=False)     # ANNUAL, QUARTERLY
    fiscal_period = Column(String(30), nullable=False)   # e.g., '2024-FY', '2025-Q1'
    fiscal_date = Column(Date, nullable=False)
    
    currency = Column(String(10), default="USD")
    raw_data_json = Column(Text, nullable=False)        # Full JSON key-value line items
    source = Column(String(50), default="SEC_EDGAR")    # SEC_EDGAR, YFINANCE, CSV_UPLOAD, XLSX_UPLOAD
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    company = relationship("Company", back_populates="financial_statements")
