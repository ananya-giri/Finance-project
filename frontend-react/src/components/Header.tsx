import React from 'react';
import type { TabId } from '../types';
import { Search, Sparkles } from 'lucide-react';

interface HeaderProps {
  currentTab: TabId;
  selectedTicker: string;
  onTickerChange: (ticker: string) => void;
  availableTickers: string[];
  onQuickIngest: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  currentTab,
  selectedTicker,
  onTickerChange,
  availableTickers,
  onQuickIngest,
}) => {
  const titles: Record<TabId, { title: string; subtitle: string }> = {
    dashboard: { title: 'Executive Dashboard', subtitle: 'Real-time financial indicators and agent orchestration summary' },
    ingest: { title: 'Historical Ingestion (FR-001)', subtitle: 'Ingest 5-year OHLCV and volume market data via Yahoo Finance' },
    documents: { title: 'Document Upload & Parsing (FR-002)', subtitle: 'Multi-modal document store with SHA-256 integrity and chunking' },
    metrics: { title: 'Financial Metrics (FR-003)', subtitle: 'Quarterly and annual financial statement metrics and trends' },
    scheduler: { title: 'Automated Monitoring (FR-004)', subtitle: 'APScheduler automated ingestion and periodic retraining jobs' },
    'market-intelligence': { title: 'Market Intelligence (FR-005–009)', subtitle: 'Macro-economic indicators, geopolitical sentiment, and risk heatmaps' },
    rag: { title: 'Knowledge Base & RAG (FR-010–014)', subtitle: 'Vector retrieval with ChromaDB and evidence-backed generative Q&A' },
    orchestration: { title: 'Multi-Agent Hub (FR-015–023)', subtitle: 'CrewAI multi-agent cooperative workflows and autonomous tasks' },
    predictions: { title: 'Predictive Analytics (FR-028–033)', subtitle: 'Multi-horizon forecasts: Prophet, ARIMA, XGBoost & Linear Regression' },
    scenarios: { title: 'Scenario Analysis (FR-034–036)', subtitle: 'Macro shock simulation (Tariffs, Currency, Rates, Supply Chain, Downturn)' },
    recommendations: { title: 'Strategic Recommendations (FR-037–040)', subtitle: 'AI strategic guidance prioritized across 6 pillars with LLM rationale' },
    explainability: { title: 'Explainable AI & SHAP (FR-041–044)', subtitle: 'SHAP feature attribution, key driver ranking, and source document traceability' },
  };

  const current = titles[currentTab] || { title: 'FinIntel', subtitle: 'Financial Intelligence' };

  return (
    <header className="px-8 py-5 border-b border-white/60 bg-[#eef2f7]/80 backdrop-blur-md sticky top-0 z-20 flex items-center justify-between">
      <div>
        <h1 className="text-2xl font-black text-slate-800 tracking-tight">{current.title}</h1>
        <p className="text-xs font-medium text-slate-500 mt-0.5">{current.subtitle}</p>
      </div>

      <div className="flex items-center gap-4">
        {/* Ticker Selector */}
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold text-slate-500 uppercase">Active Ticker:</span>
          <select
            value={selectedTicker}
            onChange={(e) => onTickerChange(e.target.value)}
            className="clay-input py-1.5 px-3 font-bold text-indigo-700 text-sm cursor-pointer"
          >
            {availableTickers.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </div>

        {/* Global Search */}
        <div className="relative">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search company or metric..."
            className="clay-input pl-9 pr-4 py-1.5 text-xs w-48 focus:w-60 transition-all"
          />
        </div>

        {/* Quick Ingest Button */}
        <button
          onClick={onQuickIngest}
          className="clay-btn clay-btn-primary py-2 px-4 text-xs font-bold"
        >
          <Sparkles className="w-3.5 h-3.5" />
          Quick Ingest
        </button>
      </div>
    </header>
  );
};
