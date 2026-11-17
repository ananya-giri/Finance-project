"""
CrewAI Financial Analysis Orchestrator
FR-015 to FR-023: Advanced multi-agent orchestration using CrewAI + LangChain + Gemini LLM.

Coordinates four specialized AI agents:
  1. Financial Analyst Agent  (FR-016)
  2. Market Intelligence Agent (FR-017, FR-018)
  3. Forecasting Agent         (FR-020)
  4. Strategy Recommendation Agent (FR-021, FR-022)
"""

import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("crewai_orchestrator")


class FinancialCrewOrchestrator:
    """
    Orchestrates a CrewAI multi-agent financial analysis pipeline using
    Google Gemini 1.5 Flash as the backbone LLM for all agents.

    Usage:
        orchestrator = FinancialCrewOrchestrator()
        result = orchestrator.run_analysis(ticker="AAPL", db=db_session)
    """

    def __init__(self):
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI

            api_key = os.getenv("GOOGLE_API_KEY", "")
            if not api_key:
                logger.warning(
                    "GOOGLE_API_KEY environment variable is not set. "
                    "CrewAI agents will fail when making LLM calls."
                )

            self.llm = ChatGoogleGenerativeAI(
                model="gemini-1.5-flash",
                google_api_key=api_key,
                temperature=0.1,
                convert_system_message_to_human=True
            )
            logger.info("FinancialCrewOrchestrator initialized with Gemini 1.5 Flash LLM.")
        except ImportError as e:
            logger.error(f"langchain-google-genai not installed: {e}")
            raise RuntimeError(
                "langchain-google-genai is required. "
                "Run: pip install langchain-google-genai"
            ) from e

    def create_financial_analysis_crew(self, ticker: str):
        """
        Builds and returns a CrewAI Crew with four specialized agents and tasks
        configured for comprehensive financial analysis of the given ticker.

        Args:
            ticker: Company ticker symbol (e.g. "AAPL")

        Returns:
            crewai.Crew instance ready to kickoff
        """
        from crewai import Agent, Task, Crew, Process
        from backend.app.services.langchain_tools import (
            get_financial_metrics,
            search_knowledge_base,
            get_market_intelligence,
            calculate_forecast,
            get_company_info,
        )

        ticker = ticker.upper().strip()

        # ------------------------------------------------------------------
        # Agent 1: Senior Financial Analyst
        # FR-016: Financial Analysis Agent
        # ------------------------------------------------------------------
        financial_analyst = Agent(
            role="Senior Financial Analyst",
            goal=(
                f"Conduct a thorough fundamental analysis of {ticker}'s financial "
                "performance, identifying key trends in revenue, profitability, "
                "cash flow generation, and capital efficiency."
            ),
            backstory=(
                "You are a veteran financial analyst with 15 years of experience at top-tier "
                "investment banks. You specialize in fundamental financial analysis, dissecting "
                "income statements, balance sheets, and cash flow statements to uncover "
                "the true economic health of companies. You are known for your rigorous, "
                "data-driven approach and your ability to spot financial red flags early."
            ),
            tools=[get_financial_metrics, get_company_info],
            llm=self.llm,
            verbose=True,
            allow_delegation=False
        )

        # ------------------------------------------------------------------
        # Agent 2: Market Intelligence Specialist
        # FR-017: Economic Intelligence Agent, FR-018: Geopolitical Risk Agent
        # ------------------------------------------------------------------
        market_analyst = Agent(
            role="Market Intelligence Specialist",
            goal=(
                "Analyze external market conditions, macroeconomic factors, and geopolitical "
                f"risks that could materially impact {ticker}'s sector and business outlook."
            ),
            backstory=(
                "You are a macroeconomic strategist and geopolitical risk analyst with deep "
                "expertise in translating global economic signals into company-level impact "
                "assessments. You monitor interest rate cycles, currency movements, commodity "
                "prices, regulatory changes, and geopolitical flashpoints. Your insights have "
                "consistently helped portfolio managers navigate volatile market environments."
            ),
            tools=[get_market_intelligence, search_knowledge_base],
            llm=self.llm,
            verbose=True,
            allow_delegation=False
        )

        # ------------------------------------------------------------------
        # Agent 3: Quantitative Forecasting Expert
        # FR-020: Forecasting Agent
        # ------------------------------------------------------------------
        forecasting_agent = Agent(
            role="Quantitative Forecasting Expert",
            goal=(
                f"Generate rigorous 1-to-3-year financial forecasts for {ticker}, "
                "using historical trend analysis and growth rate modelling to project "
                "revenue, EBITDA, and earnings trajectories."
            ),
            backstory=(
                "You are a quantitative analyst and data scientist who specializes in "
                "financial time-series forecasting. With a background in econometrics and "
                "machine learning, you build models that extrapolate historical financial "
                "patterns while accounting for mean-reversion, cyclicality, and structural "
                "breaks. Your forecasts include explicit confidence intervals and clearly "
                "stated assumptions."
            ),
            tools=[calculate_forecast, get_financial_metrics],
            llm=self.llm,
            verbose=True,
            allow_delegation=False
        )

        # ------------------------------------------------------------------
        # Agent 4: Strategic Investment Advisor
        # FR-021: Recommendation Agent, FR-022: Explainability Agent
        # ------------------------------------------------------------------
        strategy_agent = Agent(
            role="Strategic Investment Advisor",
            goal=(
                "Synthesize all financial analysis, market intelligence, and forward "
                "projections into a clear, actionable, and well-reasoned investment "
                "recommendation with explicit risk disclosure."
            ),
            backstory=(
                "You are a senior investment strategist with 20 years of experience across "
                "equity research, portfolio management, and strategic advisory. You excel at "
                "integrating quantitative data with qualitative judgment to formulate "
                "investment theses. Your recommendations are known for their clarity, "
                "transparency of reasoning, and balanced treatment of bull and bear cases. "
                "You always back your stance with explicit evidence and acknowledge uncertainty."
            ),
            tools=[search_knowledge_base],
            llm=self.llm,
            verbose=True,
            allow_delegation=False
        )

        # ------------------------------------------------------------------
        # Task 1: Financial Metrics Analysis
        # ------------------------------------------------------------------
        analysis_task = Task(
            description=(
                f"Conduct a comprehensive analysis of {ticker}'s financial metrics. "
                f"Use get_financial_metrics(ticker='{ticker}') to retrieve data, then: "
                "1) Identify revenue growth trends over the past 3-5 years. "
                "2) Assess profitability (EBITDA margins, net margins, operating margins). "
                "3) Evaluate cash flow quality (FCF generation, FCF conversion). "
                "4) Review capital efficiency (ROE, ROA, debt ratio). "
                "5) Highlight any red flags or areas of concern. "
                "Be specific with numbers and percentage changes."
            ),
            agent=financial_analyst,
            expected_output=(
                "A structured financial analysis report with: "
                "(a) Revenue trend summary with CAGR, "
                "(b) Profitability assessment with margin analysis, "
                "(c) Cash flow health evaluation, "
                "(d) Balance sheet strength indicators, "
                "(e) Top 3 financial strengths and top 3 risks identified."
            )
        )

        # ------------------------------------------------------------------
        # Task 2: Market Context Analysis
        # ------------------------------------------------------------------
        market_task = Task(
            description=(
                f"Analyze the external macro and market environment relevant to {ticker}. "
                "Use get_market_intelligence() to retrieve recent events and indicators. "
                "Use search_knowledge_base() to find any relevant market context in documents. "
                "Focus on: "
                "1) Key economic indicators affecting the sector (interest rates, inflation, FX). "
                "2) Recent geopolitical or regulatory events that could impact operations. "
                "3) Competitive dynamics and industry trends. "
                "4) Overall market sentiment and risk environment."
            ),
            agent=market_analyst,
            expected_output=(
                "A market intelligence brief covering: "
                "(a) Macro tailwinds and headwinds for the sector, "
                "(b) Top 3 geopolitical/regulatory risks, "
                "(c) Key economic indicators and their directional impact, "
                "(d) Overall market risk rating (LOW/MEDIUM/HIGH) with justification."
            )
        )

        # ------------------------------------------------------------------
        # Task 3: Quantitative Forecasts
        # ------------------------------------------------------------------
        forecast_task = Task(
            description=(
                f"Generate a 3-year financial forecast for {ticker}. "
                f"Use calculate_forecast(ticker='{ticker}', metric='revenue', periods=3) "
                "and also forecast EBITDA and net_profit. "
                "Additionally retrieve current metrics for context. "
                "Clearly state: "
                "1) Base case projections with estimated values. "
                "2) Key assumptions driving the forecast. "
                "3) Bull and bear scenario ranges. "
                "4) Confidence level in the projections."
            ),
            agent=forecasting_agent,
            expected_output=(
                "A quantitative forecast report with: "
                "(a) 3-year revenue forecast table (base/bull/bear cases), "
                "(b) 3-year EBITDA forecast table, "
                "(c) Key growth assumptions stated explicitly, "
                "(d) Confidence interval explanation, "
                "(e) Top 2 forecast risks that could cause deviation."
            )
        )

        # ------------------------------------------------------------------
        # Task 4: Investment Recommendation
        # ------------------------------------------------------------------
        strategy_task = Task(
            description=(
                f"Based on all analyses provided, formulate a final investment recommendation for {ticker}. "
                "Use search_knowledge_base() to gather any additional supporting evidence from documents. "
                "Your recommendation must include: "
                "1) A clear stance: BUY / HOLD / SELL with conviction level (High/Medium/Low). "
                "2) The primary investment thesis in 2-3 sentences. "
                "3) Key catalysts that could drive outperformance. "
                "4) Top risks that could invalidate the thesis. "
                "5) Suggested time horizon for the recommendation. "
                "Make sure to reference findings from the financial analysis, market intelligence, "
                "and forecast tasks to support your reasoning."
            ),
            agent=strategy_agent,
            expected_output=(
                "An investment recommendation report with: "
                "(a) Recommendation: BUY / HOLD / SELL + Conviction: High/Medium/Low, "
                "(b) Investment thesis (2-3 sentences), "
                "(c) Top 3 bullish catalysts, "
                "(d) Top 3 key risks, "
                "(e) Recommended investment time horizon, "
                "(f) Final summary paragraph synthesizing all evidence."
            )
        )

        # ------------------------------------------------------------------
        # Assemble Crew
        # ------------------------------------------------------------------
        crew = Crew(
            agents=[financial_analyst, market_analyst, forecasting_agent, strategy_agent],
            tasks=[analysis_task, market_task, forecast_task, strategy_task],
            process=Process.sequential,
            verbose=True
        )

        return crew

    def run_analysis(self, ticker: str, db=None) -> Dict[str, Any]:
        """
        Execute the full CrewAI multi-agent analysis pipeline for a given ticker.

        Args:
            ticker: Company ticker symbol
            db: SQLAlchemy database session (injected into tool context)

        Returns:
            Dict with status, ticker, consolidated result, and per-task outputs
        """
        import backend.app.services.langchain_tools as tools_module

        ticker = ticker.upper().strip()
        logger.info(f"Starting CrewAI analysis for ticker: {ticker}")

        # Inject DB session into tool module-level context
        tools_module._current_db = db
        tools_module._current_ticker = ticker

        try:
            crew = self.create_financial_analysis_crew(ticker)
            result = crew.kickoff()

            # Collect per-task outputs
            agent_outputs: Dict[str, str] = {}
            for task in crew.tasks:
                task_key = task.description[:60].strip().replace("\n", " ")
                raw_output = ""
                if task.output:
                    try:
                        raw_output = task.output.raw if hasattr(task.output, "raw") else str(task.output)
                    except Exception:
                        raw_output = str(task.output)
                agent_outputs[task_key] = raw_output

            logger.info(f"CrewAI analysis completed successfully for {ticker}.")
            return {
                "status": "COMPLETED",
                "ticker": ticker,
                "result": str(result),
                "agent_outputs": agent_outputs,
                "agents_count": len(crew.agents),
                "tasks_count": len(crew.tasks)
            }

        except Exception as e:
            logger.error(f"CrewAI analysis failed for {ticker}: {e}", exc_info=True)
            return {
                "status": "FAILED",
                "ticker": ticker,
                "error": str(e),
                "result": None,
                "agent_outputs": {}
            }
        finally:
            # Clean up injected DB context
            tools_module._current_db = None
            tools_module._current_ticker = None
