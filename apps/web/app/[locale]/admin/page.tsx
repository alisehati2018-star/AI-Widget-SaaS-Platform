"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { authFetch } from "@/lib/auth";
import { formatNumber } from "@/lib/datetime";
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
  const [data, setData] = useState<Overview | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    authFetch<Overview>("/admin/overview")
      .then(setData)
      .catch((e) => setError(String(e.message ?? e)));
  }, []);

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
