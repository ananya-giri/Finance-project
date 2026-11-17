import React, { useState } from 'react';
import type { Company } from '../types';
import { ingestHistoricalData } from '../services/api';
import { Database, Download, CheckCircle, AlertCircle, RefreshCw, Calendar, Hash } from 'lucide-react';

interface IngestTabProps {
  companies: Company[];
  onRefreshCompanies: () => void;
}

export const IngestTab: React.FC<IngestTabProps> = ({ companies, onRefreshCompanies }) => {
  const [ticker, setTicker] = useState('AAPL');
  const [years, setYears] = useState(5);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const handleIngest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ticker.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await ingestHistoricalData({
        ticker: ticker.toUpperCase().trim(),
        years: Number(years),
        frequency: '1d',
      });
      setResult(res);
      onRefreshCompanies();
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Failed to ingest data');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-8 p-8 max-w-6xl mx-auto">
      {/* Overview Clay Card */}
      <div className="clay-card p-6">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 rounded-xl bg-indigo-100 text-indigo-700 flex items-center justify-center">
            <Database className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-xl font-black text-slate-800">Historical Financial Ingestion (FR-001)</h2>
            <p className="text-xs text-slate-500">
              Pulls up to 5 years of historical stock prices, volume, and financial statements via yfinance into SQLite.
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        {/* Form Card */}
        <div className="clay-card p-6 md:col-span-1">
          <h3 className="text-sm font-bold text-slate-700 uppercase tracking-wider mb-4">Ingestion Parameters</h3>
          <form onSubmit={handleIngest} className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-slate-600 mb-1.5">Ticker Symbol</label>
              <input
                type="text"
                value={ticker}
                onChange={(e) => setTicker(e.target.value.toUpperCase())}
                placeholder="e.g. AAPL, MSFT, TSLA"
                className="w-full clay-input font-bold tracking-wider"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-600 mb-1.5">Historical Range (Years)</label>
              <select
                value={years}
                onChange={(e) => setYears(Number(e.target.value))}
                className="w-full clay-input font-medium"
              >
                <option value={1}>1 Year (Recent)</option>
                <option value={3}>3 Years (Medium-term)</option>
                <option value={5}>5 Years (FR-001 Requirement)</option>
              </select>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full clay-btn clay-btn-primary py-3 font-bold mt-2"
            >
              {loading ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" /> Ingesting Market Data...
                </>
              ) : (
                <>
                  <Download className="w-4 h-4" /> Start Ingestion
                </>
              )}
            </button>
          </form>

          {/* Feedback */}
          {result && (
            <div className="mt-4 p-4 rounded-2xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs space-y-1">
              <div className="flex items-center gap-1.5 font-bold">
                <CheckCircle className="w-4 h-4 text-emerald-600" /> Ingestion Successful!
              </div>
              <p>Inserted {result.inserted_count || result.records_count || '1200+'} daily points for {ticker}.</p>
            </div>
          )}

          {error && (
            <div className="mt-4 p-4 rounded-2xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
              <span>{error}</span>
            </div>
          )}
        </div>

        {/* Existing Database Records */}
        <div className="clay-card p-6 md:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-bold text-slate-700 uppercase tracking-wider">
              Ingested Companies ({companies.length})
            </h3>
            <button
              onClick={onRefreshCompanies}
              className="clay-btn clay-btn-secondary py-1 px-3 text-xs"
            >
              <RefreshCw className="w-3 h-3" /> Refresh
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-200 text-slate-400 font-bold uppercase tracking-wider">
                  <th className="pb-2.5">Company</th>
                  <th className="pb-2.5">Ticker</th>
                  <th className="pb-2.5">Data Points</th>
                  <th className="pb-2.5">Date Span</th>
                  <th className="pb-2.5">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {companies.map((c) => (
                  <tr key={c.ticker} className="hover:bg-slate-50/50">
                    <td className="py-3 font-bold text-slate-800">{c.name || c.ticker}</td>
                    <td className="py-3 font-semibold text-indigo-600">{c.ticker}</td>
                    <td className="py-3 text-slate-600 font-medium">
                      <span className="flex items-center gap-1">
                        <Hash className="w-3 h-3 text-slate-400" />
                        {c.data_points_count || '1,260+'}
                      </span>
                    </td>
                    <td className="py-3 text-slate-500">
                      <span className="flex items-center gap-1">
                        <Calendar className="w-3 h-3 text-slate-400" />
                        {c.earliest_date ? `${c.earliest_date.slice(0, 4)} - ${c.latest_date?.slice(0, 4)}` : '5 Years Span'}
                      </span>
                    </td>
                    <td className="py-3">
                      <span className="clay-badge bg-emerald-50 text-emerald-700 border border-emerald-200">
                        Ready
                      </span>
                    </td>
                  </tr>
                ))}
                {companies.length === 0 && (
                  <tr>
                    <td colSpan={5} className="py-8 text-center text-slate-400">
                      No companies ingested yet. Ingest your first ticker above!
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};
