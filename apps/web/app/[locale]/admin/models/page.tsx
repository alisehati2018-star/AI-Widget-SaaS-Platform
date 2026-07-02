"use client";

import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";
import { adminFetch as authFetch } from "@/lib/auth";
import { formatNumber } from "@/lib/datetime";
import { useAdminResource as useResource } from "@/lib/hooks/useResource";
import type { Locale } from "@/i18n/routing";
import { DashboardShell, useAdminNav } from "@/components/shell";
import { Badge, Spinner } from "@/components/ui";

interface Models {
  embeddings_url: string;
  reranker_url: string;
  llm_url: string;
  llm_model: string;
  frontier_enabled: boolean;
  frontier_model: string | null;
  rerank_enabled: boolean;
  by_rung: { rung: string; count: number }[];
}
interface PingInfo { configured: boolean; reachable: boolean; latency_ms: number | null }
type PingMap = Record<"embeddings" | "reranker" | "llm", PingInfo>;

export default function AdminModels() {
  const t = useTranslations("admin");
  const locale = useLocale() as Locale;
  const nav = useAdminNav();
  const { data } = useResource<Models>("/admin/models");
  const [ping, setPing] = useState<PingMap | null>(null);
  const [pinging, setPinging] = useState(false);

  async function runPing() {
    setPinging(true);
    try {
      const r = await authFetch<{ services: PingMap }>("/admin/models/ping", { method: "POST" });
      setPing(r.services);
    } catch {
      setPing(null);
    } finally {
      setPinging(false);
    }
  }

  const reachBadge = (key: keyof PingMap) => {
    if (!ping) return null;
    const info = ping[key];
    if (!info.configured) return <Badge>{t("models.notConfigured")}</Badge>;
    return info.reachable ? (
      <Badge tone="success">
        {t("models.reachable")} · {formatNumber(info.latency_ms ?? 0, locale)} {t("common.ms")}
      </Badge>
    ) : (
      <Badge tone="warning">{t("models.unreachable")}</Badge>
    );
  };

  if (!data) {
    return (
      <DashboardShell title={t("models.title")} nav={nav} requireAdmin loginHref="/admin/login">
        <Spinner />
      </DashboardShell>
    );
  }

  return (
    <DashboardShell title={t("models.title")} nav={nav} requireAdmin loginHref="/admin/login">
      <div className="row-between" style={{ marginTop: "-1rem", flexWrap: "wrap", gap: ".6rem" }}>
        <p style={{ margin: 0 }}>{t("models.intro")}</p>
        <button className="btn btn-primary" disabled={pinging} onClick={() => void runPing()}>
          {pinging ? <Spinner /> : t("models.pingAll")}
        </button>
      </div>
      <div className="card" style={{ margin: "1rem 0 1.5rem" }}>
        <h3>{t("models.configTitle")}</h3>
        <table className="table">
          <tbody>
            <tr>
              <td className="muted">{t("models.localLlm")}</td>
              <td>{data.llm_model} <span className="muted" dir="ltr">({data.llm_url})</span></td>
              <td>{reachBadge("llm")}</td>
            </tr>
            <tr>
              <td className="muted">{t("models.embeddings")}</td>
              <td className="muted" dir="ltr">{data.embeddings_url}</td>
              <td>{reachBadge("embeddings")}</td>
            </tr>
            <tr>
              <td className="muted">{t("models.reranker")}</td>
              <td>{data.rerank_enabled ? <Badge tone="success">{t("common.on")}</Badge> : <Badge>{t("common.off")}</Badge>} <span className="muted" dir="ltr">{data.reranker_url}</span></td>
              <td>{reachBadge("reranker")}</td>
            </tr>
            <tr>
              <td className="muted">{t("models.frontier")}</td>
              <td>{data.frontier_enabled ? <Badge tone="warning">{data.frontier_model ?? t("common.enabled")}</Badge> : <Badge>{t("common.disabled")}</Badge>}</td>
              <td></td>
            </tr>
          </tbody>
        </table>
        {ping ? <p className="hint">{t("models.pingHint")}</p> : null}
      </div>
      <div className="card">
        <h3>{t("models.byRung")}</h3>
        {data.by_rung.length ? (
          <table className="table">
            <thead><tr><th>{t("common.colRung")}</th><th>{t("common.colCalls")}</th></tr></thead>
            <tbody>{data.by_rung.map((r) => <tr key={r.rung}><td>{r.rung}</td><td>{formatNumber(r.count, locale)}</td></tr>)}</tbody>
          </table>
        ) : (
          <p className="muted">{t("models.empty")}</p>
        )}
      </div>
    </DashboardShell>
  );
}
