"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { getPlans, type PlanInfo } from "@/lib/api";
import { formatNumber } from "@/lib/datetime";
import type { Locale } from "@/i18n/routing";
import { DashboardShell, useAdminNav } from "@/components/shell";

export default function AdminPlans() {
  const t = useTranslations("admin");
  const locale = useLocale() as Locale;
  const nav = useAdminNav();
  const [plans, setPlans] = useState<PlanInfo[]>([]);
  useEffect(() => {
    getPlans().then((r) => setPlans(r.plans)).catch(() => setPlans([]));
  }, []);

  return (
    <DashboardShell title={t("plans.title")} nav={nav} requireAdmin loginHref="/admin/login">
      <p style={{ marginTop: "-1rem" }}>{t("plans.intro")}</p>
      <div className="card">
        <table className="table">
          <thead>
            <tr>
              <th>{t("plans.colPlan")}</th>
              <th>{t("plans.colPrice")}</th>
              <th>{t("plans.colCredits")}</th>
              <th>{t("plans.colRateLimit")}</th>
            </tr>
          </thead>
          <tbody>
            {plans.map((p) => (
              <tr key={p.code}>
                <td>{p.name}</td>
                <td>{p.price_monthly === 0 ? t("plans.freeCustom") : t("plans.priceMonth", { price: formatNumber(p.price_monthly, locale) })}</td>
                <td>{formatNumber(p.credits_per_month, locale)}</td>
                <td>{t("plans.perMin", { n: formatNumber(p.rate_limit_per_min, locale) })}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="hint" style={{ marginTop: "1rem" }}>{t("plans.note")}</p>
      </div>
    </DashboardShell>
  );
}
