"use client";

import { useLocale, useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";
import { ApiError, getPlans, type MyOrder, type PlanInfo, type TenantProfile } from "@/lib/api";
import { authFetch } from "@/lib/auth";
import { formatCurrency, formatDate, formatNumber } from "@/lib/datetime";
import type { Locale } from "@/i18n/routing";
import { DashboardShell, useOwnerNav } from "@/components/shell";
import { Alert, Badge, Spinner } from "@/components/ui";

interface Invoice {
  number: number;
  description: string;
  amount: number;
  currency: string;
  status: string;
  created_at: string | null;
}
interface Preview {
  base_price: number;
  proration_credit: number;
  amount_due: number;
  currency: string;
  plan_name: string;
}

const TOPUP_OPTIONS = [
  { credits: 50000, price: 50 },
  { credits: 100000, price: 100 },
  { credits: 250000, price: 250 },
];

export default function BillingPage() {
  const t = useTranslations("billing");
  const tErrors = useTranslations("errors");
  const locale = useLocale() as Locale;
  const nav = useOwnerNav();
  const [plans, setPlans] = useState<PlanInfo[]>([]);
  const [profile, setProfile] = useState<TenantProfile | null>(null);
  const [orders, setOrders] = useState<MyOrder[]>([]);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [note, setNote] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState<string | null>(null);
  const [topupCredits, setTopupCredits] = useState(50000);

  const reload = useCallback(() => {
    authFetch<TenantProfile>("/tenant/profile").then(setProfile).catch(() => setProfile(null));
    authFetch<{ orders: MyOrder[] }>("/tenant/billing/orders").then((r) => setOrders(r.orders)).catch(() => setOrders([]));
    authFetch<{ invoices: Invoice[] }>("/tenant/billing/invoices").then((r) => setInvoices(r.invoices)).catch(() => setInvoices([]));
  }, []);

  useEffect(() => {
    getPlans().then((r) => setPlans(r.plans)).catch(() => setPlans([]));
    reload();
  }, [reload]);

  async function choose(code: string) {
    setError(null);
    setNote(null);
    setPending(code);
    try {
      if (profile?.sub_status === "active" && profile.plan.toLowerCase() !== "free") {
        const pv = await authFetch<Preview>(`/tenant/billing/preview?plan_code=${code}`).catch(() => null);
        if (pv && pv.proration_credit > 0) {
          const ok = window.confirm(
            t("previewConfirm", {
              plan: pv.plan_name,
              currency: pv.currency,
              base: formatNumber(pv.base_price, locale, { minimumFractionDigits: 2, maximumFractionDigits: 2 }),
              credit: formatNumber(pv.proration_credit, locale, { minimumFractionDigits: 2, maximumFractionDigits: 2 }),
              due: formatNumber(pv.amount_due, locale, { minimumFractionDigits: 2, maximumFractionDigits: 2 }),
            }),
          );
          if (!ok) {
            setPending(null);
            return;
          }
        }
      }
      const r = await authFetch<{ instructions?: string; redirect_url?: string; next?: string }>(
        "/tenant/billing/checkout",
        { body: { plan_code: code } },
      );
      if (r.next === "redirect" && r.redirect_url) {
        window.location.href = r.redirect_url;
        return;
      }
      setNote(r.instructions ?? t("noteOrder"));
      reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : tErrors("checkoutFailed"));
    } finally {
      setPending(null);
    }
  }

  async function buyTopup() {
    setError(null);
    setNote(null);
    setPending("topup");
    try {
      await authFetch("/tenant/billing/topup", { body: { credits: topupCredits } });
      setNote(t("noteTopup", { credits: formatNumber(topupCredits, locale) }));
      reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("topupFailed"));
    } finally {
      setPending(null);
    }
  }

  async function lifecycle(action: "cancel" | "resume") {
    await authFetch(`/tenant/billing/${action}`, { method: "POST" }).catch(() => {});
    setNote(action === "cancel" ? t("noteCancel") : t("noteResume"));
    reload();
  }

  const tone = (s: string) => (s === "paid" ? "success" : s === "pending" ? "warning" : undefined);
  const onPaidPlan = profile && profile.sub_status !== "none" && profile.plan.toLowerCase() !== "free";

  return (
    <DashboardShell title={t("title")} nav={nav}>
      {note ? <Alert kind="success">{note}</Alert> : null}
      {error ? <Alert kind="error">{error}</Alert> : null}

      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <div className="row-between" style={{ flexWrap: "wrap", gap: "1rem" }}>
          <div>
            <small className="faint">{t("currentPlan")}</small>
            <h3 style={{ margin: "0.2rem 0" }}>
              {profile?.plan ?? "—"}{" "}
              <Badge tone={profile?.sub_status === "active" ? "success" : profile?.sub_status === "past_due" ? "warning" : undefined}>
                {profile?.sub_status ?? "—"}
              </Badge>
            </h3>
            <p style={{ margin: 0 }} className="muted">
              {profile?.current_period_end
                ? t("renews", { date: formatDate(profile.current_period_end, locale) })
                : t("trialIncludes")}
              {profile?.credits.cap != null
                ? t("creditsUsed", {
                    used: formatNumber(Math.round(profile.credits.spent), locale),
                    cap: formatNumber(Math.round(profile.credits.cap), locale),
                  })
                : ""}
            </p>
          </div>
          {onPaidPlan ? (
            <div className="row" style={{ gap: "0.5rem" }}>
              <button className="btn btn-soft" onClick={() => void lifecycle("resume")}>{t("resume")}</button>
              <button className="btn btn-danger" onClick={() => void lifecycle("cancel")}>{t("cancel")}</button>
            </div>
          ) : null}
        </div>
      </div>

      <h3>{t("choosePlan")}</h3>
      <div className="pricing-grid" style={{ marginBottom: "2rem" }}>
        {plans.filter((p) => p.code !== "free").map((p) => {
          const current = profile?.plan?.toLowerCase() === p.name.toLowerCase();
          return (
            <div className={`card price-card${p.code === "pro" ? " featured" : ""}`} key={p.code}>
              <h4 style={{ margin: 0 }}>{p.name}</h4>
              <div className="price">
                {p.code === "enterprise" ? t("contactSales") : `$${formatNumber(p.price_monthly, locale)}`}
              </div>
              <ul className="feature-list">
                {p.features.slice(0, 3).map((f) => <li key={f}>{f}</li>)}
              </ul>
              <button
                className={`btn ${p.code === "pro" ? "btn-primary" : "btn-ghost"} btn-block`}
                style={{ marginTop: "auto" }}
                disabled={current || pending === p.code || p.code === "enterprise"}
                onClick={() => void choose(p.code)}
              >
                {current ? t("current") : p.code === "enterprise" ? t("contactSales") : pending === p.code ? <Spinner /> : t("buy", { plan: p.name })}
              </button>
            </div>
          );
        })}
      </div>

      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <h3>{t("topupTitle")}</h3>
        <p className="hint">{t("topupHint")}</p>
        <div className="row" style={{ flexWrap: "wrap", alignItems: "center" }}>
          <select className="input" style={{ maxWidth: 240 }} value={topupCredits} onChange={(e) => setTopupCredits(Number(e.target.value))}>
            {TOPUP_OPTIONS.map((o) => (
              <option key={o.credits} value={o.credits}>
                {t("topupOption", { credits: formatNumber(o.credits, locale), price: formatNumber(o.price, locale) })}
              </option>
            ))}
          </select>
          <button className="btn btn-primary" disabled={pending === "topup"} onClick={() => void buyTopup()}>
            {pending === "topup" ? <Spinner /> : t("buyCredits")}
          </button>
        </div>
      </div>

      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <h3>{t("invoices")}</h3>
        {invoices.length === 0 ? (
          <p className="muted">{t("invoicesEmpty")}</p>
        ) : (
          <table className="table">
            <thead><tr><th>{t("colNumber")}</th><th>{t("colDescription")}</th><th>{t("colAmount")}</th><th>{t("colStatus")}</th><th>{t("colDate")}</th></tr></thead>
            <tbody>
              {invoices.map((inv) => (
                <tr key={inv.number}>
                  <td>#{formatNumber(inv.number, locale)}</td>
                  <td>{inv.description}</td>
                  <td>{formatCurrency(inv.amount, inv.currency, locale)}</td>
                  <td><Badge tone="success">{inv.status}</Badge></td>
                  <td className="muted">{formatDate(inv.created_at, locale)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="card">
        <h3>{t("orders")}</h3>
        {orders.length === 0 ? (
          <p className="muted">{t("ordersEmpty")}</p>
        ) : (
          <table className="table">
            <thead><tr><th>{t("colPlan")}</th><th>{t("colAmount")}</th><th>{t("colProvider")}</th><th>{t("colStatus")}</th><th>{t("colDate")}</th></tr></thead>
            <tbody>
              {orders.map((o) => (
                <tr key={o.id}>
                  <td>{o.plan}</td>
                  <td>{formatCurrency(o.amount, o.currency, locale)}</td>
                  <td className="muted">{o.provider}</td>
                  <td><Badge tone={tone(o.status)}>{o.status}</Badge></td>
                  <td className="muted">{formatDate(o.created_at, locale)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <p className="hint" style={{ marginTop: "1rem" }}>{t("ordersNote")}</p>
      </div>
    </DashboardShell>
  );
}
