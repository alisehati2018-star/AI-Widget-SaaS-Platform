"use client";

// The profit view: credits consumed (valued at the configured credit price)
// vs the platform's actual provider spend (COGS), by model and by tenant.

import { useLocale, useTranslations } from "next-intl";
import { formatNumber } from "@/lib/datetime";
import type { Locale } from "@/i18n/routing";
import { Stat } from "@/components/ui";
import type { FinanceData } from "./types";

function usd(v: number, locale: Locale): string {
  return `$${formatNumber(Math.round(v * 100) / 100, locale)}`;
}

export function FinanceCard({ finance }: { finance: FinanceData }) {
  const t = useTranslations("admin");
  const locale = useLocale() as Locale;

  return (
    <div className="card" style={{ marginBottom: "1.5rem" }}>
      <h3>{t("models.financeTitle", { days: finance.days })}</h3>
      <p className="hint">{t("models.financeHint")}</p>
      <div className="stat-grid" style={{ margin: ".8rem 0" }}>
        <Stat label={t("models.creditsConsumed")}
          value={formatNumber(Math.round(finance.credits_consumed), locale)} />
        <Stat label={t("models.consumptionValue")}
          value={usd(finance.consumption_value_usd, locale)} />
        <Stat label={t("models.providerCost")} value={usd(finance.provider_cost_usd, locale)} />
        <Stat label={t("models.grossMargin")} value={usd(finance.gross_margin_usd, locale)} />
      </div>
      {finance.billed_revenue.length ? (
        <p className="muted">
          {t("models.billedRevenue")}:{" "}
          {finance.billed_revenue
            .map((r) => `${formatNumber(r.amount, locale)} ${r.currency}`)
            .join(" · ")}
        </p>
      ) : null}

      {finance.by_model.length ? (
        <>
          <h4>{t("models.byModel")}</h4>
          <div style={{ overflowX: "auto" }}>
            <table className="table">
              <thead>
                <tr>
                  <th>{t("models.colModel")}</th>
                  <th>{t("common.colCalls")}</th>
                  <th>{t("models.colTokens")}</th>
                  <th>{t("models.colCredits")}</th>
                  <th>{t("models.colCogs")}</th>
                </tr>
              </thead>
              <tbody>
                {finance.by_model.map((m) => (
                  <tr key={`${m.provider}/${m.model}`}>
                    <td dir="ltr">{m.provider} / {m.model}</td>
                    <td>{formatNumber(m.calls, locale)}</td>
                    <td>{formatNumber(m.tokens_in + m.tokens_out, locale)}</td>
                    <td>{formatNumber(Math.round(m.credits), locale)}</td>
                    <td>{usd(m.cogs_usd, locale)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : null}

      {finance.by_tenant.length ? (
        <>
          <h4>{t("models.byTenant")}</h4>
          <div style={{ overflowX: "auto" }}>
            <table className="table">
              <thead>
                <tr>
                  <th>{t("models.colTenant")}</th>
                  <th>{t("common.colCalls")}</th>
                  <th>{t("models.colCredits")}</th>
                  <th>{t("models.colCogs")}</th>
                </tr>
              </thead>
              <tbody>
                {finance.by_tenant.map((r) => (
                  <tr key={r.slug}>
                    <td>{r.name}</td>
                    <td>{formatNumber(r.calls, locale)}</td>
                    <td>{formatNumber(Math.round(r.credits), locale)}</td>
                    <td>{usd(r.cogs_usd, locale)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : (
        <p className="muted">{t("models.financeEmpty")}</p>
      )}
    </div>
  );
}
