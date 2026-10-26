import json
import logging
from typing import Dict, Any, List, Optional
from backend.app.services.agents.base_agent import BaseAgent, AgentContext, AgentResult
from backend.app.models.market_intelligence import MarketIntelligenceEvent
from backend.app.models.company import Company

logger = logging.getLogger("geopolitical_risk_agent")

class GeopoliticalRiskAgent(BaseAgent):
    """
    FR-018: Geopolitical Risk Agent
    Identifies, categorizes, and quantifies geopolitical risks, trade sanctions,
    tariff barriers, supply chain bottlenecks, and cross-border regulatory shifts.
    """
    agent_id: str = "GEOPOLITICAL_RISK"
    name: str = "Geopolitical Risk Agent"
    role: str = "Geopolitical Conflict & Trade Policy Specialist"
    description: str = "Identifies cross-border geopolitical vulnerabilities, trade restrictions, export controls, and supply chain chokepoints threatening corporate stability."
    version: str = "1.0.0"
    fr_code: str = "FR-018"
    capabilities: List[str] = [
        "Trade Policy & Tariff Escalation Impact Assessment",
        "Export Control & Sanctions Exposure Detection",
        "Maritime Logistics & Critical Chokepoint Risk Modeling",
        "Geopolitical Risk Index (GRI) Scoring",
        "Scenario Stress-Testing (Tariff Shocks & Component Embargoes)"
    ]

    def execute(self, context: AgentContext) -> AgentResult:
        ticker = context.ticker
        db = context.db

        company = db.query(Company).filter(Company.ticker == ticker).first()
        company_sector = (company.sector or "Technology").lower()
        company_name = company.name if company else ticker

        # Query all active market intelligence events
        events = db.query(MarketIntelligenceEvent).order_by(MarketIntelligenceEvent.event_date.desc()).all()

        # Filter events with geopolitical / political / regulatory / trade relevance
        geopolitical_types = {
            "TARIFF_CHANGE", "TRADE_RESTRICTION", "SANCTION", "IMPORT_EXPORT_CURB",
            "TAX_POLICY", "GOVERNMENT_REGULATION", "GEOPOLITICAL_EVENT"
        }
        geopolitical_categories = {"POLITICAL", "REGULATORY", "SUPPLY_CHAIN"}

        relevant_events = []
        for ev in events:
            is_geo_type = ev.event_type.upper() in geopolitical_types
            is_geo_cat = ev.impact_category.upper() in geopolitical_categories
            if is_geo_type or is_geo_cat:
                relevant_events.append(ev)

        # Check ticker-specific mentions or sector alignment
        direct_matches = []
        for ev in relevant_events:
            tickers_list = []
            if ev.affected_tickers:
                try:
                    tickers_list = json.loads(ev.affected_tickers)
                except Exception:
                    tickers_list = [ev.affected_tickers]
            if ticker in [t.upper() for t in tickers_list]:
                direct_matches.append(ev)

        # Compute Geopolitical Risk Index (0 - 100)
        # Base risk is moderate baseline 25.0
        base_gri = 28.0
        critical_count = sum(1 for e in relevant_events if e.severity.upper() == "CRITICAL")
        high_count = sum(1 for e in relevant_events if e.severity.upper() == "HIGH")
        direct_penalty = len(direct_matches) * 15.0

        gri = min(95.0, max(10.0, base_gri + (critical_count * 12.0) + (high_count * 6.0) + direct_penalty))
        gri = round(gri, 1)

        # Geopolitical Posture & Resilience
        if gri < 35.0:
            resilience = "HIGH_RESILIENCE"
            risk_level = "LOW"
            posture_summary = "Company operates in relatively insulated geographic markets with minor trade friction."
        elif gri < 65.0:
            resilience = "MODERATE_RESILIENCE"
            risk_level = "MODERATE"
            posture_summary = "Company has identifiable exposure to cross-border tariff renegotiations and regional logistics corridors."
        else:
            resilience = "VULNERABLE"
            risk_level = "ELEVATED_CRITICAL"
            posture_summary = "Company faces active geopolitical headwinds including tariffs, export restrictions, or supply chain exposure."

        # Scenario Disruptions
        scenario_simulations = [
            {
                "scenario_name": "Tariff Surge Scenario (+15% Bilateral Levies)",
                "probability": "MODERATE",
                "estimated_margin_impact_bps": -180 if ("tech" in company_sector or "hardware" in company_sector) else -90,
                "description": "Bilateral import tariff escalation on advanced hardware components and assemblies."
            },
            {
                "scenario_name": "Critical Mineral / Semiconductor Export Curb",
                "probability": "HIGH",
                "estimated_lead_time_increase_weeks": 8,
                "description": "Restrictions on critical raw materials or high-performance wafers creating inventory bottlenecks."
            },
            {
                "scenario_name": "Maritime Shipping Chokepoint Rerouting",
                "probability": "MODERATE",
                "estimated_freight_cost_surge_pct": 25.0,
                "description": "Conflict or security threats along Red Sea and Malacca straits elevating global freight rates."
            }
        ]

        # Key Insights
        insights = [
            f"Geopolitical Risk Index (GRI): {gri}/100 - Categorized as {risk_level} risk level.",
            f"Active Policy Events: Monitored {len(relevant_events)} cross-border regulatory and trade actions in the intelligence repository.",
            f"Direct Exposure: {len(direct_matches)} active intelligence bulletins directly reference {ticker}.",
            f"Resilience Rating: {resilience.replace('_', ' ').title()} - {posture_summary}",
            "Primary Vulnerability: Supply chain dependency on East Asia manufacturing and component logistics."
        ]

        summary_text = (
            f"Geopolitical Risk Agent evaluated international trade, regulatory events, and territorial risk factors for {ticker}. "
            f"The company maintains a Geopolitical Risk Index (GRI) of {gri}/100 ({risk_level} risk). "
            f"{len(relevant_events)} systemic trade and policy events are currently tracked, resulting in a '{resilience.replace('_', ' ').title()}' posture."
        )

        data_payload = {
            "ticker": ticker,
            "geopolitical_risk_index": gri,
            "risk_level": risk_level,
            "resilience_rating": resilience,
            "total_geopolitical_events": len(relevant_events),
            "direct_ticker_matches": len(direct_matches),
            "scenarios": scenario_simulations,
            "top_risk_events": [
                {
                    "title": ev.title,
                    "event_type": ev.event_type,
                    "impact_category": ev.impact_category,
                    "severity": ev.severity,
                    "sentiment": ev.sentiment,
                    "summary": ev.summary[:180] + "..." if len(ev.summary) > 180 else ev.summary,
                    "event_date": str(ev.event_date.date()) if ev.event_date else None
                }
                for ev in relevant_events[:6]
            ]
        }

        context.set_shared("geopolitical_risk", data_payload)

        return AgentResult(
            agent_id=self.agent_id,
            agent_name=self.name,
            status="COMPLETED",
            confidence_score=0.88,
            summary=summary_text,
            data=data_payload,
            key_insights=insights
        )
