"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { ApiError, type AnalyticsBundle } from "@/lib/api";
import { adminFetch as authFetch } from "@/lib/auth";
import { formatNumber } from "@/lib/datetime";
import type { Locale } from "@/i18n/routing";
import { DashboardShell, useAdminNav } from "@/components/shell";
import { Alert, Spinner, Stat } from "@/components/ui";

interface TenantRow { id: string; name: string }
interface DropOff { from: string; to: string; drop_rate: number; from_count: number }
interface Insight {
  demand_gaps?: { term: string; count: number }[];
  funnel?: Record<string, number>;
  dropoffs?: DropOff[];
  biggest_dropoff?: DropOff | null;
  headline?: string;
}
interface AnalystResult {
  answer: string;
  narrated_by: "template" | "llm";
}

export default function AdminAnalytics() {
  const t = useTranslations("admin");
  const locale = useLocale() as Locale;
  const nav = useAdminNav();
  const [tenants, setTenants] = useState<TenantRow[]>([]);
  const [selected, setSelected] = useState("");
  const [data, setData] = useState<AnalyticsBundle | null>(null);
  const [insight, setInsight] = useState<Insight | null>(null);
  const [loading, setLoading] = useState(false);
  const [question, setQuestion] = useState("");
  const [analyst, setAnalyst] = useState<AnalystResult | null>(null);
  const [analystBusy, setAnalystBusy] = useState(false);
  const [analystError, setAnalystError] = useState<string | null>(null);

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
    setAnalyst(null);
    Promise.all([
      authFetch<AnalyticsBundle>(`/admin/analytics?tenant=${encodeURIComponent(selected)}`),
      authFetch<{ insight: Insight }>(`/admin/insight?tenant=${encodeURIComponent(selected)}`),
    ])
      .then(([a, i]) => { setData(a); setInsight(i.insight); })
      .catch(() => { setData(null); setInsight(null); })
      .finally(() => setLoading(false));
  }, [selected]);

  async function ask() {
    if (!question.trim() || !selected) return;
    setAnalystBusy(true);
    setAnalystError(null);
    try {
      const r = await authFetch<AnalystResult>(`/admin/analyst?tenant=${encodeURIComponent(selected)}`, {
        body: { question: question.trim() },
      });
      setAnalyst(r);
    } catch (e) {
      setAnalystError(e instanceof ApiError ? e.message : t("analytics.analystEmpty"));
    } finally {
      setAnalystBusy(false);
    }
  }

  const fd = data?.four_dimensions;
  const pct = (v: number) => formatNumber(v, locale, { style: "percent", maximumFractionDigits: 0 });
  const funnelKeys = Object.keys(insight?.funnel ?? {});

  return (
    <DashboardShell title={t("analytics.title")} nav={nav} requireAdmin loginHref="/admin/login">
      <div className="row-between" style={{ marginTop: "-1rem", marginBottom: "1.5rem", flexWrap: "wrap", gap: ".75rem" }}>
        <p style={{ margin: 0 }}>{t("analytics.intro")}</p>
        <select className="input" style={{ maxWidth: 260 }} value={selected} onChange={(e) => setSelected(e.target.value)}>
          {tenants.length === 0 ? <option value="">{t("common.noTenants")}</option> : null}
          {tenants.map((tn) => <option key={tn.id} value={tn.id}>{tn.name}</option>)}
        </select>
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

          <div className="dash-2col" style={{ marginBottom: "1.5rem" }}>
            <div className="card-stack">
              <div className="card">
                <h3>{t("analytics.mostWanted")}</h3>
                {data?.most_wanted?.length ? (
                  <table className="table">
                    <thead><tr><th>{t("common.query")}</th><th>{t("common.count")}</th></tr></thead>
                    <tbody>{data.most_wanted.map((z) => <tr key={z.term}><td>{z.term}</td><td>{formatNumber(z.count, locale)}</td></tr>)}</tbody>
                  </table>
                ) : <p className="muted">{t("analytics.mostWantedEmpty")}</p>}
              </div>
              <div className="card">
                <h3>{t("common.zeroTitle")}</h3>
                {data?.zero_results?.length ? (
                  <table className="table">
                    <thead><tr><th>{t("common.query")}</th><th>{t("common.count")}</th></tr></thead>
                    <tbody>{data.zero_results.map((z) => <tr key={z.term}><td>{z.term}</td><td>{formatNumber(z.count, locale)}</td></tr>)}</tbody>
                  </table>
                ) : <p className="muted">{t("analytics.zeroEmpty")}</p>}
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

          <div className="card">
            <h3>{t("analytics.analystTitle")}</h3>
            <p className="hint">{t("analytics.analystHint")}</p>
            {analystError ? <Alert kind="error">{analystError}</Alert> : null}
            <div className="row" style={{ gap: ".5rem", flexWrap: "wrap" }}>
              <input
                className="input"
                style={{ flex: 1, minWidth: 260 }}
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter") void ask(); }}
                placeholder={t("analytics.analystPlaceholder")}
              />
              <button className="btn btn-primary" disabled={analystBusy || !question.trim()} onClick={() => void ask()}>
                {analystBusy ? <Spinner /> : t("analytics.analystAsk")}
              </button>
            </div>
            {analyst ? (
              <div style={{ marginTop: "1rem" }}>
                <p style={{ whiteSpace: "pre-wrap" }}>{analyst.answer}</p>
                <p className="hint">
                  {analyst.narrated_by === "llm" ? t("analytics.analystNarratedLlm") : t("analytics.analystNarratedTemplate")}
                </p>
              </div>
            ) : !analystError ? <p className="muted" style={{ marginTop: "1rem" }}>{t("analytics.analystEmpty")}</p> : null}
          </div>
        </>
      )}
    </DashboardShell>
  );
}
