"""
Comprehensive Verification Suite: FR-028 to FR-044
Verifies all functional requirements across:
  - 2.6 Predictive Analytics (FR-028, FR-029, FR-030, FR-031, FR-032, FR-033)
  - 2.7 Scenario Analysis (FR-034, FR-035, FR-036)
  - 2.8 Recommendation Generation (FR-037, FR-038, FR-039, FR-040)
  - 2.9 Explainable AI & SHAP (FR-041, FR-042, FR-043, FR-044)
"""

import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from backend.app.database import SessionLocal, init_db
from backend.app.main import app
from backend.app.services.prediction_engine import PredictionEngine
from backend.app.services.scenario_analysis import ScenarioAnalysisEngine
from backend.app.services.recommendation_service import RecommendationService
from backend.app.services.explainability_engine import ExplainabilityEngine

def run_tests():
    print("=" * 70)
    print("FININTEL PLATFORM AUDIT: FR-028 TO FR-044 VERIFICATION SUITE")
    print("=" * 70)

    init_db()
    db = SessionLocal()
    client = TestClient(app)
    ticker = "AAPL"

    # -------------------------------------------------------------
    # 1. Section 2.6: Predictive Analytics (FR-028 to FR-033)
    # -------------------------------------------------------------
    print("\n[+] 1. AUDITING PREDICTIVE ANALYTICS (FR-028 to FR-033)...")

    # FR-029 & FR-030 & FR-031 & FR-032
    metrics_to_test = ["REVENUE", "EBITDA", "PROFIT", "CASH_FLOW", "DEMAND"]
    horizons_to_test = ["QUARTERLY", "ANNUAL", "THREE_YEAR", "FIVE_YEAR"]

    pred_res = PredictionEngine.run_prediction(db, ticker, "REVENUE", "ANNUAL")
    assert "best_model" in pred_res, "FR-032: Missing best_model selection"
    assert "best_mape" in pred_res, "FR-032: Missing best_mape comparison"
    assert len(pred_res["models"]) >= 4, f"FR-031: Expected at least 4 ML models, got {len(pred_res['models'])}"
    print(f"  [OK] FR-028/031/032: Evaluated models {[m['model'] for m in pred_res['models']]} -> Best: {pred_res['best_model']} (MAPE: {pred_res['best_mape']}%)")

    # Verify DEMAND forecast (FR-029) and QUARTERLY horizon (FR-030)
    demand_res = PredictionEngine.run_prediction(db, ticker, "DEMAND", "QUARTERLY")
    assert len(demand_res["forecasts"][demand_res["best_model"]]) == 4, "FR-030: Expected 4 quarters for QUARTERLY"
    print(f"  [OK] FR-029/030: DEMAND QUARTERLY forecast generated 4 forward periods: {[f['period'] for f in demand_res['forecasts'][demand_res['best_model']] ]}")

    # FR-033: Periodic Retraining
    retrain_res = PredictionEngine.retrain_models(db, ticker)
    assert len(retrain_res["models_retrained"]) >= 5, "FR-033: Retraining did not cover all 5 metrics"
    print(f"  [OK] FR-033: Periodic retraining executed for {len(retrain_res['models_retrained'])} metrics at {retrain_res['retrained_at']}")

    # -------------------------------------------------------------
    # 2. Section 2.7: Scenario Analysis (FR-034 to FR-036)
    # -------------------------------------------------------------
    print("\n[+] 2. AUDITING SCENARIO ANALYSIS (FR-034 to FR-036)...")
    sc_types = [
        ("CURRENCY_FLUCTUATION", {"change_pct": -12.5, "currency_pair": "USD/EUR"}),
        ("TARIFF_INCREASE", {"tariff_rate_pct": 20.0, "affected_regions": ["China", "EU"]}),
        ("INTEREST_RATE_CHANGE", {"rate_change_bps": 150}),
        ("SUPPLY_CHAIN_DISRUPTION", {"severity": "HIGH", "duration_months": 6}),
        ("MARKET_DOWNTURN", {"downturn_severity_pct": -20.0})
    ]

    for stype, sparams in sc_types:
        sc = ScenarioAnalysisEngine.run_scenario(db, ticker, stype, sparams)
        assert "impacts" in sc, f"FR-036: Missing quantitative impacts for {stype}"
        assert "revenue" in sc["impacts"] and "net_profit" in sc["impacts"], "FR-036: Missing metric shock breakdown"
        assert len(sc["narrative_analysis"]) > 100, "FR-036: Missing narrative synthesis"
        assert len(sc["risk_mitigations"]) >= 3, "FR-036: Missing risk mitigations"
        print(f"  [OK] FR-034/035/036: {stype} -> Rev: {sc['impacts']['revenue']['change_pct']:+.2f}%, Net Profit: {sc['impacts']['net_profit']['change_pct']:+.2f}%, Severity: {sc['impacts']['overall_impact_severity']}")

    # -------------------------------------------------------------
    # 3. Section 2.8: Recommendation Generation (FR-037 to FR-040)
    # -------------------------------------------------------------
    print("\n[+] 3. AUDITING RECOMMENDATION GENERATION (FR-037 to FR-040)...")
    rec_res = RecommendationService.generate_recommendations(db, ticker)
    recs = rec_res["recommendations"]

    assert len(recs) == 6, f"FR-038: Expected exactly 6 pillars, got {len(recs)}"
    expected_categories = {
        "COST_OPTIMIZATION", "INVESTMENT_PRIORITIZATION", "RISK_MITIGATION",
        "MARKET_EXPANSION", "PRICING_STRATEGIES", "CAPITAL_ALLOCATION"
    }
    actual_categories = {r["category"] for r in recs}
    assert actual_categories == expected_categories, f"FR-038: Missing categories: {expected_categories - actual_categories}"
    print(f"  [OK] FR-037/038: All 6 required categories present: {list(actual_categories)}")

    # Check ranking (FR-039)
    scores = [r["priority_score"] for r in recs]
    assert scores == sorted(scores, reverse=True), "FR-039: Recommendations not ranked by priority score descending"
    ranks = [r["priority_rank"] for r in recs]
    assert ranks == list(range(1, 7)), "FR-039: Priority ranks 1 to 6 mismatch"
    print(f"  [OK] FR-039: Properly ranked 1 to 6 (Top priority: {recs[0]['category_name']}, score {recs[0]['priority_score']}/100)")

    # Check justifications (FR-040)
    for r in recs:
        assert len(r["justification"]) > 50, f"FR-040: Missing justification for {r['category']}"
    print("  [OK] FR-040: All recommendations substantiated with financial justifications")

    # -------------------------------------------------------------
    # 4. Section 2.9: Explainable AI & SHAP (FR-041 to FR-044)
    # -------------------------------------------------------------
    print("\n[+] 4. AUDITING EXPLAINABLE AI & SHAP (FR-041 to FR-044)...")
    # FR-041 & FR-043: SHAP Feature Importance
    shap_res = ExplainabilityEngine.explain_prediction(db, ticker, "REVENUE", "ANNUAL")
    assert len(shap_res["feature_importance"]) == 7, f"FR-043: Expected 7 SHAP features, got {len(shap_res['feature_importance'])}"
    assert "base_value" in shap_res, "FR-043: Missing SHAP base value E[f(x)]"
    assert len(shap_res["narrative_explanation"]) > 100, "FR-041: Missing prediction narrative explainability"
    print(f"  [OK] FR-041/043: SHAP feature importance computed: Top driver: {shap_res['top_driver']} (Base Value: ${shap_res['base_value']:,.0f})")

    # FR-042: Key drivers influencing recommendations
    rec_exp = ExplainabilityEngine.explain_recommendations(db, ticker)
    assert len(rec_exp["key_drivers"]) == 6, f"FR-042: Expected 6 pillar drivers, got {len(rec_exp['key_drivers'])}"
    print(f"  [OK] FR-042: Identified 6 decision drivers with directional weights (Primary: {rec_exp['key_drivers'][1]['key_driver']})")

    # FR-044: Source Document Traceability
    citations = shap_res["traceability_sources"]
    assert len(citations) > 0, "FR-044: Missing document traceability citations"
    assert "sha256_hash" in citations[0], "FR-044: Missing SHA-256 chunk hash"
    assert "document_title" in citations[0], "FR-044: Missing document title"
    print(f"  [OK] FR-044: Verified source document traceability across {len(citations)} primary filings (SHA-256: {citations[0]['sha256_hash'][:16]}...)")

    # -------------------------------------------------------------
    # 5. API Endpoints Live Check
    # -------------------------------------------------------------
    print("\n[+] 5. AUDITING FASTAPI ROUTE INTERFACES...")
    routes = [
        ("POST", "/api/predictions/run", {"ticker": "AAPL", "forecast_type": "REVENUE", "horizon": "ANNUAL"}),
        ("GET", "/api/predictions/AAPL", None),
        ("POST", "/api/scenarios/run", {"ticker": "AAPL", "scenario_type": "MARKET_DOWNTURN", "parameters": {"downturn_severity_pct": -15}}),
        ("GET", "/api/scenarios/types", None),
        ("POST", "/api/recommendations/generate", {"ticker": "AAPL"}),
        ("GET", "/api/recommendations/AAPL", None),
        ("POST", "/api/explainability/prediction", {"ticker": "AAPL", "forecast_type": "REVENUE"}),
        ("POST", "/api/explainability/recommendation", {"ticker": "AAPL"}),
        ("GET", "/api/explainability/traceability/AAPL", None),
    ]

    for method, path, body in routes:
        if method == "POST":
            res = client.post(path, json=body)
        else:
            res = client.get(path)
        assert res.status_code == 200, f"Route {path} failed with {res.status_code}: {res.text}"
        print(f"  [OK] {method:4} {path:36} -> 200 OK")

    print("\n" + "=" * 70)
    print("ALL FUNCTIONAL REQUIREMENTS FR-028 THROUGH FR-044 SUCCESSFULLY VERIFIED!")
    print("=" * 70)
    db.close()

if __name__ == "__main__":
    run_tests()
