from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from backend.app.database import Base

class StructuredMetric(Base):
    """
    FR-003: Stores structured financial metrics including:
    - Revenue
    - EBITDA
    - EBIT
    - Net Profit
    - Operating Margin
    - Cash Flow
    - Debt Ratio
    - EPS
    - ROE
    - ROA
    """
    __tablename__ = "structured_metrics"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    ticker = Column(String(20), index=True, nullable=False)
    
    period_type = Column(String(20), nullable=False)   # ANNUAL, QUARTERLY
    fiscal_period = Column(String(30), nullable=False) # e.g. '2024-FY', '2025-Q1'
    period_end_date = Column(Date, nullable=False)
    
    # Core FR-003 Metrics
    revenue = Column(Float, nullable=True)                  # Total Revenue / Sales
    ebitda = Column(Float, nullable=True)                   # EBITDA
    ebit = Column(Float, nullable=True)                     # EBIT / Operating Income
    net_profit = Column(Float, nullable=True)               # Net Income / Net Profit
    operating_margin = Column(Float, nullable=True)         # Operating Margin (EBIT / Revenue)
    operating_cash_flow = Column(Float, nullable=True)      # Cash Flow from Operating Activities
    free_cash_flow = Column(Float, nullable=True)           # Operating Cash Flow - CapEx
    debt_ratio = Column(Float, nullable=True)               # Total Debt / Total Assets
    debt_to_equity = Column(Float, nullable=True)           # Total Debt / Total Stockholders Equity
    eps = Column(Float, nullable=True)                      # Diluted / Basic Earnings Per Share
    roe = Column(Float, nullable=True)                      # Return on Equity (Net Income / Equity)
    roa = Column(Float, nullable=True)                      # Return on Assets (Net Income / Assets)
    
    # Additional Contextual Financial Indicators
    gross_margin = Column(Float, nullable=True)
    current_ratio = Column(Float, nullable=True)
    
    source = Column(String(50), default="CALCULATED_ENGINE")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Unique constraint per company, period type, and fiscal period
    __table_args__ = (
        UniqueConstraint('company_id', 'period_type', 'fiscal_period', name='uix_company_period'),
    )

    # Relationships
    company = relationship("Company", back_populates="structured_metrics")
