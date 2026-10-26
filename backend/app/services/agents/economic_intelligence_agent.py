import logging
from typing import Dict, Any, List, Optional
from backend.app.services.agents.base_agent import BaseAgent, AgentContext, AgentResult
from backend.app.models.market_intelligence import EconomicIndicator
from backend.app.models.company import Company

logger = logging.getLogger("economic_intelligence_agent")

class EconomicIntelligenceAgent(BaseAgent):
    """
    FR-017: Economic Intelligence Agent
    Monitors macroeconomic indicators across interest rates, inflation metrics,
    foreign exchange rates, commodities, and benchmark indices.
    Evaluates macroeconomic regime, cost of capital, and currency translation impacts.
    """
    agent_id: str = "ECONOMIC_INTELLIGENCE"
    name: str = "Economic Intelligence Agent"
    role: str = "Macroeconomic Climate & Systemic Risk Specialist"
    description: str = "Monitors real-time and historical economic indicators (Fed funds, CPI, FX, commodities), computes macro sensitivity, and diagnoses systemic headwinds."
    version: str = "1.0.0"
    fr_code: str = "FR-017"
    capabilities: List[str] = [
        "Multi-Asset Macroeconomic Monitoring (Rates, CPI, FX, Energy)",
        "Macro Regime Diagnosis (Hawkish Restrictive vs Easing Stimulative)",
        "Currency Translation Impact Modeling for Multinational Tickers",
        "Cost of Capital & Yield Curve Transmission Analysis",
        "Systemic Inflationary Input Cost Stress Indexing"
    ]

    def execute(self, context: AgentContext) -> AgentResult:
        ticker = context.ticker
        db = context.db

        company = db.query(Company).filter(Company.ticker == ticker).first()
        company_sector = company.sector if company and company.sector else "General"

        # Fetch all economic indicators
        indicators = db.query(EconomicIndicator).all()

        if not indicators:
            # Fallback if indicators not yet populated
            return AgentResult(
                agent_id=self.agent_id,
                agent_name=self.name,
                status="COMPLETED",
                confidence_score=0.50,
                summary="No live macroeconomic indicators found in database. Market intelligence sync (FR-005) recommended.",
                key_insights=["Trigger market intelligence synchronization to collect live indicators."],
                data={"macro_score": 50.0, "regime": "NEUTRAL_BASE"}
            )

        # Categorize indicators
        by_category: Dict[str, List[EconomicIndicator]] = {}
        for ind in indicators:
            cat = ind.category.upper()
            by_category.setdefault(cat, []).append(ind)

        # 1. Interest Rate Regime
        rates = by_category.get("INTEREST_RATE", [])
        fed_funds = next((i.current_value for i in rates if "FED" in i.symbol.upper() or "FUNDS" in i.name.upper()), 4.85)
        treasury_10y = next((i.current_value for i in rates if "10Y" in i.symbol.upper() or "10-YEAR" in i.name.upper() or "^TNX" in i.symbol), 4.25)

        # 2. Inflation Regime
        cpi_items = by_category.get("INFLATION_RATE", [])
        headline_cpi = next((i.current_value for i in cpi_items if "HEADLINE" in i.name.upper()), 2.4)
        core_cpi = next((i.current_value for i in cpi_items if "CORE" in i.name.upper()), 3.3)

        # 3. Foreign Exchange
        fx_items = by_category.get("EXCHANGE_RATE", [])
        eur_usd = next((i.current_value for i in fx_items if "EUR" in i.symbol.upper() or "EUR / USD" in i.name.upper()), 1.085)
        usd_jpy = next((i.current_value for i in fx_items if "JPY" in i.symbol.upper() or "USD / JPY" in i.name.upper()), 152.0)
        usd_inr = next((i.current_value for i in fx_items if "INR" in i.symbol.upper() or "USD / INR" in i.name.upper()), 84.1)

        # 4. Commodities
        commodities = by_category.get("COMMODITY_PRICE", [])
        oil_price = next((i.current_value for i in commodities if "OIL" in i.name.upper() or "CRUDE" in i.name.upper() or "CL=F" in i.symbol), 71.5)
        gold_price = next((i.current_value for i in commodities if "GOLD" in i.name.upper() or "GC=F" in i.symbol), 2740.0)

        # 5. Market Indices
        indices = by_category.get("STOCK_INDEX", [])
        sp500 = next((i.current_value for i in indices if "S&P" in i.name.upper() or "^GSPC" in i.symbol), 5850.0)
        sp500_chg = next((i.change_pct_24h for i in indices if "S&P" in i.name.upper() or "^GSPC" in i.symbol), 0.4)

        # Diagnose Macro Regime
        if fed_funds > 4.5 and headline_cpi > 3.0:
            regime = "RESTRICTIVE_HAWKISH"
            regime_desc = "High interest rate stance combating persistent core inflation, creating moderate cost of capital headwinds."
            macro_score = 58.0
        elif fed_funds > 4.0 and headline_cpi <= 2.8:
            regime = "NORMALIZING_DISINFLATION"
            regime_desc = "Disinflation is progressing with central banks pausing rate hikes, supporting equities and credit conditions."
            macro_score = 74.0
        elif fed_funds <= 3.5:
            regime = "ACCOMMODATIVE_EXPANSION"
            regime_desc = "Eased monetary policy promoting corporate capital expenditure and consumer liquidity."
            macro_score = 85.0
        else:
            regime = "BALANCED_EQUILIBRIUM"
            regime_desc = "Macroeconomic indicators reflect steady baseline activity with balanced rate and inflation trajectories."
            macro_score = 68.0

        # Sector-Specific Macro Sensitivity
        is_tech = any(k in company_sector.lower() for k in ["tech", "software", "semiconductor", "hardware"])
        is_energy = "energy" in company_sector.lower() or "oil" in company_sector.lower()
        is_financial = "finance" in company_sector.lower() or "bank" in company_sector.lower()

        sensitivities = {
            "interest_rate_sensitivity": "HIGH" if (is_tech or is_financial) else "MEDIUM",
            "fx_dollar_strength_impact": "HEADWIND" if eur_usd < 1.08 else "NEUTRAL",
            "energy_cost_exposure": "BENEFICIARY" if is_energy else ("LOW" if oil_price < 80 else "MODERATE"),
            "equity_market_sentiment": "BULLISH" if (sp500_chg and sp500_chg > 0) else "NEUTRAL"
        }

        # Key Insights
        insights = [
            f"Macro Regime: {regime.replace('_', ' ').title()} - {regime_desc}",
            f"Monetary Policy: Benchmark Fed Funds rate is at {fed_funds:.2f}%, 10-Year Treasury Yield stands at {treasury_10y:.2f}%.",
            f"Inflation Signals: US Headline CPI YoY is {headline_cpi:.1f}% with Core CPI at {core_cpi:.1f}%.",
            f"Currency Environment: EUR/USD is trading at {eur_usd:.4f}; USD strength presents a {sensitivities['fx_dollar_strength_impact'].lower()} for overseas corporate sales.",
            f"Commodities: WTI Crude Oil is at ${oil_price:.2f}/bbl and Gold is at ${gold_price:.1f}/oz."
        ]

        summary_text = (
            f"Economic Intelligence Agent audited {len(indicators)} live indicators. Macro climate is diagnosed as "
            f"'{regime.replace('_', ' ').title()}' (Macro Health Score: {macro_score}/100). Benchmark 10Y Yield is {treasury_10y:.2f}% "
            f"and US CPI is {headline_cpi:.1f}%, indicating manageable cost of capital constraints for {ticker}."
        )

        data_payload = {
            "ticker": ticker,
            "total_indicators_monitored": len(indicators),
            "macro_regime": regime,
            "macro_health_score": macro_score,
            "key_metrics": {
                "fed_funds_rate_pct": fed_funds,
                "treasury_10y_yield_pct": treasury_10y,
                "headline_cpi_pct": headline_cpi,
                "core_cpi_pct": core_cpi,
                "eur_usd": eur_usd,
                "usd_jpy": usd_jpy,
                "usd_inr": usd_inr,
                "crude_oil_usd": oil_price,
                "gold_usd": gold_price,
                "sp500_index": sp500,
                "sp500_change_pct": sp500_chg
            },
            "sensitivities": sensitivities,
            "indicators_breakdown": [
                {
                    "symbol": ind.symbol,
                    "name": ind.name,
                    "category": ind.category,
                    "current_value": ind.current_value,
                    "unit": ind.unit,
                    "change_24h": ind.change_24h,
                    "frequency": ind.frequency
                }
                for ind in indicators[:12] # Top indicators
            ]
        }

        context.set_shared("economic_intelligence", data_payload)

        return AgentResult(
            agent_id=self.agent_id,
            agent_name=self.name,
            status="COMPLETED",
            confidence_score=0.92,
            summary=summary_text,
            data=data_payload,
            key_insights=insights
        )
