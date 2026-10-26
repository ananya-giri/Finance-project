import os
import sys
import json
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.database import Base, init_db
from backend.app.models.company import Company
from backend.app.models.structured_metrics import StructuredMetric
from backend.app.models.market_intelligence import EconomicIndicator, MarketIntelligenceEvent
from backend.app.models.multi_agent import OrchestrationRun, AgentExecutionTrace

from backend.app.services.agents.base_agent import AgentRegistry, AgentContext
from backend.app.services.agents.financial_analysis_agent import FinancialAnalysisAgent
from backend.app.services.agents.economic_intelligence_agent import EconomicIntelligenceAgent
from backend.app.services.agents.geopolitical_risk_agent import GeopoliticalRiskAgent
from backend.app.services.agents.industry_intelligence_agent import IndustryIntelligenceAgent
from backend.app.services.agents.forecasting_agent import ForecastingAgent
from backend.app.services.agents.recommendation_agent import RecommendationAgent
from backend.app.services.agents.explainability_agent import ExplainabilityAgent
from backend.app.services.agents.orchestrator_agent import OrchestratorAgent

@contextmanager
def isolated_test_context():
    """
    Creates an isolated temporary SQLite database for verification.
    Copies existing production data for testing, leaving production fintech.db untouched.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)
        temp_db_path = temp_dir_path / "temp_fintech.db"

        prod_db = PROJECT_ROOT / "data" / "fintech.db"
        if prod_db.exists():
            shutil.copy2(prod_db, temp_db_path)

        test_engine = create_engine(
            f"sqlite:///{temp_db_path}",
            connect_args={"check_same_thread": False}
        )
        Base.metadata.create_all(bind=test_engine)
        TestSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
        test_db = TestSession()

        try:
            yield test_db
        finally:
            test_db.close()
            test_engine.dispose()

def run_multi_agent_verification(db=None):
    if db is None:
        with isolated_test_context() as isolated_db:
            return run_multi_agent_verification(db=isolated_db)

    print("==================================================================")
    print("  FUNCTION 2.4: MULTI-AGENT ORCHESTRATION (FR-015 to FR-023)      ")
    print("  COMPREHENSIVE VERIFICATION SUITE                                ")
    print("==================================================================")

    target_ticker = "AAPL"

    # -----------------------------------------------------------------
    # STEP 1: Verify FR-015 (Platform Multi-Agent Support & Registry)
    # -----------------------------------------------------------------
    print("\n--- [FR-015] Verifying Platform Multi-Agent Support & Agent Registry ---")
    registered = AgentRegistry.list_agents()
    agent_ids = [a["agent_id"] for a in registered]
    print(f"Registered Agent Count: {len(registered)}")
    print(f"Registered Agent IDs: {agent_ids}")

    expected_agents = [
        "FINANCIAL_ANALYSIS",
        "ECONOMIC_INTELLIGENCE",
        "GEOPOLITICAL_RISK",
        "INDUSTRY_INTELLIGENCE",
        "FORECASTING",
        "RECOMMENDATION",
        "EXPLAINABILITY",
        "ORCHESTRATOR"
    ]
    for exp in expected_agents:
        assert exp in agent_ids, f"Agent '{exp}' must be registered in AgentRegistry (FR-015)"
        agent_meta = next(a for a in registered if a["agent_id"] == exp)
        assert len(agent_meta["capabilities"]) > 0, f"Agent '{exp}' must expose capabilities"
        assert len(agent_meta["role"]) > 0, f"Agent '{exp}' must have a defined role"

    print("[PASS] FR-015: Agent Registry, metadata, and lifecycle verified.")

    # -----------------------------------------------------------------
    # STEP 2: Verify FR-016 (Financial Analysis Agent)
    # -----------------------------------------------------------------
    print(f"\n--- [FR-016] Verifying Financial Analysis Agent for {target_ticker} ---")
    ctx = AgentContext(ticker=target_ticker, db=db)
    fin_agent = FinancialAnalysisAgent()
    res_fin = fin_agent.run(ctx)

    assert res_fin.status == "COMPLETED", "Financial Analysis Agent must complete successfully"
    assert "metrics_summary" in res_fin.data, "Must contain structured metrics summary"
    assert "scorecard" in res_fin.data, "Must compute quantitative scorecard"
    assert "verdict" in res_fin.data, "Must formulate historical performance verdict"
    scorecard = res_fin.data["scorecard"]
    print(f"  Composite Financial Score: {scorecard['composite_financial_score']}/100")
    print(f"  Historical Verdict: {res_fin.data['verdict']}")
    print(f"  Latest Operating Margin: {res_fin.data['metrics_summary']['latest_operating_margin_pct']}%")
    print(f"  Key Insights: {len(res_fin.key_insights)} insights formulated")
    assert scorecard["composite_financial_score"] > 0, "Composite score must be positive"
    print("[PASS] FR-016: Financial Analysis Agent verified.")

    # -----------------------------------------------------------------
    # STEP 3: Verify FR-017 (Economic Intelligence Agent)
    # -----------------------------------------------------------------
    print("\n--- [FR-017] Verifying Economic Intelligence Agent ---")
    econ_agent = EconomicIntelligenceAgent()
    res_econ = econ_agent.run(ctx)

    assert res_econ.status == "COMPLETED", "Economic Intelligence Agent must complete successfully"
    assert "macro_regime" in res_econ.data, "Must diagnose macro regime"
    assert "macro_health_score" in res_econ.data, "Must compute macro health score"
    assert "key_metrics" in res_econ.data, "Must monitor key economic indicators"
    print(f"  Macro Regime: {res_econ.data['macro_regime']}")
    print(f"  Macro Health Score: {res_econ.data['macro_health_score']}/100")
    print(f"  Monitored Indicators: {res_econ.data['total_indicators_monitored']}")
    print("[PASS] FR-017: Economic Intelligence Agent verified.")

    # -----------------------------------------------------------------
    # STEP 4: Verify FR-018 (Geopolitical Risk Agent)
    # -----------------------------------------------------------------
    print(f"\n--- [FR-018] Verifying Geopolitical Risk Agent for {target_ticker} ---")
    geo_agent = GeopoliticalRiskAgent()
    res_geo = geo_agent.run(ctx)

    assert res_geo.status == "COMPLETED", "Geopolitical Risk Agent must complete successfully"
    assert "geopolitical_risk_index" in res_geo.data, "Must compute Geopolitical Risk Index (GRI)"
    assert "scenarios" in res_geo.data, "Must model disruption scenarios"
    assert len(res_geo.data["scenarios"]) >= 3, "Must evaluate at least 3 geopolitical disruption scenarios"
    print(f"  Geopolitical Risk Index (GRI): {res_geo.data['geopolitical_risk_index']}/100")
    print(f"  Risk Level: {res_geo.data['risk_level']}")
    print(f"  Resilience Rating: {res_geo.data['resilience_rating']}")
    print("[PASS] FR-018: Geopolitical Risk Agent verified.")

    # -----------------------------------------------------------------
    # STEP 5: Verify FR-019 (Industry Intelligence Agent)
    # -----------------------------------------------------------------
    print(f"\n--- [FR-019] Verifying Industry Intelligence Agent for {target_ticker} ---")
    ind_agent = IndustryIntelligenceAgent()
    res_ind = ind_agent.run(ctx)

    assert res_ind.status == "COMPLETED", "Industry Intelligence Agent must complete successfully"
    assert "competitive_moat" in res_ind.data, "Must evaluate competitive moat"
    assert "estimated_industry_cagr_pct" in res_ind.data, "Must project industry CAGR"
    print(f"  Industry / Sector: {res_ind.data['sector']} / {res_ind.data['industry']}")
    print(f"  Competitive Moat: {res_ind.data['competitive_moat']['rating']} (Score: {res_ind.data['competitive_moat']['score']})")
    print(f"  Projected Sector CAGR: {res_ind.data['estimated_industry_cagr_pct']}%")
    print("[PASS] FR-019: Industry Intelligence Agent verified.")

    # -----------------------------------------------------------------
    # STEP 6: Verify FR-020 (Forecasting Agent)
    # -----------------------------------------------------------------
    print(f"\n--- [FR-020] Verifying Forecasting Agent for {target_ticker} ---")
    fc_agent = ForecastingAgent()
    res_fc = fc_agent.run(ctx)

    assert res_fc.status == "COMPLETED", "Forecasting Agent must complete successfully"
    assert "scenarios" in res_fc.data, "Must generate scenario models"
    scenarios = res_fc.data["scenarios"]
    assert "base_case" in scenarios and "bull_case" in scenarios and "bear_case" in scenarios, "Must generate Bull, Base, Bear cases"
    print(f"  Base Case 3-Yr CAGR: {scenarios['base_case']['assumed_growth_cagr_pct']}%")
    print(f"  Bull Case 3-Yr CAGR: {scenarios['bull_case']['assumed_growth_cagr_pct']}%")
    print(f"  Bear Case 3-Yr CAGR: {scenarios['bear_case']['assumed_growth_cagr_pct']}%")
    assert len(scenarios["base_case"]["projections"]) == 3, "Must project 3-year forward horizon"
    print("[PASS] FR-020: Forecasting Agent verified.")

    # -----------------------------------------------------------------
    # STEP 7: Verify FR-021 (Recommendation Agent)
    # -----------------------------------------------------------------
    print(f"\n--- [FR-021] Verifying Recommendation Agent for {target_ticker} ---")
    recom_agent = RecommendationAgent()
    res_recom = recom_agent.run(ctx)

    assert res_recom.status == "COMPLETED", "Recommendation Agent must complete successfully"
    assert "strategic_stance" in res_recom.data, "Must formulate strategic stance"
    assert "conviction_index" in res_recom.data, "Must compute conviction index"
    assert "capital_allocation" in res_recom.data, "Must provide capital allocation guidance"
    assert "phased_horizons" in res_recom.data, "Must formulate phased action roadmaps"
    print(f"  Strategic Stance: {res_recom.data['strategic_stance']}")
    print(f"  Conviction Index: {res_recom.data['conviction_index']}/100")
    print(f"  Capital Allocation Directives: {len(res_recom.data['capital_allocation'])} actions")
    print("[PASS] FR-021: Recommendation Agent verified.")

    # -----------------------------------------------------------------
    # STEP 8: Verify FR-022 (Explainability Agent)
    # -----------------------------------------------------------------
    print(f"\n--- [FR-022] Verifying Explainability Agent for {target_ticker} ---")
    exp_agent = ExplainabilityAgent()
    res_exp = exp_agent.run(ctx)

    assert res_exp.status == "COMPLETED", "Explainability Agent must complete successfully"
    assert "factor_attribution" in res_exp.data, "Must calculate factor attribution"
    assert "causal_chain" in res_exp.data, "Must construct causal reasoning chain"
    assert "counterfactual_triggers" in res_exp.data, "Must determine counterfactual sensitivity triggers"
    print(f"  Factor Attribution Pillars: {len(res_exp.data['factor_attribution'])}")
    print(f"  Causal Chain Stages: {len(res_exp.data['causal_chain'])}")
    print(f"  Counterfactual Triggers: {len(res_exp.data['counterfactual_triggers'])}")
    print("[PASS] FR-022: Explainability Agent verified.")

    # -----------------------------------------------------------------
    # STEP 9: Verify FR-023 (Orchestrator Agent & Persistence)
    # -----------------------------------------------------------------
    print(f"\n--- [FR-023] Verifying Master Orchestrator Agent Pipeline for {target_ticker} ---")
    orchestrator = OrchestratorAgent()
    orch_ctx = AgentContext(ticker=target_ticker, db=db)
    res_orch = orchestrator.run(orch_ctx)

    assert res_orch.status == "COMPLETED", "Master Orchestration must complete successfully"
    assert "dossier" in res_orch.data or "agent_findings" in res_orch.data, "Must produce complete multi-agent dossier"
    dossier = res_orch.data
    assert "consensus_stance" in dossier, "Must derive consensus stance"
    assert "inter_agent_messages" in dossier, "Must capture inter-agent communication messages"
    assert len(dossier["inter_agent_messages"]) >= 6, "Must log communication across workflow phases"
    print(f"  Consensus Stance: {dossier['consensus_stance']}")
    print(f"  Conviction Score: {dossier['conviction_score']}%")
    print(f"  Total Workflow Execution Time: {res_orch.execution_time_ms}ms")
    print(f"  Inter-Agent Messages Recorded: {len(dossier['inter_agent_messages'])}")

    # Verify Database Persistence in isolated test DB
    saved_run = db.query(OrchestrationRun).filter(OrchestrationRun.run_id == orch_ctx.run_id).first()
    assert saved_run is not None, "Orchestration run must be persisted to database (FR-023)"
    saved_traces = db.query(AgentExecutionTrace).filter(AgentExecutionTrace.run_id == orch_ctx.run_id).all()
    assert len(saved_traces) >= 7, "All individual agent execution traces must be persisted"
    print(f"  DB Audit Check: Saved OrchestrationRun ID '{saved_run.run_id}' with {len(saved_traces)} AgentExecutionTraces.")
    print("[PASS] FR-023: Master Orchestrator and Database Persistence verified.")

    print("\n==================================================================")
    print("  ALL MULTI-AGENT ORCHESTRATION REQUIREMENTS (FR-015 to FR-023)   ")
    print("  SUCCESSFULLY PASSED AND VERIFIED!                               ")
    print("==================================================================")

if __name__ == "__main__":
    run_multi_agent_verification()
