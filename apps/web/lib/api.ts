// Thin client for the Vitrin backend. The browser calls same-origin /api/*,
// which next.config.mjs proxies to the FastAPI backend (no CORS).
//
// Auth is cookie-based: the backend sets httpOnly `vitrin_access` /
// `vitrin_refresh` cookies (sent automatically on same-origin requests) plus a
// JS-readable `vitrin_csrf` cookie. We never read or store the access/refresh
// tokens in JS — that's the whole point of the httpOnly cookies (XSS can't
// exfiltrate them). For unsafe methods we echo the CSRF cookie back in the
// `x-csrf-token` header (double-submit) so the backend's CsrfMiddleware passes.

const BASE = "/api";
const CSRF_COOKIE = "vitrin_csrf";
const CSRF_HEADER = "x-csrf-token";
const SAFE_METHODS = new Set(["GET", "HEAD", "OPTIONS"]);

export class ApiError extends Error {
  code: string;
  status: number;
  constructor(status: number, code: string, message: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

/** Read a non-httpOnly cookie value (used only for the CSRF token). */
function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  for (const part of document.cookie.split(";")) {
    const [k, ...v] = part.trim().split("=");
    if (k === name) return decodeURIComponent(v.join("="));
  }
  return null;
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
  opts: { method?: string; body?: unknown } = {},
): Promise<T> {
  const method = opts.method ?? (opts.body ? "POST" : "GET");
  const headers: Record<string, string> = { "content-type": "application/json" };
  if (!SAFE_METHODS.has(method)) {
    const csrf = readCookie(CSRF_COOKIE);
    if (csrf) headers[CSRF_HEADER] = csrf;
  }
  const resp = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: opts.body ? JSON.stringify(opts.body) : undefined,
    // Send the httpOnly auth cookies (same-origin via the /api proxy).
    credentials: "include",
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
  email_verified: boolean;
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
