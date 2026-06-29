"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import type { AnalyticsBundle } from "@/lib/api";
import { authFetch } from "@/lib/auth";
import { formatNumber } from "@/lib/datetime";
import type { Locale } from "@/i18n/routing";
import { DashboardShell, useOwnerNav } from "@/components/shell";
import { Stat } from "@/components/ui";

export default function ChatAnalyticsPage() {
  const t = useTranslations("dashboard");
  const locale = useLocale() as Locale;
  const nav = useOwnerNav();
  const [data, setData] = useState<AnalyticsBundle | null>(null);

  useEffect(() => {
    authFetch<AnalyticsBundle>("/tenant/analytics").then(setData).catch(() => setData(null));
  }, []);

  const fd = data?.four_dimensions;
  const pct = (v: number) => formatNumber(v, locale, { style: "percent", maximumFractionDigits: 0 });

  return (
    <DashboardShell title={t("nav.chat")} nav={nav}>
      <p style={{ marginTop: "-1rem" }}>{t("chat.intro")}</p>
      <div className="stat-grid" style={{ marginBottom: "2rem" }}>
        <Stat label={t("chat.turns")} value={fd?.reliability?.turns != null ? formatNumber(fd.reliability.turns, locale) : "—"} />
        <Stat label={t("chat.noPaidShare")} value={fd?.cost?.no_paid_share != null ? pct(fd.cost.no_paid_share) : "—"} />
        <Stat label={t("chat.firstToken")} value={fd?.latency?.p95_ms != null ? `${formatNumber(fd.latency.p95_ms, locale)} ${t("analytics.ms")}` : "—"} />
        <Stat label={t("chat.creditsChat")} value={fd?.cost?.total != null ? formatNumber(fd.cost.total, locale) : "—"} />
      </div>
      <div className="card">
        <h3>{t("chat.topicsTitle")}</h3>
        <p className="hint">{t("chat.topicsHint")}</p>
        {data?.most_wanted?.length ? (
          <table className="table">
            <thead><tr><th>{t("chat.colTopic")}</th><th>{t("chat.colMentions")}</th></tr></thead>
            <tbody>
              {data.most_wanted.map((m) => (
                <tr key={m.term}><td>{m.term}</td><td>{formatNumber(m.count, locale)}</td></tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="muted">{t("chat.empty")}</p>
        )}
      </div>
    </DashboardShell>
  );
}
