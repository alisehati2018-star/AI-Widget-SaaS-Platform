"use client";

import { useEffect, useState } from "react";
import type { AnalyticsBundle } from "../../../lib/api";
import { authFetch } from "../../../lib/auth";
import { ADMIN_NAV, DashboardShell } from "../../../components/shell";
import { Field, Spinner, Stat } from "../../../components/ui";

interface TenantRow { id: string; name: string }

export default function AdminAnalytics() {
  const [tenants, setTenants] = useState<TenantRow[]>([]);
  const [selected, setSelected] = useState("");
  const [data, setData] = useState<AnalyticsBundle | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    authFetch<{ tenants: TenantRow[] }>("/admin/tenants")
      .then((r) => {
        setTenants(r.tenants);
        if (r.tenants[0]) setSelected(r.tenants[0].id);
      })
      .catch(() => setTenants([]));
  }, []);

  useEffect(() => {
    if (!selected) return;
    setLoading(true);
    authFetch<AnalyticsBundle>(`/admin/analytics?tenant=${encodeURIComponent(selected)}`)
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [selected]);

  const fd = data?.four_dimensions;
  return (
    <DashboardShell title="Analytics" nav={ADMIN_NAV} requireAdmin loginHref="/admin/login">
      <p style={{ marginTop: "-1rem" }}>Drill into any tenant&apos;s search &amp; assistant metrics.</p>

      <div className="card" style={{ marginBottom: "1.5rem", maxWidth: 420 }}>
        <Field label="Tenant">
          <select className="input" value={selected} onChange={(e) => setSelected(e.target.value)}>
            {tenants.length === 0 ? <option value="">No tenants</option> : null}
            {tenants.map((t) => (
              <option key={t.id} value={t.id}>{t.name}</option>
            ))}
          </select>
        </Field>
      </div>

      {loading ? (
        <Spinner />
      ) : (
        <>
          <div className="stat-grid" style={{ marginBottom: "1.5rem" }}>
            <Stat label="Latency p95" value={fd?.latency?.p95_ms != null ? `${fd.latency.p95_ms} ms` : "—"} />
            <Stat label="No-paid share" value={fd?.cost?.no_paid_share != null ? `${Math.round(fd.cost.no_paid_share * 100)}%` : "—"} />
            <Stat label="Cost (credits)" value={fd?.cost?.total ?? "—"} />
            <Stat label="Assistant turns" value={fd?.reliability?.turns ?? "—"} />
          </div>
          <div className="card">
            <h3>Zero-result searches</h3>
            {data?.zero_results?.length ? (
              <table className="table">
                <thead><tr><th>Query</th><th>Count</th></tr></thead>
                <tbody>{data.zero_results.map((z) => <tr key={z.term}><td>{z.term}</td><td>{z.count}</td></tr>)}</tbody>
              </table>
            ) : (
              <p className="muted">No data for this tenant yet.</p>
            )}
          </div>
        </>
      )}
    </DashboardShell>
  );
}
