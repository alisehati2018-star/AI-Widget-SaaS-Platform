"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { formatCurrency, formatDate, formatNumber } from "@/lib/datetime";
import { useAdminResource as useResource } from "@/lib/hooks/useResource";
import type { Locale } from "@/i18n/routing";
import { Badge, Input, Spinner, Stat } from "@/components/ui";

interface Invoice {
  id: string;
  number: number;
  tenant_slug: string;
  tenant_name: string;
  description: string;
  amount: number;
  currency: string;
  status: string;
  created_at: string | null;
}
interface InvoicePage {
  invoices: Invoice[];
  total: number;
  paid_amount: number;
  paid_count: number;
  limit: number;
  offset: number;
}

const PAGE = 20;

/** Platform-wide invoice browser: tenant search + status filter + a revenue
 *  summary computed over the SAME filter, so the numbers always match the list. */
export function InvoicesPanel() {
  const t = useTranslations("admin");
  const locale = useLocale() as Locale;

  const [q, setQ] = useState("");
  const [debouncedQ, setDebouncedQ] = useState("");
  const [status, setStatus] = useState("");
  const [offset, setOffset] = useState(0);

  useEffect(() => {
    const id = setTimeout(() => { setDebouncedQ(q.trim()); setOffset(0); }, 300);
    return () => clearTimeout(id);
  }, [q]);

  const params = new URLSearchParams({ limit: String(PAGE), offset: String(offset) });
  if (debouncedQ) params.set("q", debouncedQ);
  if (status) params.set("status", status);
  const { data, error, loading } = useResource<InvoicePage>(`/admin/invoices?${params.toString()}`);
  const invoices = loading ? null : (data?.invoices ?? []);
  const total = data?.total ?? 0;

  return (
    <>
      <div className="stat-grid" style={{ marginBottom: "1rem" }}>
        <Stat label={t("billing.invPaidAmount")} value={`$${formatNumber(Math.round(data?.paid_amount ?? 0), locale)}`} />
        <Stat label={t("billing.invPaidCount")} value={formatNumber(data?.paid_count ?? 0, locale)} />
        <Stat label={t("billing.invTotal")} value={formatNumber(total, locale)} />
      </div>

      <div className="row" style={{ flexWrap: "wrap", gap: ".6rem", marginBottom: "1rem" }}>
        <Input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder={t("billing.invSearchPlaceholder")}
          style={{ flex: 1, minWidth: 220 }}
        />
        <select className="input" style={{ width: "auto" }} value={status} onChange={(e) => { setStatus(e.target.value); setOffset(0); }}>
          <option value="">{t("billing.invAllStatuses")}</option>
          <option value="paid">{t("billing.invStatusPaid")}</option>
          <option value="void">{t("billing.invStatusVoid")}</option>
        </select>
      </div>

      {error ? <p className="muted">{t("common.loadError")}: {error}</p> : null}
      {invoices === null ? <Spinner /> : (
        <>
          <table className="table">
            <thead>
              <tr>
                <th>{t("billing.invColNumber")}</th>
                <th>{t("billing.colStore")}</th>
                <th>{t("billing.invColDescription")}</th>
                <th>{t("billing.colAmount")}</th>
                <th>{t("billing.colStatus")}</th>
                <th>{t("common.when")}</th>
              </tr>
            </thead>
            <tbody>
              {invoices.map((inv) => (
                <tr key={inv.id}>
                  <td><code>#{formatNumber(inv.number, locale)}</code></td>
                  <td>{inv.tenant_name} <span className="muted">{inv.tenant_slug}</span></td>
                  <td className="muted">{inv.description}</td>
                  <td>{formatCurrency(inv.amount, inv.currency, locale)}</td>
                  <td><Badge tone={inv.status === "paid" ? "success" : undefined}>{inv.status === "paid" ? t("billing.invStatusPaid") : t("billing.invStatusVoid")}</Badge></td>
                  <td className="muted">{inv.created_at ? formatDate(inv.created_at, locale) : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {invoices.length === 0 ? <p className="muted">{t("billing.invEmpty")}</p> : null}
          <div className="row-between" style={{ marginTop: "1rem" }}>
            <span className="hint">
              {t("billing.invPageInfo", {
                from: formatNumber(total === 0 ? 0 : offset + 1, locale),
                to: formatNumber(Math.min(offset + PAGE, total), locale),
                total: formatNumber(total, locale),
              })}
            </span>
            <div className="row" style={{ gap: ".4rem" }}>
              <button className="btn btn-soft" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE))}>
                {t("billing.invPrev")}
              </button>
              <button className="btn btn-soft" disabled={offset + PAGE >= total} onClick={() => setOffset(offset + PAGE)}>
                {t("billing.invNext")}
              </button>
            </div>
          </div>
        </>
      )}
    </>
  );
}
