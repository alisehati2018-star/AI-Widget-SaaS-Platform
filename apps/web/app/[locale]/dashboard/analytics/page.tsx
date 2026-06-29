"use client";

import { useLocale, useTranslations } from "next-intl";
import type { AnalyticsBundle } from "@/lib/api";
import { formatNumber } from "@/lib/datetime";
import { useResource } from "@/lib/hooks/useResource";
import type { Locale } from "@/i18n/routing";
import { DashboardShell, useOwnerNav } from "@/components/shell";
import { Stat } from "@/components/ui";

export default function AnalyticsPage() {
  const t = useTranslations("dashboard");
  const locale = useLocale() as Locale;
  const nav = useOwnerNav();
  const { data } = useResource<AnalyticsBundle>("/tenant/analytics");

  const fd = data?.four_dimensions;
  const pct = (v: number) => formatNumber(v, locale, { style: "percent", maximumFractionDigits: 0 });

  return (
    <DashboardShell title={t("nav.analytics")} nav={nav}>
      <p style={{ marginTop: "-1rem" }}>{t("analytics.intro")}</p>
      <div className="stat-grid" style={{ marginBottom: "2rem" }}>
        <Stat
          label={t("analytics.latencyP95")}
          value={fd?.latency?.p95_ms != null ? `${formatNumber(fd.latency.p95_ms, locale)} ${t("analytics.ms")}` : "—"}
        />
        <Stat label={t("analytics.noPaidShare")} value={fd?.cost?.no_paid_share != null ? pct(fd.cost.no_paid_share) : "—"} />
        <Stat label={t("analytics.costCredits")} value={fd?.cost?.total != null ? formatNumber(fd.cost.total, locale) : "—"} />
        <Stat label={t("analytics.assistantTurns")} value={fd?.reliability?.turns != null ? formatNumber(fd.reliability.turns, locale) : "—"} />
      </div>

      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <h3>{t("analytics.mostWanted")}</h3>
        {data?.most_wanted?.length ? (
          <table className="table">
            <thead><tr><th>{t("common.query")}</th><th>{t("common.count")}</th></tr></thead>
            <tbody>
              {data.most_wanted.map((m) => (
                <tr key={m.term}><td>{m.term}</td><td>{formatNumber(m.count, locale)}</td></tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="muted">{t("analytics.mostWantedEmpty")}</p>
        )}
      </div>

      <div className="card">
        <h3>{t("analytics.zeroTitle")}</h3>
        <p className="hint">{t("analytics.zeroHint")}</p>
        {data?.zero_results?.length ? (
          <table className="table">
            <thead><tr><th>{t("common.query")}</th><th>{t("common.count")}</th></tr></thead>
            <tbody>
              {data.zero_results.map((z) => (
                <tr key={z.term}><td>{z.term}</td><td>{formatNumber(z.count, locale)}</td></tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="muted">{t("analytics.zeroEmpty")}</p>
        )}
      </div>
    </DashboardShell>
  );
}
