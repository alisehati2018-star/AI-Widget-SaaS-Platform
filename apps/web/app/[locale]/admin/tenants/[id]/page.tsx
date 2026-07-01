"use client";

import { useLocale, useTranslations } from "next-intl";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import type { AnalyticsBundle } from "@/lib/api";
import { adminFetch as authFetch } from "@/lib/auth";
import { formatNumber } from "@/lib/datetime";
import type { Locale } from "@/i18n/routing";
import { DashboardShell, useAdminNav } from "@/components/shell";
import { Alert, Badge, Spinner, Stat } from "@/components/ui";
import { CreditsCard, LifecycleCard, PlanCard } from "./actions";
import { KeysCard, NotesCard, ProfileCard, type TenantDetail } from "./sections";

export default function TenantDetailPage() {
  const t = useTranslations("admin");
  const locale = useLocale() as Locale;
  const nav = useAdminNav();
  const params = useParams<{ id: string }>();
  const id = params.id;

  const [detail, setDetail] = useState<TenantDetail | null>(null);
  const [analytics, setAnalytics] = useState<AnalyticsBundle | null>(null);
  const [loadError, setLoadError] = useState(false);
  const [note, setNote] = useState<string | null>(null);

  const reload = useCallback(() => {
    if (!id) return;
    authFetch<TenantDetail>(`/admin/tenants/${id}`)
      .then((d) => { setDetail(d); setLoadError(false); })
      .catch(() => setLoadError(true));
  }, [id]);

  useEffect(() => {
    reload();
    if (!id) return;
    authFetch<AnalyticsBundle>(`/admin/analytics?tenant=${encodeURIComponent(id)}`)
      .then(setAnalytics)
      .catch(() => setAnalytics(null));
  }, [id, reload]);

  // Every mutation surfaces its confirmation AND refetches the profile so the
  // page always reflects the database, never a stale optimistic guess.
  function onDone(message: string) {
    setNote(message);
    reload();
  }

  const fd = analytics?.four_dimensions;
  const pct = (v: number) => formatNumber(v, locale, { style: "percent", maximumFractionDigits: 0 });

  if (loadError) {
    return (
      <DashboardShell title={t("tenantDetail.title")} nav={nav} requireAdmin loginHref="/admin/login">
        <Alert kind="error">{t("tenantDetail.loadFailed")}</Alert>
      </DashboardShell>
    );
  }
  if (!detail) {
    return (
      <DashboardShell title={t("tenantDetail.title")} nav={nav} requireAdmin loginHref="/admin/login">
        <Spinner />
      </DashboardShell>
    );
  }

  return (
    <DashboardShell title={detail.name} nav={nav} requireAdmin loginHref="/admin/login">
      <div className="row" style={{ marginTop: "-1rem", marginBottom: "1.5rem", flexWrap: "wrap", gap: ".6rem" }}>
        <code>{detail.slug}</code>
        <Badge tone={detail.status === "active" ? "success" : "warning"}>{detail.status}</Badge>
        {detail.subscription.plan_name ? <Badge tone="brand">{detail.subscription.plan_name}</Badge> : null}
      </div>
      {note ? <Alert kind="success">{note}</Alert> : null}

      <div className="stat-grid" style={{ marginBottom: "1.5rem" }}>
        <Stat label={t("common.latencyP95")} value={fd?.latency?.p95_ms != null ? `${formatNumber(fd.latency.p95_ms, locale)} ${t("common.ms")}` : "—"} />
        <Stat label={t("common.noPaidShare")} value={fd?.cost?.no_paid_share != null ? pct(fd.cost.no_paid_share) : "—"} />
        <Stat label={t("common.costCredits")} value={fd?.cost?.total != null ? formatNumber(fd.cost.total, locale) : "—"} />
        <Stat label={t("common.assistantTurns")} value={fd?.reliability?.turns != null ? formatNumber(fd.reliability.turns, locale) : "—"} />
      </div>

      <div className="dash-2col">
        <div className="card-stack">
          <ProfileCard d={detail} />
          <KeysCard d={detail} onDone={onDone} />
          <NotesCard key={detail.admin_notes ?? ""} d={detail} onDone={onDone} />
        </div>
        <div className="card-stack">
          <CreditsCard d={detail} onDone={onDone} />
          <PlanCard d={detail} onDone={onDone} />
          <LifecycleCard d={detail} onDone={onDone} />
        </div>
      </div>
    </DashboardShell>
  );
}
