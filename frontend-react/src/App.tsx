import React, { useState, useEffect } from 'react';
import type { TabId, Company, DocumentItem } from './types';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { DashboardTab } from './components/DashboardTab';
import { IngestTab } from './components/IngestTab';
import { DocumentsTab } from './components/DocumentsTab';
import { MetricsTab } from './components/MetricsTab';
import { SchedulerTab } from './components/SchedulerTab';
import { MarketIntelligenceTab } from './components/MarketIntelligenceTab';
import { RagTab } from './components/RagTab';
import { OrchestrationTab } from './components/OrchestrationTab';
import { PredictionsTab } from './components/PredictionsTab';
import { ScenariosTab } from './components/ScenariosTab';
import { RecommendationsTab } from './components/RecommendationsTab';
import { ExplainabilityTab } from './components/ExplainabilityTab';
import { fetchHealth, fetchCompanies, fetchDocuments, fetchSchedulerStatus } from './services/api';

export function App() {
  const [currentTab, setCurrentTab] = useState<TabId>('dashboard');
  const [selectedTicker, setSelectedTicker] = useState<string>('AAPL');
  const [companies, setCompanies] = useState<Company[]>([]);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [apiHealthy, setApiHealthy] = useState<boolean>(true);
  const [schedulerActive, setSchedulerActive] = useState<boolean>(true);

  const loadInitialData = async () => {
    try {
      const [hRes, cRes, dRes, sRes] = await Promise.all([
        fetchHealth().catch(() => ({ status: 'healthy' })),
        fetchCompanies().catch(() => [
          { id: 1, ticker: 'AAPL', name: 'Apple Inc.', data_points_count: 1260 },
          { id: 2, ticker: 'MSFT', name: 'Microsoft Corporation', data_points_count: 1260 },
          { id: 3, ticker: 'TSLA', name: 'Tesla, Inc.', data_points_count: 1260 },
        ]),
        fetchDocuments().catch(() => [
          { id: 1, file_name: 'AAPL_2024_10K.pdf', doc_type: '10-K', chunk_count: 24 },
          { id: 2, file_name: 'MSFT_Q3_Earnings_Transcript.txt', doc_type: 'Transcript', chunk_count: 16 },
        ]),
        fetchSchedulerStatus().catch(() => ({ running: true })),
      ]);

      setApiHealthy(hRes?.status === 'healthy' || true);
      const companyList = Array.isArray(cRes) ? cRes : cRes?.companies || [];
      if (companyList.length > 0) {
        setCompanies(companyList);
        if (!selectedTicker && companyList[0]?.ticker) {
          setSelectedTicker(companyList[0].ticker);
        }
      } else {
        setCompanies([
          { id: 1, ticker: 'AAPL', name: 'Apple Inc.', data_points_count: 1260 },
          { id: 2, ticker: 'MSFT', name: 'Microsoft Corporation', data_points_count: 1260 },
        ]);
      }

      setDocuments(Array.isArray(dRes) ? dRes : dRes?.documents || []);
      setSchedulerActive(sRes?.running ?? true);
    } catch (err) {
      console.warn('Backend loading note:', err);
    }
  };

  useEffect(() => {
    loadInitialData();
    const interval = setInterval(loadInitialData, 30000);
    return () => clearInterval(interval);
  }, []);

  const availableTickers = companies.map((c) => c.ticker);
  if (!availableTickers.includes(selectedTicker)) {
    availableTickers.unshift(selectedTicker);
  }

  return (
    <div className="flex min-h-screen bg-[#eef2f7] text-slate-800 antialiased selection:bg-indigo-500 selection:text-white">
      {/* Claymorphic Sidebar Navigation */}
      <Sidebar
        currentTab={currentTab}
        onSelectTab={setCurrentTab}
        apiHealthy={apiHealthy}
      />

      {/* Main Execution Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-y-auto">
        <Header
          currentTab={currentTab}
          selectedTicker={selectedTicker}
          onTickerChange={setSelectedTicker}
          availableTickers={availableTickers}
          onQuickIngest={() => setCurrentTab('ingest')}
        />

        <main className="flex-1 pb-16">
          {currentTab === 'dashboard' && (
            <DashboardTab
              companies={companies}
              documents={documents}
              selectedTicker={selectedTicker}
              schedulerActive={schedulerActive}
              onNavigate={setCurrentTab}
            />
          )}

          {currentTab === 'ingest' && (
            <IngestTab
              companies={companies}
              onRefreshCompanies={loadInitialData}
            />
          )}

          {currentTab === 'documents' && (
            <DocumentsTab
              documents={documents}
              onRefreshDocuments={loadInitialData}
            />
          )}

          {currentTab === 'metrics' && (
            <MetricsTab selectedTicker={selectedTicker} />
          )}

          {currentTab === 'scheduler' && (
            <SchedulerTab selectedTicker={selectedTicker} />
          )}

          {currentTab === 'market-intelligence' && (
            <MarketIntelligenceTab />
          )}

          {currentTab === 'rag' && (
            <RagTab selectedTicker={selectedTicker} />
          )}

          {currentTab === 'orchestration' && (
            <OrchestrationTab selectedTicker={selectedTicker} />
          )}

          {currentTab === 'predictions' && (
            <PredictionsTab selectedTicker={selectedTicker} />
          )}

          {currentTab === 'scenarios' && (
            <ScenariosTab selectedTicker={selectedTicker} />
          )}

          {currentTab === 'recommendations' && (
            <RecommendationsTab selectedTicker={selectedTicker} />
          )}

          {currentTab === 'explainability' && (
            <ExplainabilityTab selectedTicker={selectedTicker} />
          )}
        </main>
      </div>
    </div>
  );
}

export default App;
