"use client";

import { useLocale, useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";
import type { Order } from "@/lib/api";
import { authFetch } from "@/lib/auth";
import { formatCurrency, formatDate, formatNumber } from "@/lib/datetime";
import type { Locale } from "@/i18n/routing";
import { DashboardShell, useAdminNav } from "@/components/shell";
import { Alert, Badge, Spinner, Stat } from "@/components/ui";

export default function AdminBilling() {
  const t = useTranslations("admin");
  const locale = useLocale() as Locale;
  const nav = useAdminNav();
  const [orders, setOrders] = useState<Order[] | null>(null);
  const [revenue, setRevenue] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  const load = useCallback(() => {
    authFetch<{ orders: Order[]; revenue_total: number }>("/admin/orders")
      .then((r) => { setOrders(r.orders); setRevenue(r.revenue_total); })
      .catch((e) => setError(String(e.message ?? e)));
  }, []);

  useEffect(() => load(), [load]);

  async function act(id: string, action: "mark-paid" | "refund") {
    setBusy(id + action);
    try {
      await authFetch(`/admin/orders/${id}/${action}`, { method: "POST" });
      load();
    } finally {
      setBusy(null);
    }
  }

  const tone = (s: string) => (s === "paid" ? "success" : s === "pending" ? "warning" : undefined);
  const num = (n: number | undefined) => (n != null ? formatNumber(n, locale) : "—");

  async function runJob(job: "run-renewals" | "run-dunning") {
    setBusy(job);
    try {
      const r = await authFetch<Record<string, number>>(`/admin/billing/${job}`, { method: "POST" });
      setMsg(
        job === "run-renewals"
          ? t("billing.renewalsResult", { downgraded: r.downgraded ?? 0, pastDue: r.past_due ?? 0 })
          : t("billing.dunningResult", { emailed: r.emailed ?? 0, pastDue: r.past_due ?? 0 }),
      );
      load();
    } finally {
      setBusy(null);
    }
  }

  return (
    <DashboardShell title={t("billing.title")} nav={nav} requireAdmin loginHref="/admin/login">
      <p style={{ marginTop: "-1rem" }}>{t("billing.intro")}</p>
      {msg ? <Alert kind="success">{msg}</Alert> : null}
      <div className="stat-grid" style={{ marginBottom: "1.5rem" }}>
        <Stat label={t("billing.paidRevenue")} value={`$${formatNumber(Math.round(revenue), locale)}`} />
        <Stat label={t("billing.orders")} value={num(orders?.length)} />
        <Stat label={t("billing.pending")} value={num(orders?.filter((o) => o.status === "pending").length)} />
        <Stat label={t("billing.refunded")} value={num(orders?.filter((o) => o.status === "refunded").length)} />
      </div>
      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <h3>{t("billing.opsTitle")}</h3>
        <p className="hint">{t("billing.opsHint")}</p>
        <div className="row" style={{ flexWrap: "wrap" }}>
          <button className="btn btn-soft" disabled={busy !== null} onClick={() => void runJob("run-renewals")}>
            {busy === "run-renewals" ? <Spinner /> : t("billing.runRenewals")}
          </button>
          <button className="btn btn-soft" disabled={busy !== null} onClick={() => void runJob("run-dunning")}>
            {busy === "run-dunning" ? <Spinner /> : t("billing.runDunning")}
          </button>
        </div>
      </div>
      <div className="card">
        <h3>{t("billing.recentOrders")}</h3>
        {error ? <p className="muted">{t("common.loadError")}: {error}</p> : null}
        {orders === null ? (
          <Spinner />
        ) : orders.length === 0 ? (
          <p className="muted">{t("billing.ordersEmpty")}</p>
        ) : (
          <table className="table">
            <thead><tr><th>{t("billing.colStore")}</th><th>{t("billing.colPlan")}</th><th>{t("billing.colAmount")}</th><th>{t("billing.colProvider")}</th><th>{t("billing.colStatus")}</th><th>{t("common.when")}</th><th></th></tr></thead>
            <tbody>
              {orders.map((o) => (
                <tr key={o.id}>
                  <td>{o.tenant}</td>
                  <td>{o.plan}</td>
                  <td>{formatCurrency(o.amount, o.currency, locale)}</td>
                  <td className="muted">{o.provider}</td>
                  <td><Badge tone={tone(o.status)}>{o.status}</Badge></td>
                  <td className="muted">{formatDate(o.created_at, locale)}</td>
                  <td>
                    <div className="row" style={{ gap: "0.4rem" }}>
                      {o.status === "pending" ? (
                        <button className="btn btn-soft" disabled={busy !== null} onClick={() => void act(o.id, "mark-paid")}>
                          {busy === o.id + "mark-paid" ? <Spinner /> : t("billing.markPaid")}
                        </button>
                      ) : null}
                      {o.status === "paid" ? (
                        <button className="btn btn-danger" disabled={busy !== null} onClick={() => void act(o.id, "refund")}>
                          {busy === o.id + "refund" ? <Spinner /> : t("billing.refund")}
                        </button>
                      ) : null}
                    </div>
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
