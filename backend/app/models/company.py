from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from backend.app.database import Base

class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(20), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    sector = Column(String(100), nullable=True)
    industry = Column(String(100), nullable=True)
    country = Column(String(50), default="USA")
    currency = Column(String(10), default="USD")
    cik = Column(String(20), nullable=True)
    
    # Tracking & Data Completeness (FR-001)
    years_of_data_available = Column(Integer, default=0)
    has_five_year_history = Column(Boolean, default=False)
    latest_fiscal_year = Column(Integer, nullable=True)
    latest_fiscal_period = Column(String(20), nullable=True)
    last_synced_at = Column(DateTime, nullable=True)
    
    # Automated Monitoring (FR-004)
    auto_sync_enabled = Column(Boolean, default=True)
    last_checked_for_updates = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    financial_statements = relationship("FinancialStatement", back_populates="company", cascade="all, delete-orphan")
    structured_metrics = relationship("StructuredMetric", back_populates="company", cascade="all, delete-orphan")
    documents = relationship("UnstructuredDocument", back_populates="company", cascade="all, delete-orphan")
    update_logs = relationship("UpdateLog", back_populates="company", cascade="all, delete-orphan")
