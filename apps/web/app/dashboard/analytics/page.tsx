"use client";

import { useEffect, useState } from "react";
import { DashboardShell, OWNER_NAV } from "../../../components/shell";
import { Stat } from "../../../components/ui";
import { authFetch, useSession } from "../../../lib/auth";

interface Analytics {
  four_dimensions?: {
    cost?: { total?: number; no_paid_share?: number };
    latency?: { p95_ms?: number | null };
    reliability?: { turns?: number };
  };
  most_wanted?: { term: string; count: number }[];
  zero_results?: { term: string; count: number }[];
}

export default function AnalyticsPage() {
  const { user } = useSession();
  const [data, setData] = useState<Analytics | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user?.tenant_id) return;
    authFetch<Analytics>(`/admin/analytics?tenant=${encodeURIComponent(user.tenant_id)}`)
      .then(setData)
      .catch((e) => setError(String(e.message ?? e)));
  }, [user?.tenant_id]);

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

      <div className="card">
        <h3>Zero-result searches</h3>
        <p className="hint">Demand your catalogue isn&apos;t meeting — opportunities to add products or synonyms.</p>
        {error ? <p className="muted">No data yet ({error}).</p> : null}
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
