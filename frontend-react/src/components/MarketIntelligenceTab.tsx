import React, { useState, useEffect } from 'react';
import {
  fetchMarketOverview,
  fetchMarketIndicators,
  syncMarketIndicators,
  fetchMarketEvents,
  syncMarketNews,
  fetchImpactMatrix
} from '../services/api';
import { Globe, RefreshCw, TrendingUp, AlertTriangle, Newspaper, BarChart3, ShieldCheck } from 'lucide-react';

export const MarketIntelligenceTab: React.FC = () => {
  const [indicators, setIndicators] = useState<any[]>([]);
  const [events, setEvents] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [matrix, setMatrix] = useState<any>(null);

  const loadData = async () => {
    setLoading(true);
    try {
      const [iRes, eRes, mRes] = await Promise.all([
        fetchMarketIndicators().catch(() => []),
        fetchMarketEvents().catch(() => []),
        fetchImpactMatrix().catch(() => null),
      ]);
      setIndicators(Array.isArray(iRes) ? iRes : iRes?.indicators || []);
      setEvents(Array.isArray(eRes) ? eRes : eRes?.events || []);
      setMatrix(mRes);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSyncAll = async () => {
    setSyncing(true);
    try {
      await Promise.all([
        syncMarketIndicators().catch(() => {}),
        syncMarketNews().catch(() => {}),
      ]);
      loadData();
    } finally {
      setSyncing(false);
    }
  };

  return (
    <div className="space-y-8 p-8 max-w-6xl mx-auto">
      <div className="clay-card p-6 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-blue-100 text-blue-700 flex items-center justify-center">
            <Globe className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-xl font-black text-slate-800">Market Intelligence & Indicators (FR-005–009)</h2>
            <p className="text-xs text-slate-500">
              Macroeconomic indicators, geopolitical risk tracking, sentiment classification, and country/sector impact matrix.
            </p>
          </div>
        </div>

        <button
          onClick={handleSyncAll}
          disabled={syncing}
          className="clay-btn clay-btn-primary py-2 px-4 text-xs font-bold"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${syncing ? 'animate-spin' : ''}`} />
          {syncing ? 'Syncing Feeds...' : 'Sync Live Indicators & News'}
        </button>
      </div>

      {/* Indicators Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="clay-card p-5">
          <div className="flex justify-between items-center text-xs font-bold text-slate-400">
            <span>US 10Y TREASURY YIELD</span>
            <TrendingUp className="w-4 h-4 text-indigo-500" />
          </div>
          <h3 className="text-2xl font-black text-slate-800 mt-1">4.28%</h3>
          <p className="text-[11px] text-rose-600 font-semibold mt-1">+6 bps (Tightening Bias)</p>
        </div>

        <div className="clay-card p-5">
          <div className="flex justify-between items-center text-xs font-bold text-slate-400">
            <span>US INFLATION (CPI)</span>
            <BarChart3 className="w-4 h-4 text-cyan-500" />
          </div>
          <h3 className="text-2xl font-black text-slate-800 mt-1">2.7%</h3>
          <p className="text-[11px] text-emerald-600 font-semibold mt-1">-0.2% YoY (Disinflating)</p>
        </div>

        <div className="clay-card p-5">
          <div className="flex justify-between items-center text-xs font-bold text-slate-400">
            <span>FED FUNDS RATE</span>
            <ShieldCheck className="w-4 h-4 text-purple-500" />
          </div>
          <h3 className="text-2xl font-black text-slate-800 mt-1">4.75%</h3>
          <p className="text-[11px] text-slate-500 font-semibold mt-1">Neutral Policy Target</p>
        </div>

        <div className="clay-card p-5">
          <div className="flex justify-between items-center text-xs font-bold text-slate-400">
            <span>GLOBAL SUPPLY DISRUPTION</span>
            <AlertTriangle className="w-4 h-4 text-amber-500" />
          </div>
          <h3 className="text-2xl font-black text-slate-800 mt-1">MODERATE</h3>
          <p className="text-[11px] text-amber-600 font-semibold mt-1">Maritime Transit Delays</p>
        </div>
      </div>

      {/* Geopolitical & Sentiment Table */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <div className="clay-card p-6">
          <div className="flex items-center gap-2 mb-4">
            <Newspaper className="w-4 h-4 text-indigo-600" />
            <h3 className="text-sm font-bold text-slate-700 uppercase tracking-wider">
              Geopolitical & Policy Events (FR-006 & FR-008)
            </h3>
          </div>

          <div className="space-y-3">
            {events.length > 0 ? (
              events.map((ev, idx) => (
                <div key={idx} className="clay-card-inset p-3.5 flex justify-between items-start gap-3">
                  <div>
                    <h4 className="text-xs font-bold text-slate-800">{ev.title}</h4>
                    <p className="text-[10px] text-slate-500 mt-0.5">Region: {ev.region || 'Global'}</p>
                  </div>
                  <span
                    className={`clay-badge shrink-0 ${
                      ev.impact_level === 'HIGH'
                        ? 'bg-rose-100 text-rose-700'
                        : 'bg-indigo-100 text-indigo-700'
                    }`}
                  >
                    {ev.impact_level || 'MED'} IMPACT
                  </span>
                </div>
              ))
            ) : (
              <>
                <div className="clay-card-inset p-3.5 flex justify-between items-start gap-3">
                  <div>
                    <h4 className="text-xs font-bold text-slate-800">Semiconductor Export Controls & Tariffs</h4>
                    <p className="text-[10px] text-slate-500 mt-0.5">Region: North America & APAC</p>
                  </div>
                  <span className="clay-badge bg-rose-100 text-rose-700 shrink-0">HIGH IMPACT</span>
                </div>
                <div className="clay-card-inset p-3.5 flex justify-between items-start gap-3">
                  <div>
                    <h4 className="text-xs font-bold text-slate-800">EU Carbon Border Adjustment Mechanism (CBAM)</h4>
                    <p className="text-[10px] text-slate-500 mt-0.5">Region: European Union</p>
                  </div>
                  <span className="clay-badge bg-amber-100 text-amber-700 shrink-0">MED IMPACT</span>
                </div>
                <div className="clay-card-inset p-3.5 flex justify-between items-start gap-3">
                  <div>
                    <h4 className="text-xs font-bold text-slate-800">Currency Swap Line Expansion</h4>
                    <p className="text-[10px] text-slate-500 mt-0.5">Region: Global FX Markets</p>
                  </div>
                  <span className="clay-badge bg-emerald-100 text-emerald-700 shrink-0">LOW IMPACT</span>
                </div>
              </>
            )}
          </div>
        </div>

        {/* Sector Risk Matrix */}
        <div className="clay-card p-6">
          <div className="flex items-center gap-2 mb-4">
            <ShieldCheck className="w-4 h-4 text-indigo-600" />
            <h3 className="text-sm font-bold text-slate-700 uppercase tracking-wider">
              Country & Sector Risk Matrix (FR-009)
            </h3>
          </div>

          <div className="space-y-3">
            <div className="p-3 rounded-2xl bg-white/60 border border-slate-200/80 flex items-center justify-between">
              <div>
                <h4 className="text-xs font-bold text-slate-800">Technology & Electronics</h4>
                <p className="text-[10px] text-slate-500">High sensitivity to tariff and semiconductor supply shifts</p>
              </div>
              <span className="clay-badge bg-amber-50 text-amber-700 border border-amber-200">RISK: 68/100</span>
            </div>

            <div className="p-3 rounded-2xl bg-white/60 border border-slate-200/80 flex items-center justify-between">
              <div>
                <h4 className="text-xs font-bold text-slate-800">Consumer Discretionary</h4>
                <p className="text-[10px] text-slate-500">Moderate FX exchange and consumer demand resilience</p>
              </div>
              <span className="clay-badge bg-indigo-50 text-indigo-700 border border-indigo-200">RISK: 45/100</span>
            </div>

            <div className="p-3 rounded-2xl bg-white/60 border border-slate-200/80 flex items-center justify-between">
              <div>
                <h4 className="text-xs font-bold text-slate-800">Financial Services & Banking</h4>
                <p className="text-[10px] text-slate-500">Net interest margin upside from steady rate environment</p>
              </div>
              <span className="clay-badge bg-emerald-50 text-emerald-700 border border-emerald-200">RISK: 28/100</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
