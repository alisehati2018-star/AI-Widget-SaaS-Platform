"use client";

import { useCallback, useEffect, useState } from "react";
import { getPlans, type MyOrder, type PlanInfo, type TenantProfile } from "../../../lib/api";
import { ApiError } from "../../../lib/api";
import { authFetch } from "../../../lib/auth";
import { DashboardShell, OWNER_NAV } from "../../../components/shell";
import { Alert, Badge, Spinner } from "../../../components/ui";

interface Invoice {
  number: number;
  description: string;
  amount: number;
  currency: string;
  status: string;
  created_at: string | null;
}
interface Preview {
  base_price: number;
  proration_credit: number;
  amount_due: number;
  currency: string;
  plan_name: string;
}

export default function BillingPage() {
  const [plans, setPlans] = useState<PlanInfo[]>([]);
  const [profile, setProfile] = useState<TenantProfile | null>(null);
  const [orders, setOrders] = useState<MyOrder[]>([]);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [note, setNote] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState<string | null>(null);
  const [topupCredits, setTopupCredits] = useState(50000);

  const reload = useCallback(() => {
    authFetch<TenantProfile>("/tenant/profile").then(setProfile).catch(() => setProfile(null));
    authFetch<{ orders: MyOrder[] }>("/tenant/billing/orders").then((r) => setOrders(r.orders)).catch(() => setOrders([]));
    authFetch<{ invoices: Invoice[] }>("/tenant/billing/invoices").then((r) => setInvoices(r.invoices)).catch(() => setInvoices([]));
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
      // Show proration before committing an upgrade from a paid plan.
      if (profile?.sub_status === "active" && profile.plan.toLowerCase() !== "free") {
        const pv = await authFetch<Preview>(`/tenant/billing/preview?plan_code=${code}`).catch(() => null);
        if (pv && pv.proration_credit > 0) {
          const ok = window.confirm(
            `Switch to ${pv.plan_name}: ${pv.currency} ${pv.base_price.toFixed(2)} − ` +
              `${pv.currency} ${pv.proration_credit.toFixed(2)} credit = ${pv.currency} ${pv.amount_due.toFixed(2)} due. Continue?`,
          );
          if (!ok) { setPending(null); return; }
        }
      }
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

  async function buyTopup() {
    setError(null);
    setNote(null);
    setPending("topup");
    try {
      await authFetch("/tenant/billing/topup", { body: { credits: topupCredits } });
      setNote(`Top-up order created for ${topupCredits.toLocaleString()} credits — pending confirmation.`);
      reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Top-up failed.");
    } finally {
      setPending(null);
    }
  }

  async function lifecycle(action: "cancel" | "resume") {
    await authFetch(`/tenant/billing/${action}`, { method: "POST" }).catch(() => {});
    setNote(action === "cancel" ? "Subscription will cancel at period end." : "Subscription resumed.");
    reload();
  }

  const tone = (s: string) => (s === "paid" ? "success" : s === "pending" ? "warning" : undefined);
  const onPaidPlan = profile && profile.sub_status !== "none" && profile.plan.toLowerCase() !== "free";

  return (
    <DashboardShell title="Plan & billing" nav={OWNER_NAV}>
      {note ? <Alert kind="success">{note}</Alert> : null}
      {error ? <Alert kind="error">{error}</Alert> : null}

      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <div className="row-between" style={{ flexWrap: "wrap", gap: "1rem" }}>
          <div>
            <small className="faint">Current plan</small>
            <h3 style={{ margin: "0.2rem 0" }}>
              {profile?.plan ?? "—"}{" "}
              <Badge tone={profile?.sub_status === "active" ? "success" : profile?.sub_status === "past_due" ? "warning" : undefined}>
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
          {onPaidPlan ? (
            <div className="row" style={{ gap: "0.5rem" }}>
              <button className="btn btn-soft" onClick={() => void lifecycle("resume")}>Resume</button>
              <button className="btn btn-danger" onClick={() => void lifecycle("cancel")}>Cancel plan</button>
            </div>
          ) : null}
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

      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <h3>Buy more credits</h3>
        <p className="hint">One-off top-up that never expires. ~1,000 credits per $1.</p>
        <div className="row" style={{ flexWrap: "wrap", alignItems: "center" }}>
          <select className="input" style={{ maxWidth: 220 }} value={topupCredits} onChange={(e) => setTopupCredits(Number(e.target.value))}>
            <option value={50000}>50,000 credits — $50</option>
            <option value={100000}>100,000 credits — $100</option>
            <option value={250000}>250,000 credits — $250</option>
          </select>
          <button className="btn btn-primary" disabled={pending === "topup"} onClick={() => void buyTopup()}>
            {pending === "topup" ? <Spinner /> : "Buy credits"}
          </button>
        </div>
      </div>

      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <h3>Invoices</h3>
        {invoices.length === 0 ? (
          <p className="muted">No invoices yet.</p>
        ) : (
          <table className="table">
            <thead><tr><th>#</th><th>Description</th><th>Amount</th><th>Status</th><th>Date</th></tr></thead>
            <tbody>
              {invoices.map((inv) => (
                <tr key={inv.number}>
                  <td>#{inv.number}</td>
                  <td>{inv.description}</td>
                  <td>{inv.currency} {inv.amount.toFixed(2)}</td>
                  <td><Badge tone="success">{inv.status}</Badge></td>
                  <td className="muted">{inv.created_at?.slice(0, 10) ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="card">
        <h3>Orders</h3>
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
