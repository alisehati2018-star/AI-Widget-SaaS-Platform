"use client";

import { useLocale, useTranslations } from "next-intl";
import { formatCurrency, formatDate, formatNumber } from "@/lib/datetime";
import type { Locale } from "@/i18n/routing";
import { Badge } from "@/components/ui";

export interface Invoice {
  number: number;
  description: string;
  amount: number;
  currency: string;
  status: string;
  created_at: string | null;
}

/** The tenant's invoices with printable-HTML and PDF downloads. */
export function InvoicesCard({ invoices }: { invoices: Invoice[] }) {
  const t = useTranslations("billing");
  const locale = useLocale() as Locale;
  return (
    <div className="card" style={{ marginBottom: "1.5rem" }}>
      <h3>{t("invoices")}</h3>
      {invoices.length === 0 ? (
        <p className="muted">{t("invoicesEmpty")}</p>
      ) : (
        <table className="table">
          <thead><tr><th>{t("colNumber")}</th><th>{t("colDescription")}</th><th>{t("colAmount")}</th><th>{t("colStatus")}</th><th>{t("colDate")}</th><th></th></tr></thead>
          <tbody>
            {invoices.map((inv) => (
              <tr key={inv.number}>
                <td>#{formatNumber(inv.number, locale)}</td>
                <td>{inv.description}</td>
                <td>{formatCurrency(inv.amount, inv.currency, locale)}</td>
                <td><Badge tone="success">{inv.status}</Badge></td>
                <td className="muted">{formatDate(inv.created_at, locale)}</td>
                <td>
                  <a
                    className="btn btn-ghost"
                    href={`/api/tenant/billing/invoices/${inv.number}/html`}
                    target="_blank"
                    rel="noreferrer"
                  >
                    {t("invoiceDownload")}
                  </a>
                  <a className="btn btn-ghost" href={`/api/tenant/billing/invoices/${inv.number}/pdf`}>
                    {t("invoicePdf")}
                  </a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
