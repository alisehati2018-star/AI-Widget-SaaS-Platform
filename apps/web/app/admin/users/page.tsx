"use client";

import { useCallback, useEffect, useState } from "react";
import type { AdminUser } from "../../../lib/api";
import { authFetch } from "../../../lib/auth";
import { ADMIN_NAV, DashboardShell } from "../../../components/shell";
import { Badge, Spinner } from "../../../components/ui";

export default function AdminUsers() {
  const [users, setUsers] = useState<AdminUser[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    authFetch<{ users: AdminUser[] }>("/admin/users")
      .then((r) => setUsers(r.users))
      .catch((e) => setError(String(e.message ?? e)));
  }, []);
  useEffect(() => load(), [load]);

  async function setStatus(email: string, status: string) {
    await authFetch(`/admin/users/${encodeURIComponent(email)}/status`, { body: { status } }).catch(() => {});
    load();
  }

  return (
    <DashboardShell title="Users" nav={ADMIN_NAV} requireAdmin loginHref="/admin/login">
      <p style={{ marginTop: "-1rem" }}>Everyone with a login across the platform.</p>
      <div className="card">
        {error ? <p className="muted">Couldn&apos;t load users: {error}</p> : null}
        {users === null ? (
          <Spinner />
        ) : (
          <table className="table">
            <thead><tr><th>Email</th><th>Role</th><th>Tenant</th><th>Status</th><th></th></tr></thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.email}>
                  <td>{u.email}</td>
                  <td><Badge tone={u.role === "platform_admin" ? "brand" : undefined}>{u.role.replace("_", " ")}</Badge></td>
                  <td className="muted">{u.tenant}</td>
                  <td>{u.status === "active" ? <Badge tone="success">active</Badge> : <Badge tone="warning">{u.status}</Badge>}</td>
                  <td>
                    {u.role !== "platform_admin" ? (
                      u.status === "active" ? (
                        <button className="btn btn-danger" onClick={() => void setStatus(u.email, "suspended")}>Suspend</button>
                      ) : (
                        <button className="btn btn-soft" onClick={() => void setStatus(u.email, "active")}>Activate</button>
                      )
                    ) : null}
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
