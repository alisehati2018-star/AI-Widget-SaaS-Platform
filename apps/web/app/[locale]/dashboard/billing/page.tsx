"use client";

import { useLocale, useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";
import { ApiError, getPlans, localizePlan, type BillingMeta, type MyOrder, type PlanInfo, type TenantProfile } from "@/lib/api";
import { authFetch } from "@/lib/auth";
import { formatCurrency, formatDate, formatNumber } from "@/lib/datetime";
import type { Locale } from "@/i18n/routing";
import { DashboardShell, useOwnerNav } from "@/components/shell";
import { InvoicesCard, type Invoice } from "./invoices-card";
import { Alert, Badge, Spinner } from "@/components/ui";

interface Preview {
  base_price: number;
  proration_credit: number;
  amount_due: number;
  currency: string;
  plan_name: string;
}

const TOPUP_CREDIT_CHOICES = [50000, 100000, 250000];

export default function BillingPage() {
  const t = useTranslations("billing");
  const tErrors = useTranslations("errors");
  const locale = useLocale() as Locale;
  const nav = useOwnerNav();
  const [plans, setPlans] = useState<PlanInfo[]>([]);
  const [billingMeta, setBillingMeta] = useState<BillingMeta | null>(null);
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
    getPlans()
      .then((r) => { setPlans(r.plans); setBillingMeta(r.billing ?? null); })
      .catch(() => setPlans([]));
    reload();
    // Returning from the payment gateway: surface the outcome once.
    const params = new URLSearchParams(window.location.search);
    const payment = params.get("payment");
    if (payment === "success") setNote(t("paymentSuccess"));
    else if (payment === "failed") setError(t("paymentFailed"));
    if (payment) {
      params.delete("payment");
      params.delete("ref");
      const rest = params.toString();
      window.history.replaceState({}, "", window.location.pathname + (rest ? `?${rest}` : ""));
    }
  }, [reload, t]);

  const [preview, setPreview] = useState<(Preview & { code: string }) | null>(null);

  async function checkout(code: string) {
    setPending(code);
    try {
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

  async function choose(code: string) {
    setError(null);
    setNote(null);
    setPreview(null);
    // Upgrading from a live paid plan → show the proration preview inline and
    // wait for an explicit confirm; fresh/trial stores check out directly.
    if (profile?.sub_status === "active" && profile.plan.toLowerCase() !== "free") {
      setPending(code);
      const pv = await authFetch<Preview>(`/tenant/billing/preview?plan_code=${code}`).catch(() => null);
      setPending(null);
      if (pv) {
        setPreview({ ...pv, code });
        return;
      }
    }
    await checkout(code);
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
              {(locale === "fa" ? profile?.plan_fa : profile?.plan) ?? profile?.plan ?? "—"}{" "}
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

      {preview ? (
        <div className="card" style={{ marginBottom: "1.5rem", borderColor: "var(--brand)" }}>
          <h3>{t("previewTitle", { plan: preview.plan_name })}</h3>
          <table className="table" style={{ maxWidth: 480 }}>
            <tbody>
              <tr>
                <td className="muted">{t("previewBase")}</td>
                <td>{formatCurrency(preview.base_price, preview.currency, locale)}</td>
              </tr>
              <tr>
                <td className="muted">{t("previewCredit")}</td>
                <td>−{formatCurrency(preview.proration_credit, preview.currency, locale)}</td>
              </tr>
              <tr>
                <td><strong>{t("previewDue")}</strong></td>
                <td><strong>{formatCurrency(preview.amount_due, preview.currency, locale)}</strong></td>
              </tr>
            </tbody>
          </table>
          <p className="hint">{t("previewHint")}</p>
          <div className="row" style={{ gap: ".5rem" }}>
            <button
              className="btn btn-primary"
              disabled={pending === preview.code}
              onClick={() => { const c = preview.code; setPreview(null); void checkout(c); }}
            >
              {pending === preview.code ? <Spinner /> : t("previewConfirmBtn")}
            </button>
            <button className="btn btn-soft" onClick={() => setPreview(null)}>{t("previewCancel")}</button>
          </div>
        </div>
      ) : null}

      <h3>{t("choosePlan")}</h3>
      <div className="pricing-grid" style={{ marginBottom: "2rem" }}>
        {plans.filter((p) => p.code !== "free").map((p) => {
          const current = profile?.plan_code
            ? profile.plan_code === p.code
            : profile?.plan?.toLowerCase() === p.name.toLowerCase();
          const custom = p.code === "enterprise";
          const loc = localizePlan(p, locale);
          return (
            <div className={`card price-card${p.code === "pro" ? " featured" : ""}`} key={p.code}>
              <h4 style={{ margin: 0 }}>{loc.name}</h4>
              <div className="price" style={custom ? { fontSize: "1.05rem", lineHeight: 2.2 } : undefined}>
                {custom ? t("contactSales") : formatCurrency(p.price_monthly, p.currency, locale)}
              </div>
              <ul className="feature-list">
                {loc.features.slice(0, 3).map((f) => <li key={f}>{f}</li>)}
              </ul>
              <button
                className={`btn ${p.code === "pro" ? "btn-primary" : "btn-ghost"} btn-block`}
                style={{ marginTop: "auto" }}
                disabled={current || pending === p.code || custom}
                onClick={() => void choose(p.code)}
              >
                {current ? t("current") : custom ? t("contactSales") : pending === p.code ? <Spinner /> : t("buy", { plan: loc.name })}
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
            {TOPUP_CREDIT_CHOICES.map((credits) => {
              const rate = billingMeta?.topup_credits_per_unit ?? 1000;
              const price = Math.round((credits / Math.max(1, rate)) * 100) / 100;
              return (
                <option key={credits} value={credits}>
                  {t("topupOption", { credits: formatNumber(credits, locale), price: formatNumber(price, locale) })}
                </option>
              );
            })}
          </select>
          <button className="btn btn-primary" disabled={pending === "topup"} onClick={() => void buyTopup()}>
            {pending === "topup" ? <Spinner /> : t("buyCredits")}
          </button>
        </div>
      </div>

      <InvoicesCard invoices={invoices} />

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
