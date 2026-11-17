from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Text, DateTime
from backend.app.database import Base

class ExplainabilityRun(Base):
    """
    FR-041 to FR-044: Stores explainability telemetry, SHAP feature importance values,
    key recommendation drivers, and source document traceability citations.
    """
    __tablename__ = "explainability_runs"

    id = Column(Integer, primary_key=True, index=True)
    explain_id = Column(String(64), unique=True, index=True, nullable=False)
    ticker = Column(String(20), index=True, nullable=False)
    target_type = Column(String(50), nullable=False)  # PREDICTION, RECOMMENDATION, ORCHESTRATION
    target_id = Column(String(64), index=True, nullable=True)
    shap_values_json = Column(Text, nullable=False, default="{}")
    feature_importance_json = Column(Text, nullable=False, default="[]")
    key_drivers_json = Column(Text, nullable=False, default="[]")
    traceability_sources_json = Column(Text, nullable=False, default="[]")
    narrative_summary = Column(Text, nullable=False, default="")
    confidence_score = Column(Float, default=94.0)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
