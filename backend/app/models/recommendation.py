"""
DB Models for Strategic Recommendations - FR-037, FR-038, FR-039, FR-040
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Text, DateTime

from backend.app.database import Base


class RecommendationReport(Base):
    """FR-037–040: Stores LLM-generated strategic recommendation reports."""
    __tablename__ = "recommendation_reports"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(String(64), unique=True, index=True, nullable=False)
    ticker = Column(String(20), index=True, nullable=False)
    recommendations_json = Column(Text, nullable=False, default="[]")  # JSON list of 6+ recommendation objects
    total_recommendations = Column(Integer, default=0)
    top_priority_category = Column(String(50), nullable=True)  # e.g. COST_OPTIMIZATION
    llm_executive_summary = Column(Text, nullable=True)  # LLM-generated executive summary
    generated_at = Column(DateTime, default=datetime.utcnow, index=True)
    status = Column(String(20), nullable=False, default="COMPLETED")
