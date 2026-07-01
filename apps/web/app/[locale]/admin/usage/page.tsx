"use client";

import { useLocale, useTranslations } from "next-intl";
import { formatNumber } from "@/lib/datetime";
import { useAdminResource as useResource } from "@/lib/hooks/useResource";
import type { Locale } from "@/i18n/routing";
import { DashboardShell, useAdminNav } from "@/components/shell";
import { Spinner, Stat } from "@/components/ui";

interface Usage {
  calls: number;
  tokens_in: number;
  tokens_out: number;
  cost: number;
  credits_spent: number;
  by_rung: { rung: string; count: number }[];
}

export default function AdminUsage() {
  const t = useTranslations("admin");
  const locale = useLocale() as Locale;
  const nav = useAdminNav();
  const { data } = useResource<Usage>("/admin/usage");

  const num = (n: number | undefined) => (n != null ? formatNumber(Math.round(n), locale) : "—");

  return (
    <DashboardShell title={t("usage.title")} nav={nav} requireAdmin loginHref="/admin/login">
      <p style={{ marginTop: "-1rem" }}>{t("usage.intro")}</p>
      <div className="stat-grid" style={{ marginBottom: "2rem" }}>
        <Stat label={t("usage.modelCalls")} value={num(data?.calls)} />
        <Stat label={t("usage.tokensIn")} value={num(data?.tokens_in)} />
        <Stat label={t("usage.tokensOut")} value={num(data?.tokens_out)} />
        <Stat label={t("usage.creditsSpent")} value={num(data?.credits_spent)} />
      </div>
      <div className="card">
        <h3>{t("usage.byRung")}</h3>
        {data === null ? <Spinner /> : data.by_rung.length === 0 ? (
          <p className="muted">{t("usage.empty")}</p>
        ) : (
          <table className="table">
            <thead><tr><th>{t("common.colRung")}</th><th>{t("common.colCalls")}</th></tr></thead>
            <tbody>{data.by_rung.map((r) => <tr key={r.rung}><td>{r.rung}</td><td>{formatNumber(r.count, locale)}</td></tr>)}</tbody>
          </table>
        )}
      </div>
    </DashboardShell>
  );
}
