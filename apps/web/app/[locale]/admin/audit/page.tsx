"use client";

import { useLocale, useTranslations } from "next-intl";
import type { AuditEntry } from "@/lib/api";
import { formatDateTime } from "@/lib/datetime";
import { useAdminResource as useResource } from "@/lib/hooks/useResource";
import type { Locale } from "@/i18n/routing";
import { DashboardShell, useAdminNav } from "@/components/shell";
import { Badge, Spinner } from "@/components/ui";

export default function AdminAudit() {
  const t = useTranslations("admin");
  const locale = useLocale() as Locale;
  const nav = useAdminNav();
  const { data, error, loading } = useResource<{ entries: AuditEntry[] }>("/admin/audit");
  const entries = loading ? null : (data?.entries ?? []);

  return (
    <DashboardShell title={t("audit.title")} nav={nav} requireAdmin loginHref="/admin/login">
      <p style={{ marginTop: "-1rem" }}>{t("audit.intro")}</p>
      <div className="card">
        {error ? <p className="muted">{t("common.loadError")}: {error}</p> : null}
        {entries === null ? (
          <Spinner />
        ) : entries.length === 0 ? (
          <p className="muted">{t("audit.empty")}</p>
        ) : (
          <table className="table">
            <thead><tr><th>{t("common.when")}</th><th>{t("common.actor")}</th><th>{t("common.action")}</th><th>{t("audit.colDetail")}</th></tr></thead>
            <tbody>
              {entries.map((e, i) => (
                <tr key={i}>
                  <td className="muted">{formatDateTime(e.created_at, locale)}</td>
                  <td>{e.actor}</td>
                  <td><Badge>{e.action}</Badge></td>
                  <td className="muted" style={{ fontSize: "0.8rem" }}>
                    {Object.keys(e.detail).length ? JSON.stringify(e.detail) : "—"}
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
