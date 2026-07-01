"use client";

import { useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";
import type { AdminUser } from "@/lib/api";
import { authFetch } from "@/lib/auth";
import { DashboardShell, useAdminNav } from "@/components/shell";
import { Alert, Badge, Spinner } from "@/components/ui";

export default function AdminUsers() {
  const t = useTranslations("admin");
  const nav = useAdminNav();
  const [users, setUsers] = useState<AdminUser[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);

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

  async function setRole(user: AdminUser, role: string) {
    setError(null);
    setNote(null);
    if (role === user.role) return;
    const confirmMsg =
      role === "platform_admin"
        ? t("users.confirmPromote", { email: user.email })
        : t("users.confirmDemote", { email: user.email });
    if (!window.confirm(confirmMsg)) return;
    try {
      await authFetch(`/admin/users/${encodeURIComponent(user.email)}/role`, { body: { role } });
      setNote(t("users.roleChanged"));
      load();
    } catch {
      setError(t("users.roleChangeFailed"));
    }
  }

  const roleLabel = (role: string) =>
    role === "platform_admin"
      ? t("users.rolePlatformAdmin")
      : role === "store_owner"
        ? t("users.roleStoreOwner")
        : t("users.roleStoreStaff");

  return (
    <DashboardShell title={t("users.title")} nav={nav} requireAdmin loginHref="/admin/login">
      <p style={{ marginTop: "-1rem" }}>{t("users.intro")}</p>
      {note ? <Alert kind="success">{note}</Alert> : null}
      {error ? <Alert kind="error">{error}</Alert> : null}
      <div className="card">
        {users === null ? (
          <Spinner />
        ) : (
          <table className="table">
            <thead><tr>
              <th>{t("users.colEmail")}</th><th>{t("users.colRole")}</th><th>{t("users.colTenant")}</th>
              <th>{t("users.colStatus")}</th><th>{t("users.colActions")}</th>
            </tr></thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.email}>
                  <td>{u.email}</td>
                  <td><Badge tone={u.role === "platform_admin" ? "brand" : undefined}>{roleLabel(u.role)}</Badge></td>
                  <td className="muted">{u.tenant}</td>
                  <td>{u.status === "active" ? <Badge tone="success">{t("common.active")}</Badge> : <Badge tone="warning">{u.status}</Badge>}</td>
                  <td>
                    <div className="row" style={{ flexWrap: "wrap", gap: ".4rem" }}>
                      <select
                        className="input"
                        style={{ width: "auto", padding: "0.4rem 0.6rem" }}
                        value={u.role}
                        disabled={u.role !== "platform_admin" && !u.has_tenant}
                        onChange={(e) => void setRole(u, e.target.value)}
                      >
                        <option value="platform_admin">{t("users.rolePlatformAdmin")}</option>
                        <option value="store_owner" disabled={!u.has_tenant}>{t("users.roleStoreOwner")}</option>
                        <option value="store_staff" disabled={!u.has_tenant}>{t("users.roleStoreStaff")}</option>
                      </select>
                      {u.role !== "platform_admin" ? (
                        u.status === "active" ? (
                          <button className="btn btn-danger" onClick={() => void setStatus(u.email, "suspended")}>{t("users.suspend")}</button>
                        ) : (
                          <button className="btn btn-soft" onClick={() => void setStatus(u.email, "active")}>{t("users.activate")}</button>
                        )
                      ) : null}
                    </div>
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
