from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Text, DateTime
from backend.app.database import Base

class ScenarioRun(Base):
    """FR-034, FR-035, FR-036: Stores what-if scenario simulations and financial impact estimations."""
    __tablename__ = "scenario_runs"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(String(64), unique=True, index=True, nullable=False)
    ticker = Column(String(20), index=True, nullable=False)
    scenario_type = Column(String(50), index=True, nullable=False)
    # Types: CURRENCY_FLUCTUATION, TARIFF_INCREASE, INTEREST_RATE_CHANGE, SUPPLY_CHAIN_DISRUPTION, MARKET_DOWNTURN
    scenario_name = Column(String(100), nullable=False)
    parameters_json = Column(Text, nullable=False, default="{}")
    baseline_metrics_json = Column(Text, nullable=False, default="{}")
    impact_metrics_json = Column(Text, nullable=False, default="{}")
    narrative_analysis = Column(Text, nullable=False, default="")
    risk_mitigations_json = Column(Text, nullable=False, default="[]")
    confidence_score = Column(Float, default=85.0)
    status = Column(String(20), nullable=False, default="COMPLETED")
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
