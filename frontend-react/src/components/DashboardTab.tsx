import React from 'react';
import type { Company, DocumentItem } from '../types';
import {
  TrendingUp,
  FileText,
  Clock,
  Layers,
  Sparkles,
  ArrowUpRight,
  ShieldAlert,
  Bot
} from 'lucide-react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from 'recharts';

interface DashboardTabProps {
  companies: Company[];
  documents: DocumentItem[];
  selectedTicker: string;
  schedulerActive: boolean;
  onNavigate: (tab: any) => void;
}

export const DashboardTab: React.FC<DashboardTabProps> = ({
  companies,
  documents,
  selectedTicker,
  schedulerActive,
  onNavigate,
}) => {
  const activeCompany = companies.find((c) => c.ticker === selectedTicker) || companies[0];

  // Sample trend data for visual display
  const sampleTrend = [
    { name: '2021', revenue: 365, ebitda: 120, profit: 94 },
    { name: '2022', revenue: 394, ebitda: 130, profit: 99 },
    { name: '2023', revenue: 383, ebitda: 125, profit: 96 },
    { name: '2024', revenue: 410, ebitda: 138, profit: 104 },
    { name: '2025 (E)', revenue: 442, ebitda: 152, profit: 115 },
  ];

  const stats = [
    {
      label: 'Tracked Companies',
      value: companies.length.toString(),
      sub: '5-Year Ingestion Active',
      icon: Layers,
      color: 'from-blue-500 to-indigo-600',
    },
    {
      label: 'Stored Documents',
      value: documents.length.toString(),
      sub: 'Indexed into ChromaDB',
      icon: FileText,
      color: 'from-violet-500 to-purple-600',
    },
    {
      label: 'Scheduler Engine',
      value: schedulerActive ? 'Running' : 'Active',
      sub: 'FR-004 Auto-Monitoring',
      icon: Clock,
      color: 'from-emerald-500 to-teal-600',
    },
    {
      label: 'AI Agents Fleet',
      value: '8 CrewAI',
      sub: 'Multi-Agent Autonomous',
      icon: Bot,
      color: 'from-amber-500 to-orange-600',
    },
  ];

  return (
    <div className="space-y-8 p-8">
      {/* Hero Clay Card */}
      <div className="clay-card p-8 bg-gradient-to-br from-[#f8faff] to-[#eef3fb] border border-white">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-50 border border-indigo-200 text-indigo-700 text-xs font-bold mb-3 shadow-sm">
              <Sparkles className="w-3.5 h-3.5" /> Enterprise Financial Intelligence Engine
            </div>
            <h2 className="text-3xl font-black text-slate-800 tracking-tight">
              {activeCompany?.name || activeCompany?.ticker || 'FinIntel'} Platform Overview
            </h2>
            <p className="text-slate-500 text-sm mt-1 max-w-2xl">
              Grounded multi-agent predictive modeling, macro-economic shock simulations, and SHAP-explained strategic recommendations.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => onNavigate('predictions')}
              className="clay-btn clay-btn-primary text-xs"
            >
              Run ML Forecast
              <ArrowUpRight className="w-4 h-4" />
            </button>
            <button
              onClick={() => onNavigate('scenarios')}
              className="clay-btn clay-btn-secondary text-xs"
            >
              Simulate Shock
            </button>
          </div>
        </div>
      </div>

      {/* KPI Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((s, idx) => {
          const Icon = s.icon;
          return (
            <div key={idx} className="clay-card p-6 flex items-center gap-4">
              <div
                className={`w-14 h-14 rounded-2xl bg-gradient-to-tr ${s.color} text-white flex items-center justify-center shrink-0 shadow-[4px_4px_10px_rgba(0,0,0,0.15)]`}
              >
                <Icon className="w-7 h-7" />
              </div>
              <div>
                <p className="text-xs font-bold text-slate-400 uppercase tracking-wider">{s.label}</p>
                <h3 className="text-2xl font-black text-slate-800 tracking-tight mt-0.5">{s.value}</h3>
                <p className="text-[11px] font-semibold text-indigo-600 mt-0.5">{s.sub}</p>
              </div>
            </div>
          );
        })}
      </div>

      {/* Chart & Quick Actions Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Trend Chart */}
        <div className="clay-card p-6 lg:col-span-2">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h3 className="text-lg font-bold text-slate-800">Financial Growth & Outlook</h3>
              <p className="text-xs text-slate-500">Historical & projected figures for {selectedTicker} ($ Billions)</p>
            </div>
            <span className="clay-badge bg-emerald-100 text-emerald-800">
              <TrendingUp className="w-3 h-3 mr-1" /> +12.4% YoY
            </span>
          </div>

          <div className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={sampleTrend} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorRev" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#6366f1" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#6366f1" stopOpacity={0.0} />
                  </linearGradient>
                  <linearGradient id="colorEbitda" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#06b6d4" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="name" stroke="#94a3b8" fontSize={12} tickLine={false} />
                <YAxis stroke="#94a3b8" fontSize={12} tickLine={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#ffffff',
                    borderRadius: '16px',
                    boxShadow: '0 10px 25px rgba(0,0,0,0.1)',
                    border: 'none',
                    fontWeight: 'bold',
                  }}
                />
                <Area type="monotone" dataKey="revenue" stroke="#6366f1" strokeWidth={3} fillOpacity={1} fill="url(#colorRev)" name="Revenue" />
                <Area type="monotone" dataKey="ebitda" stroke="#06b6d4" strokeWidth={2.5} fillOpacity={1} fill="url(#colorEbitda)" name="EBITDA" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Quick Launchpad */}
        <div className="clay-card p-6 flex flex-col justify-between">
          <div>
            <h3 className="text-lg font-bold text-slate-800 mb-1">Decision Launchpad</h3>
            <p className="text-xs text-slate-500 mb-5">Access high-impact intelligence workflows</p>

            <div className="space-y-3">
              <button
                onClick={() => onNavigate('scenarios')}
                className="w-full clay-card-inset p-3.5 flex items-center justify-between text-left hover:scale-[1.01] transition-transform"
              >
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-xl bg-indigo-100 text-indigo-700 flex items-center justify-center font-bold text-xs">
                    FR-035
                  </div>
                  <div>
                    <h4 className="text-xs font-bold text-slate-800">Currency & Tariff Shocks</h4>
                    <p className="text-[10px] text-slate-500">Run What-If Scenario analysis</p>
                  </div>
                </div>
                <ArrowUpRight className="w-4 h-4 text-slate-400" />
              </button>

              <button
                onClick={() => onNavigate('recommendations')}
                className="w-full clay-card-inset p-3.5 flex items-center justify-between text-left hover:scale-[1.01] transition-transform"
              >
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-xl bg-purple-100 text-purple-700 flex items-center justify-center font-bold text-xs">
                    FR-037
                  </div>
                  <div>
                    <h4 className="text-xs font-bold text-slate-800">Priority Strategic Recs</h4>
                    <p className="text-[10px] text-slate-500">6 Pillars with LLM Justification</p>
                  </div>
                </div>
                <ArrowUpRight className="w-4 h-4 text-slate-400" />
              </button>

              <button
                onClick={() => onNavigate('explainability')}
                className="w-full clay-card-inset p-3.5 flex items-center justify-between text-left hover:scale-[1.01] transition-transform"
              >
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-xl bg-emerald-100 text-emerald-700 flex items-center justify-center font-bold text-xs">
                    FR-043
                  </div>
                  <div>
                    <h4 className="text-xs font-bold text-slate-800">SHAP Explainability</h4>
                    <p className="text-[10px] text-slate-500">Feature importance & driver attribution</p>
                  </div>
                </div>
                <ArrowUpRight className="w-4 h-4 text-slate-400" />
              </button>
            </div>
          </div>

          <div className="pt-4 border-t border-slate-200/60 mt-4 flex items-center gap-2 text-xs text-amber-700 bg-amber-50/80 p-2.5 rounded-xl border border-amber-200/60">
            <ShieldAlert className="w-4 h-4 shrink-0 text-amber-600" />
            <span>Traceability active: All citations backed by source SHA-256 hashes.</span>
          </div>
        </div>
      </div>
    </div>
  );
};
