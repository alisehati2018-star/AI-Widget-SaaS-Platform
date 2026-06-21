"use client";

import { useEffect, useState } from "react";
import type { AuditEntry } from "../../../lib/api";
import { authFetch } from "../../../lib/auth";
import { DashboardShell, OWNER_NAV } from "../../../components/shell";
import { Badge, Spinner } from "../../../components/ui";

export default function ActivityPage() {
  const [entries, setEntries] = useState<AuditEntry[] | null>(null);

  useEffect(() => {
    authFetch<{ entries: AuditEntry[] }>("/tenant/audit")
      .then((r) => setEntries(r.entries))
      .catch(() => setEntries([]));
  }, []);

  return (
    <DashboardShell title="Activity log" nav={OWNER_NAV}>
      <p style={{ marginTop: "-1rem" }}>Recent actions on your store account.</p>
      <div className="card">
        {entries === null ? (
          <Spinner />
        ) : entries.length === 0 ? (
          <p className="muted">No activity yet.</p>
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
                    {Object.keys(e.detail ?? {}).length ? JSON.stringify(e.detail) : "—"}
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
