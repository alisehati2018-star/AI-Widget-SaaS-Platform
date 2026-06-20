"use client";

import { useSession } from "../../../lib/auth";
import { ADMIN_NAV, DashboardShell } from "../../../components/shell";
import { Badge } from "../../../components/ui";

export default function AdminSettings() {
  const { user } = useSession();
  return (
    <DashboardShell title="Platform settings" nav={ADMIN_NAV} requireAdmin loginHref="/admin/login">
      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <h3>Your admin account</h3>
        <table className="table">
          <tbody>
            <tr><td className="muted">Email</td><td>{user?.email ?? "—"}</td></tr>
            <tr><td className="muted">Role</td><td><Badge tone="brand">platform admin</Badge></td></tr>
          </tbody>
        </table>
      </div>

      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <h3>Security</h3>
        <ul className="feature-list">
          <li>Admin access requires the platform-admin role (or the operator token for automation).</li>
          <li>All admin mutations are written to the append-only audit log.</li>
          <li>Sessions use short-lived access tokens with single-use rotating refresh tokens.</li>
          <li>Passwords are PBKDF2-hashed; failed logins trigger temporary lockout.</li>
        </ul>
        <p className="hint">2FA (TOTP) and IP allowlisting are on the security roadmap.</p>
      </div>

      <div className="card">
        <h3>Platform</h3>
        <p className="muted" style={{ marginBottom: 0 }}>
          Vitrin — on-premise, multi-tenant AI Commerce Intelligence Platform. Plans, credit limits and
          AI-gateway budgets are configured via the control plane and the <code>.env</code> secret store.
        </p>
      </div>
    </DashboardShell>
  );
}
