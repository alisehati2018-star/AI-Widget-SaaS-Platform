"use client";

import { useLocale, useTranslations } from "next-intl";
import type { Lead } from "@/lib/api";
import { authFetch } from "@/lib/auth";
import { formatDate, formatNumber } from "@/lib/datetime";
import { useResource } from "@/lib/hooks/useResource";
import type { Locale } from "@/i18n/routing";
import { DashboardShell, useOwnerNav } from "@/components/shell";
import { Badge, Spinner, Stat } from "@/components/ui";

export default function LeadsPage() {
  const t = useTranslations("dashboard");
  const locale = useLocale() as Locale;
  const nav = useOwnerNav();
  const { data, loading } = useResource<{ leads: Lead[] }>("/tenant/leads");
  const leads = loading ? null : (data?.leads ?? []);

  async function exportData() {
    const data = await authFetch<unknown>("/tenant/export").catch(() => null);
    if (!data) return;
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "vitrin-leads.json";
    a.click();
    URL.revokeObjectURL(url);
  }

  const withIntent = leads?.filter((l) => l.has_intent).length ?? 0;
  const num = (v: number | undefined) => (v != null ? formatNumber(v, locale) : "—");

  return (
    <DashboardShell title={t("nav.leads")} nav={nav}>
      <p style={{ marginTop: "-1rem" }}>{t("leads.intro")}</p>

      <div className="stat-grid" style={{ marginBottom: "1.5rem" }}>
        <Stat label={t("leads.total")} value={num(leads?.length)} />
        <Stat label={t("leads.withIntent")} value={formatNumber(withIntent, locale)} />
        <Stat label={t("leads.fromChat")} value={num(leads?.filter((l) => l.source === "chat").length)} />
        <Stat label={t("leads.withEmail")} value={num(leads?.filter((l) => l.email).length)} />
      </div>

      <div className="card">
        <div className="row-between" style={{ marginBottom: "1rem" }}>
          <h3 style={{ margin: 0 }}>{t("leads.captured")}</h3>
          <button className="btn btn-ghost" onClick={() => void exportData()}>
            {t("leads.exportJson")}
          </button>
        </div>
        {leads === null ? (
          <Spinner />
        ) : leads.length === 0 ? (
          <p className="muted">{t("leads.empty")}</p>
        ) : (
          <table className="table">
            <thead>
              <tr><th>{t("leads.colEmail")}</th><th>{t("leads.colPhone")}</th><th>{t("leads.colIntent")}</th><th>{t("leads.colSource")}</th><th>{t("common.when")}</th></tr>
            </thead>
            <tbody>
              {leads.map((l, i) => (
                <tr key={i}>
                  <td>{l.email ?? "—"}</td>
                  <td>{l.phone ?? "—"}</td>
                  <td>{l.has_intent ? <Badge tone="success">{t("common.yes")}</Badge> : <Badge>{t("common.no")}</Badge>}</td>
                  <td>{l.source}</td>
                  <td className="muted">{formatDate(l.created_at, locale)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </DashboardShell>
  );
}
