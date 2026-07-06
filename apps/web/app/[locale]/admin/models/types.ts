// Shared shapes for the AI providers / pricing / finance admin page.

export interface AiModel {
  id: string;
  provider_id: string;
  model: string;
  label: string | null;
  input_usd_per_1m: number;
  output_usd_per_1m: number;
  enabled: boolean;
}

export interface AiProvider {
  id: string;
  name: string;
  kind: "openai-compatible" | "local";
  base_url: string;
  api_key_masked: string;
  has_api_key: boolean;
  is_local: boolean;
  enabled: boolean;
  timeout_s: number;
  notes: string | null;
  models: AiModel[];
}

export interface RouteEntry {
  model_id: string;
  model: string;
  provider: string;
  is_local: boolean;
}

export interface RoutesData {
  routes: Record<string, RouteEntry[]>;
  tasks: string[];
}

export interface PricingData {
  usd_per_credit: number;
  margin_percent: number;
  search_credits: number;
  local_input_usd_per_1m: number;
  local_output_usd_per_1m: number;
}

export interface FinanceData {
  days: number;
  usd_per_credit: number;
  margin_percent: number;
  credits_consumed: number;
  consumption_value_usd: number;
  provider_cost_usd: number;
  gross_margin_usd: number;
  calls: number;
  billed_revenue: { currency: string; amount: number }[];
  by_day: { day: string; credits: number; cogs_usd: number }[];
  by_model: {
    provider: string;
    model: string;
    calls: number;
    tokens_in: number;
    tokens_out: number;
    credits: number;
    cogs_usd: number;
  }[];
  by_tenant: { name: string; slug: string; calls: number; credits: number; cogs_usd: number }[];
}

export interface GatewayStatus {
  embeddings_url: string;
  reranker_url: string;
  llm_url: string;
  llm_model: string;
  frontier_enabled: boolean;
  frontier_model: string | null;
  rerank_enabled: boolean;
  by_rung: { rung: string; count: number }[];
}
