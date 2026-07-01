"use client";

import { useLocale, useTranslations } from "next-intl";
import type { AnalyticsBundle } from "@/lib/api";
import { formatNumber } from "@/lib/datetime";
import { useResource } from "@/lib/hooks/useResource";
import type { Locale } from "@/i18n/routing";
import { DashboardShell, useOwnerNav } from "@/components/shell";
import { Stat } from "@/components/ui";

interface DropOff { from: string; to: string; drop_rate: number }
interface Insight {
  funnel?: Record<string, number>;
  biggest_dropoff?: DropOff | null;
  headline?: string;
}

export default function AnalyticsPage() {
  const t = useTranslations("dashboard");
  const locale = useLocale() as Locale;
  const nav = useOwnerNav();
  const { data } = useResource<AnalyticsBundle>("/tenant/analytics");
  const { data: insightData } = useResource<{ insight: Insight }>("/tenant/insight");
  const insight = insightData?.insight;

  const fd = data?.four_dimensions;
  const pct = (v: number) => formatNumber(v, locale, { style: "percent", maximumFractionDigits: 0 });
  const funnelKeys = Object.keys(insight?.funnel ?? {});

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

      <div className="dash-2col">
        <div className="card-stack">
          <div className="card">
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
        </div>

        <div className="card-stack">
          <div className="card">
            <h3>{t("analytics.insightTitle")}</h3>
            {insight?.headline ? (
              <>
                <p>{insight.headline}</p>
                {insight.biggest_dropoff ? (
                  <>
                    <h4>{t("analytics.dropoffTitle")}</h4>
                    <p className="muted">
                      {insight.biggest_dropoff.from} → {insight.biggest_dropoff.to}: {pct(insight.biggest_dropoff.drop_rate)}
                    </p>
                  </>
                ) : null}
              </>
            ) : <p className="muted">{t("analytics.insightEmpty")}</p>}
          </div>
          <div className="card">
            <h3>{t("analytics.funnelTitle")}</h3>
            {funnelKeys.length ? (
              <table className="table">
                <thead><tr><th>{t("analytics.colStage")}</th><th>{t("common.count")}</th></tr></thead>
                <tbody>{funnelKeys.map((k) => <tr key={k}><td>{k}</td><td>{formatNumber(insight?.funnel?.[k] ?? 0, locale)}</td></tr>)}</tbody>
              </table>
            ) : <p className="muted">{t("analytics.funnelEmpty")}</p>}
          </div>
        </div>
      </div>
    </DashboardShell>
  );
}
