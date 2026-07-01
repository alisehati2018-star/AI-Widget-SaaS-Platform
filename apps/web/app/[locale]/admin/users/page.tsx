"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import type { AdminUser } from "@/lib/api";
import { adminFetch as authFetch } from "@/lib/auth";
import { formatNumber } from "@/lib/datetime";
import { useAdminResource as useResource } from "@/lib/hooks/useResource";
import type { Locale } from "@/i18n/routing";
import { DashboardShell, useAdminNav } from "@/components/shell";
import { Alert, Badge, Input, Spinner } from "@/components/ui";

interface UserPage {
  users: AdminUser[];
  total: number;
  limit: number;
  offset: number;
}

const PAGE = 25;

export default function AdminUsers() {
  const t = useTranslations("admin");
  const locale = useLocale() as Locale;
  const nav = useAdminNav();
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);

  const [q, setQ] = useState("");
  const [debouncedQ, setDebouncedQ] = useState("");
  const [role, setRole] = useState("");
  const [status, setStatus] = useState("");
  const [offset, setOffset] = useState(0);

  useEffect(() => {
    const id = setTimeout(() => { setDebouncedQ(q.trim()); setOffset(0); }, 300);
    return () => clearTimeout(id);
  }, [q]);

  const params = new URLSearchParams({ limit: String(PAGE), offset: String(offset) });
  if (debouncedQ) params.set("q", debouncedQ);
  if (role) params.set("role", role);
  if (status) params.set("status", status);
  const { data, error: loadError, loading, reload } = useResource<UserPage>(`/admin/users?${params.toString()}`);
  const users = loading ? null : (data?.users ?? []);
  const total = data?.total ?? 0;

  async function setUserStatus(email: string, nextStatus: string) {
    setError(null);
    setNote(null);
    try {
      await authFetch(`/admin/users/${encodeURIComponent(email)}/status`, { body: { status: nextStatus } });
      reload();
    } catch {
      setError(t("users.statusChangeFailed"));
    }
  }

  async function setUserRole(user: AdminUser, nextRole: string) {
    setError(null);
    setNote(null);
    if (nextRole === user.role) return;
    try {
      await authFetch(`/admin/users/${encodeURIComponent(user.email)}/role`, { body: { role: nextRole } });
      setNote(t("users.roleChanged"));
      reload();
    } catch {
      setError(t("users.roleChangeFailed"));
    }
  }

  const roleLabel = (r: string) =>
    r === "store_owner" ? t("users.roleStoreOwner") : t("users.roleStoreStaff");

  return (
    <DashboardShell title={t("users.title")} nav={nav} requireAdmin loginHref="/admin/login">
      <p style={{ marginTop: "-1rem" }}>{t("users.intro")}</p>
      {note ? <Alert kind="success">{note}</Alert> : null}
      {error ? <Alert kind="error">{error}</Alert> : null}
      <div className="card">
        <div className="row" style={{ flexWrap: "wrap", gap: ".6rem", marginBottom: "1rem" }}>
          <Input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder={t("users.searchPlaceholder")}
            style={{ flex: 1, minWidth: 220 }}
          />
          <select className="input" style={{ width: "auto" }} value={role} onChange={(e) => { setRole(e.target.value); setOffset(0); }}>
            <option value="">{t("users.filterAllRoles")}</option>
            <option value="store_owner">{t("users.roleStoreOwner")}</option>
            <option value="store_staff">{t("users.roleStoreStaff")}</option>
          </select>
          <select className="input" style={{ width: "auto" }} value={status} onChange={(e) => { setStatus(e.target.value); setOffset(0); }}>
            <option value="">{t("users.filterAllStatuses")}</option>
            <option value="active">{t("common.active")}</option>
            <option value="suspended">{t("users.statusSuspended")}</option>
          </select>
        </div>

        {loadError ? <p className="muted">{t("common.loadError")}: {loadError}</p> : null}
        {users === null ? (
          <Spinner />
        ) : (
          <>
            <table className="table">
              <thead><tr>
                <th>{t("users.colEmail")}</th><th>{t("users.colRole")}</th><th>{t("users.colTenant")}</th>
                <th>{t("users.colStatus")}</th><th>{t("users.colActions")}</th>
              </tr></thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.email}>
                    <td>{u.email}</td>
                    <td><Badge>{roleLabel(u.role)}</Badge></td>
                    <td className="muted">{u.tenant}</td>
                    <td>{u.status === "active" ? <Badge tone="success">{t("common.active")}</Badge> : <Badge tone="warning">{u.status}</Badge>}</td>
                    <td>
                      <div className="row" style={{ flexWrap: "wrap", gap: ".4rem" }}>
                        <select
                          className="input"
                          style={{ width: "auto", padding: "0.4rem 0.6rem" }}
                          value={u.role}
                          disabled={!u.has_tenant}
                          onChange={(e) => void setUserRole(u, e.target.value)}
                        >
                          <option value="store_owner">{t("users.roleStoreOwner")}</option>
                          <option value="store_staff">{t("users.roleStoreStaff")}</option>
                        </select>
                        {u.status === "active" ? (
                          <button className="btn btn-danger" onClick={() => void setUserStatus(u.email, "suspended")}>{t("users.suspend")}</button>
                        ) : (
                          <button className="btn btn-soft" onClick={() => void setUserStatus(u.email, "active")}>{t("users.activate")}</button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {users.length === 0 ? <p className="muted">{t("users.noMatches")}</p> : null}
            <div className="row-between" style={{ marginTop: "1rem" }}>
              <span className="hint">
                {t("users.pageInfo", {
                  from: formatNumber(total === 0 ? 0 : offset + 1, locale),
                  to: formatNumber(Math.min(offset + PAGE, total), locale),
                  total: formatNumber(total, locale),
                })}
              </span>
              <div className="row" style={{ gap: ".4rem" }}>
                <button className="btn btn-soft" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE))}>
                  {t("users.prev")}
                </button>
                <button className="btn btn-soft" disabled={offset + PAGE >= total} onClick={() => setOffset(offset + PAGE)}>
                  {t("users.next")}
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </DashboardShell>
  );
}
