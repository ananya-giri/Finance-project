from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Text, DateTime
from backend.app.database import Base

class EconomicIndicator(Base):
    """
    FR-005 & FR-006: External Economic Indicators
    Collects Exchange Rates, Inflation Rates, Interest Rates, Commodity Prices,
    Stock Market Indices, and Industry Growth Rates.
    """
    __tablename__ = "economic_indicators"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(50), nullable=False, index=True)
    # EXCHANGE_RATE, INFLATION_RATE, INTEREST_RATE, COMMODITY_PRICE, STOCK_INDEX, INDUSTRY_GROWTH

    name = Column(String(120), nullable=False)
    symbol = Column(String(50), nullable=False, unique=True, index=True)
    current_value = Column(Float, nullable=False)
    previous_value = Column(Float, nullable=True)
    unit = Column(String(30), nullable=False, default="")
    change_24h = Column(Float, nullable=True, default=0.0)
    change_pct_24h = Column(Float, nullable=True, default=0.0)
    frequency = Column(String(30), nullable=False, default="DAILY") # REALTIME, DAILY, MONTHLY, ANNUAL
    source = Column(String(120), nullable=False, default="Market Feed")
    historical_sparkline = Column(Text, nullable=True) # JSON array of recent values
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)


class MarketIntelligenceEvent(Base):
    """
    FR-007, FR-008, FR-009: Geopolitical & Regulatory Events, News, and Impact Classification
    Categorized into Financial, Regulatory, Political, Environmental, Supply Chain, Competitive.
    """
    __tablename__ = "market_intelligence_events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(300), nullable=False)
    summary = Column(Text, nullable=False)
    
    # FR-007 & FR-008 Event Types:
    # TARIFF_CHANGE, TRADE_RESTRICTION, SANCTION, IMPORT_EXPORT_CURB,
    # TAX_POLICY, GOVERNMENT_REGULATION, NEWS_ARTICLE, MARKET_REPORT, GEOPOLITICAL_EVENT
    event_type = Column(String(60), nullable=False, index=True)

    # FR-009 Impact Categories:
    # FINANCIAL, REGULATORY, POLITICAL, ENVIRONMENTAL, SUPPLY_CHAIN, COMPETITIVE
    impact_category = Column(String(50), nullable=False, index=True)

    # Severity & Sentiment:
    severity = Column(String(20), nullable=False, default="MEDIUM") # LOW, MEDIUM, HIGH, CRITICAL
    sentiment = Column(String(20), nullable=False, default="NEUTRAL") # POSITIVE, NEUTRAL, NEGATIVE
    confidence_score = Column(Float, nullable=False, default=0.85)

    source = Column(String(120), nullable=False, default="Intelligence Network")
    source_url = Column(String(500), nullable=True)
    
    # JSON strings of affected tags
    affected_sectors = Column(Text, nullable=True, default="[]") # e.g. ["Technology", "Semiconductors"]
    affected_tickers = Column(Text, nullable=True, default="[]") # e.g. ["NVDA", "AAPL"]
    
    event_date = Column(DateTime, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
