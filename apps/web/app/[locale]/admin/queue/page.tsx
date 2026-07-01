"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { adminFetch as authFetch } from "@/lib/auth";
import { formatNumber } from "@/lib/datetime";
import type { Locale } from "@/i18n/routing";
import { DashboardShell, useAdminNav } from "@/components/shell";
import { Badge, Spinner, Stat } from "@/components/ui";

interface Queue { broker: string; reachable: boolean; pending: number | null }

export default function AdminQueue() {
  const t = useTranslations("admin");
  const locale = useLocale() as Locale;
  const nav = useAdminNav();
  const [data, setData] = useState<Queue | null>(null);

  useEffect(() => {
    const load = () => authFetch<Queue>("/admin/queue").then(setData).catch(() => setData(null));
    load();
    const id = setInterval(load, 10000);
    return () => clearInterval(id);
  }, []);

  return (
    <DashboardShell title={t("queue.title")} nav={nav} requireAdmin loginHref="/admin/login">
      <p style={{ marginTop: "-1rem" }}>{t("queue.intro")}</p>
      <div className="stat-grid" style={{ marginBottom: "1.5rem" }}>
        <Stat label={t("queue.broker")} value={data ? <Badge tone={data.reachable ? "success" : "warning"}>{data.reachable ? t("queue.reachable") : t("queue.down")}</Badge> : <Spinner />} />
        <Stat label={t("queue.pendingTasks")} value={data?.pending != null ? formatNumber(data.pending, locale) : "—"} />
      </div>
      <div className="card">
        <h3>{t("queue.brokerTitle")}</h3>
        <p className="muted" style={{ marginBottom: 0, wordBreak: "break-all" }}>{data?.broker ?? "—"}</p>
        <p className="hint">{t("queue.hint")}</p>
      </div>
    </DashboardShell>
  );
}
