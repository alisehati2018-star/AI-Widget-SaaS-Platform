"use client";

import { useCallback, useEffect, useState } from "react";
import { authFetch } from "../../../lib/auth";
import { ADMIN_NAV, DashboardShell } from "../../../components/shell";
import { Badge, Spinner } from "../../../components/ui";

interface Flag { key: string; enabled: boolean; description: string | null }

export default function AdminFlags() {
  const [flags, setFlags] = useState<Flag[] | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(() => {
    authFetch<{ flags: Flag[] }>("/admin/feature-flags").then((r) => setFlags(r.flags)).catch(() => setFlags([]));
  }, []);
  useEffect(() => load(), [load]);

  async function toggle(key: string, enabled: boolean) {
    setBusy(key);
    try {
      await authFetch(`/admin/feature-flags/${key}`, { body: { enabled } });
      load();
    } finally {
      setBusy(null);
    }
  }

  return (
    <DashboardShell title="Feature flags" nav={ADMIN_NAV} requireAdmin loginHref="/admin/login">
      <p style={{ marginTop: "-1rem" }}>Toggle platform capabilities without a deploy.</p>
      <div className="card">
        {flags === null ? (
          <Spinner />
        ) : (
          <table className="table">
            <thead><tr><th>Flag</th><th>Description</th><th>State</th><th></th></tr></thead>
            <tbody>
              {flags.map((f) => (
                <tr key={f.key}>
                  <td><code>{f.key}</code></td>
                  <td className="muted">{f.description ?? "—"}</td>
                  <td>{f.enabled ? <Badge tone="success">on</Badge> : <Badge>off</Badge>}</td>
                  <td>
                    <button className="btn btn-soft" disabled={busy === f.key} onClick={() => void toggle(f.key, !f.enabled)}>
                      {busy === f.key ? <Spinner /> : f.enabled ? "Disable" : "Enable"}
                    </button>
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
