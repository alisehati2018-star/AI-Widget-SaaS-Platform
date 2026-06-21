"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiFetch, type ApiKey, type TenantProfile } from "../../lib/api";
import { authFetch, useSession } from "../../lib/auth";
import { DashboardShell, OWNER_NAV } from "../../components/shell";
import { Loading } from "../../components/states";

interface Step {
  title: string;
  body: string;
  done: boolean;
  cta: { href: string; label: string } | null;
  action?: () => void;
  actionLabel?: string;
}

export default function OnboardingPage() {
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
      <DashboardShell title="Get started" nav={OWNER_NAV}>
        <Loading />
      </DashboardShell>
    );
  }

  const hasWidgetKey = keys.some((k) => k.scope === "widget" && !k.revoked);
  const hasSyncKey = keys.some((k) => k.scope === "sync" && !k.revoked);
  const connected = Boolean(profile.settings.store_url);

  const steps: Step[] = [
    {
      title: "Verify your email",
      body: "Confirm your email to unlock plan purchases and secure your account.",
      done: profile.email_verified,
      cta: null,
      action: resend,
      actionLabel: resent ? "Verification sent ✓" : "Resend verification",
    },
    {
      title: "Connect your store",
      body: "Tell us where your storefront lives so we can index your catalogue.",
      done: connected,
      cta: { href: "/dashboard/catalog", label: "Connect store" },
    },
    {
      title: "Create API keys",
      body: "Generate a sync key (catalogue import) and a widget key (storefront search + chat).",
      done: hasWidgetKey && hasSyncKey,
      cta: { href: "/dashboard/keys", label: "Create keys" },
    },
    {
      title: "Install the widget",
      body: "Embed the search + chat widget on your storefront and match your brand.",
      done: hasWidgetKey && connected,
      cta: { href: "/dashboard/widget", label: "Install widget" },
    },
  ];

  const doneCount = steps.filter((s) => s.done).length;
  const pct = Math.round((doneCount / steps.length) * 100);

  return (
    <DashboardShell title="Get started" nav={OWNER_NAV}>
      <p style={{ marginTop: "-1rem" }}>
        Welcome{user?.full_name ? `, ${user.full_name}` : ""}! Finish these steps to go live.
      </p>

      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <div className="row-between" style={{ marginBottom: "0.6rem" }}>
          <strong>{doneCount} of {steps.length} complete</strong>
          <span className="grad-text" style={{ fontWeight: 700 }}>{pct}%</span>
        </div>
        <div className="progress-track" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
          <div className="progress-fill" style={{ width: `${pct}%` }} />
        </div>
        {pct === 100 ? (
          <div style={{ marginTop: "1rem" }}>
            <Link href="/dashboard" className="btn btn-primary">You&apos;re all set → Go to dashboard</Link>
          </div>
        ) : null}
      </div>

      <div className="steps">
        {steps.map((s, i) => (
          <div key={s.title} className={`step${s.done ? " done" : ""}`}>
            <span className="step-num">{s.done ? "✓" : i + 1}</span>
            <div style={{ flex: 1 }}>
              <div className="row-between">
                <strong>{s.title}</strong>
                {s.done ? <span className="badge badge-success">done</span> : null}
              </div>
              <p style={{ margin: "0.3rem 0 0.8rem" }}>{s.body}</p>
              {!s.done ? (
                s.cta ? (
                  <Link href={s.cta.href} className="btn btn-soft">{s.cta.label}</Link>
                ) : s.action ? (
                  <button className="btn btn-soft" onClick={s.action}>{s.actionLabel}</button>
                ) : null
              ) : null}
            </div>
          </div>
        ))}
      </div>
    </DashboardShell>
  );
}
