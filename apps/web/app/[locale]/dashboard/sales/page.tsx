"use client";

import { useLocale, useTranslations } from "next-intl";
import type { AnalyticsBundle } from "@/lib/api";
import { formatNumber } from "@/lib/datetime";
import { useResource } from "@/lib/hooks/useResource";
import type { Locale } from "@/i18n/routing";
import { DashboardShell, useOwnerNav } from "@/components/shell";
import { Stat } from "@/components/ui";

export default function ConversionPage() {
  const t = useTranslations("dashboard");
  const locale = useLocale() as Locale;
  const nav = useOwnerNav();
  const { data } = useResource<AnalyticsBundle>("/tenant/analytics");

  const funnel = data?.funnel ?? {};
  const keys = Object.keys(funnel);
  const num = (v: number | undefined) => (v != null ? formatNumber(v, locale) : "—");
  const ctr =
    funnel.search && funnel.click
      ? formatNumber(funnel.click / funnel.search, locale, { style: "percent", maximumFractionDigits: 0 })
      : "—";

  return (
    <DashboardShell title={t("nav.conversion")} nav={nav}>
      <p style={{ marginTop: "-1rem" }}>{t("conversion.intro")}</p>
      <div className="stat-grid" style={{ marginBottom: "2rem" }}>
        <Stat label={t("conversion.searches")} value={num(funnel.search ?? funnel.searches)} />
        <Stat label={t("conversion.clicks")} value={num(funnel.click ?? funnel.clicks)} />
        <Stat label={t("conversion.addToCart")} value={num(funnel.add_to_cart ?? funnel.cart)} />
        <Stat label={t("conversion.ctr")} value={ctr} />
      </div>
      <div className="card">
        <h3>{t("conversion.breakdown")}</h3>
        {keys.length ? (
          <table className="table">
            <thead><tr><th>{t("conversion.colStage")}</th><th>{t("common.count")}</th></tr></thead>
            <tbody>
              {keys.map((k) => (
                <tr key={k}><td>{k}</td><td>{formatNumber(funnel[k], locale)}</td></tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="muted">{t("conversion.empty")}</p>
        )}
      </div>
    </DashboardShell>
  );
}
