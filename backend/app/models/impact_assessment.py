
from datetime import datetime

# pyright: reportMissingImports=false
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Text,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import relationship

from backend.app.database import Base


class ImpactAssessment(Base):
    """
    Impact Assessment Engine: FR-024 to FR-027.

    Stores the estimated financial impact of an external event
    on an individual company and financial metric.
    """

    __tablename__ = "impact_assessments"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Link the assessment to an existing external event
    event_id = Column(
        Integer,
        ForeignKey("market_intelligence_events.id"),
        nullable=False,
        index=True,
    )

    # Link the assessment to the affected company
    company_id = Column(
        Integer,
        ForeignKey("companies.id"),
        nullable=False,
        index=True,
    )

    # FR-025: Revenue, EBITDA, PROFITABILITY,
    # COSTS, CASH_FLOW, or MARKET_SHARE
    metric_name = Column(String(30), nullable=False, index=True)

    # BASE, OPTIMISTIC, or PESSIMISTIC
    scenario = Column(String(20), nullable=False, default="BASE")

    # Baseline and predicted financial values
    baseline_value = Column(Float, nullable=True)
    estimated_change = Column(Float, nullable=True)
    estimated_change_pct = Column(Float, nullable=True)
    projected_value = Column(Float, nullable=True)

    # Unit of measurement, e.g. USD, INR, or percentage points
    unit = Column(String(30), nullable=True)

    # POSITIVE, NEGATIVE, NEUTRAL, or UNKNOWN
    direction = Column(String(20), nullable=False, default="UNKNOWN")

    # FR-027: Confidence score from 0 to 100
    confidence_score = Column(Float, nullable=True)

    # Evidence and assumptions used by the engine
    confidence_factors_json = Column(Text, nullable=True)
    assumptions_json = Column(Text, nullable=True)
    rationale = Column(Text, nullable=True)

    # COMPLETE, PARTIAL, or INSUFFICIENT_DATA
    data_quality = Column(
        String(30),
        nullable=False,
        default="INSUFFICIENT_DATA",
    )

    # Period of the financial baseline, e.g. 2025-FY
    baseline_period = Column(String(30), nullable=True)

    # Timestamp of assessment creation
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # ORM references to the existing database models
    event = relationship("MarketIntelligenceEvent")
    company = relationship("Company")
