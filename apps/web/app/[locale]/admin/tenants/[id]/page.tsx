"use client";

import { useLocale, useTranslations } from "next-intl";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import type { AnalyticsBundle } from "@/lib/api";
import { authFetch } from "@/lib/auth";
import { formatNumber } from "@/lib/datetime";
import type { Locale } from "@/i18n/routing";
import { DashboardShell, useAdminNav } from "@/components/shell";
import { Alert, Spinner, Stat } from "@/components/ui";

export default function TenantDetail() {
  const t = useTranslations("admin");
  const locale = useLocale() as Locale;
  const nav = useAdminNav();
  const params = useParams<{ id: string }>();
  const id = params.id;
  const [data, setData] = useState<AnalyticsBundle | null>(null);
  const [note, setNote] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    authFetch<AnalyticsBundle>(`/admin/analytics?tenant=${encodeURIComponent(id)}`)
      .then(setData)
      .catch(() => setData(null));
  }, [id]);

  async function setTracking(enabled: boolean) {
    await authFetch(`/admin/tenants/${id}/tracking`, { body: { enabled } }).catch(() => {});
    setNote(enabled ? t("tenantDetail.noteTrackingOn") : t("tenantDetail.noteTrackingOff"));
  }

  async function exportData() {
    const out = await authFetch<unknown>(`/admin/tenants/${id}/export`).catch(() => null);
    if (!out) return;
    const blob = new Blob([JSON.stringify(out, null, 2)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `tenant-${id}-export.json`;
    a.click();
    URL.revokeObjectURL(a.href);
  }

  async function erase() {
    if (!window.confirm(t("tenantDetail.eraseConfirm"))) return;
    await authFetch(`/admin/tenants/${id}/erase`, { method: "POST" }).catch(() => {});
    setNote(t("tenantDetail.noteErased"));
  }

  async function setStatus(status: string) {
    await authFetch(`/admin/tenants/${id}/status`, { body: { status } }).catch(() => {});
    setNote(status === "suspended" ? t("tenantDetail.noteSuspended") : t("tenantDetail.noteActivated"));
  }

  const fd = data?.four_dimensions;
  const pct = (v: number) => formatNumber(v, locale, { style: "percent", maximumFractionDigits: 0 });

  return (
    <DashboardShell title={t("tenantDetail.title")} nav={nav} requireAdmin loginHref="/admin/login">
      <p style={{ marginTop: "-1rem" }} className="muted">{t("tenantDetail.tenantId", { id })}</p>
      {note ? <Alert kind="success">{note}</Alert> : null}

      <div className="stat-grid" style={{ marginBottom: "1.5rem" }}>
        <Stat label={t("common.latencyP95")} value={fd?.latency?.p95_ms != null ? `${formatNumber(fd.latency.p95_ms, locale)} ${t("common.ms")}` : "—"} />
        <Stat label={t("common.noPaidShare")} value={fd?.cost?.no_paid_share != null ? pct(fd.cost.no_paid_share) : "—"} />
        <Stat label={t("common.costCredits")} value={fd?.cost?.total != null ? formatNumber(fd.cost.total, locale) : "—"} />
        <Stat label={t("common.assistantTurns")} value={fd?.reliability?.turns != null ? formatNumber(fd.reliability.turns, locale) : "—"} />
      </div>

      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <h3>{t("tenantDetail.lifecycleTitle")}</h3>
        <p className="hint">{t("tenantDetail.lifecycleHint")}</p>
        <div className="row" style={{ flexWrap: "wrap" }}>
          <button className="btn btn-danger" onClick={() => void setStatus("suspended")}>{t("tenantDetail.suspend")}</button>
          <button className="btn btn-soft" onClick={() => void setStatus("active")}>{t("tenantDetail.activate")}</button>
        </div>
      </div>

      <div className="card">
        <h3>{t("tenantDetail.governanceTitle")}</h3>
        <p className="hint">{t("tenantDetail.governanceHint")}</p>
        <div className="row" style={{ flexWrap: "wrap" }}>
          <button className="btn btn-soft" onClick={() => void setTracking(true)}>{t("tenantDetail.enableTracking")}</button>
          <button className="btn btn-soft" onClick={() => void setTracking(false)}>{t("tenantDetail.disableTracking")}</button>
          <button className="btn btn-ghost" onClick={() => void exportData()}>{t("tenantDetail.exportData")}</button>
          <button className="btn btn-danger" onClick={() => void erase()}>{t("tenantDetail.eraseData")}</button>
        </div>
      </div>
    </DashboardShell>
  );
}
