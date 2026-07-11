"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { adminFetch as authFetch } from "@/lib/auth";
import { formatNumber, formatTime } from "@/lib/datetime";
import { Link } from "@/i18n/navigation";
import type { Locale } from "@/i18n/routing";
import { DashboardShell, useAdminNav } from "@/components/shell";
import { TrendChart } from "@/components/trend-chart";
import { Alert, Badge, Spinner } from "@/components/ui";
import { LocalInfraCard } from "./local-infra-card";

interface Sample { ts: number; ok: number; total: number; pg_ms: number | null }
interface Health {
  status: string;
  dependencies: Record<string, string>;
  latency_ms: Record<string, number | null>;
  history: Sample[];
}

export default function AdminHealth() {
  const t = useTranslations("admin");
  const locale = useLocale() as Locale;
  const nav = useAdminNav();
  const [data, setData] = useState<Health | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const load = () =>
      authFetch<Health>("/admin/health")
        .then((r) => { setData(r); setFailed(false); })
        .catch(() => { setData(null); setFailed(true); });
    load();
    const id = setInterval(load, 10000);
    return () => clearInterval(id);
  }, []);

  const spark = (data?.history ?? [])
    .filter((s) => s.pg_ms != null)
    .map((s) => ({ date: new Date(s.ts * 1000).toISOString(), value: s.pg_ms as number }));

  return (
    <DashboardShell title={t("health.title")} nav={nav} requireAdmin loginHref="/admin/login">
      <p style={{ marginTop: "-1rem" }}>{t("health.intro")}</p>
      <div className="dash-2col-even">
        <div className="card">
          <div className="row-between" style={{ marginBottom: "1rem" }}>
            <h3 style={{ margin: 0 }}>{t("health.overall")}</h3>
            {data ? (
              <Badge tone={data.status === "ok" ? "success" : "warning"}>{data.status}</Badge>
            ) : failed ? (
              <Badge tone="warning">{t("common.off")}</Badge>
            ) : <Spinner />}
          </div>
          {failed ? <Alert kind="error">{t("common.loadFailed")}</Alert> : null}
          {data ? (
            <table className="table">
              <tbody>
                {Object.entries(data.dependencies).map(([k, v]) => (
                  <tr key={k}>
                    <td style={{ textTransform: "capitalize" }}>{k}</td>
                    <td><Badge tone={v === "ok" ? "success" : "warning"}>{v}</Badge></td>
                    <td className="muted">
                      {data.latency_ms?.[k] != null
                        ? `${formatNumber(data.latency_ms[k] as number, locale)} ${t("common.ms")}`
                        : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : null}
        </div>

        <div className="card">
          <h3>{t("health.quickLinksTitle")}</h3>
          <div className="stack">
            <Link className="btn btn-soft btn-block" href="/admin/queue">{t("health.linkQueue")}</Link>
            <Link className="btn btn-soft btn-block" href="/admin/elasticsearch">{t("health.linkElasticsearch")}</Link>
            <Link className="btn btn-soft btn-block" href="/admin/models">{t("health.linkModels")}</Link>
            <Link className="btn btn-soft btn-block" href="/admin/security">{t("health.linkSecurity")}</Link>
          </div>
        </div>
      </div>

      <div className="card" style={{ marginTop: "1.5rem" }}>
        <h3>{t("health.sparklineTitle")}</h3>
        {spark.length >= 2 ? (
          <TrendChart
            data={spark}
            label={t("health.sparklineLabel")}
            formatValue={(v) => `${formatNumber(Math.round(v), locale)} ${t("common.ms")}`}
            formatDate={(iso) => formatTime(iso, locale)}
            height={80}
          />
        ) : (
          <p className="muted">{t("health.sparklineEmpty")}</p>
        )}
        <p className="hint">{t("health.sparklineHint")}</p>
      </div>

      <LocalInfraCard />
    </DashboardShell>
  );
}
