"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { authFetch } from "@/lib/auth";
import { formatDateTime, formatNumber } from "@/lib/datetime";
import type { Locale } from "@/i18n/routing";
import { DashboardShell, useOwnerNav } from "@/components/shell";
import { Badge, Spinner, Stat } from "@/components/ui";

interface LedgerEntry {
  delta: number;
  rung: string | null;
  reason: string | null;
  created_at: string | null;
}
interface CreditsResp {
  used: number;
  granted: number;
  cap: number | null;
  within_plan: boolean;
  ledger: LedgerEntry[];
}

export default function CreditsPage() {
  const t = useTranslations("dashboard");
  const locale = useLocale() as Locale;
  const nav = useOwnerNav();
  const [data, setData] = useState<CreditsResp | null>(null);

  useEffect(() => {
    authFetch<CreditsResp>("/tenant/credits").then(setData).catch(() => setData(null));
  }, []);

  const remaining = data?.cap != null ? Math.max(0, data.cap - data.used) : null;
  const num = (n: number | null | undefined) =>
    n != null ? formatNumber(Math.round(n), locale) : "—";

  return (
    <DashboardShell title={t("nav.credits")} nav={nav}>
      <p style={{ marginTop: "-1rem" }}>{t("credits.intro")}</p>
      <div className="stat-grid" style={{ marginBottom: "2rem" }}>
        <Stat label={t("credits.used")} value={num(data?.used)} />
        <Stat label={t("credits.granted")} value={num(data?.granted)} />
        <Stat label={t("credits.cap")} value={num(data?.cap)} />
        <Stat label={t("credits.remaining")} value={num(remaining)} />
      </div>

      <div className="card">
        <h3>{t("credits.ledger")}</h3>
        {data === null ? (
          <Spinner />
        ) : data.ledger.length === 0 ? (
          <p className="muted">{t("credits.empty")}</p>
        ) : (
          <table className="table">
            <thead><tr><th>{t("common.when")}</th><th>{t("credits.colReason")}</th><th>{t("credits.colRung")}</th><th>{t("credits.colDelta")}</th></tr></thead>
            <tbody>
              {data.ledger.map((e, i) => (
                <tr key={i}>
                  <td className="muted">{formatDateTime(e.created_at, locale)}</td>
                  <td>{e.reason ?? "—"}</td>
                  <td>{e.rung ?? "—"}</td>
                  <td>
                    <Badge tone={e.delta >= 0 ? "success" : "warning"}>
                      {e.delta >= 0 ? "+" : ""}{formatNumber(Math.round(e.delta), locale)}
                    </Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </DashboardShell>
  );
}
