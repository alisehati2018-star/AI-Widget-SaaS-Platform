"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { apiFetch, type ApiKey, type TenantProfile } from "@/lib/api";
import { authFetch, useSession } from "@/lib/auth";
import { formatNumber } from "@/lib/datetime";
import type { Locale } from "@/i18n/routing";
import { Link } from "@/i18n/navigation";
import { DashboardShell, useOwnerNav } from "@/components/shell";
import { Loading } from "@/components/states";

interface Step {
  title: string;
  body: string;
  done: boolean;
  cta: { href: string; label: string } | null;
  action?: () => void;
  actionLabel?: string;
}

export default function OnboardingPage() {
  const t = useTranslations("dashboard");
  const locale = useLocale() as Locale;
  const nav = useOwnerNav();
  const { user } = useSession();
  const [profile, setProfile] = useState<TenantProfile | null>(null);
  const [keys, setKeys] = useState<ApiKey[] | null>(null);
  const [resent, setResent] = useState(false);

  function load() {
    authFetch<TenantProfile>("/tenant/profile").then(setProfile).catch(() => setProfile(null));
    authFetch<{ keys: ApiKey[] }>("/tenant/keys").then((r) => setKeys(r.keys)).catch(() => setKeys([]));
  }
  useEffect(() => load(), []);

  async function resend() {
    if (!user?.email) return;
    await apiFetch("/auth/verify-request", { body: { email: user.email } }).catch(() => {});
    setResent(true);
  }

  if (!profile || keys === null) {
    return (
      <DashboardShell title={t("getStarted.title")} nav={nav}>
        <Loading />
      </DashboardShell>
    );
  }

  const hasWidgetKey = keys.some((k) => k.scope === "widget" && !k.revoked);
  const hasSyncKey = keys.some((k) => k.scope === "sync" && !k.revoked);
  const connected = Boolean(profile.settings.store_url);

  const steps: Step[] = [
    {
      title: t("getStarted.steps.verifyTitle"),
      body: t("getStarted.steps.verifyBody"),
      done: profile.email_verified,
      cta: null,
      action: resend,
      actionLabel: resent ? t("getStarted.steps.verifySent") : t("getStarted.steps.verifyAction"),
    },
    {
      title: t("getStarted.steps.connectTitle"),
      body: t("getStarted.steps.connectBody"),
      done: connected,
      cta: { href: "/dashboard/catalog", label: t("getStarted.steps.connectCta") },
    },
    {
      title: t("getStarted.steps.keysTitle"),
      body: t("getStarted.steps.keysBody"),
      done: hasWidgetKey && hasSyncKey,
      cta: { href: "/dashboard/keys", label: t("getStarted.steps.keysCta") },
    },
    {
      title: t("getStarted.steps.widgetTitle"),
      body: t("getStarted.steps.widgetBody"),
      done: hasWidgetKey && connected,
      cta: { href: "/dashboard/widget", label: t("getStarted.steps.widgetCta") },
    },
  ];

  const doneCount = steps.filter((s) => s.done).length;
  const pct = Math.round((doneCount / steps.length) * 100);

  return (
    <DashboardShell title={t("getStarted.title")} nav={nav}>
      <p style={{ marginTop: "-1rem" }}>
        {user?.full_name
          ? t("getStarted.welcomeNamed", { name: user.full_name })
          : t("getStarted.welcome")}
      </p>

      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <div className="row-between" style={{ marginBottom: "0.6rem" }}>
          <strong>{t("getStarted.progress", { done: doneCount, total: steps.length })}</strong>
          <span className="grad-text" style={{ fontWeight: 700 }}>
            {formatNumber(pct, locale)}%
          </span>
        </div>
        <div className="progress-track" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
          <div className="progress-fill" style={{ width: `${pct}%` }} />
        </div>
        {pct === 100 ? (
          <div style={{ marginTop: "1rem" }}>
            <Link href="/dashboard" className="btn btn-primary">
              {t("getStarted.allSet")}
            </Link>
          </div>
        ) : null}
      </div>

      <div className="steps">
        {steps.map((s, i) => (
          <div key={s.title} className={`step${s.done ? " done" : ""}`}>
            <span className="step-num">{s.done ? "✓" : formatNumber(i + 1, locale)}</span>
            <div style={{ flex: 1 }}>
              <div className="row-between">
                <strong>{s.title}</strong>
                {s.done ? <span className="badge badge-success">{t("getStarted.doneBadge")}</span> : null}
              </div>
              <p style={{ margin: "0.3rem 0 0.8rem" }}>{s.body}</p>
              {!s.done ? (
                s.cta ? (
                  <Link href={s.cta.href} className="btn btn-soft">
                    {s.cta.label}
                  </Link>
                ) : s.action ? (
                  <button className="btn btn-soft" onClick={s.action}>
                    {s.actionLabel}
                  </button>
                ) : null
              ) : null}
            </div>
          </div>
        ))}
      </div>
    </DashboardShell>
  );
}
