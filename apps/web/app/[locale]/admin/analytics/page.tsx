"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import type { AnalyticsBundle } from "@/lib/api";
import { authFetch } from "@/lib/auth";
import { formatNumber } from "@/lib/datetime";
import type { Locale } from "@/i18n/routing";
import { DashboardShell, useAdminNav } from "@/components/shell";
import { Field, Spinner, Stat } from "@/components/ui";

interface TenantRow { id: string; name: string }

export default function AdminAnalytics() {
  const t = useTranslations("admin");
  const locale = useLocale() as Locale;
  const nav = useAdminNav();
  const [tenants, setTenants] = useState<TenantRow[]>([]);
  const [selected, setSelected] = useState("");
  const [data, setData] = useState<AnalyticsBundle | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    authFetch<{ tenants: TenantRow[] }>("/admin/tenants")
      .then((r) => {
        setTenants(r.tenants);
        if (r.tenants[0]) setSelected(r.tenants[0].id);
      })
      .catch(() => setTenants([]));
  }, []);

  useEffect(() => {
    if (!selected) return;
    setLoading(true);
    authFetch<AnalyticsBundle>(`/admin/analytics?tenant=${encodeURIComponent(selected)}`)
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [selected]);

  const fd = data?.four_dimensions;
  const pct = (v: number) => formatNumber(v, locale, { style: "percent", maximumFractionDigits: 0 });

  return (
    <DashboardShell title={t("analytics.title")} nav={nav} requireAdmin loginHref="/admin/login">
      <p style={{ marginTop: "-1rem" }}>{t("analytics.intro")}</p>

      <div className="card" style={{ marginBottom: "1.5rem", maxWidth: 420 }}>
        <Field label={t("common.tenant")}>
          <select className="input" value={selected} onChange={(e) => setSelected(e.target.value)}>
            {tenants.length === 0 ? <option value="">{t("common.noTenants")}</option> : null}
            {tenants.map((tn) => (
              <option key={tn.id} value={tn.id}>{tn.name}</option>
            ))}
          </select>
        </Field>
      </div>

      {loading ? (
        <Spinner />
      ) : (
        <>
          <div className="stat-grid" style={{ marginBottom: "1.5rem" }}>
            <Stat label={t("common.latencyP95")} value={fd?.latency?.p95_ms != null ? `${formatNumber(fd.latency.p95_ms, locale)} ${t("common.ms")}` : "—"} />
            <Stat label={t("common.noPaidShare")} value={fd?.cost?.no_paid_share != null ? pct(fd.cost.no_paid_share) : "—"} />
            <Stat label={t("common.costCredits")} value={fd?.cost?.total != null ? formatNumber(fd.cost.total, locale) : "—"} />
            <Stat label={t("common.assistantTurns")} value={fd?.reliability?.turns != null ? formatNumber(fd.reliability.turns, locale) : "—"} />
          </div>
          <div className="card">
            <h3>{t("common.zeroTitle")}</h3>
            {data?.zero_results?.length ? (
              <table className="table">
                <thead><tr><th>{t("common.query")}</th><th>{t("common.count")}</th></tr></thead>
                <tbody>{data.zero_results.map((z) => <tr key={z.term}><td>{z.term}</td><td>{formatNumber(z.count, locale)}</td></tr>)}</tbody>
              </table>
            ) : (
              <p className="muted">{t("analytics.zeroEmpty")}</p>
            )}
          </div>
        </>
      )}
    </DashboardShell>
  );
}
