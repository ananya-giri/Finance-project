import logging
from typing import Dict, Any, List, Optional
from backend.app.services.agents.base_agent import BaseAgent, AgentContext, AgentResult
from backend.app.models.company import Company
from backend.app.services.rag_service import RAGService

logger = logging.getLogger("recommendation_agent")

class RecommendationAgent(BaseAgent):
    """
    FR-021: Recommendation Agent
    Synthesizes intelligence from the Financial Analysis, Economic Intelligence,
    Geopolitical Risk, Industry Intelligence, and Forecasting agents to formulate
    actionable, multi-horizon strategic and capital allocation recommendations.
    """
    agent_id: str = "RECOMMENDATION"
    name: str = "Recommendation Agent"
    role: str = "Chief Strategic Investment & Capital Allocation Officer"
    description: str = "Synthesizes multi-agent telemetry to formulate actionable corporate strategy, capital allocation directives, and risk mitigation roadmaps."
    version: str = "1.0.0"
    fr_code: str = "FR-021"
    capabilities: List[str] = [
        "Holistic Multi-Domain Strategic Synthesis",
        "Capital Allocation Prioritization (R&D, Deleveraging, Dividends/Buybacks)",
        "Operational Supply Chain Risk Mitigation Roadmap Formulation",
        "Conviction & Investment Stance Formulation (Buy, Hold, Reduce)",
        "Multi-Horizon Phased Action Directives (Tactical, Strategic, Structural)"
    ]

    def execute(self, context: AgentContext) -> AgentResult:
        ticker = context.ticker
        db = context.db

        fin_data = context.get_shared("financial_analysis", {})
        econ_data = context.get_shared("economic_intelligence", {})
        geo_data = context.get_shared("geopolitical_risk", {})
        ind_data = context.get_shared("industry_intelligence", {})
        fc_data = context.get_shared("forecasting", {})

        # Extract scores
        fin_score = fin_data.get("scorecard", {}).get("composite_financial_score", 70.0)
        macro_score = econ_data.get("macro_health_score", 65.0)
        geo_risk_idx = geo_data.get("geopolitical_risk_index", 35.0)
        # Invert geo risk so higher = safer
        geo_safety_score = max(0.0, 100.0 - geo_risk_idx)
        ind_score = ind_data.get("industry_health_score", 75.0)
        
        # Forecast score based on base CAGR
        base_cagr = fc_data.get("scenarios", {}).get("base_case", {}).get("assumed_growth_cagr_pct", 8.0)
        fc_score = min(100.0, max(20.0, 50.0 + (base_cagr * 3.5)))

        # Weighted Strategic Conviction Index (0 - 100)
        conviction_index = round(
            (fin_score * 0.30) +
            (macro_score * 0.15) +
            (geo_safety_score * 0.15) +
            (ind_score * 0.20) +
            (fc_score * 0.20),
            1
        )

        # Stance Formulation
        if conviction_index >= 80.0:
            stance = "STRONG_BUY"
            stance_narrative = "Outstanding fundamentals, wide competitive moat, and strong forward cash generation outweigh external macro friction."
        elif conviction_index >= 68.0:
            stance = "BUY"
            stance_narrative = "Favorable growth profile and robust balance sheet provide attractive risk-adjusted strategic expansion opportunity."
        elif conviction_index >= 52.0:
            stance = "HOLD"
            stance_narrative = "Solid historical performance balanced against elevated geopolitical exposure and monetary rate tightening."
        elif conviction_index >= 40.0:
            stance = "REDUCE"
            stance_narrative = "Margin pressure, heavy debt service, or severe trade restrictions warrant capital preservation."
        else:
            stance = "RISK_OFF"
            stance_narrative = "Substantial systemic headwinds across financial and external macro vectors indicate defensive restructuring."

        # Strategic Action Directives
        capital_allocation = [
            {
                "priority": "HIGH",
                "category": "Organic R&D Reinvestment",
                "action": "Maintain disciplined R&D spending targeting next-generation proprietary platforms and artificial intelligence architectures.",
                "allocation_pct": 45
            },
            {
                "priority": "MEDIUM",
                "category": "Supply Chain Diversification & Near-Shoring",
                "action": "Allocate capital expenditure toward dual-sourcing manufacturing hubs outside concentrated geopolitical regions.",
                "allocation_pct": 25
            },
            {
                "priority": "MEDIUM",
                "category": "Shareholder Return & Deleveraging",
                "action": "Deploy surplus free cash flow toward opportunistic share repurchases while keeping net leverage below 1.5x EBITDA.",
                "allocation_pct": 30
            }
        ]

        # Multi-Horizon Phased Roadmaps
        phased_horizons = {
            "tactical_0_6m": [
                "Institute targeted foreign exchange hedging to mitigate US Dollar volatility against international sales.",
                "Review tier-1 supplier logistics resilience against emerging maritime trade chokepoints."
            ],
            "strategic_12_24m": [
                "Accelerate market expansion in high-margin enterprise segments where ecosystem switching costs are highest.",
                "Optimize working capital cycles to sustain 90%+ Free Cash Flow conversion."
            ],
            "structural_3_5y": [
                "Reinforce proprietary intellectual property moats against emerging low-cost competitors.",
                "Scale strategic international partnerships to safeguard market leadership across emerging markets."
            ]
        }

        # Check for RAG document evidence attribution
        rag_citation = None
        try:
            rag_res = RAGService.search_evidence(
                db=db,
                query=f"{ticker} strategic performance capital allocation competitive advantage",
                ticker=ticker,
                top_k=2
            )
            if rag_res.get("evidence"):
                top_chunk = rag_res["evidence"][0]
                rag_citation = {
                    "document_title": top_chunk["document_title"],
                    "doc_type": top_chunk["doc_type"],
                    "provenance": f"Page {top_chunk.get('page_number', 1)} / Section: {top_chunk.get('fiscal_period', 'N/A')}",
                    "snippet": top_chunk["text"][:160] + "..."
                }
        except Exception:
            pass

        insights = [
            f"Strategic Stance: {stance.replace('_', ' ')} (Conviction Score: {conviction_index}/100).",
            f"Core Rationale: {stance_narrative}",
            f"Primary Capital Allocation Priority: {capital_allocation[0]['action']}",
            f"Risk Mitigation: Focus on supply chain near-shoring and active FX hedging (Tactical 0-6m).",
            f"Growth Vector: Base forward 3-year revenue CAGR of {base_cagr:.1f}% supports continued reinvestment."
        ]

        summary_text = (
            f"Recommendation Agent synthesized telemetry across all specialized agents for {ticker}. "
            f"The formulated strategic stance is '{stance.replace('_', ' ')}' with an overall Conviction Index of {conviction_index}/100. "
            f"Key guidance emphasizes disciplined organic R&D reinvestment (45% allocation) alongside aggressive supply chain near-shoring."
        )

        data_payload = {
            "ticker": ticker,
            "strategic_stance": stance,
            "conviction_index": conviction_index,
            "core_rationale": stance_narrative,
            "capital_allocation": capital_allocation,
            "phased_horizons": phased_horizons,
            "grounded_document_citation": rag_citation,
            "component_scores": {
                "financial_performance": fin_score,
                "macroeconomic_climate": macro_score,
                "geopolitical_safety": geo_safety_score,
                "industry_competitiveness": ind_score,
                "forward_projections": fc_score
            }
        }

        context.set_shared("recommendation", data_payload)

        return AgentResult(
            agent_id=self.agent_id,
            agent_name=self.name,
            status="COMPLETED",
            confidence_score=0.92,
            summary=summary_text,
            data=data_payload,
            key_insights=insights
        )
