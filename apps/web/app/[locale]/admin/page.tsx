"use client";

import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";
import { Link } from "@/i18n/navigation";
import { formatDate, formatNumber } from "@/lib/datetime";
import { useAdminResource as useResource } from "@/lib/hooks/useResource";
import type { Locale } from "@/i18n/routing";
import { DashboardShell, useAdminNav } from "@/components/shell";
import { TrendChart, type TrendPoint } from "@/components/trend-chart";
import { Spinner, Stat } from "@/components/ui";

type RawPoint = { date: string } & Record<string, number | string>;

interface Overview {
  tenants: number;
  users: number;
  active_subscriptions: number;
  past_due_subscriptions: number;
  mrr: number;
  days: number;
  trends: {
    signups: RawPoint[];
    usage: RawPoint[];
    revenue: RawPoint[];
    failed_payments: RawPoint[];
  };
  totals: { signups: number; calls: number; revenue: number; failed_payments: number };
}

const RANGES = [7, 30, 90] as const;

export default function AdminOverview() {
  const t = useTranslations("admin");
  const locale = useLocale() as Locale;
  const nav = useAdminNav();
  const [days, setDays] = useState<number>(30);
  const { data, error, loading } = useResource<Overview>(`/admin/overview?days=${days}`);

  const num = (n: number | undefined) => (n != null ? formatNumber(n, locale) : "—");
  const fmtDay = (iso: string) => formatDate(iso, locale);
  const series = (rows: RawPoint[], field: string): TrendPoint[] =>
    rows.map((r) => ({ date: r.date, value: Number(r[field] ?? 0) }));

  const trendCards = data
    ? [
        {
          key: "signups",
          title: t("overview.trendSignups"),
          total: num(data.totals.signups),
          data: series(data.trends.signups, "signups"),
        },
        {
          key: "usage",
          title: t("overview.trendUsage"),
          total: num(data.totals.calls),
          data: series(data.trends.usage, "calls"),
        },
        {
          key: "revenue",
          title: t("overview.trendRevenue"),
          total: `$${num(Math.round(data.totals.revenue))}`,
          data: series(data.trends.revenue, "revenue"),
        },
        {
          key: "failed",
          title: t("overview.trendFailed"),
          total: num(data.totals.failed_payments),
          data: series(data.trends.failed_payments, "failed"),
        },
      ]
    : [];

  return (
    <DashboardShell title={t("overview.title")} nav={nav} requireAdmin loginHref="/admin/login">
      <div className="row-between" style={{ marginTop: "-1rem", marginBottom: "1.5rem", flexWrap: "wrap", gap: ".75rem" }}>
        <p style={{ margin: 0 }}>{t("overview.intro")}</p>
        <div className="row" style={{ gap: ".35rem" }}>
          {RANGES.map((r) => (
            <button
              key={r}
              className={`btn ${days === r ? "btn-primary" : "btn-soft"}`}
              style={{ padding: "0.4rem 0.8rem" }}
              onClick={() => setDays(r)}
            >
              {t("overview.rangeDays", { n: formatNumber(r, locale) })}
            </button>
          ))}
        </div>
      </div>

      <div className="stat-grid" style={{ marginBottom: "1.5rem" }}>
        <Stat label={t("overview.tenants")} value={num(data?.tenants)} />
        <Stat label={t("overview.users")} value={num(data?.users)} />
        <Stat label={t("overview.activeSubs")} value={num(data?.active_subscriptions)} />
        <Stat label={t("overview.mrr")} value={data ? `$${formatNumber(Math.round(data.mrr), locale)}` : "—"} />
      </div>

      {error ? (
        <div className="card" style={{ marginBottom: "1.5rem" }}>
          <p className="muted" style={{ margin: 0 }}>{t("common.loadError")}: {error}</p>
        </div>
      ) : loading ? (
        <div className="card" style={{ marginBottom: "1.5rem" }}><Spinner /></div>
      ) : (
        <div className="dash-2col-even" style={{ marginBottom: "1.5rem" }}>
          {trendCards.map((c) => (
            <div className="card" key={c.key}>
              <div className="row-between" style={{ marginBottom: ".5rem" }}>
                <h3 style={{ margin: 0, fontSize: "0.95rem" }}>{c.title}</h3>
                <strong style={{ fontSize: "1.25rem" }}>{c.total}</strong>
              </div>
              <TrendChart
                data={c.data}
                label={c.title}
                formatValue={(v) => (c.key === "revenue" ? `$${num(Math.round(v))}` : num(v))}
                formatDate={fmtDay}
              />
            </div>
          ))}
        </div>
      )}

      {data && data.past_due_subscriptions > 0 ? (
        <div className="alert alert-error" style={{ marginBottom: "1.5rem" }}>
          {t("overview.pastDueWarning", { n: formatNumber(data.past_due_subscriptions, locale) })}
        </div>
      ) : null}

      <div className="card">
        <h3>{t("overview.quickLinksTitle")}</h3>
        <div className="row" style={{ flexWrap: "wrap", gap: ".5rem" }}>
          <Link className="btn btn-soft" href="/admin/tenants">{t("nav.tenants")}</Link>
          <Link className="btn btn-soft" href="/admin/billing">{t("nav.billing")}</Link>
          <Link className="btn btn-soft" href="/admin/health">{t("nav.health")}</Link>
          <Link className="btn btn-soft" href="/admin/elasticsearch">{t("nav.elasticsearch")}</Link>
        </div>
      </div>
    </DashboardShell>
  );
}
