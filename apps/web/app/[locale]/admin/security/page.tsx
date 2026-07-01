"use client";

import { useLocale, useTranslations } from "next-intl";
import { formatDateTime, formatNumber } from "@/lib/datetime";
import { useAdminResource as useResource } from "@/lib/hooks/useResource";
import type { Locale } from "@/i18n/routing";
import { DashboardShell, useAdminNav } from "@/components/shell";
import { Badge, Spinner, Stat } from "@/components/ui";

interface Locked { email: string; failed_logins: number; locked_until: string | null }
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
  const { data } = useResource<SecResp>("/admin/security");

  const num = (n: number | undefined) => (n != null ? formatNumber(n, locale) : "—");

  return (
    <DashboardShell title={t("security.title")} nav={nav} requireAdmin loginHref="/admin/login">
      <p style={{ marginTop: "-1rem" }}>{t("security.intro")}</p>
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
            <thead><tr><th>{t("security.colEmail")}</th><th>{t("security.colFailed")}</th><th>{t("security.colLockedUntil")}</th></tr></thead>
            <tbody>
              {data.locked_accounts.map((l) => (
                <tr key={l.email}>
                  <td>{l.email}</td>
                  <td><Badge tone="warning">{formatNumber(l.failed_logins, locale)}</Badge></td>
                  <td className="muted">{formatDateTime(l.locked_until, locale)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
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
