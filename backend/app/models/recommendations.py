from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Text, DateTime
from backend.app.database import Base

class StrategicRecommendationReport(Base):
    """FR-037 to FR-040: Stores generated strategic recommendations ranked by priority with justification."""
    __tablename__ = "recommendation_reports"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(String(64), unique=True, index=True, nullable=False)
    ticker = Column(String(20), index=True, nullable=False)
    title = Column(String(150), nullable=False)
    executive_summary = Column(Text, nullable=False, default="")
    recommendations_json = Column(Text, nullable=False, default="[]")
    # List of 6 categories:
    # COST_OPTIMIZATION, INVESTMENT_PRIORITIZATION, RISK_MITIGATION,
    # MARKET_EXPANSION, PRICING_STRATEGIES, CAPITAL_ALLOCATION
    total_recommendations = Column(Integer, default=6)
    top_priority_category = Column(String(50), nullable=True)
    methodology = Column(String(100), default="LangChain + ChromaDB RAG + CrewAI Intelligence")
    confidence_score = Column(Float, default=88.0)
    status = Column(String(20), nullable=False, default="COMPLETED")
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
