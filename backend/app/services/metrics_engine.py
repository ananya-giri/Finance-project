from datetime import date, datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from backend.app.models.structured_metrics import StructuredMetric
from backend.app.models.company import Company
from backend.app.models.financial_statement import FinancialStatement

class MetricsEngine:
    """
    FR-003 Calculation & Storage Engine for structured financial metrics:
    - Revenue
    - EBITDA
    - EBIT
    - Net Profit
    - Operating Margin
    - Cash Flow (Operating & Free Cash Flow)
    - Debt Ratio (Debt-to-Assets, Debt-to-Equity)
    - EPS
    - ROE
    - ROA
    """

    @staticmethod
    def calculate_and_store_metrics(
        db: Session,
        company: Company,
        period_type: str,           # 'ANNUAL' or 'QUARTERLY'
        fiscal_period: str,         # e.g., '2024-FY' or '2025-Q1'
        period_end_date: date,
        data: Dict[str, Any],
        source: str = "FINANCIAL_STATEMENTS"
    ) -> StructuredMetric:
        """
        Parses raw line items or direct inputs, computes missing ratios,
        and upserts the record into structured_metrics table.
        """
        # 1. Revenue
        revenue = data.get("revenue") or data.get("Total Revenue") or data.get("Operating Revenue")
        revenue = float(revenue) if revenue is not None else None

        # 2. EBIT (Operating Income)
        ebit = data.get("ebit") or data.get("Operating Income") or data.get("EBIT")
        ebit = float(ebit) if ebit is not None else None

        # 3. EBITDA (EBIT + Depreciation & Amortization)
        ebitda = data.get("ebitda") or data.get("EBITDA") or data.get("Normalized EBITDA")
        if ebitda is None and ebit is not None:
            da = data.get("depreciation_amortization") or data.get("Reconciled Depreciation") or data.get("Depreciation And Amortization") or 0.0
            ebitda = ebit + float(da)
        ebitda = float(ebitda) if ebitda is not None else None

        # 4. Net Profit (Net Income)
        net_profit = data.get("net_profit") or data.get("Net Income") or data.get("Net Income Common Stockholders")
        net_profit = float(net_profit) if net_profit is not None else None

        # 5. Operating Margin (EBIT / Revenue)
        operating_margin = data.get("operating_margin")
        if operating_margin is None and ebit is not None and revenue and revenue > 0:
            operating_margin = round(ebit / revenue, 4)
        elif operating_margin is not None:
            operating_margin = round(float(operating_margin), 4)

        # 6. Cash Flow (Operating & Free)
        operating_cash_flow = (
            data.get("operating_cash_flow") or 
            data.get("cash_flow") or 
            data.get("Operating Cash Flow") or 
            data.get("Cash Flow From Continuing Operating Activities")
        )
        operating_cash_flow = float(operating_cash_flow) if operating_cash_flow is not None else None

        free_cash_flow = data.get("free_cash_flow") or data.get("Free Cash Flow")
        if free_cash_flow is None and operating_cash_flow is not None:
            capex = data.get("capital_expenditure") or data.get("Capital Expenditure") or 0.0
            free_cash_flow = operating_cash_flow - abs(float(capex))
        free_cash_flow = float(free_cash_flow) if free_cash_flow is not None else None

        # Assets & Equity for Balance Sheet ratios
        total_assets = data.get("total_assets") or data.get("Total Assets")
        total_assets = float(total_assets) if total_assets is not None else None

        total_equity = data.get("total_equity") or data.get("Stockholders Equity") or data.get("Total Equity Gross Minority Interest")
        total_equity = float(total_equity) if total_equity is not None else None

        total_debt = data.get("total_debt") or data.get("Total Debt")
        total_debt = float(total_debt) if total_debt is not None else None

        # 7. Debt Ratio (Debt to Assets & Debt to Equity)
        debt_ratio = data.get("debt_ratio")
        if debt_ratio is None and total_debt is not None and total_assets and total_assets > 0:
            debt_ratio = round(total_debt / total_assets, 4)
        elif debt_ratio is not None:
            debt_ratio = round(float(debt_ratio), 4)

        debt_to_equity = data.get("debt_to_equity")
        if debt_to_equity is None and total_debt is not None and total_equity and total_equity > 0:
            debt_to_equity = round(total_debt / total_equity, 4)
        elif debt_to_equity is not None:
            debt_to_equity = round(float(debt_to_equity), 4)

        # 8. EPS (Earnings Per Share)
        eps = data.get("eps") or data.get("Diluted EPS") or data.get("Basic EPS")
        eps = round(float(eps), 4) if eps is not None else None

        # 9. ROE (Return on Equity = Net Income / Total Equity)
        roe = data.get("roe")
        if roe is None and net_profit is not None and total_equity and total_equity > 0:
            roe = round(net_profit / total_equity, 4)
        elif roe is not None:
            roe = round(float(roe), 4)

        # 10. ROA (Return on Assets = Net Income / Total Assets)
        roa = data.get("roa")
        if roa is None and net_profit is not None and total_assets and total_assets > 0:
            roa = round(net_profit / total_assets, 4)
        elif roa is not None:
            roa = round(float(roa), 4)

        # Additional indicators
        gross_margin = data.get("gross_margin")
        gross_profit = data.get("Gross Profit")
        if gross_margin is None and gross_profit is not None and revenue and revenue > 0:
            gross_margin = round(float(gross_profit) / revenue, 4)

        current_ratio = data.get("current_ratio")
        current_assets = data.get("Current Assets")
        current_liabilities = data.get("Current Liabilities")
        if current_ratio is None and current_assets and current_liabilities and float(current_liabilities) > 0:
            current_ratio = round(float(current_assets) / float(current_liabilities), 4)

        # Find existing record or create new
        existing_metric = db.query(StructuredMetric).filter(
            StructuredMetric.company_id == company.id,
            StructuredMetric.period_type == period_type,
            StructuredMetric.fiscal_period == fiscal_period
        ).first()

        if existing_metric:
            metric = existing_metric
            metric.period_end_date = period_end_date
            metric.revenue = revenue if revenue is not None else metric.revenue
            metric.ebitda = ebitda if ebitda is not None else metric.ebitda
            metric.ebit = ebit if ebit is not None else metric.ebit
            metric.net_profit = net_profit if net_profit is not None else metric.net_profit
            metric.operating_margin = operating_margin if operating_margin is not None else metric.operating_margin
            metric.operating_cash_flow = operating_cash_flow if operating_cash_flow is not None else metric.operating_cash_flow
            metric.free_cash_flow = free_cash_flow if free_cash_flow is not None else metric.free_cash_flow
            metric.debt_ratio = debt_ratio if debt_ratio is not None else metric.debt_ratio
            metric.debt_to_equity = debt_to_equity if debt_to_equity is not None else metric.debt_to_equity
            metric.eps = eps if eps is not None else metric.eps
            metric.roe = roe if roe is not None else metric.roe
            metric.roa = roa if roa is not None else metric.roa
            metric.gross_margin = gross_margin if gross_margin is not None else metric.gross_margin
            metric.current_ratio = current_ratio if current_ratio is not None else metric.current_ratio
            metric.source = source
            metric.updated_at = datetime.utcnow()
        else:
            metric = StructuredMetric(
                company_id=company.id,
                ticker=company.ticker,
                period_type=period_type,
                fiscal_period=fiscal_period,
                period_end_date=period_end_date,
                revenue=revenue,
                ebitda=ebitda,
                ebit=ebit,
                net_profit=net_profit,
                operating_margin=operating_margin,
                operating_cash_flow=operating_cash_flow,
                free_cash_flow=free_cash_flow,
                debt_ratio=debt_ratio,
                debt_to_equity=debt_to_equity,
                eps=eps,
                roe=roe,
                roa=roa,
                gross_margin=gross_margin,
                current_ratio=current_ratio,
                source=source,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(metric)

        db.flush()
        MetricsEngine.update_company_history_status(db, company)
        db.commit()
        db.refresh(metric)
        return metric

    @staticmethod
    def update_company_history_status(db: Session, company: Company):
        """
        Validates FR-001 (minimum 5 years of historical data) and updates company status.
        """
        # Count distinct annual fiscal years
        annual_metrics = db.query(StructuredMetric).filter(
            StructuredMetric.company_id == company.id,
            StructuredMetric.period_type == "ANNUAL"
        ).order_by(StructuredMetric.period_end_date.desc()).all()

        distinct_years = set([m.period_end_date.year for m in annual_metrics])
        years_count = len(distinct_years)
        company.years_of_data_available = years_count
        company.has_five_year_history = (years_count >= 5)

        if annual_metrics:
            latest = annual_metrics[0]
            company.latest_fiscal_year = latest.period_end_date.year
            company.latest_fiscal_period = latest.fiscal_period

        company.updated_at = datetime.utcnow()

    @staticmethod
    def get_metrics_timeline(db: Session, ticker: str, period_type: str = "ANNUAL") -> List[Dict[str, Any]]:
        """
        Retrieves chronological timeline of structured metrics for frontend charts and tables.
        """
        records = db.query(StructuredMetric).filter(
            StructuredMetric.ticker == ticker.upper(),
            StructuredMetric.period_type == period_type
        ).order_by(StructuredMetric.period_end_date.asc()).all()

        result = []
        for r in records:
            result.append({
                "id": r.id,
                "fiscal_period": r.fiscal_period,
                "period_end_date": str(r.period_end_date),
                "year": r.period_end_date.year,
                # All 10 FR-003 Metrics:
                "revenue": r.revenue,
                "ebitda": r.ebitda,
                "ebit": r.ebit,
                "net_profit": r.net_profit,
                "operating_margin": r.operating_margin,
                "operating_cash_flow": r.operating_cash_flow,
                "free_cash_flow": r.free_cash_flow,
                "debt_ratio": r.debt_ratio,
                "debt_to_equity": r.debt_to_equity,
                "eps": r.eps,
                "roe": r.roe,
                "roa": r.roa,
                # Auxiliary
                "gross_margin": r.gross_margin,
                "current_ratio": r.current_ratio,
                "source": r.source,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None
            })
        return result
