import React from 'react';
import type { TabId } from '../types';
import {
  LayoutDashboard,
  Database,
  FileText,
  TrendingUp,
  Clock,
  Globe,
  BrainCircuit,
  Bot,
  LineChart,
  GitBranch,
  Lightbulb,
  HelpCircle,
  Activity
} from 'lucide-react';

interface SidebarProps {
  currentTab: TabId;
  onSelectTab: (tab: TabId) => void;
  apiHealthy: boolean;
}

interface NavItem {
  id: TabId;
  label: string;
  fr?: string;
  icon: React.ComponentType<{ className?: string }>;
}

interface NavSection {
  title: string;
  items: NavItem[];
}

export const Sidebar: React.FC<SidebarProps> = ({ currentTab, onSelectTab, apiHealthy }) => {
  const navSections: NavSection[] = [
    {
      title: 'Overview',
      items: [
        { id: 'dashboard' as TabId, label: 'Dashboard', icon: LayoutDashboard },
      ],
    },
    {
      title: 'Data Management',
      items: [
        { id: 'ingest' as TabId, label: 'Ingest Data', fr: 'FR-001', icon: Database },
        { id: 'documents' as TabId, label: 'Documents', fr: 'FR-002', icon: FileText },
      ],
    },
    {
      title: 'Analytics & Monitor',
      items: [
        { id: 'metrics' as TabId, label: 'Financial Metrics', fr: 'FR-003', icon: TrendingUp },
        { id: 'scheduler' as TabId, label: 'Auto-Monitoring', fr: 'FR-004', icon: Clock },
      ],
    },
    {
      title: 'Intelligence & RAG',
      items: [
        { id: 'market-intelligence' as TabId, label: 'Market Intel', fr: 'FR-005–009', icon: Globe },
        { id: 'rag' as TabId, label: 'Knowledge Base & RAG', fr: 'FR-010–014', icon: BrainCircuit },
      ],
    },
    {
      title: 'Multi-Agent',
      items: [
        { id: 'orchestration' as TabId, label: 'Multi-Agent Hub', fr: 'FR-015–023', icon: Bot },
      ],
    },
    {
      title: 'Predictive & Strategy',
      items: [
        { id: 'predictions' as TabId, label: 'ML Predictions', fr: 'FR-028–033', icon: LineChart },
        { id: 'scenarios' as TabId, label: 'Scenario Analysis', fr: 'FR-034–036', icon: GitBranch },
        { id: 'recommendations' as TabId, label: 'Recommendations', fr: 'FR-037–040', icon: Lightbulb },
        { id: 'explainability' as TabId, label: 'Explainable AI (SHAP)', fr: 'FR-041–044', icon: HelpCircle },
      ],
    },
  ];

  return (
    <aside className="w-72 bg-[#f0f4f9] border-r border-white/60 p-5 flex flex-col justify-between shrink-0 h-screen sticky top-0 overflow-y-auto">
      <div>
        {/* Brand */}
        <div className="flex items-center gap-3.5 px-3 py-2 mb-6">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-indigo-500 to-cyan-400 flex items-center justify-center text-white shadow-[4px_4px_10px_rgba(99,102,241,0.4),-3px_-3px_8px_rgba(255,255,255,0.9)]">
            <Activity className="w-6 h-6 stroke-[2.5]" />
          </div>
          <div>
            <h1 className="text-xl font-black text-slate-800 tracking-tight leading-tight">FinIntel</h1>
            <p className="text-xs font-semibold text-indigo-600 tracking-wide uppercase">Agentic AI Platform</p>
          </div>
        </div>

        {/* Navigation */}
        <nav className="space-y-4">
          {navSections.map((sec) => (
            <div key={sec.title}>
              <h2 className="text-[11px] font-bold text-slate-400 uppercase tracking-wider px-3 mb-1.5">
                {sec.title}
              </h2>
              <div>
                {sec.items.map((item) => {
                  const Icon = item.icon;
                  const isActive = currentTab === item.id;
                  return (
                    <button
                      key={item.id}
                      onClick={() => onSelectTab(item.id)}
                      className={`w-full clay-nav-item ${isActive ? 'active' : ''}`}
                    >
                      <Icon className={`w-4 h-4 shrink-0 ${isActive ? 'text-indigo-600' : 'text-slate-500'}`} />
                      <span className="flex-1 text-left truncate">{item.label}</span>
                      {item.fr && (
                        <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-full bg-indigo-100 text-indigo-700">
                          {item.fr}
                        </span>
                      )}
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>
      </div>

      {/* Footer Status */}
      <div className="pt-4 border-t border-slate-200/60 mt-4">
        <div className="clay-card-inset px-3.5 py-2.5 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span
              className={`w-2.5 h-2.5 rounded-full ${
                apiHealthy ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.8)]' : 'bg-rose-500'
              }`}
            />
            <span className="text-xs font-bold text-slate-700">
              {apiHealthy ? 'FastAPI Connected' : 'Connecting to API...'}
            </span>
          </div>
          <span className="text-[10px] font-semibold text-slate-400">v1.0.0</span>
        </div>
      </div>
    </aside>
  );
};
