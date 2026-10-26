from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey
from backend.app.database import Base

class OrchestrationRun(Base):
    """
    FR-015 & FR-023: Multi-Agent Orchestration Run Record.
    Stores the full execution trace, consensus stance, and synthesized multi-agent dossier.
    """
    __tablename__ = "orchestration_runs"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(String(64), unique=True, index=True, nullable=False)
    ticker = Column(String(20), index=True, nullable=False)
    status = Column(String(30), nullable=False, default="COMPLETED") # PENDING, RUNNING, COMPLETED, FAILED
    
    # Synthesized Stance: STRONG_BUY, BUY, HOLD, REDUCE, RISK_OFF
    consensus_stance = Column(String(30), nullable=False, default="HOLD")
    confidence_score = Column(Float, nullable=False, default=0.85)
    
    executive_summary = Column(Text, nullable=False)
    full_dossier_json = Column(Text, nullable=False) # Complete JSON serialization of all agent outputs
    
    total_execution_ms = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime, default=datetime.utcnow)


class AgentExecutionTrace(Base):
    """
    FR-015 & FR-023: Granular execution trace for individual specialized agents.
    Tracks execution status, timing, parameters, confidence, and output payload.
    """
    __tablename__ = "agent_execution_traces"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(String(64), index=True, nullable=False)
    
    # FR-016: FINANCIAL_ANALYSIS
    # FR-017: ECONOMIC_INTELLIGENCE
    # FR-018: GEOPOLITICAL_RISK
    # FR-019: INDUSTRY_INTELLIGENCE
    # FR-020: FORECASTING
    # FR-021: RECOMMENDATION
    # FR-022: EXPLAINABILITY
    # FR-023: ORCHESTRATOR
    agent_id = Column(String(50), nullable=False, index=True)
    agent_name = Column(String(100), nullable=False)
    
    status = Column(String(30), nullable=False, default="COMPLETED") # RUNNING, COMPLETED, FAILED
    confidence_score = Column(Float, nullable=False, default=0.85)
    execution_time_ms = Column(Integer, nullable=False, default=0)
    
    input_context_json = Column(Text, nullable=True)
    output_data_json = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
