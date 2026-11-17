import axios from 'axios';

const api = axios.create({
  baseURL: '',
  headers: {
    'Content-Type': 'application/json',
  },
});

export const fetchHealth = async () => (await api.get('/api/health')).data;
export const fetchCompanies = async () => (await api.get('/api/companies')).data;
export const fetchDocuments = async () => (await api.get('/api/documents')).data;

export const uploadDocument = async (file: File) => {
  const formData = new FormData();
  formData.append('file', file);
  return (await api.post('/api/documents/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })).data;
};

export const ingestHistoricalData = async (data: {
  ticker: string;
  start_year?: number;
  years?: number;
  frequency?: string;
}) => (await api.post('/api/companies/ingest-historical', data)).data;

export const fetchMetrics = async (ticker: string, periodType: string = 'quarterly') =>
  (await api.get(`/api/metrics/${ticker}?period_type=${periodType}`)).data;

export const fetchMetricsSummary = async (ticker: string) =>
  (await api.get(`/api/metrics/${ticker}/summary`)).data;

export const fetchSchedulerStatus = async () => (await api.get('/api/scheduler/status')).data;
export const fetchSchedulerLogs = async (limit: number = 20) =>
  (await api.get(`/api/scheduler/logs?limit=${limit}`)).data;
export const triggerSchedulerCheck = async () => (await api.post('/api/scheduler/check-now')).data;
export const simulateNewReport = async (ticker: string, reportType: string) =>
  (await api.post(`/api/scheduler/simulate-new-report?ticker=${ticker}&report_type=${reportType}`)).data;

export const fetchMarketOverview = async () => (await api.get('/api/market-intelligence/overview')).data;
export const fetchMarketIndicators = async (category?: string) =>
  (await api.get(category ? `/api/market-intelligence/indicators?category=${category}` : '/api/market-intelligence/indicators')).data;
export const syncMarketIndicators = async () => (await api.post('/api/market-intelligence/indicators/sync')).data;
export const fetchMarketEvents = async () => (await api.get('/api/market-intelligence/events?limit=50')).data;
export const syncMarketNews = async () => (await api.post('/api/market-intelligence/news/sync')).data;
export const fetchImpactMatrix = async () => (await api.get('/api/market-intelligence/impact-matrix')).data;

export const fetchRagStatus = async () => (await api.get('/api/rag/status')).data;
export const ragSearch = async (query: string, n_results: number = 4) =>
  (await api.post('/api/rag/search', { query, n_results })).data;
export const ragRecommend = async (query: string, ticker?: string) =>
  (await api.post('/api/rag/recommend', { query, ticker })).data;
export const ragIndexAll = async () => (await api.post('/api/rag/index-all')).data;

export const fetchAgents = async () => (await api.get('/api/agents')).data;
export const runAgent = async (agentId: string, payload: any) =>
  (await api.post(`/api/agents/${agentId}/run`, payload)).data;
export const runOrchestration = async (payload: { ticker: string; goals?: string[] }) =>
  (await api.post('/api/orchestration/run', payload)).data;
export const fetchOrchestrationRuns = async () => (await api.get('/api/orchestration/runs')).data;

export const runPrediction = async (payload: {
  ticker: string;
  target_type: string;
  horizon: string;
  models?: string[];
}) => (await api.post('/api/predictions/run', payload)).data;

export const retrainPredictions = async (ticker: string) =>
  (await api.post(`/api/predictions/retrain/${ticker}`)).data;

export const fetchPredictionHistory = async (ticker: string) =>
  (await api.get(`/api/predictions/${ticker}`)).data;

export const fetchScenarioTypes = async () => (await api.get('/api/scenarios/types')).data;
export const runScenario = async (payload: {
  ticker: string;
  scenario_type: string;
  parameters: Record<string, any>;
}) => (await api.post('/api/scenarios/run', payload)).data;

export const fetchScenarioHistory = async (ticker: string) =>
  (await api.get(`/api/scenarios/${ticker}`)).data;

export const generateRecommendations = async (payload: {
  ticker: string;
  focus_areas?: string[];
}) => (await api.post('/api/recommendations/generate', payload)).data;

export const fetchRecommendations = async (ticker: string) =>
  (await api.get(`/api/recommendations/${ticker}`)).data;

export const explainPrediction = async (payload: {
  ticker: string;
  target_type: string;
  model_name?: string;
}) => (await api.post('/api/explainability/prediction', payload)).data;

export const explainRecommendation = async (payload: {
  ticker: string;
  recommendation_id?: string;
}) => (await api.post('/api/explainability/recommendation', payload)).data;

export const fetchTraceability = async (ticker: string) =>
  (await api.get(`/api/explainability/traceability/${ticker}`)).data;
