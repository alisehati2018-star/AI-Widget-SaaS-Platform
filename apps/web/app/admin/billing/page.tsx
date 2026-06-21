"use client";

import { useCallback, useEffect, useState } from "react";
import type { Order } from "../../../lib/api";
import { authFetch } from "../../../lib/auth";
import { ADMIN_NAV, DashboardShell } from "../../../components/shell";
import { Alert, Badge, Spinner, Stat } from "../../../components/ui";

export default function AdminBilling() {
  const [orders, setOrders] = useState<Order[] | null>(null);
  const [revenue, setRevenue] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  const load = useCallback(() => {
    authFetch<{ orders: Order[]; revenue_total: number }>("/admin/orders")
      .then((r) => { setOrders(r.orders); setRevenue(r.revenue_total); })
      .catch((e) => setError(String(e.message ?? e)));
  }, []);

  useEffect(() => load(), [load]);

  async function act(id: string, action: "mark-paid" | "refund") {
    setBusy(id + action);
    try {
      await authFetch(`/admin/orders/${id}/${action}`, { method: "POST" });
      load();
    } finally {
      setBusy(null);
    }
  }

  const tone = (s: string) => (s === "paid" ? "success" : s === "pending" ? "warning" : undefined);

  async function runJob(job: "run-renewals" | "run-dunning") {
    setBusy(job);
    try {
      const r = await authFetch<Record<string, number>>(`/admin/billing/${job}`, { method: "POST" });
      setMsg(job === "run-renewals"
        ? `Renewals: ${r.downgraded ?? 0} downgraded, ${r.past_due ?? 0} past-due.`
        : `Dunning: emailed ${r.emailed ?? 0} of ${r.past_due ?? 0} past-due tenants.`);
      load();
    } finally {
      setBusy(null);
    }
  }

  return (
    <DashboardShell title="Billing" nav={ADMIN_NAV} requireAdmin loginHref="/admin/login">
      <p style={{ marginTop: "-1rem" }}>Orders, revenue, and billing operations.</p>
      {msg ? <Alert kind="success">{msg}</Alert> : null}
      <div className="stat-grid" style={{ marginBottom: "1.5rem" }}>
        <Stat label="Paid revenue" value={`$${revenue.toFixed(0)}`} />
        <Stat label="Orders" value={orders?.length ?? "—"} />
        <Stat label="Pending" value={orders?.filter((o) => o.status === "pending").length ?? "—"} />
        <Stat label="Refunded" value={orders?.filter((o) => o.status === "refunded").length ?? "—"} />
      </div>
      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <h3>Billing operations</h3>
        <p className="hint">Run period-end processing and dunning (normally scheduled).</p>
        <div className="row" style={{ flexWrap: "wrap" }}>
          <button className="btn btn-soft" disabled={busy !== null} onClick={() => void runJob("run-renewals")}>
            {busy === "run-renewals" ? <Spinner /> : "Run renewals"}
          </button>
          <button className="btn btn-soft" disabled={busy !== null} onClick={() => void runJob("run-dunning")}>
            {busy === "run-dunning" ? <Spinner /> : "Run dunning"}
          </button>
        </div>
      </div>
      <div className="card">
        <h3>Recent orders</h3>
        {error ? <p className="muted">Couldn&apos;t load orders: {error}</p> : null}
        {orders === null ? (
          <Spinner />
        ) : orders.length === 0 ? (
          <p className="muted">No orders yet. Checkout activates with the billing release.</p>
        ) : (
          <table className="table">
            <thead><tr><th>Store</th><th>Plan</th><th>Amount</th><th>Provider</th><th>Status</th><th>When</th><th></th></tr></thead>
            <tbody>
              {orders.map((o) => (
                <tr key={o.id}>
                  <td>{o.tenant}</td>
                  <td>{o.plan}</td>
                  <td>{o.currency} {o.amount.toFixed(2)}</td>
                  <td className="muted">{o.provider}</td>
                  <td><Badge tone={tone(o.status)}>{o.status}</Badge></td>
                  <td className="muted">{o.created_at?.slice(0, 10) ?? "—"}</td>
                  <td>
                    <div className="row" style={{ gap: "0.4rem" }}>
                      {o.status === "pending" ? (
                        <button className="btn btn-soft" disabled={busy !== null}
                          onClick={() => void act(o.id, "mark-paid")}>
                          {busy === o.id + "mark-paid" ? <Spinner /> : "Mark paid"}
                        </button>
                      ) : null}
                      {o.status === "paid" ? (
                        <button className="btn btn-danger" disabled={busy !== null}
                          onClick={() => void act(o.id, "refund")}>
                          {busy === o.id + "refund" ? <Spinner /> : "Refund"}
                        </button>
                      ) : null}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </DashboardShell>
  );
}
