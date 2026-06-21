"use client";

import { useEffect, useState } from "react";
import type { AdminUser } from "../../../lib/api";
import { authFetch } from "../../../lib/auth";
import { ADMIN_NAV, DashboardShell } from "../../../components/shell";
import { Badge, Spinner } from "../../../components/ui";

export default function AdminUsers() {
  const [users, setUsers] = useState<AdminUser[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    authFetch<{ users: AdminUser[] }>("/admin/users")
      .then((r) => setUsers(r.users))
      .catch((e) => setError(String(e.message ?? e)));
  }, []);

  return (
    <DashboardShell title="Users" nav={ADMIN_NAV} requireAdmin loginHref="/admin/login">
      <p style={{ marginTop: "-1rem" }}>Everyone with a login across the platform.</p>
      <div className="card">
        {error ? <p className="muted">Couldn&apos;t load users: {error}</p> : null}
        {users === null ? (
          <Spinner />
        ) : (
          <table className="table">
            <thead><tr><th>Email</th><th>Name</th><th>Role</th><th>Tenant</th><th>Status</th><th>Last login</th></tr></thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.email}>
                  <td>{u.email}</td>
                  <td>{u.full_name ?? "—"}</td>
                  <td><Badge tone={u.role === "platform_admin" ? "brand" : undefined}>{u.role.replace("_", " ")}</Badge></td>
                  <td className="muted">{u.tenant}</td>
                  <td>{u.status === "active" ? <Badge tone="success">active</Badge> : <Badge tone="warning">{u.status}</Badge>}</td>
                  <td className="muted">{u.last_login_at?.slice(0, 10) ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </DashboardShell>
  );
}
