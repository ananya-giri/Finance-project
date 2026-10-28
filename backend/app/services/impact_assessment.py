
import json
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from backend.app.models.impact_assessment import ImpactAssessment

if TYPE_CHECKING:
    try:
        from sqlalchemy.orm import Session as SQLAlchemySession  # pyright: ignore[reportMissingImports]
    except ImportError:  # pragma: no cover - SQLAlchemy is optional at type-check time.
        SQLAlchemySession = Any
else:
    SQLAlchemySession = Any

Session = SQLAlchemySession

from backend.app.models.company import Company
from backend.app.models.market_intelligence import MarketIntelligenceEvent
from backend.app.models.structured_metrics import StructuredMetric


class ImpactAssessmentService:
    """
    FR-024: Connect external events to potentially affected companies
    and retrieve their latest available financial baselines.

    This service identifies potential relationships. It does not
    claim that an event caused a particular financial outcome.
    """

    # Potential financial channels by external event type.
    # These are initial rules and should be refined as the project grows.
    EVENT_METRIC_MAP = {
        "TARIFF_CHANGE": [
            "revenue", "ebitda", "profitability",
            "costs", "cash_flow", "market_share"
        ],
        "TRADE_RESTRICTION": [
            "revenue", "ebitda", "profitability",
            "costs", "cash_flow", "market_share"
        ],
        "SANCTION": [
            "revenue", "ebitda", "profitability",
            "costs", "cash_flow"
        ],
        "IMPORT_EXPORT_CURB": [
            "revenue", "ebitda", "profitability",
            "costs", "cash_flow", "market_share"
        ],
        "TAX_POLICY": [
            "ebitda", "profitability", "costs", "cash_flow"
        ],
        "GOVERNMENT_REGULATION": [
            "revenue", "ebitda", "profitability",
            "costs", "cash_flow"
        ],
        "NEWS_ARTICLE": [
            "revenue", "ebitda", "profitability",
            "costs", "cash_flow", "market_share"
        ],
        "MARKET_REPORT": [
            "revenue", "ebitda", "profitability",
            "costs", "cash_flow", "market_share"
        ],
        "GEOPOLITICAL_EVENT": [
            "revenue", "ebitda", "profitability",
            "costs", "cash_flow", "market_share"
        ],
    }

    @staticmethod
    def _parse_json_list(value: Optional[str]) -> List[str]:
        """Safely parse JSON strings stored in event tag fields."""

        if not value:
            return []

        # Also accept an already-parsed list for testing or reuse.
        if isinstance(value, list):
            return [
                str(item).strip()
                for item in value
                if item is not None and str(item).strip()
            ]

        try:
            parsed = json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return []

        if not isinstance(parsed, list):
            return []

        return [
            str(item).strip()
            for item in parsed
            if item is not None and str(item).strip()
        ]

    @staticmethod
    def _normalize(value: Optional[str]) -> str:
        """Normalize names for case-insensitive exact matching."""

        return " ".join((value or "").casefold().split())
    
    
    @classmethod
    def determine_financial_channels(
        cls,
        event: MarketIntelligenceEvent
    ) -> List[str]:
        """
        Return the financial metrics potentially affected by an event.
        The result is a hypothesis, not a measured financial impact.
        """

        return cls.EVENT_METRIC_MAP.get(
            (event.event_type or "").upper(),
            [
                "revenue",
                "ebitda",
                "profitability",
                "costs",
                "cash_flow",
                "market_share",
            ],
        )

    @staticmethod
    def get_financial_baseline(
        db: Session,
        company: Company
    ) -> Dict[str, Any]:
        """
        Fetch the latest available StructuredMetric row for a company.

        Costs and market share are explicitly marked unavailable because
        StructuredMetric does not currently store dedicated fields for them.
        """

        metric = (
            db.query(StructuredMetric)
            .filter(StructuredMetric.company_id == company.id)
            .order_by(
                StructuredMetric.period_end_date.desc(),
                StructuredMetric.id.desc(),
            )
            .first()
        )

        if metric is None:
            return {
                "available": False,
                "reason": "No structured financial metrics found for this company.",
                "currency": company.currency or "USD",
                "fiscal_period": None,
                "period_end_date": None,
                "revenue": None,
                "ebitda": None,
                "net_profit": None,
                "operating_margin": None,
                "operating_cash_flow": None,
                "free_cash_flow": None,
                "costs": None,
                "market_share": None,
                "unavailable_metrics": [
                    "revenue",
                    "ebitda",
                    "profitability",
                    "costs",
                    "cash_flow",
                    "market_share",
                ],
            }

        # Identify which metrics are unavailable in the latest record.
        unavailable = []

        if metric.revenue is None:
            unavailable.append("revenue")

        if metric.ebitda is None:
            unavailable.append("ebitda")

        if metric.net_profit is None and metric.operating_margin is None:
            unavailable.append("profitability")

        if (
            metric.operating_cash_flow is None
            and metric.free_cash_flow is None
        ):
            unavailable.append("cash_flow")

        # The current StructuredMetric model has no dedicated normalized
        # expense or market-share fields.
        unavailable.extend(["costs", "market_share"])

        return {
            "available": True,
            "currency": company.currency or "USD",
            "period_type": metric.period_type,
            "fiscal_period": metric.fiscal_period,
            "period_end_date": (
                metric.period_end_date.isoformat()
                if metric.period_end_date
                else None
            ),
            "revenue": metric.revenue,
            "ebitda": metric.ebitda,
            "net_profit": metric.net_profit,
            "operating_margin": metric.operating_margin,
            "operating_cash_flow": metric.operating_cash_flow,
            "free_cash_flow": metric.free_cash_flow,
            "costs": None,
            "market_share": None,
            "unavailable_metrics": unavailable,
        }

    @classmethod
    def match_event_to_companies(
        cls,
        db: Session,
        event_id: int,
    ) -> Dict[str, Any]:
        """
        FR-024:
        1. Retrieve an external event.
        2. Match affected tickers directly.
        3. Match affected sectors against company sector/industry.
        4. Retrieve financial baselines for matched companies.
        5. Return the evidence supporting each relationship.

        Raises ValueError if the requested event does not exist.
        """

        event = (
            db.query(MarketIntelligenceEvent)
            .filter(MarketIntelligenceEvent.id == event_id)
            .first()
        )

        if event is None:
            raise ValueError(f"External event with ID {event_id} was not found.")

        affected_tickers = {
            ticker.upper()
            for ticker in cls._parse_json_list(event.affected_tickers)
        }

        affected_sectors = {
            cls._normalize(sector)
            for sector in cls._parse_json_list(event.affected_sectors)
        }

        companies = (
            db.query(Company)
            .order_by(Company.ticker.asc())
            .all()
        )

        matches = []

        for company in companies:
            reasons = []

            company_ticker = (company.ticker or "").strip().upper()

            # Strongest available link: explicit ticker match.
            if company_ticker and company_ticker in affected_tickers:
                reasons.append("DIRECT_TICKER_MATCH")

            # Additional evidence: sector or industry matches an event tag.
            company_sector = cls._normalize(company.sector)
            company_industry = cls._normalize(company.industry)

            if (
                company_sector
                and company_sector in affected_sectors
            ):
                reasons.append("SECTOR_MATCH")

            if (
                company_industry
                and company_industry in affected_sectors
            ):
                reasons.append("INDUSTRY_MATCH")

            # No evidence means no company match.
            if not reasons:
                continue

            baseline = cls.get_financial_baseline(db, company)

            matches.append({
                "company_id": company.id,
                "ticker": company.ticker,
                "company_name": company.name,
                "sector": company.sector,
                "industry": company.industry,
                "match_reasons": reasons,
                "match_strength": (
                    "DIRECT_TICKER"
                    if "DIRECT_TICKER_MATCH" in reasons
                    else "SECTOR_OR_INDUSTRY"
                ),
                "baseline": baseline,
            })

        return {
            "requirement": "FR-024",
            "status": "SUCCESS" if matches else "NO_MATCHES",
            "event": {
                "id": event.id,
                "title": event.title,
                "event_type": event.event_type,
                "impact_category": event.impact_category,
                "severity": event.severity,
                "sentiment": event.sentiment,
                "classification_confidence": event.confidence_score,
                "affected_tickers": sorted(affected_tickers),
                "affected_sectors": sorted(affected_sectors),
                "event_date": (
                    event.event_date.isoformat()
                    if event.event_date
                    else None
                ),
            },
            "potential_financial_channels": (
                cls.determine_financial_channels(event)
            ),
            "matched_companies_count": len(matches),
            "matches": matches,
            "limitations": [
                "A ticker match or sector match indicates potential exposure, not causation.",
                "The latest available financial record is used as the baseline.",
                "Costs and market share are unavailable until dedicated data is added.",
                "Sector-level matches are less specific than direct ticker matches.",
            ],
        }

    # FR-026: Initial configurable sensitivity assumptions.
    # These are prototype assumptions and must be calibrated against
    # historical event outcomes before being used for real forecasts.

    BASE_IMPACT_PCT = {
        "REVENUE": 2.0,
        "EBITDA": 3.0,
        "PROFITABILITY": 3.0,
        "COSTS": 2.5,
        "CASH_FLOW": 3.0,
        "MARKET_SHARE": 1.0,
    }

    SEVERITY_MULTIPLIERS = {
        "LOW": 0.5,
        "MEDIUM": 1.0,
        "HIGH": 1.5,
        "CRITICAL": 2.0,
    }

    @classmethod
    def _get_metric_baseline(
        cls,
        baseline: Dict[str, Any],
        metric_name: str,
    ):
        """
        Returns:
            baseline_value, unit, source_field, unavailable_reason

        Operating margin is converted from a decimal fraction
        (e.g. 0.15) to percentage points (15.0).
        """

        currency = baseline.get("currency") or "USD"

        if metric_name == "REVENUE":
            value = baseline.get("revenue")
            return (
                value, currency, "revenue",
                None if value is not None else "Revenue baseline unavailable."
            )

        if metric_name == "EBITDA":
            value = baseline.get("ebitda")
            return (
                value, currency, "ebitda",
                None if value is not None else "EBITDA baseline unavailable."
            )

        if metric_name == "PROFITABILITY":
            # Prefer a monetary profit baseline.
            net_profit = baseline.get("net_profit")

            if net_profit is not None and abs(net_profit) > 0:
                return net_profit, currency, "net_profit", None

            # If net profit is unavailable or zero, use operating margin.
            margin = baseline.get("operating_margin")

            if margin is not None:
                return (
                    float(margin) * 100.0,
                    "percentage_points",
                    "operating_margin",
                    None,
                )

            return (
                None, None, None,
                "Neither net profit nor operating margin is available."
            )

        if metric_name == "COSTS":
            return (
                None, currency, None,
                "No dedicated normalized cost baseline is currently available."
            )

        if metric_name == "CASH_FLOW":
            operating_cf = baseline.get("operating_cash_flow")

            if operating_cf is not None and abs(operating_cf) > 0:
                return operating_cf, currency, "operating_cash_flow", None

            free_cf = baseline.get("free_cash_flow")

            if free_cf is not None:
                return free_cf, currency, "free_cash_flow", None

            return (
                None, currency, None,
                "Operating and free cash flow are unavailable."
            )

        if metric_name == "MARKET_SHARE":
            return (
                None, "percentage_points", None,
                "A comparable market-share baseline is required."
            )

        raise ValueError(f"Unsupported metric: {metric_name}")

    @staticmethod
    def _scenario_factors(financial_polarity: int) -> Dict[str, float]:
        """
        An optimistic scenario means a better company outcome.
        For an adverse event, that means a smaller loss.
        For a beneficial event, that means a larger gain.
        """

        if financial_polarity < 0:
            return {
                "OPTIMISTIC": 0.5,
                "BASE": 1.0,
                "PESSIMISTIC": 1.5,
            }

        return {
            "OPTIMISTIC": 1.5,
            "BASE": 1.0,
            "PESSIMISTIC": 0.5,
        }
    
    @classmethod
    def _calculate_impact_confidence(
        cls,
        db: Session,
        company_id: int,
        source_field: Optional[str],
        baseline_value: Optional[float],
        match_reasons: List[str],
        raw_classification_confidence: Any,
        estimate_available: bool,
        history_cache: Dict[Any, int],
    ) -> tuple[Optional[float], Dict[str, Any], str]:
        """
        FR-027: Calculate an explainable 0-100 impact confidence score.

        Historical evidence means historical financial metric coverage.
        It does not mean evidence from comparable past events.
        """

        # --------------------------------------------------------------
        # 1. Financial data completeness: 30%
        # --------------------------------------------------------------
        if baseline_value is None or not source_field:
            data_score = 0.0
            data_detail = (
                "Required metric baseline is unavailable."
            )
        elif source_field in {"operating_margin", "free_cash_flow"}:
            data_score = 80.0
            data_detail = (
                f"Baseline uses the available fallback field "
                f"{source_field}."
            )
        else:
            data_score = 100.0
            data_detail = (
                f"Required baseline field {source_field} is available."
            )

        # --------------------------------------------------------------
        # 2. Event-company match quality: 25%
        # --------------------------------------------------------------
        reasons = set(match_reasons or [])

        if "DIRECT_TICKER_MATCH" in reasons:
            match_score = 100.0
            match_detail = "Event explicitly identifies the company ticker."
        elif (
            "SECTOR_MATCH" in reasons
            and "INDUSTRY_MATCH" in reasons
        ):
            match_score = 70.0
            match_detail = "Both sector and industry match the event tags."
        elif "SECTOR_MATCH" in reasons:
            match_score = 60.0
            match_detail = "Match is based on sector only."
        elif "INDUSTRY_MATCH" in reasons:
            match_score = 55.0
            match_detail = "Match is based on industry only."
        else:
            match_score = 0.0
            match_detail = "No recognized company-event match evidence."

        # --------------------------------------------------------------
        # 3. Historical financial evidence: 25%
        # --------------------------------------------------------------
        # Cache counts because all three scenarios reuse the same baseline.
        periods_with_metric = 0

        if source_field and hasattr(StructuredMetric, source_field):
            cache_key = (company_id, source_field)

            if cache_key not in history_cache:
                metric_column = getattr(StructuredMetric, source_field)

                history_cache[cache_key] = (
                    db.query(StructuredMetric.period_end_date)
                    .filter(
                        StructuredMetric.company_id == company_id,
                        metric_column.isnot(None),
                    )
                    .distinct()
                    .count()
                )

            periods_with_metric = history_cache[cache_key]

        # The latest available period is the baseline, not prior evidence.
        prior_periods = max(periods_with_metric - 1, 0)

        # Four or more prior periods receive the maximum coverage score.
        historical_score = min(prior_periods / 4.0, 1.0) * 100.0

        historical_detail = (
            f"{prior_periods} prior distinct financial periods contain "
            f"this metric; {periods_with_metric} periods are available "
            f"including the baseline."
        )

        # --------------------------------------------------------------
        # 4. Existing event-classification confidence: 20%
        # --------------------------------------------------------------
        try:
            classification_score = float(
                raw_classification_confidence
            )
        except (TypeError, ValueError):
            classification_score = 0.0

        # Existing classifier scores may be represented as 0-1 or 0-100.
        if 0.0 <= classification_score <= 1.0:
            classification_score *= 100.0

        classification_score = max(
            0.0, min(classification_score, 100.0)
        )

        # --------------------------------------------------------------
        # 5. Weighted score
        # --------------------------------------------------------------
        weights = {
            "data_completeness": 0.30,
            "match_quality": 0.25,
            "historical_evidence": 0.25,
            "classification_confidence": 0.20,
        }

        weighted_score = round(
            data_score * weights["data_completeness"]
            + match_score * weights["match_quality"]
            + historical_score * weights["historical_evidence"]
            + classification_score * weights["classification_confidence"],
            2,
        )

        # A score is only reported when a numerical impact was estimated.
        if baseline_value is None or data_score == 0.0:
            confidence_score = None
            confidence_level = "INSUFFICIENT_DATA"
        elif not estimate_available:
            confidence_score = None
            confidence_level = "NOT_ESTIMATED"
        else:
            confidence_score = weighted_score

            if confidence_score >= 80:
                confidence_level = "HIGH"
            elif confidence_score >= 60:
                confidence_level = "MODERATE"
            else:
                confidence_level = "LOW"

        factors = {
            "method": "WEIGHTED_HEURISTIC_V1",
            "score_scale": "0-100",
            "weights": weights,
            "components": {
                "data_completeness": {
                    "score": round(data_score, 2),
                    "weight": weights["data_completeness"],
                    "detail": data_detail,
                },
                "match_quality": {
                    "score": round(match_score, 2),
                    "weight": weights["match_quality"],
                    "detail": match_detail,
                    "match_reasons": sorted(reasons),
                },
                "historical_evidence": {
                    "score": round(historical_score, 2),
                    "weight": weights["historical_evidence"],
                    "prior_periods": prior_periods,
                    "periods_including_baseline": periods_with_metric,
                    "detail": historical_detail,
                    "limitation": (
                        "Measures financial history coverage only. "
                        "Comparable historical event outcomes are not "
                        "currently available to validate event impact."
                    ),
                },
                "classification_confidence": {
                    "score": round(classification_score, 2),
                    "weight": weights["classification_confidence"],
                    "original_value": raw_classification_confidence,
                    "detail": (
                        "Confidence in event classification, not the "
                        "probability that the financial forecast is correct."
                    ),
                },
            },
            "weighted_score": (
                weighted_score if estimate_available else None
            ),
            "confidence_level": confidence_level,
            "interpretation": (
                "Heuristic evidence score; not a calibrated probability "
                "or a statistically validated forecast."
            ),
        }

        return confidence_score, factors, confidence_level


    @classmethod
    def calculate_and_save_event_impacts(
        cls,
        db: Session,
        event_id: int,
        ticker: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        FR-026: Calculate and save scenario-based financial impacts
        for companies matched to an external event.

        Uses financial baselines from StructuredMetric.
        Missing cost and market-share inputs are recorded as unavailable,
        never silently replaced with zero.
        """

        match_result = cls.match_event_to_companies(db, event_id)

        matches = match_result.get("matches", [])

        if ticker:
            requested_ticker = ticker.strip().upper()
            matches = [
                match for match in matches
                if (match.get("ticker") or "").upper() == requested_ticker
            ]

        if not matches:
            return {
                "status": "NO_MATCHES",
                "event_id": event_id,
                "message": (
                    f"No tracked company matched event {event_id}"
                    + (f" for ticker {ticker.upper()}" if ticker else "")
                    + "."
                ),
                "companies_assessed": 0,
                "assessment_records_created": 0,
                "assessments": [],
            }

        event_data = match_result["event"]
        sentiment = (event_data.get("sentiment") or "NEUTRAL").upper()
        severity = (event_data.get("severity") or "MEDIUM").upper()

        # Sentiment provides an initial directional assumption.
        # NEUTRAL sentiment does not support a signed numerical estimate.
        financial_polarity = {
            "POSITIVE": 1,
            "NEGATIVE": -1,
        }.get(sentiment)

        severity_factor = cls.SEVERITY_MULTIPLIERS.get(severity, 1.0)
        scenarios = cls._scenario_factors(
            financial_polarity if financial_polarity is not None else 1
        )

        metric_names = [
            "REVENUE",
            "EBITDA",
            "PROFITABILITY",
            "COSTS",
            "CASH_FLOW",
            "MARKET_SHARE",
        ]

        created_rows = []
        history_cache = {}
        try:
            for match in matches:
                company_id = match["company_id"]
                baseline = match.get("baseline") or {}

                # Re-running the same event/company assessment replaces
                # its previous scenario rows instead of duplicating them.
                db.query(ImpactAssessment).filter(
                    ImpactAssessment.event_id == event_id,
                    ImpactAssessment.company_id == company_id,
                ).delete(synchronize_session=False)

                for metric_name in metric_names:
                    (
                        baseline_value,
                        unit,
                        source_field,
                        unavailable_reason,
                    ) = cls._get_metric_baseline(baseline, metric_name)

                    for scenario, scenario_factor in scenarios.items():
                        estimated_change = None
                        estimated_change_pct = None
                        projected_value = None
                        direction = "UNKNOWN"
                        rationale = unavailable_reason
                        data_quality = "INSUFFICIENT_DATA"

                        if (
                            unavailable_reason is None
                            and baseline_value is not None
                            and financial_polarity is not None
                        ):
                            # A zero monetary baseline cannot support a
                            # percentage-of-baseline calculation.
                            is_margin = source_field == "operating_margin"

                            if abs(baseline_value) > 0 or is_margin:
                                base_rate = cls.BASE_IMPACT_PCT[metric_name]
                                impact_rate_pct = min(
                                    base_rate
                                    * severity_factor
                                    * scenario_factor,
                                    20.0,
                                )

                                # Margin is represented in percentage points.
                                # A one-point floor allows an estimate at 0%.
                                impact_scale = (
                                    max(abs(baseline_value), 1.0)
                                    if is_margin
                                    else abs(baseline_value)
                                )

                                # For costs, an increase is adverse and
                                # a reduction is beneficial.
                                metric_sign = (
                                    -financial_polarity
                                    if metric_name == "COSTS"
                                    else financial_polarity
                                )

                                estimated_change = (
                                    metric_sign
                                    * impact_scale
                                    * impact_rate_pct
                                    / 100.0
                                )

                                projected_value = (
                                    baseline_value + estimated_change
                                )

                                if abs(baseline_value) > 0:
                                    estimated_change_pct = (
                                        estimated_change
                                        / abs(baseline_value)
                                        * 100.0
                                    )

                                # Direction describes the business effect,
                                # not just whether the raw metric increased.
                                business_effect = (
                                    -estimated_change
                                    if metric_name == "COSTS"
                                    else estimated_change
                                )

                                if business_effect > 0:
                                    direction = "POSITIVE"
                                elif business_effect < 0:
                                    direction = "NEGATIVE"
                                else:
                                    direction = "NEUTRAL"

                                data_quality = "COMPLETE"
                                rationale = (
                                    f"Rules-based sensitivity estimate using "
                                    f"{source_field} as the baseline; "
                                    f"event sentiment={sentiment}, "
                                    f"severity={severity}, "
                                    f"applied impact rate={impact_rate_pct:.2f}%. "
                                    f"This is a scenario estimate, not proof "
                                    f"of causal impact."
                                )

                            else:
                                rationale = (
                                    f"The {source_field} baseline is zero; "
                                    "a percentage-based estimate cannot be "
                                    "calculated reliably."
                                )

                        elif financial_polarity is None:
                            rationale = (
                                "Event sentiment is neutral or unknown. "
                                "A signed impact estimate requires an "
                                "explicit directional assumption."
                            )
                            data_quality = (
                                "PARTIAL"
                                if baseline_value is not None
                                else "INSUFFICIENT_DATA"
                            )

                        elif unavailable_reason is None:
                            rationale = "A usable financial baseline is unavailable."

                        (
                            confidence_score,
                            confidence_factors,
                            confidence_level,
                        ) = cls._calculate_impact_confidence(
                            db=db,
                            company_id=company_id,
                            source_field=source_field,
                            baseline_value=baseline_value,
                            match_reasons=match.get("match_reasons", []),
                            raw_classification_confidence=event_data.get(
                                "classification_confidence"
                            ),
                            estimate_available=(
                                estimated_change is not None
                            ),
                            history_cache=history_cache,
                        )

                        assumptions = {
                            "method": "RULE_BASED_SENSITIVITY_V1",
                            "event_id": event_id,
                            "metric": metric_name,
                            "event_sentiment": sentiment,
                            "event_severity": severity,
                            "scenario": scenario,
                            "scenario_factor": scenario_factor,
                            "severity_multiplier": severity_factor,
                            "base_impact_pct": cls.BASE_IMPACT_PCT[metric_name],
                            "baseline_source": source_field,
                            "baseline_period": baseline.get("fiscal_period"),
                            "directional_assumption": (
                                "Event sentiment is used as an initial proxy; "
                                "company-specific exposure may change the effect."
                            ),
                        }

                        row = ImpactAssessment(
                            event_id=event_id,
                            company_id=company_id,
                            metric_name=metric_name,
                            scenario=scenario,
                            baseline_value=(
                                round(float(baseline_value), 4)
                                if baseline_value is not None
                                else None
                            ),
                            estimated_change=(
                                round(estimated_change, 4)
                                if estimated_change is not None
                                else None
                            ),
                            estimated_change_pct=(
                                round(estimated_change_pct, 4)
                                if estimated_change_pct is not None
                                else None
                            ),
                            projected_value=(
                                round(projected_value, 4)
                                if projected_value is not None
                                else None
                            ),
                            unit=unit,
                            direction=direction,
                            confidence_score=confidence_score,
confidence_factors_json=json.dumps(confidence_factors),
                            assumptions_json=json.dumps(assumptions),
                            rationale=rationale,
                            data_quality=data_quality,
                            baseline_period=baseline.get("fiscal_period"),
                        )

                        db.add(row)
                        created_rows.append(row)

            db.commit()

        except Exception:
            db.rollback()
            raise

        calculated_count = sum(
            1 for row in created_rows
            if row.estimated_change is not None
        )

        return {
            "status": (
                "SUCCESS"
                if calculated_count == len(created_rows)
                else "PARTIAL_SUCCESS"
                if calculated_count > 0
                else "INSUFFICIENT_DATA"
            ),
            "requirement": "FR-026",
            "event_id": event_id,
            "event_title": event_data.get("title"),
            "event_sentiment": sentiment,
            "event_severity": severity,
            "companies_assessed": len(matches),
            "assessment_records_created": len(created_rows),
            "calculated_records": calculated_count,
            "unavailable_or_unestimated_records": (
                len(created_rows) - calculated_count
            ),
            "assumptions_note": (
                "Impact percentages are initial heuristic assumptions, "
                "not statistically calibrated forecasts. Confidence scores "
                "will be implemented separately for FR-027."
            ),
            "assessments": [
                {
                    "id": row.id,
                    "company_id": row.company_id,
                    "metric_name": row.metric_name,
                    "scenario": row.scenario,
                    "baseline_value": row.baseline_value,
                    "estimated_change": row.estimated_change,
                    "estimated_change_pct": row.estimated_change_pct,
                    "projected_value": row.projected_value,
                    "unit": row.unit,
                    "direction": row.direction,
                    "data_quality": row.data_quality,
                    
                    "confidence_score": row.confidence_score,
                    "confidence_level": (
                        json.loads(row.confidence_factors_json).get(
                            "confidence_level",
                            "INSUFFICIENT_DATA",
                        )
                        if row.confidence_factors_json
                        else "INSUFFICIENT_DATA"
                    ),
                    "confidence_factors": (
                        json.loads(row.confidence_factors_json)
                        if row.confidence_factors_json
                        else None
                    ),

                    "baseline_period": row.baseline_period,
                    "rationale": row.rationale,
                }
                for row in created_rows
            ],
        }
