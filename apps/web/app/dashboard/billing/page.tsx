"use client";

import { useCallback, useEffect, useState } from "react";
import { getPlans, type MyOrder, type PlanInfo, type TenantProfile } from "../../../lib/api";
import { ApiError } from "../../../lib/api";
import { authFetch } from "../../../lib/auth";
import { DashboardShell, OWNER_NAV } from "../../../components/shell";
import { Alert, Badge, Spinner } from "../../../components/ui";

export default function BillingPage() {
  const [plans, setPlans] = useState<PlanInfo[]>([]);
  const [profile, setProfile] = useState<TenantProfile | null>(null);
  const [orders, setOrders] = useState<MyOrder[]>([]);
  const [note, setNote] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState<string | null>(null);

  const reload = useCallback(() => {
    authFetch<TenantProfile>("/tenant/profile").then(setProfile).catch(() => setProfile(null));
    authFetch<{ orders: MyOrder[] }>("/tenant/billing/orders").then((r) => setOrders(r.orders)).catch(() => setOrders([]));
  }, []);

  useEffect(() => {
    getPlans().then((r) => setPlans(r.plans)).catch(() => setPlans([]));
    reload();
  }, [reload]);

  async function choose(code: string) {
    setError(null);
    setNote(null);
    setPending(code);
    try {
      const r = await authFetch<{ instructions?: string; redirect_url?: string; next?: string }>(
        "/tenant/billing/checkout", { body: { plan_code: code } },
      );
      if (r.next === "redirect" && r.redirect_url) {
        window.location.href = r.redirect_url;
        return;
      }
      setNote(r.instructions ?? "Order created — pending confirmation.");
      reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Checkout failed.");
    } finally {
      setPending(null);
    }
  }

  const tone = (s: string) => (s === "paid" ? "success" : s === "pending" ? "warning" : undefined);

  return (
    <DashboardShell title="Plan & billing" nav={OWNER_NAV}>
      {note ? <Alert kind="success">{note}</Alert> : null}
      {error ? <Alert kind="error">{error}</Alert> : null}

      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <div className="row-between">
          <div>
            <small className="faint">Current plan</small>
            <h3 style={{ margin: "0.2rem 0" }}>
              {profile?.plan ?? "—"}{" "}
              <Badge tone={profile?.sub_status === "active" ? "success" : "warning"}>
                {profile?.sub_status ?? "—"}
              </Badge>
            </h3>
            <p style={{ margin: 0 }} className="muted">
              {profile?.current_period_end
                ? `Renews / ends ${profile.current_period_end.slice(0, 10)}.`
                : "Trial includes hybrid search and the assistant."}
              {profile?.credits.cap != null
                ? ` · ${Math.round(profile.credits.spent).toLocaleString()} / ${Math.round(profile.credits.cap).toLocaleString()} credits used.`
                : ""}
            </p>
          </div>
        </div>
      </div>

      <h3>Choose a plan</h3>
      <div className="pricing-grid" style={{ marginBottom: "2rem" }}>
        {plans.filter((p) => p.code !== "free").map((p) => {
          const current = profile?.plan?.toLowerCase() === p.name.toLowerCase();
          return (
            <div className={`card price-card${p.code === "pro" ? " featured" : ""}`} key={p.code}>
              <h4 style={{ margin: 0 }}>{p.name}</h4>
              <div className="price">
                {p.code === "enterprise" ? "Custom" : `$${p.price_monthly}`}
                {p.price_monthly > 0 ? <small> /mo</small> : null}
              </div>
              <ul className="feature-list">
                {p.features.slice(0, 3).map((f) => <li key={f}>{f}</li>)}
              </ul>
              <button
                className={`btn ${p.code === "pro" ? "btn-primary" : "btn-ghost"} btn-block`}
                style={{ marginTop: "auto" }}
                disabled={current || pending === p.code || p.code === "enterprise"}
                onClick={() => void choose(p.code)}
              >
                {current ? "Current plan" : p.code === "enterprise" ? "Contact sales" : pending === p.code ? <Spinner /> : `Buy ${p.name}`}
              </button>
            </div>
          );
        })}
      </div>

      <div className="card">
        <h3>Invoices &amp; orders</h3>
        {orders.length === 0 ? (
          <p className="muted">No orders yet.</p>
        ) : (
          <table className="table">
            <thead><tr><th>Plan</th><th>Amount</th><th>Provider</th><th>Status</th><th>Date</th></tr></thead>
            <tbody>
              {orders.map((o) => (
                <tr key={o.id}>
                  <td>{o.plan}</td>
                  <td>{o.currency} {o.amount.toFixed(2)}</td>
                  <td className="muted">{o.provider}</td>
                  <td><Badge tone={tone(o.status)}>{o.status}</Badge></td>
                  <td className="muted">{o.created_at?.slice(0, 10) ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <p className="hint" style={{ marginTop: "1rem" }}>
          Manual orders activate once the platform confirms payment. Card / gateway checkout
          (Stripe / ZarinPal) plugs into the same flow.
        </p>
      </div>
    </DashboardShell>
  );
}
