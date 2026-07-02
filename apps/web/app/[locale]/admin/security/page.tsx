"use client";

import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";
import { ApiError } from "@/lib/api";
import { adminFetch as authFetch } from "@/lib/auth";
import { formatDateTime, formatNumber } from "@/lib/datetime";
import { useAdminResource as useResource } from "@/lib/hooks/useResource";
import type { Locale } from "@/i18n/routing";
import { DashboardShell, useAdminNav } from "@/components/shell";
import { Alert, Badge, Spinner, Stat } from "@/components/ui";

interface Locked {
  email: string;
  plane: "customer" | "admin";
  failed_logins: number;
  locked_until: string | null;
}
interface AuthEvent { actor: string; action: string; created_at: string | null }
interface SecResp {
  locked_accounts: Locked[];
  accounts_with_failures: number;
  recent_auth_events: AuthEvent[];
}

export default function AdminSecurity() {
  const t = useTranslations("admin");
  const locale = useLocale() as Locale;
  const nav = useAdminNav();
  const { data, reload } = useResource<SecResp>("/admin/security");
  const [note, setNote] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const num = (n: number | undefined) => (n != null ? formatNumber(n, locale) : "—");

  async function unlock(account: Locked) {
    setNote(null);
    setError(null);
    setBusy(account.email);
    try {
      await authFetch("/admin/security/unlock", {
        body: { email: account.email, plane: account.plane },
      });
      setNote(t("security.unlocked", { email: account.email }));
      reload();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : t("security.unlockFailed"));
    } finally {
      setBusy(null);
    }
  }

  return (
    <DashboardShell title={t("security.title")} nav={nav} requireAdmin loginHref="/admin/login">
      <p style={{ marginTop: "-1rem" }}>{t("security.intro")}</p>
      {note ? <Alert kind="success">{note}</Alert> : null}
      {error ? <Alert kind="error">{error}</Alert> : null}
      <div className="stat-grid" style={{ marginBottom: "2rem" }}>
        <Stat label={t("security.lockedAccounts")} value={num(data?.locked_accounts.length)} />
        <Stat label={t("security.accountsWithFailures")} value={num(data?.accounts_with_failures)} />
        <Stat label={t("security.recentAuthEvents")} value={num(data?.recent_auth_events.length)} />
      </div>

      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <h3>{t("security.lockedTitle")}</h3>
        {data === null ? <Spinner /> : data.locked_accounts.length === 0 ? (
          <p className="muted">{t("security.noLocked")}</p>
        ) : (
          <table className="table">
            <thead><tr>
              <th>{t("security.colEmail")}</th><th>{t("security.colPlane")}</th>
              <th>{t("security.colFailed")}</th><th>{t("security.colLockedUntil")}</th><th></th>
            </tr></thead>
            <tbody>
              {data.locked_accounts.map((l) => (
                <tr key={`${l.plane}:${l.email}`}>
                  <td dir="ltr">{l.email}</td>
                  <td>
                    <Badge tone={l.plane === "admin" ? "brand" : undefined}>
                      {l.plane === "admin" ? t("security.planeAdmin") : t("security.planeCustomer")}
                    </Badge>
                  </td>
                  <td><Badge tone="warning">{formatNumber(l.failed_logins, locale)}</Badge></td>
                  <td className="muted">{formatDateTime(l.locked_until, locale)}</td>
                  <td>
                    <button className="btn btn-soft" disabled={busy !== null} onClick={() => void unlock(l)}>
                      {busy === l.email ? <Spinner /> : t("security.unlock")}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <p className="hint" style={{ marginTop: "1rem" }}>{t("security.unlockHint")}</p>
      </div>

      <div className="card">
        <h3>{t("security.recentTitle")}</h3>
        {data?.recent_auth_events.length ? (
          <table className="table">
            <thead><tr><th>{t("common.when")}</th><th>{t("common.actor")}</th><th>{t("common.action")}</th></tr></thead>
            <tbody>
              {data.recent_auth_events.map((e, i) => (
                <tr key={i}>
                  <td className="muted">{formatDateTime(e.created_at, locale)}</td>
                  <td>{e.actor}</td>
                  <td><Badge>{e.action}</Badge></td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="muted">{t("security.noEvents")}</p>
        )}
      </div>
    </DashboardShell>
  );
}
