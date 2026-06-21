"use client";

import { useEffect, useState } from "react";
import type { AnalyticsBundle } from "../../../lib/api";
import { authFetch } from "../../../lib/auth";
import { DashboardShell, OWNER_NAV } from "../../../components/shell";
import { Stat } from "../../../components/ui";

export default function AnalyticsPage() {
  const [data, setData] = useState<AnalyticsBundle | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    authFetch<AnalyticsBundle>("/tenant/analytics")
      .then(setData)
      .catch((e) => setError(String(e.message ?? e)));
  }, []);

  const fd = data?.four_dimensions;
  return (
    <DashboardShell title="Analytics" nav={OWNER_NAV}>
      <p style={{ marginTop: "-1rem" }}>Relevance · latency · cost · reliability for your store.</p>
      <div className="stat-grid" style={{ marginBottom: "2rem" }}>
        <Stat label="Latency p95" value={fd?.latency?.p95_ms != null ? `${fd.latency.p95_ms} ms` : "—"} />
        <Stat label="No-paid share" value={fd?.cost?.no_paid_share != null ? `${Math.round(fd.cost.no_paid_share * 100)}%` : "—"} />
        <Stat label="Cost (credits)" value={fd?.cost?.total ?? "—"} />
        <Stat label="Assistant turns" value={fd?.reliability?.turns ?? "—"} />
      </div>

      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <h3>Most-wanted searches</h3>
        {data?.most_wanted?.length ? (
          <table className="table">
            <thead><tr><th>Query</th><th>Count</th></tr></thead>
            <tbody>
              {data.most_wanted.map((m) => (
                <tr key={m.term}><td>{m.term}</td><td>{m.count}</td></tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="muted">No search data yet{error ? ` (${error})` : ""}.</p>
        )}
      </div>

      <div className="card">
        <h3>Zero-result searches</h3>
        <p className="hint">Demand your catalogue isn&apos;t meeting — add products or synonyms.</p>
        {data?.zero_results?.length ? (
          <table className="table">
            <thead><tr><th>Query</th><th>Count</th></tr></thead>
            <tbody>
              {data.zero_results.map((z) => (
                <tr key={z.term}><td>{z.term}</td><td>{z.count}</td></tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="muted">No zero-result data yet.</p>
        )}
      </div>
    </DashboardShell>
  );
}
