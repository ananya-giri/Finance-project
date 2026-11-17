export type TabId = 
  | 'dashboard'
  | 'ingest'
  | 'documents'
  | 'metrics'
  | 'scheduler'
  | 'market-intelligence'
  | 'rag'
  | 'orchestration'
  | 'predictions'
  | 'scenarios'
  | 'recommendations'
  | 'explainability';

export interface Company {
  id: number;
  ticker: string;
  name?: string;
  sector?: string;
  country?: string;
  currency?: string;
  data_points_count?: number;
  earliest_date?: string;
  latest_date?: string;
}

export interface DocumentItem {
  id: number;
  file_name: string;
  doc_type?: string;
  upload_timestamp?: string;
  chunk_count?: number;
  file_hash?: string;
  snippet?: string;
}

export interface MetricItem {
  id: number;
  ticker: string;
  period_type: string;
  period_end: string;
  revenue?: number;
  ebitda?: number;
  net_income?: number;
  free_cash_flow?: number;
  eps?: number;
}

export interface EconomicIndicator {
  id: number;
  indicator_name: string;
  country: string;
  current_value: number;
  unit: string;
  category: string;
  last_updated: string;
}

export interface GeopoliticalEvent {
  id: number;
  title: string;
  region: string;
  impact_level: string;
  sentiment_score: number;
  created_at: string;
}

export interface PredictionResult {
  run_id?: number;
  ticker: string;
  target_type: string;
  horizon: string;
  best_model: string;
  models?: Record<string, {
    rmse?: number;
    mape?: number;
    r2?: number;
    forecast?: number[];
  }>;
  forecast_dates?: string[];
  results?: any;
}

export interface ScenarioResult {
  run_id?: number;
  ticker: string;
  scenario_type: string;
  parameters: Record<string, any>;
  impact_metrics: {
    revenue_impact_pct?: number;
    ebitda_impact_pct?: number;
    cash_flow_impact_pct?: number;
    net_income_impact_pct?: number;
    summary?: string;
  };
  narrative_analysis?: string;
}

export interface RecommendationReport {
  report_id?: number;
  ticker: string;
  generated_at?: string;
  recommendations: Array<{
    id?: string;
    category: string;
    title: string;
    description: string;
    priority_score: number;
    priority_level: 'HIGH' | 'MEDIUM' | 'LOW';
    justification: string;
    impact_estimate?: string;
    timeline?: string;
  }>;
}

export interface ExplainabilityData {
  ticker: string;
  target_type?: string;
  model_name?: string;
  feature_importance?: Array<{ feature: string; importance: number }>;
  key_drivers?: Array<{ name: string; impact: string; value: number }>;
  shap_summary?: any;
  traceability_sources?: Array<{
    document_name: string;
    file_hash: string;
    relevance_score: number;
    snippet: string;
  }>;
}
