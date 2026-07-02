"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { apiFetch, type TenantProfile } from "@/lib/api";
import { authFetch, useSession } from "@/lib/auth";
import { formatNumber } from "@/lib/datetime";
import type { Locale } from "@/i18n/routing";
import { Link } from "@/i18n/navigation";
import { DashboardShell, useOwnerNav } from "@/components/shell";
import { Alert, Badge, Stat } from "@/components/ui";

interface WidgetInfo { ready: boolean; has_widget_key: boolean }
interface SyncStatus { sources: { source: string }[]; docs_indexed: number | null }

export default function DashboardHome() {
  const t = useTranslations("dashboard");
  const locale = useLocale() as Locale;
  const nav = useOwnerNav();
  const { user } = useSession();
  const [profile, setProfile] = useState<TenantProfile | null>(null);
  const [widget, setWidget] = useState<WidgetInfo | null>(null);
  const [sync, setSync] = useState<SyncStatus | null>(null);
  const [resent, setResent] = useState(false);

  useEffect(() => {
    authFetch<TenantProfile>("/tenant/profile").then(setProfile).catch(() => setProfile(null));
    authFetch<WidgetInfo>("/tenant/widget").then(setWidget).catch(() => setWidget(null));
    authFetch<SyncStatus>("/tenant/sync-status").then(setSync).catch(() => setSync(null));
  }, []);

  async function resendVerification() {
    if (!user?.email) return;
    try {
      await apiFetch("/auth/verify-request", { body: { email: user.email } });
    } catch {
      /* generic */
    } finally {
      setResent(true);
    }
  }

  const credits = profile?.credits;
  const remaining = credits?.cap != null ? Math.max(0, credits.cap - credits.spent) : null;
  const lowCredits =
    credits?.cap != null && credits.cap > 0 && remaining != null && remaining / credits.cap < 0.1;
  const store = profile?.name ?? t("overview.storeFallback");
  const num = (n: number | null | undefined) =>
    n != null ? formatNumber(Math.round(n), locale) : "—";

  // Onboarding checklist derived from REAL state — each step links to where
  // it gets done and ticks itself off as the store completes it.
  const steps: { key: string; done: boolean; label: string; href: string }[] = [
    {
      key: "verify",
      done: Boolean(profile?.email_verified),
      label: t("overview.stepVerify"),
      href: "/dashboard/settings",
    },
    {
      key: "connect",
      done: Boolean(profile?.settings?.store_url),
      label: t("overview.stepConnect"),
      href: "/dashboard/catalog",
    },
    {
      key: "sync",
      done: Boolean((sync?.docs_indexed ?? 0) > 0 || (sync?.sources.length ?? 0) > 0),
      label: t("overview.stepSync"),
      href: "/dashboard/catalog",
    },
    {
      key: "widget",
      done: Boolean(widget?.has_widget_key),
      label: t("overview.stepWidget"),
      href: "/dashboard/widget",
    },
  ];
  const doneCount = steps.filter((s) => s.done).length;

  return (
    <DashboardShell title={t("overview.title")} nav={nav}>
      {profile && !profile.email_verified ? (
        <Alert kind="error">
          {t("overview.verifyBanner")}{" "}
          {resent ? (
            <strong>{t("overview.verifySent")}</strong>
          ) : (
            <button className="btn btn-soft" style={{ marginInlineStart: "0.5rem" }} onClick={() => void resendVerification()}>
              {t("overview.verifyResend")}
            </button>
          )}
        </Alert>
      ) : null}
      {lowCredits ? (
        <div className="alert alert-warning" role="status">
          {t("overview.lowCreditsWarning", { remaining: num(remaining) })}{" "}
          <Link href="/dashboard/credits" className="btn btn-soft" style={{ marginInlineStart: "0.5rem" }}>
            {t("overview.lowCreditsCta")}
          </Link>
        </div>
      ) : null}
      <p style={{ marginTop: "-0.5rem" }}>
        {user?.full_name
          ? t("overview.welcomeNamed", { name: user.full_name, store })
          : t("overview.welcome", { store })}
      </p>
      <div className="stat-grid" style={{ marginBottom: "2rem" }}>
        <Stat label={t("overview.statPlan")} value={profile?.plan ?? "—"} />
        <Stat
          label={t("overview.statSubscription")}
          value={profile ? <Badge tone={profile.sub_status === "active" ? "success" : "warning"}>{profile.sub_status}</Badge> : "—"}
        />
        <Stat label={t("overview.statCreditsUsed")} value={num(credits?.spent)} />
        <Stat label={t("overview.statCreditsLeft")} value={num(remaining)} />
      </div>

      <div className="dash-2col">
        <div className="card">
          <div className="row-between">
            <h3 style={{ margin: 0 }}>{t("overview.checklistTitle")}</h3>
            <Badge tone={doneCount === steps.length ? "success" : undefined}>
              {t("overview.checklistProgress", {
                done: formatNumber(doneCount, locale),
                total: formatNumber(steps.length, locale),
              })}
            </Badge>
          </div>
          <table className="table" style={{ marginTop: "1rem" }}>
            <tbody>
              {steps.map((s) => (
                <tr key={s.key}>
                  <td style={{ width: 36 }}>
                    {s.done
                      ? <Badge tone="success">✓</Badge>
                      : <Badge>{t("overview.stepPending")}</Badge>}
                  </td>
                  <td className={s.done ? "muted" : undefined}>{s.label}</td>
                  <td style={{ textAlign: "left" }}>
                    {!s.done ? (
                      <Link className="btn btn-ghost" href={s.href}>{t("overview.stepGo")}</Link>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {doneCount === steps.length ? (
            <p className="hint">{t("overview.checklistDone")}</p>
          ) : null}
        </div>

        <div className="card">
          <h3>{t("overview.setupTitle")}</h3>
          <p>{t("overview.setupBody")}</p>
          <div className="row" style={{ marginTop: "1rem", flexWrap: "wrap" }}>
            <Link href="/onboarding" className="btn btn-primary">
              {t("overview.setupOpenGuide")}
            </Link>
            <Link href="/dashboard/keys" className="btn btn-ghost">
              {t("overview.setupApiKeys")}
            </Link>
            <Link href="/dashboard/catalog" className="btn btn-ghost">
              {t("overview.setupConnect")}
            </Link>
          </div>
        </div>
      </div>
    </DashboardShell>
  );
}
