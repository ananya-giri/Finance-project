from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.database import Base

class UpdateLog(Base):
    """
    FR-004: Audit and activity log for automatic monitoring and ingestion
    of new quarterly and annual reports.
    """
    __tablename__ = "update_logs"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True, index=True)
    ticker = Column(String(20), index=True, nullable=True)
    
    event_type = Column(String(50), nullable=False) 
    # SCHEDULED_CHECK, MANUAL_SYNC, NEW_REPORT_DETECTED, METRICS_UPDATED, ERROR
    
    status = Column(String(30), nullable=False) 
    # SUCCESS, UPDATED, NO_NEW_DATA, ERROR
    
    report_type_detected = Column(String(50), nullable=True) # e.g. 10-Q, 10-K, Quarterly Earnings
    fiscal_period_detected = Column(String(30), nullable=True)
    
    details = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    company = relationship("Company", back_populates="update_logs")
