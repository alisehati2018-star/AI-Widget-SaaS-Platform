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
