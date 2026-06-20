"use client";

import { useEffect, useState } from "react";
import type { Order } from "../../../lib/api";
import { authFetch } from "../../../lib/auth";
import { ADMIN_NAV, DashboardShell } from "../../../components/shell";
import { Badge, Spinner, Stat } from "../../../components/ui";

export default function AdminBilling() {
  const [orders, setOrders] = useState<Order[] | null>(null);
  const [revenue, setRevenue] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    authFetch<{ orders: Order[]; revenue_total: number }>("/admin/orders")
      .then((r) => { setOrders(r.orders); setRevenue(r.revenue_total); })
      .catch((e) => setError(String(e.message ?? e)));
  }, []);

  const tone = (s: string) => (s === "paid" ? "success" : s === "pending" ? "warning" : undefined);

  return (
    <DashboardShell title="Billing" nav={ADMIN_NAV} requireAdmin loginHref="/admin/login">
      <p style={{ marginTop: "-1rem" }}>Orders and revenue across the platform.</p>
      <div className="stat-grid" style={{ marginBottom: "2rem" }}>
        <Stat label="Paid revenue" value={`$${revenue.toFixed(0)}`} />
        <Stat label="Orders" value={orders?.length ?? "—"} />
        <Stat label="Pending" value={orders?.filter((o) => o.status === "pending").length ?? "—"} />
        <Stat label="Refunded" value={orders?.filter((o) => o.status === "refunded").length ?? "—"} />
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
            <thead><tr><th>Store</th><th>Plan</th><th>Amount</th><th>Provider</th><th>Status</th><th>When</th></tr></thead>
            <tbody>
              {orders.map((o, i) => (
                <tr key={i}>
                  <td>{o.tenant}</td>
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
      </div>
    </DashboardShell>
  );
}
