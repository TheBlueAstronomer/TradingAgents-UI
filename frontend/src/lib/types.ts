export type AnalystKey = "market" | "social" | "news" | "fundamentals";
export type AssetType = "stock" | "crypto";
export type RunStatus = "queued" | "running" | "completed" | "failed";
export type AgentStatus = "pending" | "in_progress" | "completed" | "error";
export type Signal =
  "BUY" | "OVERWEIGHT" | "HOLD" | "UNDERWEIGHT" | "SELL" | "REVIEW";
export type ReportKey =
  | "market_report"
  | "sentiment_report"
  | "news_report"
  | "fundamentals_report"
  | "investment_plan"
  | "trader_investment_plan"
  | "final_trade_decision";
export interface AnalysisCreate {
  ticker: string;
  analysis_date: string;
  analysts: AnalystKey[];
  llm_provider: string;
  quick_think_llm: string;
  deep_think_llm: string;
  research_depth: number;
  backend_url?: string;
}
export interface AnalysisSummary {
  id: string;
  ticker: string;
  analysis_date: string;
  asset_type: AssetType;
  analysts: AnalystKey[];
  llm_provider: string;
  research_depth: number;
  status: RunStatus;
  signal: Signal | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}
export interface AnalysisDetail extends AnalysisSummary {
  quick_think_llm: string;
  deep_think_llm: string;
  reports: Partial<Record<ReportKey, string>>;
  agent_statuses: Record<string, AgentStatus>;
  error_message: string | null;
  final_state: Record<string, unknown> | null;
  last_event_seq: number;
}
export interface HistoryQuery {
  page: number;
  page_size: number;
  ticker?: string;
  status?: RunStatus;
  signal?: Signal;
  sort_by: "created_at" | "ticker" | "analysis_date" | "status" | "signal";
  sort_order: "asc" | "desc";
}
export interface HistoryPage {
  items: AnalysisSummary[];
  total: number;
  page: number;
  page_size: number;
}
export interface ModelOption {
  label: string;
  value: string;
}
export interface ProviderOption {
  id: string;
  label: string;
  quick_models: ModelOption[];
  deep_models: ModelOption[];
  allows_custom_model: boolean;
  requires_backend_url: boolean;
  default_quick_model: string;
  default_deep_model: string;
}
export interface AnalystOption {
  id: AnalystKey;
  label: string;
  description: string;
  selected_by_default: boolean;
}
export type AgentTeam =
  | "Analyst Team"
  | "Research Team"
  | "Trading Team"
  | "Risk Management"
  | "Portfolio Management";
export type ActivityMessage = {
  id?: string;
  category: "User" | "Agent" | "Data" | "Control" | "System";
  content: string;
  source?: string;
  stage?: string;
  emittedAt?: string;
};
export type StreamEvent = {
  run_id: string;
  seq: number;
  emitted_at: string;
  type: string;
  data: Record<string, unknown>;
};
