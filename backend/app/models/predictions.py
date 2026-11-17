from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, Boolean
from backend.app.database import Base

class PredictionRun(Base):
    """FR-028 to FR-033: Stores ML prediction runs and forecast results."""
    __tablename__ = "prediction_runs"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(String(64), unique=True, index=True, nullable=False)
    ticker = Column(String(20), index=True, nullable=False)
    forecast_type = Column(String(50), nullable=False)  # REVENUE, EBITDA, PROFIT, CASH_FLOW, DEMAND
    horizon = Column(String(20), nullable=False)  # QUARTERLY, ANNUAL, THREE_YEAR, FIVE_YEAR
    best_model = Column(String(50), nullable=True)
    best_mape = Column(Float, nullable=True)
    models_json = Column(Text, nullable=False, default="[]")  # JSON list of model results
    historical_json = Column(Text, nullable=False, default="[]")  # historical data points
    forecasts_json = Column(Text, nullable=False, default="[]")  # forecast data points per model
    status = Column(String(20), nullable=False, default="COMPLETED")
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    retrained_at = Column(DateTime, nullable=True)
    is_retrained = Column(Boolean, default=False)

class ModelRegistry(Base):
    """FR-032: Tracks model performance over time for auto-comparison."""
    __tablename__ = "model_registry"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(20), index=True, nullable=False)
    forecast_type = Column(String(50), nullable=False)
    model_name = Column(String(50), nullable=False)
    rmse = Column(Float, nullable=True)
    mae = Column(Float, nullable=True)
    mape = Column(Float, nullable=True)
    r_squared = Column(Float, nullable=True)
    is_best = Column(Boolean, default=False)
    trained_at = Column(DateTime, default=datetime.utcnow)
    data_points_used = Column(Integer, default=0)
