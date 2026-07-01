"use client";

// Tenant-detail mutation sections: credit adjustment, plan change, lifecycle
// + governance. Every successful mutation reports up so the page refetches.

import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";
import { ApiError } from "@/lib/api";
import { adminFetch as authFetch } from "@/lib/auth";
import { formatNumber } from "@/lib/datetime";
import { useAdminResource } from "@/lib/hooks/useResource";
import type { Locale } from "@/i18n/routing";
import { Alert, Field, Input, Spinner } from "@/components/ui";
import type { TenantDetail } from "./sections";

export function CreditsCard({ d, onDone }: { d: TenantDetail; onDone: (msg: string) => void }) {
  const t = useTranslations("admin");
  const locale = useLocale() as Locale;
  const [delta, setDelta] = useState("");
  const [reason, setReason] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const num = (v: number) => formatNumber(v, locale);

  async function adjust(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    const value = parseFloat(delta);
    if (!value) {
      setErr(t("tenantDetail.creditDeltaInvalid"));
      return;
    }
    setBusy(true);
    try {
      await authFetch(`/admin/tenants/${d.id}/credits`, { body: { delta: value, reason } });
      setDelta("");
      setReason("");
      onDone(t("tenantDetail.creditAdjusted"));
    } catch (e2) {
      setErr(e2 instanceof ApiError ? e2.message : t("tenantDetail.actionFailed"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card">
      <h3>{t("tenantDetail.creditsTitle")}</h3>
      <table className="table">
        <tbody>
          <tr><td className="muted">{t("tenantDetail.creditsUsed")}</td><td>{num(d.credits.used)}</td></tr>
          <tr><td className="muted">{t("tenantDetail.creditsGranted")}</td><td>{num(d.credits.granted)}</td></tr>
          <tr>
            <td className="muted">{t("tenantDetail.creditsCap")}</td>
            <td>{d.credits.cap != null ? num(d.credits.cap) : "—"}</td>
          </tr>
        </tbody>
      </table>
      {!d.credits.within_plan ? (
        <Alert kind="error">{t("tenantDetail.creditsOverCap")}</Alert>
      ) : null}
      {err ? <Alert kind="error">{err}</Alert> : null}
      <form onSubmit={adjust} style={{ marginTop: ".5rem" }}>
        <Field label={t("tenantDetail.creditDelta")}>
          <Input
            type="number"
            step="any"
            value={delta}
            onChange={(e) => setDelta(e.target.value)}
            placeholder={t("tenantDetail.creditDeltaPlaceholder")}
            required
          />
        </Field>
        <Field label={t("tenantDetail.creditReason")}>
          <Input value={reason} onChange={(e) => setReason(e.target.value)} placeholder={t("tenantDetail.creditReasonPlaceholder")} />
        </Field>
        <button className="btn btn-primary" disabled={busy}>
          {busy ? <Spinner /> : t("tenantDetail.creditApply")}
        </button>
      </form>
    </div>
  );
}

interface PlanOption { code: string; name: string; price_monthly: number }

export function PlanCard({ d, onDone }: { d: TenantDetail; onDone: (msg: string) => void }) {
  const t = useTranslations("admin");
  const { data } = useAdminResource<{ plans: PlanOption[] }>("/admin/plans");
  const [code, setCode] = useState(d.subscription.plan_code ?? "");
  const [status, setStatus] = useState(d.subscription.status === "none" ? "active" : d.subscription.status);
  const [periodDays, setPeriodDays] = useState("30");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function apply(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    if (!code) {
      setErr(t("tenantDetail.planPickOne"));
      return;
    }
    setBusy(true);
    try {
      await authFetch(`/admin/tenants/${d.id}/plan`, {
        method: "PATCH",
        body: { plan_code: code, status, period_days: parseInt(periodDays, 10) || 30 },
      });
      onDone(t("tenantDetail.planChanged"));
    } catch (e2) {
      setErr(e2 instanceof ApiError ? e2.message : t("tenantDetail.actionFailed"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card">
      <h3>{t("tenantDetail.planTitle")}</h3>
      <p className="hint">{t("tenantDetail.planHint")}</p>
      {err ? <Alert kind="error">{err}</Alert> : null}
      <form onSubmit={apply}>
        <Field label={t("tenantDetail.planField")}>
          <select className="input" value={code} onChange={(e) => setCode(e.target.value)}>
            <option value="">{t("tenantDetail.planPickOne")}</option>
            {(data?.plans ?? []).map((p) => (
              <option key={p.code} value={p.code}>{p.name} — ${p.price_monthly}</option>
            ))}
          </select>
        </Field>
        <Field label={t("tenantDetail.planStatusField")}>
          <select className="input" value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="active">{t("tenantDetail.subActive")}</option>
            <option value="trialing">{t("tenantDetail.subTrialing")}</option>
            <option value="past_due">{t("tenantDetail.subPastDue")}</option>
            <option value="canceled">{t("tenantDetail.subCanceled")}</option>
          </select>
        </Field>
        <Field label={t("tenantDetail.planPeriodField")}>
          <Input type="number" min={1} max={366} value={periodDays} onChange={(e) => setPeriodDays(e.target.value)} />
        </Field>
        <button className="btn btn-primary" disabled={busy}>
          {busy ? <Spinner /> : t("tenantDetail.planApply")}
        </button>
      </form>
    </div>
  );
}

export function LifecycleCard({ d, onDone }: { d: TenantDetail; onDone: (msg: string) => void }) {
  const t = useTranslations("admin");

  async function setStatus(status: string) {
    await authFetch(`/admin/tenants/${d.id}/status`, { body: { status } }).catch(() => {});
    onDone(status === "suspended" ? t("tenantDetail.noteSuspended") : t("tenantDetail.noteActivated"));
  }

  async function setTracking(enabled: boolean) {
    await authFetch(`/admin/tenants/${d.id}/tracking`, { body: { enabled } }).catch(() => {});
    onDone(enabled ? t("tenantDetail.noteTrackingOn") : t("tenantDetail.noteTrackingOff"));
  }

  async function exportData() {
    const out = await authFetch<unknown>(`/admin/tenants/${d.id}/export`).catch(() => null);
    if (!out) return;
    const blob = new Blob([JSON.stringify(out, null, 2)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `tenant-${d.slug}-export.json`;
    a.click();
    URL.revokeObjectURL(a.href);
  }

  async function erase() {
    if (!window.confirm(t("tenantDetail.eraseConfirm"))) return;
    await authFetch(`/admin/tenants/${d.id}/erase`, { method: "POST", body: {} }).catch(() => {});
    onDone(t("tenantDetail.noteErased"));
  }

  return (
    <div className="card">
      <h3>{t("tenantDetail.lifecycleTitle")}</h3>
      <p className="hint">{t("tenantDetail.lifecycleHint")}</p>
      <div className="row" style={{ flexWrap: "wrap", marginBottom: "1rem" }}>
        {d.status === "active" ? (
          <button className="btn btn-danger" onClick={() => void setStatus("suspended")}>{t("tenantDetail.suspend")}</button>
        ) : (
          <button className="btn btn-soft" onClick={() => void setStatus("active")}>{t("tenantDetail.activate")}</button>
        )}
      </div>
      <h4>{t("tenantDetail.governanceTitle")}</h4>
      <p className="hint">{t("tenantDetail.governanceHint")}</p>
      <div className="row" style={{ flexWrap: "wrap" }}>
        {d.tracking_enabled ? (
          <button className="btn btn-soft" onClick={() => void setTracking(false)}>{t("tenantDetail.disableTracking")}</button>
        ) : (
          <button className="btn btn-soft" onClick={() => void setTracking(true)}>{t("tenantDetail.enableTracking")}</button>
        )}
        <button className="btn btn-ghost" onClick={() => void exportData()}>{t("tenantDetail.exportData")}</button>
        <button className="btn btn-danger" onClick={() => void erase()}>{t("tenantDetail.eraseData")}</button>
      </div>
    </div>
  );
}
