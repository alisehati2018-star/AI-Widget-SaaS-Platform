"use client";

import { useLocale, useTranslations } from "next-intl";
import { formatNumber } from "@/lib/datetime";
import { useAdminResource as useResource } from "@/lib/hooks/useResource";
import type { Locale } from "@/i18n/routing";
import { DashboardShell, useAdminNav } from "@/components/shell";
import { Stat } from "@/components/ui";

interface Overview {
  tenants: number;
  users: number;
  active_subscriptions: number;
  mrr: number;
}

export default function AdminOverview() {
  const t = useTranslations("admin");
  const locale = useLocale() as Locale;
  const nav = useAdminNav();
  const { data, error } = useResource<Overview>("/admin/overview");

  const num = (n: number | undefined) => (n != null ? formatNumber(n, locale) : "—");

  return (
    <DashboardShell title={t("overview.title")} nav={nav} requireAdmin loginHref="/admin/login">
      <p style={{ marginTop: "-1rem" }}>{t("overview.intro")}</p>
      <div className="stat-grid" style={{ marginBottom: "2rem" }}>
        <Stat label={t("overview.tenants")} value={num(data?.tenants)} />
        <Stat label={t("overview.users")} value={num(data?.users)} />
        <Stat label={t("overview.activeSubs")} value={num(data?.active_subscriptions)} />
        <Stat label={t("overview.mrr")} value={data ? `$${formatNumber(Math.round(data.mrr), locale)}` : "—"} />
      </div>
      {error ? (
        <div className="card"><p className="muted" style={{ margin: 0 }}>{t("common.loadError")}: {error}</p></div>
      ) : null}
    </DashboardShell>
  );
}
