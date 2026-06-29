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

export default function DashboardHome() {
  const t = useTranslations("dashboard");
  const locale = useLocale() as Locale;
  const nav = useOwnerNav();
  const { user } = useSession();
  const [profile, setProfile] = useState<TenantProfile | null>(null);
  const [resent, setResent] = useState(false);

  useEffect(() => {
    authFetch<TenantProfile>("/tenant/profile").then(setProfile).catch(() => setProfile(null));
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
  const store = profile?.name ?? t("overview.storeFallback");
  const num = (n: number | null | undefined) =>
    n != null ? formatNumber(Math.round(n), locale) : "—";

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
    </DashboardShell>
  );
}
