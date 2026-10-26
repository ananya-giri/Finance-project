import logging
from typing import Dict, Any, List, Optional
from backend.app.services.agents.base_agent import BaseAgent, AgentContext, AgentResult
from backend.app.models.company import Company
from backend.app.models.structured_metrics import StructuredMetric
from backend.app.models.financial_statement import FinancialStatement

logger = logging.getLogger("financial_analysis_agent")

class FinancialAnalysisAgent(BaseAgent):
    """
    FR-016: Financial Analysis Agent
    Analyzes historical company performance over a minimum 5-year timeline.
    Evaluates growth rates (CAGR), profitability trends, balance sheet leverage,
    cash flow quality, and operational efficiency.
    """
    agent_id: str = "FINANCIAL_ANALYSIS"
    name: str = "Financial Analysis Agent"
    role: str = "Historical Financial Performance Specialist"
    description: str = "Analyzes 5-year historical financial statements, computes growth CAGRs, evaluates margin resilience, capital efficiency, and solvency metrics."
    version: str = "1.0.0"
    fr_code: str = "FR-016"
    capabilities: List[str] = [
        "5-Year Revenue & Earnings CAGR Calculation",
        "Operating & Gross Margin Trajectory Analysis",
        "Debt Leverage & Solvency Stress Evaluation",
        "Free Cash Flow Conversion & Quality of Earnings Audit",
        "DuPont Capital Efficiency (ROE & ROA) Decomposition",
        "Historical Anomaly & Margin Volatility Detection"
    ]

    def execute(self, context: AgentContext) -> AgentResult:
        ticker = context.ticker
        db = context.db

        company = db.query(Company).filter(Company.ticker == ticker).first()
        if not company:
            # Fallback or synthetic diagnostic if ticker not ingested yet
            return AgentResult(
                agent_id=self.agent_id,
                agent_name=self.name,
                status="COMPLETED",
                confidence_score=0.40,
                summary=f"No ingested historical financial records found for ticker {ticker}. Ingestion (FR-001) required for comprehensive audit.",
                key_insights=[
                    f"Ticker {ticker} is not yet registered in the historical repository.",
                    "Execute FR-001 historical ingestion to populate 5-year statements."
                ],
                data={
                    "ticker": ticker,
                    "records_found": 0,
                    "composite_score": 50.0,
                    "verdict": "DATA_DEFICIENT"
                }
            )

        # Retrieve annual structured metrics ordered by period_end_date ascending
        metrics = (
            db.query(StructuredMetric)
            .filter(StructuredMetric.company_id == company.id, StructuredMetric.period_type == "ANNUAL")
            .order_by(StructuredMetric.period_end_date.asc())
            .all()
        )

        if not metrics:
            # Check for quarterly if annual not available
            metrics = (
                db.query(StructuredMetric)
                .filter(StructuredMetric.company_id == company.id)
                .order_by(StructuredMetric.period_end_date.asc())
                .all()
            )

        if not metrics:
            return AgentResult(
                agent_id=self.agent_id,
                agent_name=self.name,
                status="COMPLETED",
                confidence_score=0.50,
                summary=f"Company profile exists for {company.name} ({ticker}), but zero structured metrics are available.",
                key_insights=["Financial metrics calculation engine (FR-003) must be triggered."],
                data={"ticker": ticker, "company_name": company.name, "composite_score": 50.0, "verdict": "UNCOMPUTED_METRICS"}
            )

        years_count = len(metrics)
        earliest = metrics[0]
        latest = metrics[-1]

        # 1. Growth CAGR Calculations
        revenue_series = [m.revenue for m in metrics if m.revenue is not None and m.revenue > 0]
        rev_cagr = None
        if len(revenue_series) >= 2 and revenue_series[0] > 0:
            periods = len(revenue_series) - 1
            rev_cagr = ((revenue_series[-1] / revenue_series[0]) ** (1.0 / periods) - 1.0) * 100.0

        net_profit_series = [m.net_profit for m in metrics if m.net_profit is not None]
        net_profit_cagr = None
        if len(net_profit_series) >= 2 and net_profit_series[0] > 0 and net_profit_series[-1] > 0:
            periods = len(net_profit_series) - 1
            net_profit_cagr = ((net_profit_series[-1] / net_profit_series[0]) ** (1.0 / periods) - 1.0) * 100.0

        # 2. Margin Trends
        latest_op_margin = (latest.operating_margin * 100.0) if latest.operating_margin is not None else 0.0
        earliest_op_margin = (earliest.operating_margin * 100.0) if earliest.operating_margin is not None else 0.0
        margin_change_bps = (latest_op_margin - earliest_op_margin) * 100.0

        # 3. Cash Flow Quality: FCF Conversion Rate (Free Cash Flow / Net Profit)
        fcf_conversion = None
        if latest.net_profit and latest.net_profit > 0 and latest.free_cash_flow is not None:
            fcf_conversion = (latest.free_cash_flow / latest.net_profit) * 100.0

        # 4. Solvency & Balance Sheet Leverage
        latest_debt_to_equity = latest.debt_to_equity if latest.debt_to_equity is not None else 0.0
        latest_debt_ratio = (latest.debt_ratio * 100.0) if latest.debt_ratio is not None else 0.0

        # 5. Capital Efficiency: ROE & ROA
        latest_roe = (latest.roe * 100.0) if latest.roe is not None else 0.0
        latest_roa = (latest.roa * 100.0) if latest.roa is not None else 0.0

        # 6. Quantitative Health Scores (0 - 100)
        # Profitability Score
        prof_score = min(100.0, max(10.0, (latest_op_margin * 2.0) + (latest_roe * 0.8)))
        # Growth Score
        growth_val = rev_cagr if rev_cagr is not None else 5.0
        growth_score = min(100.0, max(10.0, 50.0 + (growth_val * 2.5)))
        # Solvency Score (lower debt = higher score)
        solvency_score = 100.0 - min(80.0, max(0.0, (latest_debt_to_equity * 25.0)))
        # Cash Flow Score
        fcf_conv_val = fcf_conversion if fcf_conversion is not None else 75.0
        cash_score = min(100.0, max(20.0, fcf_conv_val * 0.9))

        composite_score = round((prof_score * 0.30) + (growth_score * 0.30) + (solvency_score * 0.20) + (cash_score * 0.20), 1)

        # Verdict
        if composite_score >= 82:
            verdict = "EXEMPLARY_COMPOUNDER"
        elif composite_score >= 68:
            verdict = "ROBUST_PERFORMANCE"
        elif composite_score >= 50:
            verdict = "MODERATE_STABILITY"
        else:
            verdict = "MARGIN_LEVERAGE_STRESS"

        # Key Insights & Takeaways
        insights = []
        if rev_cagr is not None:
            insights.append(
                f"Historical Revenue expanded at a {rev_cagr:.1f}% CAGR over {len(revenue_series)} periods "
                f"(Latest Revenue: ${latest.revenue:,.0f} from ${earliest.revenue:,.0f})."
            )
        if latest.operating_margin is not None:
            trend_str = "expanded" if margin_change_bps >= 0 else "compressed"
            insights.append(
                f"Operating Margin currently stands at {latest_op_margin:.1f}%, having {trend_str} by {abs(margin_change_bps):.0f} bps over the analyzed horizon."
            )
        if fcf_conversion is not None:
            insights.append(
                f"Cash Flow conversion is strong at {fcf_conversion:.1f}% of net profit converted to free cash flow (FCF: ${latest.free_cash_flow:,.0f})."
            )
        if latest_debt_to_equity is not None:
            solv_desc = "conservative" if latest_debt_to_equity < 1.0 else "moderately leveraged"
            insights.append(
                f"Capital structure reflects a {solv_desc} balance sheet with a Debt-to-Equity ratio of {latest_debt_to_equity:.2f}."
            )
        if latest_roe > 0:
            insights.append(f"Return on Equity (ROE) stands at {latest_roe:.1f}%, demonstrating high capital reinvestment efficiency.")

        summary_text = (
            f"Financial Analysis Agent evaluated {years_count} historical financial reporting periods for {company.name} ({ticker}). "
            f"The company demonstrates a {verdict.replace('_', ' ').title()} trajectory with a Composite Financial Score of {composite_score}/100. "
            f"Revenue CAGR is {rev_cagr:.1f}% with an Operating Margin of {latest_op_margin:.1f}% and ROE of {latest_roe:.1f}%."
        )

        data_payload = {
            "ticker": ticker,
            "company_name": company.name,
            "sector": company.sector or "Technology",
            "industry": company.industry or "Information Technology",
            "periods_analyzed": years_count,
            "earliest_period": earliest.fiscal_period,
            "latest_period": latest.fiscal_period,
            "has_five_year_history": company.has_five_year_history,
            "metrics_summary": {
                "latest_revenue": latest.revenue,
                "latest_ebitda": latest.ebitda,
                "latest_net_profit": latest.net_profit,
                "latest_operating_margin_pct": round(latest_op_margin, 2),
                "latest_operating_cash_flow": latest.operating_cash_flow,
                "latest_free_cash_flow": latest.free_cash_flow,
                "latest_debt_to_equity": round(latest_debt_to_equity, 2),
                "latest_debt_ratio_pct": round(latest_debt_ratio, 2),
                "latest_eps": latest.eps,
                "latest_roe_pct": round(latest_roe, 2),
                "latest_roa_pct": round(latest_roa, 2),
                "revenue_cagr_pct": round(rev_cagr, 2) if rev_cagr is not None else None,
                "net_profit_cagr_pct": round(net_profit_cagr, 2) if net_profit_cagr is not None else None,
                "margin_change_bps": round(margin_change_bps, 0),
                "fcf_conversion_pct": round(fcf_conversion, 1) if fcf_conversion is not None else None
            },
            "scorecard": {
                "profitability_score": round(prof_score, 1),
                "growth_score": round(growth_score, 1),
                "solvency_score": round(solvency_score, 1),
                "cash_flow_score": round(cash_score, 1),
                "composite_financial_score": composite_score
            },
            "verdict": verdict,
            "historical_trend_data": [
                {
                    "period": m.fiscal_period,
                    "date": str(m.period_end_date),
                    "revenue": m.revenue,
                    "net_profit": m.net_profit,
                    "operating_margin": round((m.operating_margin * 100.0), 2) if m.operating_margin is not None else None,
                    "free_cash_flow": m.free_cash_flow,
                    "roe": round((m.roe * 100.0), 2) if m.roe is not None else None
                }
                for m in metrics
            ]
        }

        # Store in shared memory for downstream orchestrator and agents
        context.set_shared("financial_analysis", data_payload)

        return AgentResult(
            agent_id=self.agent_id,
            agent_name=self.name,
            status="COMPLETED",
            confidence_score=0.95 if company.has_five_year_history else 0.85,
            summary=summary_text,
            data=data_payload,
            key_insights=insights
        )
