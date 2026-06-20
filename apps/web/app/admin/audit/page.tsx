"use client";

import { useEffect, useState } from "react";
import type { AuditEntry } from "../../../lib/api";
import { authFetch } from "../../../lib/auth";
import { ADMIN_NAV, DashboardShell } from "../../../components/shell";
import { Badge, Spinner } from "../../../components/ui";

export default function AdminAudit() {
  const [entries, setEntries] = useState<AuditEntry[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    authFetch<{ entries: AuditEntry[] }>("/admin/audit")
      .then((r) => setEntries(r.entries))
      .catch((e) => setError(String(e.message ?? e)));
  }, []);

  return (
    <DashboardShell title="Audit log" nav={ADMIN_NAV} requireAdmin loginHref="/admin/login">
      <p style={{ marginTop: "-1rem" }}>Append-only record of admin actions, auth events, and money tools.</p>
      <div className="card">
        {error ? <p className="muted">Couldn&apos;t load audit log: {error}</p> : null}
        {entries === null ? (
          <Spinner />
        ) : entries.length === 0 ? (
          <p className="muted">No audit entries yet.</p>
        ) : (
          <table className="table">
            <thead><tr><th>When</th><th>Actor</th><th>Action</th><th>Detail</th></tr></thead>
            <tbody>
              {entries.map((e, i) => (
                <tr key={i}>
                  <td className="muted">{e.created_at?.replace("T", " ").slice(0, 16) ?? "—"}</td>
                  <td>{e.actor}</td>
                  <td><Badge>{e.action}</Badge></td>
                  <td className="muted" style={{ fontSize: "0.8rem" }}>
                    {Object.keys(e.detail).length ? JSON.stringify(e.detail) : "—"}
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
