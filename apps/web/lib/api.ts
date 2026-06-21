// Thin client for the Vitrin backend. The browser calls same-origin /api/*,
// which next.config.mjs proxies to the FastAPI backend (no CORS).

const BASE = "/api";

export class ApiError extends Error {
  code: string;
  status: number;
  constructor(status: number, code: string, message: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

export interface PlanInfo {
  code: string;
  name: string;
  description: string | null;
  price_monthly: number;
  currency: string;
  credits_per_month: number;
  rate_limit_per_min: number;
  features: string[];
}

export interface SessionUser {
  id: string;
  email: string;
  full_name?: string | null;
  role: "platform_admin" | "store_owner" | "store_staff";
  tenant_id: string | null;
}

export async function apiFetch<T = unknown>(
  path: string,
  opts: { method?: string; body?: unknown; token?: string | null } = {},
): Promise<T> {
  const headers: Record<string, string> = { "content-type": "application/json" };
  if (opts.token) headers["authorization"] = `Bearer ${opts.token}`;
  const resp = await fetch(`${BASE}${path}`, {
    method: opts.method ?? (opts.body ? "POST" : "GET"),
    headers,
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  const text = await resp.text();
  const data = text ? JSON.parse(text) : {};
  if (!resp.ok) {
    const err = (data as { error?: { code?: string; message?: string } }).error;
    throw new ApiError(resp.status, err?.code ?? "error", err?.message ?? `Request failed (${resp.status})`);
  }
  return data as T;
}

export function getPlans(): Promise<{ plans: PlanInfo[] }> {
  return apiFetch("/plans");
}

// --- Tenant (store-owner) shapes ---
export interface TenantProfile {
  tenant_id: string;
  slug: string;
  name: string;
  status: string;
  plan: string;
  sub_status: string;
  current_period_end: string | null;
  tracking_enabled: boolean;
  settings: Record<string, string>;
  credits: { spent: number; granted: number; cap: number | null; within_plan: boolean };
  role: string;
}
export interface MyOrder {
  id: string;
  plan: string;
  amount: number;
  currency: string;
  status: string;
  provider: string;
  created_at: string | null;
  paid_at: string | null;
}
export interface ApiKey {
  id: string;
  scope: string;
  label: string | null;
  revoked: boolean;
  created_at: string | null;
  last_used_at: string | null;
}
export interface Lead {
  email: string | null;
  phone: string | null;
  has_intent: boolean;
  source: string;
  created_at: string | null;
}
export interface TeamMember {
  email: string;
  full_name: string | null;
  role: string;
  status: string;
  last_login_at: string | null;
}
export interface FourDimensions {
  cost?: { total?: number; no_paid_share?: number };
  latency?: { p95_ms?: number | null };
  reliability?: { turns?: number };
}
export interface AnalyticsBundle {
  four_dimensions?: FourDimensions;
  most_wanted?: { term: string; count: number }[];
  zero_results?: { term: string; count: number }[];
  funnel?: Record<string, number>;
}

// --- Admin shapes ---
export interface AdminUser {
  email: string;
  full_name: string | null;
  role: string;
  status: string;
  tenant: string;
  last_login_at: string | null;
}
export interface AuditEntry {
  actor: string;
  action: string;
  detail: Record<string, unknown>;
  created_at: string | null;
}
export interface Order {
  id: string;
  tenant: string;
  plan: string;
  amount: number;
  currency: string;
  status: string;
  provider: string;
  created_at: string | null;
}
