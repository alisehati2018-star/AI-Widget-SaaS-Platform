"use client";

import { useEffect, useState } from "react";
import { ADMIN_NAV, DashboardShell } from "../../components/shell";
import { Stat } from "../../components/ui";
import { authFetch } from "../../lib/auth";

interface Overview {
  tenants: number;
  users: number;
  active_subscriptions: number;
  mrr: number;
}

export default function AdminOverview() {
  const [data, setData] = useState<Overview | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    authFetch<Overview>("/admin/overview")
      .then(setData)
      .catch((e) => setError(String(e.message ?? e)));
  }, []);

  return (
    <DashboardShell title="Platform overview" nav={ADMIN_NAV} requireAdmin loginHref="/admin/login">
      <p style={{ marginTop: "-1rem" }}>Health of the whole Vitrin platform.</p>
      <div className="stat-grid" style={{ marginBottom: "2rem" }}>
        <Stat label="Tenants" value={data?.tenants ?? "—"} />
        <Stat label="Users" value={data?.users ?? "—"} />
        <Stat label="Active subscriptions" value={data?.active_subscriptions ?? "—"} />
        <Stat label="MRR" value={data ? `$${data.mrr.toFixed(0)}` : "—"} />
      </div>
      {error ? (
        <div className="card"><p className="muted" style={{ margin: 0 }}>Couldn&apos;t load metrics: {error}</p></div>
      ) : null}
    </DashboardShell>
  );
}
