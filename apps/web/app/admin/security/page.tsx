"use client";

import { useEffect, useState } from "react";
import { authFetch } from "../../../lib/auth";
import { ADMIN_NAV, DashboardShell } from "../../../components/shell";
import { Badge, Spinner, Stat } from "../../../components/ui";

interface Locked { email: string; failed_logins: number; locked_until: string | null }
interface AuthEvent { actor: string; action: string; created_at: string | null }
interface SecResp {
  locked_accounts: Locked[];
  accounts_with_failures: number;
  recent_auth_events: AuthEvent[];
}

export default function AdminSecurity() {
  const [data, setData] = useState<SecResp | null>(null);

  useEffect(() => {
    authFetch<SecResp>("/admin/security").then(setData).catch(() => setData(null));
  }, []);

  return (
    <DashboardShell title="Security monitoring" nav={ADMIN_NAV} requireAdmin loginHref="/admin/login">
      <p style={{ marginTop: "-1rem" }}>Account lockouts, failed logins, and recent auth events.</p>
      <div className="stat-grid" style={{ marginBottom: "2rem" }}>
        <Stat label="Locked accounts" value={data?.locked_accounts.length ?? "—"} />
        <Stat label="Accounts with failures" value={data?.accounts_with_failures ?? "—"} />
        <Stat label="Recent auth events" value={data?.recent_auth_events.length ?? "—"} />
      </div>

      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <h3>Locked accounts</h3>
        {data === null ? <Spinner /> : data.locked_accounts.length === 0 ? (
          <p className="muted">No locked accounts. 🎉</p>
        ) : (
          <table className="table">
            <thead><tr><th>Email</th><th>Failed</th><th>Locked until</th></tr></thead>
            <tbody>
              {data.locked_accounts.map((l) => (
                <tr key={l.email}>
                  <td>{l.email}</td>
                  <td><Badge tone="warning">{l.failed_logins}</Badge></td>
                  <td className="muted">{l.locked_until?.replace("T", " ").slice(0, 16) ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="card">
        <h3>Recent auth events</h3>
        {data?.recent_auth_events.length ? (
          <table className="table">
            <thead><tr><th>When</th><th>Actor</th><th>Action</th></tr></thead>
            <tbody>
              {data.recent_auth_events.map((e, i) => (
                <tr key={i}>
                  <td className="muted">{e.created_at?.replace("T", " ").slice(0, 16) ?? "—"}</td>
                  <td>{e.actor}</td>
                  <td><Badge>{e.action}</Badge></td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="muted">No auth events yet.</p>
        )}
      </div>
    </DashboardShell>
  );
}
