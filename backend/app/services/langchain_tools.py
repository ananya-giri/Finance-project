"""
LangChain Tools for FinIntel Multi-Agent System
FR-015 to FR-023: Specialized tools used by CrewAI agents via LangChain.

Thread-local DB context is set by the orchestrator before running a crew.
"""

import json
import logging
from typing import Optional

from langchain_core.tools import tool

logger = logging.getLogger("langchain_tools")

# Module-level context variables — set by crewai_orchestrator before kickoff
_current_db = None
_current_ticker: Optional[str] = None


# ---------------------------------------------------------------------------
# Helper: safe DB session accessor
# ---------------------------------------------------------------------------

def _get_db():
    if _current_db is None:
        raise RuntimeError(
            "Database session not initialized. "
            "Set langchain_tools._current_db before running tools."
        )
    return _current_db


# ---------------------------------------------------------------------------
# Tool 1: Financial Metrics
# ---------------------------------------------------------------------------

@tool
def get_financial_metrics(ticker: str) -> str:
    """Get the latest financial metrics for a company ticker symbol.
    Returns revenue, EBITDA, net profit, operating margin, EPS, ROE, ROA,
    free cash flow, and debt ratio for the most recent annual periods."""
    try:
        from backend.app.models.structured_metrics import StructuredMetric

        db = _get_db()
        ticker = ticker.upper().strip()

        metrics = (
            db.query(StructuredMetric)
            .filter(
                StructuredMetric.ticker == ticker,
                StructuredMetric.period_type == "ANNUAL"
            )
            .order_by(StructuredMetric.period_end_date.desc())
            .limit(5)
            .all()
        )

        if not metrics:
            return f"No financial metrics found for ticker '{ticker}'. Please ingest historical data first."

        output_lines = [f"=== Financial Metrics for {ticker} (Latest 5 Annual Periods) ===\n"]
        for m in metrics:
            output_lines.append(f"Period: {m.fiscal_period} (ending {m.period_end_date})")
            output_lines.append(f"  Revenue:           ${m.revenue:,.0f}" if m.revenue else "  Revenue:           N/A")
            output_lines.append(f"  EBITDA:            ${m.ebitda:,.0f}" if m.ebitda else "  EBITDA:            N/A")
            output_lines.append(f"  EBIT:              ${m.ebit:,.0f}" if m.ebit else "  EBIT:              N/A")
            output_lines.append(f"  Net Profit:        ${m.net_profit:,.0f}" if m.net_profit else "  Net Profit:        N/A")
            output_lines.append(f"  Operating Margin:  {m.operating_margin * 100:.1f}%" if m.operating_margin else "  Operating Margin:  N/A")
            output_lines.append(f"  Operating CF:      ${m.operating_cash_flow:,.0f}" if m.operating_cash_flow else "  Operating CF:      N/A")
            output_lines.append(f"  Free Cash Flow:    ${m.free_cash_flow:,.0f}" if m.free_cash_flow else "  Free Cash Flow:    N/A")
            output_lines.append(f"  Debt Ratio:        {m.debt_ratio:.3f}" if m.debt_ratio else "  Debt Ratio:        N/A")
            output_lines.append(f"  EPS:               ${m.eps:.2f}" if m.eps else "  EPS:               N/A")
            output_lines.append(f"  ROE:               {m.roe * 100:.1f}%" if m.roe else "  ROE:               N/A")
            output_lines.append(f"  ROA:               {m.roa * 100:.1f}%" if m.roa else "  ROA:               N/A")
            output_lines.append("")

        return "\n".join(output_lines)

    except Exception as e:
        logger.error(f"get_financial_metrics error for {ticker}: {e}")
        return f"Error retrieving financial metrics for '{ticker}': {str(e)}"


# ---------------------------------------------------------------------------
# Tool 2: Knowledge Base Search (ChromaDB)
# ---------------------------------------------------------------------------

@tool
def search_knowledge_base(query: str, ticker: str = "") -> str:
    """Search the ChromaDB knowledge base for relevant financial documents.
    Performs semantic similarity search over indexed document chunks.
    Provide an optional ticker to filter results to a specific company."""
    try:
        from backend.app.services.chroma_service import ChromaService

        ticker_filter = ticker.upper().strip() if ticker and ticker.strip() else None
        result = ChromaService.search_similar(
            query=query,
            ticker=ticker_filter,
            n_results=5
        )

        if not result.get("results"):
            fallback_msg = f"No documents found in ChromaDB for query: '{query}'"
            if ticker_filter:
                fallback_msg += f" (ticker filter: {ticker_filter})"

            # Fall back to SQLite-based RAG if ChromaDB is empty
            try:
                db = _get_db()
                from backend.app.services.rag_service import RAGService
                sqlite_result = RAGService.search_evidence(
                    db=db,
                    query=query,
                    ticker=ticker_filter,
                    top_k=5
                )
                if sqlite_result.get("evidence"):
                    lines = [f"=== Knowledge Base Search Results (SQLite RAG) for: '{query}' ===\n"]
                    for ev in sqlite_result["evidence"]:
                        lines.append(f"Source: {ev.get('title', 'Unknown')} [{ev.get('ticker', '')}]")
                        lines.append(f"Similarity: {ev.get('similarity_score', 0):.3f}")
                        lines.append(f"Text: {ev.get('text', '')[:300]}...")
                        lines.append("")
                    return "\n".join(lines)
            except Exception:
                pass

            return fallback_msg

        lines = [f"=== Knowledge Base Search Results for: '{query}' ===\n"]
        for item in result["results"]:
            meta = item.get("metadata", {})
            lines.append(f"Rank {item['rank']}: {meta.get('title', item['id'])}")
            lines.append(f"  Ticker: {meta.get('ticker', 'N/A')} | Doc Type: {meta.get('doc_type', 'N/A')}")
            lines.append(f"  Similarity: {item['similarity_score']:.3f}")
            lines.append(f"  Text: {item['text'][:350]}...")
            lines.append("")

        return "\n".join(lines)

    except Exception as e:
        logger.error(f"search_knowledge_base error: {e}")
        return f"Error searching knowledge base: {str(e)}"


# ---------------------------------------------------------------------------
# Tool 3: Market Intelligence
# ---------------------------------------------------------------------------

@tool
def get_market_intelligence(category: str = "ALL") -> str:
    """Get external market intelligence events and economic indicators.
    Filter by category: FINANCIAL, REGULATORY, POLITICAL, ENVIRONMENTAL,
    SUPPLY_CHAIN, COMPETITIVE, or ALL for everything.
    Returns recent geopolitical events, regulatory changes, and market news."""
    try:
        from backend.app.models.market_intelligence import MarketIntelligenceEvent, EconomicIndicator

        db = _get_db()
        category = category.upper().strip()

        # Query events
        event_query = db.query(MarketIntelligenceEvent)
        if category and category != "ALL":
            event_query = event_query.filter(
                MarketIntelligenceEvent.impact_category == category
            )
        events = event_query.order_by(
            MarketIntelligenceEvent.event_date.desc()
        ).limit(10).all()

        # Query economic indicators
        indicators = db.query(EconomicIndicator).limit(8).all()

        lines = [f"=== Market Intelligence Report (Category: {category}) ===\n"]

        if events:
            lines.append("--- Recent Market Events ---")
            for ev in events:
                affected = []
                try:
                    affected = json.loads(ev.affected_sectors or "[]")
                except Exception:
                    pass
                lines.append(f"[{ev.severity}] {ev.title}")
                lines.append(f"  Category: {ev.impact_category} | Type: {ev.event_type}")
                lines.append(f"  Sentiment: {ev.sentiment} | Confidence: {ev.confidence_score:.0%}")
                lines.append(f"  Summary: {ev.summary[:250]}")
                if affected:
                    lines.append(f"  Affected Sectors: {', '.join(affected[:5])}")
                lines.append("")
        else:
            lines.append("No market events found for the specified category.\n")

        if indicators:
            lines.append("--- Key Economic Indicators ---")
            for ind in indicators:
                change_str = f" ({ind.change_pct_24h:+.2f}%)" if ind.change_pct_24h else ""
                lines.append(
                    f"  {ind.name}: {ind.current_value} {ind.unit}{change_str} [{ind.category}]"
                )
            lines.append("")

        return "\n".join(lines)

    except Exception as e:
        logger.error(f"get_market_intelligence error: {e}")
        return f"Error retrieving market intelligence: {str(e)}"


# ---------------------------------------------------------------------------
# Tool 4: Financial Forecast
# ---------------------------------------------------------------------------

@tool
def calculate_forecast(ticker: str, metric: str, periods: int) -> str:
    """Generate a financial forecast using historical data for a company.
    
    Args:
        ticker: Company ticker symbol (e.g. AAPL)
        metric: Metric to forecast. Options: revenue, ebitda, net_profit,
                operating_margin, eps, free_cash_flow
        periods: Number of future annual periods to forecast (1-5)

    Returns:
        Forecast values with estimated growth rates and confidence ranges.
    """
    try:
        from backend.app.models.structured_metrics import StructuredMetric

        db = _get_db()
        ticker = ticker.upper().strip()
        metric = metric.lower().strip()
        periods = max(1, min(int(periods), 5))

        valid_metrics = {
            "revenue", "ebitda", "ebit", "net_profit",
            "operating_margin", "eps", "free_cash_flow",
            "operating_cash_flow", "roe", "roa"
        }
        if metric not in valid_metrics:
            return (
                f"Invalid metric '{metric}'. "
                f"Valid options: {', '.join(sorted(valid_metrics))}"
            )

        historical = (
            db.query(StructuredMetric)
            .filter(
                StructuredMetric.ticker == ticker,
                StructuredMetric.period_type == "ANNUAL"
            )
            .order_by(StructuredMetric.period_end_date.asc())
            .all()
        )

        if not historical:
            return f"No historical data found for '{ticker}'. Ingest data first."

        values = []
        fiscal_periods = []
        for m in historical:
            val = getattr(m, metric, None)
            if val is not None and val != 0:
                values.append(float(val))
                fiscal_periods.append(m.fiscal_period)

        if len(values) < 2:
            return f"Insufficient historical data for '{metric}' forecasting (need ≥ 2 data points)."

        # Calculate compound annual growth rate from historical data
        import math
        n_years = len(values) - 1
        if values[0] > 0 and values[-1] > 0:
            cagr = (values[-1] / values[0]) ** (1 / n_years) - 1
        else:
            # Simple average growth rate when CAGR isn't applicable
            growth_rates = [
                (values[i] - values[i - 1]) / abs(values[i - 1])
                for i in range(1, len(values))
                if values[i - 1] != 0
            ]
            cagr = sum(growth_rates) / len(growth_rates) if growth_rates else 0.05

        # Cap extreme growth rates for plausibility
        cagr = max(-0.50, min(cagr, 0.50))

        last_val = values[-1]
        last_period = fiscal_periods[-1]

        lines = [
            f"=== Financial Forecast: {ticker} — {metric.upper()} ===",
            f"Historical data points: {len(values)} annual periods",
            f"Last actual ({last_period}): {last_val:,.2f}",
            f"Estimated CAGR: {cagr * 100:.1f}%\n",
            "--- Projections ---"
        ]

        # Extract base year from last fiscal period (e.g. "2024-FY")
        try:
            base_year = int(last_period.split("-")[0])
        except Exception:
            base_year = 2024

        for i in range(1, periods + 1):
            proj = last_val * ((1 + cagr) ** i)
            # Simple confidence band: ±15% at 1 year, widening 5% per additional year
            margin = 0.15 + (i - 1) * 0.05
            low = proj * (1 - margin)
            high = proj * (1 + margin)
            year = base_year + i
            lines.append(
                f"  FY{year}: {proj:,.2f}  "
                f"[Range: {low:,.2f} — {high:,.2f}]  "
                f"(±{margin * 100:.0f}% confidence band)"
            )

        lines.append(
            f"\nNote: Projections are trend-extrapolations based on {n_years}-year CAGR. "
            "Actual results depend on macro conditions, competitive dynamics, and company execution."
        )

        return "\n".join(lines)

    except Exception as e:
        logger.error(f"calculate_forecast error for {ticker}/{metric}: {e}")
        return f"Error generating forecast for '{ticker}' metric '{metric}': {str(e)}"


# ---------------------------------------------------------------------------
# Tool 5: Company Info
# ---------------------------------------------------------------------------

@tool
def get_company_info(ticker: str) -> str:
    """Get basic company information from the database including name, sector,
    industry, country, and data availability for the given ticker symbol."""
    try:
        from backend.app.models.company import Company
        from backend.app.models.structured_metrics import StructuredMetric

        db = _get_db()
        ticker = ticker.upper().strip()

        company = (
            db.query(Company)
            .filter(Company.ticker == ticker)
            .first()
        )

        if not company:
            return (
                f"Company '{ticker}' not found in the database. "
                "Please ingest historical data for this ticker first."
            )

        metric_count = (
            db.query(StructuredMetric)
            .filter(
                StructuredMetric.ticker == ticker,
                StructuredMetric.period_type == "ANNUAL"
            )
            .count()
        )

        lines = [
            f"=== Company Profile: {ticker} ===",
            f"Name:              {company.name}",
            f"Sector:            {company.sector or 'N/A'}",
            f"Industry:          {company.industry or 'N/A'}",
            f"Country:           {company.country or 'USA'}",
            f"Currency:          {company.currency or 'USD'}",
            f"Years of Data:     {company.years_of_data_available}",
            f"5-Year History:    {'Yes' if company.has_five_year_history else 'No'}",
            f"Latest Fiscal Year:{company.latest_fiscal_year or 'N/A'}",
            f"Annual Metrics:    {metric_count} periods available",
            f"Last Synced:       {company.last_synced_at.date() if company.last_synced_at else 'Never'}",
            f"Auto-Sync:         {'Enabled' if company.auto_sync_enabled else 'Disabled'}",
        ]

        return "\n".join(lines)

    except Exception as e:
        logger.error(f"get_company_info error for {ticker}: {e}")
        return f"Error retrieving company info for '{ticker}': {str(e)}"


# ---------------------------------------------------------------------------
# Tool 6: Scenario Analysis (FR-034 to FR-036)
# ---------------------------------------------------------------------------

@tool
def run_scenario_analysis(ticker: str, scenario_type: str, parameters_json: str = "{}") -> str:
    """Run what-if scenario simulation and estimate financial impacts (FR-034 to FR-036).
    scenario_type must be one of:
      CURRENCY_FLUCTUATION, TARIFF_INCREASE, INTEREST_RATE_CHANGE,
      SUPPLY_CHAIN_DISRUPTION, MARKET_DOWNTURN.
    parameters_json: JSON string with scenario-specific shock parameters."""
    try:
        from backend.app.services.scenario_analysis import ScenarioAnalysisEngine

        db = _get_db()
        params = json.loads(parameters_json) if parameters_json else {}
        res = ScenarioAnalysisEngine.run_scenario(
            db=db,
            ticker=ticker,
            scenario_type=scenario_type,
            parameters=params
        )

        impacts = res["impacts"]
        lines = [
            f"=== Scenario Analysis: {res['scenario_name']} for {ticker.upper()} ===",
            f"Run ID: {res['run_id']} | Severity: {impacts['overall_impact_severity']}",
            f"Revenue Shock:     {impacts['revenue']['change_pct']:+.2f}% (${impacts['revenue']['delta']:+,.0f}) -> ${impacts['revenue']['post_scenario']:,.0f}",
            f"EBITDA Shock:      {impacts['ebitda']['change_pct']:+.2f}% (${impacts['ebitda']['delta']:+,.0f}) -> ${impacts['ebitda']['post_scenario']:,.0f}",
            f"Net Profit Shock:  {impacts['net_profit']['change_pct']:+.2f}% (${impacts['net_profit']['delta']:+,.0f}) -> ${impacts['net_profit']['post_scenario']:,.0f}",
            f"Operating CF Shock:{impacts['operating_cash_flow']['change_pct']:+.2f}% (${impacts['operating_cash_flow']['delta']:+,.0f})",
            f"EPS Impact:        {impacts['eps']['change_pct']:+.2f}% (${impacts['eps']['delta']:+.2f}) -> ${impacts['eps']['post_scenario']:.2f}",
            "",
            "=== Strategic Risk Mitigations ==="
        ]
        for m in res["risk_mitigations"]:
            lines.append(f"- [{m['horizon']}]: {m['action']}")

        return "\n".join(lines)

    except Exception as e:
        logger.error(f"run_scenario_analysis error for {ticker}: {e}")
        return f"Error executing scenario analysis for '{ticker}': {str(e)}"


# ---------------------------------------------------------------------------
# Tool 7: Strategic Recommendations (FR-037 to FR-040)
# ---------------------------------------------------------------------------

@tool
def generate_strategic_recommendations(ticker: str) -> str:
    """Generate 6-Pillar priority-ranked strategic recommendations with financial justifications (FR-037 to FR-040).
    Covers Cost Optimization, Investment Prioritization, Risk Mitigation,
    Market Expansion, Pricing Strategies, and Capital Allocation."""
    try:
        from backend.app.services.recommendation_service import RecommendationService

        db = _get_db()
        report = RecommendationService.generate_recommendations(db=db, ticker=ticker)

        lines = [
            f"=== Strategic Recommendations: {ticker.upper()} ===",
            f"Report ID: {report['report_id']} | Top Category: {report['top_priority_category']}",
            f"Total Recommendations: {report['total_recommendations']} (Ranked by Priority Score)",
            ""
        ]

        for r in report["recommendations"]:
            lines.append(f"Rank #{r['priority_rank']} [{r['priority']}] {r['category_name']} (Score: {r['priority_score']}/100)")
            lines.append(f"  Title: {r['title']}")
            lines.append(f"  Timeframe: {r['timeframe']} | Expected Impact: {r['expected_impact']}")
            lines.append(f"  Justification: {r['justification'][:250]}...")
            lines.append("")

        return "\n".join(lines)

    except Exception as e:
        logger.error(f"generate_strategic_recommendations error for {ticker}: {e}")
        return f"Error generating strategic recommendations for '{ticker}': {str(e)}"

