"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import type { AuditEntry } from "@/lib/api";
import { authFetch } from "@/lib/auth";
import { formatDateTime } from "@/lib/datetime";
import type { Locale } from "@/i18n/routing";
import { DashboardShell, useOwnerNav } from "@/components/shell";
import { Badge, Spinner } from "@/components/ui";

export default function ActivityPage() {
  const t = useTranslations("dashboard");
  const locale = useLocale() as Locale;
  const nav = useOwnerNav();
  const [entries, setEntries] = useState<AuditEntry[] | null>(null);

  useEffect(() => {
    authFetch<{ entries: AuditEntry[] }>("/tenant/audit")
      .then((r) => setEntries(r.entries))
      .catch(() => setEntries([]));
  }, []);

  return (
    <DashboardShell title={t("nav.activity")} nav={nav}>
      <p style={{ marginTop: "-1rem" }}>{t("activity.intro")}</p>
      <div className="card">
        {entries === null ? (
          <Spinner />
        ) : entries.length === 0 ? (
          <p className="muted">{t("activity.empty")}</p>
        ) : (
          <table className="table">
            <thead><tr><th>{t("common.when")}</th><th>{t("activity.colActor")}</th><th>{t("activity.colAction")}</th><th>{t("activity.colDetail")}</th></tr></thead>
            <tbody>
              {entries.map((e, i) => (
                <tr key={i}>
                  <td className="muted">{formatDateTime(e.created_at, locale)}</td>
                  <td>{e.actor}</td>
                  <td><Badge>{e.action}</Badge></td>
                  <td className="muted" style={{ fontSize: "0.8rem" }}>
                    {Object.keys(e.detail ?? {}).length ? JSON.stringify(e.detail) : "—"}
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
