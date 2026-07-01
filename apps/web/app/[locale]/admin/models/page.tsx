"use client";

import { useLocale, useTranslations } from "next-intl";
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

export default function AdminModels() {
  const t = useTranslations("admin");
  const locale = useLocale() as Locale;
  const nav = useAdminNav();
  const { data } = useResource<Models>("/admin/models");

  if (!data) {
    return (
      <DashboardShell title={t("models.title")} nav={nav} requireAdmin loginHref="/admin/login">
        <Spinner />
      </DashboardShell>
    );
  }

  return (
    <DashboardShell title={t("models.title")} nav={nav} requireAdmin loginHref="/admin/login">
      <p style={{ marginTop: "-1rem" }}>{t("models.intro")}</p>
      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <h3>{t("models.configTitle")}</h3>
        <table className="table">
          <tbody>
            <tr><td className="muted">{t("models.localLlm")}</td><td>{data.llm_model} <span className="muted">({data.llm_url})</span></td></tr>
            <tr><td className="muted">{t("models.embeddings")}</td><td className="muted">{data.embeddings_url}</td></tr>
            <tr><td className="muted">{t("models.reranker")}</td><td>{data.rerank_enabled ? <Badge tone="success">{t("common.on")}</Badge> : <Badge>{t("common.off")}</Badge>} <span className="muted">{data.reranker_url}</span></td></tr>
            <tr><td className="muted">{t("models.frontier")}</td><td>{data.frontier_enabled ? <Badge tone="warning">{data.frontier_model ?? t("common.enabled")}</Badge> : <Badge>{t("common.disabled")}</Badge>}</td></tr>
          </tbody>
        </table>
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
