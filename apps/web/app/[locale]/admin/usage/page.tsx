"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { formatDateTime, formatNumber } from "@/lib/datetime";
import { useAdminResource as useResource } from "@/lib/hooks/useResource";
import type { Locale } from "@/i18n/routing";
import { DashboardShell, useAdminNav } from "@/components/shell";
import { Input, Spinner, Stat } from "@/components/ui";

interface UsageEvent {
  occurred_at: string | null;
  tenant: string;
  route: string | null;
  rung: string;
  tokens_in: number;
  tokens_out: number;
  cache_outcome: string | null;
  latency_ms: number | null;
  cost: number;
}
interface Usage {
  calls: number;
  tokens_in: number;
  tokens_out: number;
  cost: number;
  credits_spent: number;
  by_rung: { rung: string; count: number }[];
  events: UsageEvent[];
  days: number;
}

const RUNGS = ["L1", "L2", "L3", "L4", "unknown"];
const DAY_RANGES = [7, 30, 90];

export default function AdminUsage() {
  const t = useTranslations("admin");
  const locale = useLocale() as Locale;
  const nav = useAdminNav();

  const [tenant, setTenant] = useState("");
  const [debouncedTenant, setDebouncedTenant] = useState("");
  const [route, setRoute] = useState("");
  const [debouncedRoute, setDebouncedRoute] = useState("");
  const [rung, setRung] = useState("");
  const [days, setDays] = useState(30);

  useEffect(() => {
    const id = setTimeout(() => {
      setDebouncedTenant(tenant.trim());
      setDebouncedRoute(route.trim());
    }, 300);
    return () => clearTimeout(id);
  }, [tenant, route]);

  const params = new URLSearchParams({ days: String(days) });
  if (debouncedTenant) params.set("tenant", debouncedTenant);
  if (debouncedRoute) params.set("route", debouncedRoute);
  if (rung) params.set("rung", rung);
  const { data, error, loading } = useResource<Usage>(`/admin/usage?${params.toString()}`);

  const num = (n: number | undefined) => (n != null ? formatNumber(Math.round(n), locale) : "—");
  const csvHref = `/api/admin/usage?${params.toString()}&fmt=csv`;

  return (
    <DashboardShell title={t("usage.title")} nav={nav} requireAdmin loginHref="/admin/login">
      <p style={{ marginTop: "-1rem" }}>{t("usage.intro")}</p>

      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <div className="row" style={{ flexWrap: "wrap", gap: ".6rem" }}>
          <Input value={tenant} onChange={(e) => setTenant(e.target.value)} placeholder={t("usage.filterTenant")} style={{ flex: 1, minWidth: 170 }} />
          <Input value={route} onChange={(e) => setRoute(e.target.value)} placeholder={t("usage.filterRoute")} style={{ flex: 1, minWidth: 150 }} dir="ltr" />
          <select className="input" style={{ width: "auto" }} aria-label={t("usage.filterAllRungs")} value={rung} onChange={(e) => setRung(e.target.value)}>
            <option value="">{t("usage.filterAllRungs")}</option>
            {RUNGS.map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
          <select className="input" style={{ width: "auto" }} aria-label={t("usage.rangeDays", { days: formatNumber(days, locale) })} value={days} onChange={(e) => setDays(Number(e.target.value))}>
            {DAY_RANGES.map((d) => <option key={d} value={d}>{t("usage.rangeDays", { days: formatNumber(d, locale) })}</option>)}
          </select>
          <a className="btn btn-soft" href={csvHref} download>{t("usage.exportCsv")}</a>
        </div>
      </div>

      <div className="stat-grid" style={{ marginBottom: "1.5rem" }}>
        <Stat label={t("usage.modelCalls")} value={num(data?.calls)} />
        <Stat label={t("usage.tokensIn")} value={num(data?.tokens_in)} />
        <Stat label={t("usage.tokensOut")} value={num(data?.tokens_out)} />
        <Stat label={t("usage.creditsSpent")} value={num(data?.credits_spent)} />
      </div>

      <div className="dash-2col">
        <div className="card">
          <h3>{t("usage.recentEvents")}</h3>
          {error ? <p className="muted">{t("common.loadError")}: {error}</p> : null}
          {loading || !data ? <Spinner /> : data.events.length === 0 ? (
            <p className="muted">{t("usage.empty")}</p>
          ) : (
            <table className="table">
              <thead><tr>
                <th>{t("common.when")}</th><th>{t("usage.colTenant")}</th><th>{t("usage.colRoute")}</th>
                <th>{t("common.colRung")}</th><th>{t("usage.colLatency")}</th><th>{t("usage.colCost")}</th>
              </tr></thead>
              <tbody>
                {data.events.map((e, i) => (
                  <tr key={i}>
                    <td className="muted">{formatDateTime(e.occurred_at, locale)}</td>
                    <td>{e.tenant}</td>
                    <td className="muted" dir="ltr">{e.route ?? "—"}</td>
                    <td>{e.rung}</td>
                    <td className="muted">{e.latency_ms != null ? `${formatNumber(e.latency_ms, locale)} ${t("common.ms")}` : "—"}</td>
                    <td className="muted">{formatNumber(e.cost, locale, { maximumFractionDigits: 4 })}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <div className="card">
          <h3>{t("usage.byRung")}</h3>
          {!data ? <Spinner /> : data.by_rung.length === 0 ? (
            <p className="muted">{t("usage.empty")}</p>
          ) : (
            <table className="table">
              <thead><tr><th>{t("common.colRung")}</th><th>{t("common.colCalls")}</th></tr></thead>
              <tbody>{data.by_rung.map((r) => <tr key={r.rung}><td>{r.rung}</td><td>{formatNumber(r.count, locale)}</td></tr>)}</tbody>
            </table>
          )}
          <p className="hint" style={{ marginTop: "1rem" }}>{t("usage.rungHint")}</p>
        </div>
      </div>
    </DashboardShell>
  );
}
