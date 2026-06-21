"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import type { AnalyticsBundle } from "../../../../lib/api";
import { authFetch } from "../../../../lib/auth";
import { ADMIN_NAV, DashboardShell } from "../../../../components/shell";
import { Alert, Spinner, Stat } from "../../../../components/ui";

export default function TenantDetail() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const [data, setData] = useState<AnalyticsBundle | null>(null);
  const [note, setNote] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    authFetch<AnalyticsBundle>(`/admin/analytics?tenant=${encodeURIComponent(id)}`)
      .then(setData)
      .catch(() => setData(null));
  }, [id]);

  async function setTracking(enabled: boolean) {
    await authFetch(`/admin/tenants/${id}/tracking`, { body: { enabled } }).catch(() => {});
    setNote(`Tracking ${enabled ? "enabled" : "disabled"}.`);
  }

  async function erase() {
    if (!window.confirm("Erase ALL data for this tenant? This cannot be undone.")) return;
    await authFetch(`/admin/tenants/${id}/erase`, { method: "POST" }).catch(() => {});
    setNote("Tenant data erased.");
  }

  const fd = data?.four_dimensions;
  return (
    <DashboardShell title="Tenant detail" nav={ADMIN_NAV} requireAdmin loginHref="/admin/login">
      <p style={{ marginTop: "-1rem" }} className="muted">Tenant ID: {id}</p>
      {note ? <Alert kind="success">{note}</Alert> : null}

      <div className="stat-grid" style={{ marginBottom: "1.5rem" }}>
        <Stat label="Latency p95" value={fd?.latency?.p95_ms != null ? `${fd.latency.p95_ms} ms` : "—"} />
        <Stat label="No-paid share" value={fd?.cost?.no_paid_share != null ? `${Math.round(fd.cost.no_paid_share * 100)}%` : "—"} />
        <Stat label="Cost (credits)" value={fd?.cost?.total ?? "—"} />
        <Stat label="Assistant turns" value={fd?.reliability?.turns ?? "—"} />
      </div>

      <div className="card">
        <h3>Governance (GDPR)</h3>
        <p className="hint">Operator controls for this tenant&apos;s data.</p>
        <div className="row" style={{ flexWrap: "wrap" }}>
          <button className="btn btn-soft" onClick={() => void setTracking(true)}>Enable tracking</button>
          <button className="btn btn-soft" onClick={() => void setTracking(false)}>Disable tracking</button>
          <button className="btn btn-danger" onClick={() => void erase()}>Erase all data</button>
        </div>
      </div>
    </DashboardShell>
  );
}
