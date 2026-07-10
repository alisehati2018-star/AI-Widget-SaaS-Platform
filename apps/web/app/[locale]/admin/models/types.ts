// Shared shapes for the AI providers / pricing / finance admin page.

export type ModelModality = "chat" | "embedding" | "rerank";

export interface AiModel {
  id: string;
  provider_id: string;
  model: string;
  label: string | null;
  input_usd_per_1m: number;
  output_usd_per_1m: number;
  enabled: boolean;
  modality: ModelModality;
  dims: number | null;
  context_window: number | null;
  is_free_tier: boolean;
  // Only present on the flat GET /admin/ai/models listing.
  provider_name?: string;
  provider_is_local?: boolean;
}

export type ProviderDiscoverKind = "openai_compatible" | "openrouter" | "google" | "bynara" | "conduit";

export interface ProviderPlatformUsage {
  period_days: number;
  call_count: number;
  platform_credits: number;
  estimated_cost_usd: number;
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
  discover_kind: ProviderDiscoverKind;
  // Retries of the same endpoint before the chain fails over to the next
  // provider/model (0 = one attempt, today's behavior).
  max_retries: number;
  retry_backoff_ms: number;
  priority: number;
  models: AiModel[];
  platform_usage: ProviderPlatformUsage;
}

export interface ProviderTemplate {
  key: string;
  display_name: string;
  base_url: string;
  discover_kind: ProviderDiscoverKind;
  description: string;
  dashboard_url: string;
  already_created: boolean;
}

export interface DiscoveredModel {
  model: string;
  label: string;
  input_usd_per_1m: number;
  output_usd_per_1m: number;
  context_length: number | null;
  already_imported: boolean;
}

export type IneligibleReason = "MODEL_INACTIVE" | "PROVIDER_INACTIVE" | "PROVIDER_NO_API_KEY";

export interface RouteEntry {
  model_id: string;
  model: string;
  label: string | null;
  provider: string;
  is_local: boolean;
  is_eligible: boolean;
  ineligible_reason: IneligibleReason | null;
}

export interface RoutesData {
  routes: Record<string, RouteEntry[]>;
  tasks: string[];
}

export interface CreditCheckResult {
  credit: {
    source: "external_api" | "api_key_check";
    usage?: number;
    limit?: number | null;
    remaining?: number | null;
    currency?: string;
    key_valid?: boolean;
    models_available?: number;
    note?: string;
    dashboard_url?: string;
  };
  platform_usage: ProviderPlatformUsage;
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
