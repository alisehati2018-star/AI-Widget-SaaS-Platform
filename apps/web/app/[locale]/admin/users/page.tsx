"use client";

import { useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";
import type { AdminUser } from "@/lib/api";
import { authFetch } from "@/lib/auth";
import { DashboardShell, useAdminNav } from "@/components/shell";
import { Badge, Spinner } from "@/components/ui";

export default function AdminUsers() {
  const t = useTranslations("admin");
  const nav = useAdminNav();
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

  const roleLabel = (role: string) =>
    role === "platform_admin"
      ? t("users.rolePlatformAdmin")
      : role === "store_owner"
        ? t("users.roleStoreOwner")
        : t("users.roleStoreStaff");

  return (
    <DashboardShell title={t("users.title")} nav={nav} requireAdmin loginHref="/admin/login">
      <p style={{ marginTop: "-1rem" }}>{t("users.intro")}</p>
      <div className="card">
        {error ? <p className="muted">{t("common.loadError")}: {error}</p> : null}
        {users === null ? (
          <Spinner />
        ) : (
          <table className="table">
            <thead><tr><th>{t("users.colEmail")}</th><th>{t("users.colRole")}</th><th>{t("users.colTenant")}</th><th>{t("users.colStatus")}</th><th></th></tr></thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.email}>
                  <td>{u.email}</td>
                  <td><Badge tone={u.role === "platform_admin" ? "brand" : undefined}>{roleLabel(u.role)}</Badge></td>
                  <td className="muted">{u.tenant}</td>
                  <td>{u.status === "active" ? <Badge tone="success">{t("common.active")}</Badge> : <Badge tone="warning">{u.status}</Badge>}</td>
                  <td>
                    {u.role !== "platform_admin" ? (
                      u.status === "active" ? (
                        <button className="btn btn-danger" onClick={() => void setStatus(u.email, "suspended")}>{t("users.suspend")}</button>
                      ) : (
                        <button className="btn btn-soft" onClick={() => void setStatus(u.email, "active")}>{t("users.activate")}</button>
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
