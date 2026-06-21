"use client";

import { useEffect, useState } from "react";
import { authFetch } from "../../../lib/auth";
import { ADMIN_NAV, DashboardShell } from "../../../components/shell";
import { Spinner, Stat } from "../../../components/ui";

interface Usage {
  calls: number;
  tokens_in: number;
  tokens_out: number;
  cost: number;
  credits_spent: number;
  by_rung: { rung: string; count: number }[];
}

export default function AdminUsage() {
  const [data, setData] = useState<Usage | null>(null);

  useEffect(() => {
    authFetch<Usage>("/admin/usage").then(setData).catch(() => setData(null));
  }, []);

  return (
    <DashboardShell title="Usage monitoring" nav={ADMIN_NAV} requireAdmin loginHref="/admin/login">
      <p style={{ marginTop: "-1rem" }}>Platform-wide AI usage and credit consumption.</p>
      <div className="stat-grid" style={{ marginBottom: "2rem" }}>
        <Stat label="Model calls" value={data ? data.calls.toLocaleString() : "—"} />
        <Stat label="Tokens in" value={data ? data.tokens_in.toLocaleString() : "—"} />
        <Stat label="Tokens out" value={data ? data.tokens_out.toLocaleString() : "—"} />
        <Stat label="Credits spent" value={data ? Math.round(data.credits_spent).toLocaleString() : "—"} />
      </div>
      <div className="card">
        <h3>Calls by rung</h3>
        {data === null ? <Spinner /> : data.by_rung.length === 0 ? (
          <p className="muted">No usage recorded yet (needs live traffic through the gateway).</p>
        ) : (
          <table className="table">
            <thead><tr><th>Rung</th><th>Calls</th></tr></thead>
            <tbody>{data.by_rung.map((r) => <tr key={r.rung}><td>{r.rung}</td><td>{r.count}</td></tr>)}</tbody>
          </table>
        )}
      </div>
    </DashboardShell>
  );
}
