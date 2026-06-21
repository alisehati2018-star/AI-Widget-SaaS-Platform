"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiFetch, type TenantProfile } from "../../lib/api";
import { authFetch, useSession } from "../../lib/auth";
import { DashboardShell, OWNER_NAV } from "../../components/shell";
import { Alert, Badge, Stat } from "../../components/ui";

export default function DashboardHome() {
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
  const remaining =
    credits?.cap != null ? Math.max(0, credits.cap - credits.spent) : null;

  return (
    <DashboardShell title="Overview" nav={OWNER_NAV}>
      {profile && !profile.email_verified ? (
        <Alert kind="error">
          Your email isn&apos;t verified yet — verify it to unlock plan purchases.{" "}
          {resent ? (
            <strong>Verification email sent.</strong>
          ) : (
            <button className="btn btn-soft" style={{ marginLeft: "0.5rem" }} onClick={() => void resendVerification()}>
              Resend verification
            </button>
          )}
        </Alert>
      ) : null}
      <p style={{ marginTop: "-0.5rem" }}>
        Welcome{user?.full_name ? `, ${user.full_name}` : ""}. Here&apos;s {profile?.name ?? "your store"} at a glance.
      </p>
      <div className="stat-grid" style={{ marginBottom: "2rem" }}>
        <Stat label="Plan" value={profile?.plan ?? "—"} />
        <Stat
          label="Subscription"
          value={profile ? <Badge tone={profile.sub_status === "active" ? "success" : "warning"}>{profile.sub_status}</Badge> : "—"}
        />
        <Stat label="Credits used" value={credits ? Math.round(credits.spent).toLocaleString() : "—"} />
        <Stat label="Credits left" value={remaining != null ? Math.round(remaining).toLocaleString() : "—"} />
      </div>

      <div className="card">
        <h3>Finish setting up</h3>
        <p>Connect your store and drop in the search widget to start seeing data.</p>
        <ol className="muted" style={{ paddingLeft: "1.2rem", lineHeight: 2 }}>
          <li>Create an API key and install the OpenCart / WooCommerce plugin.</li>
          <li>Run the first catalogue sync.</li>
          <li>Embed the Vitrin widget on your storefront.</li>
        </ol>
        <div className="row" style={{ marginTop: "1rem", flexWrap: "wrap" }}>
          <Link href="/dashboard/keys" className="btn btn-primary">Get your API key</Link>
          <Link href="/dashboard/catalog" className="btn btn-ghost">Connect store</Link>
          <Link href="/dashboard/widget" className="btn btn-ghost">Install widget</Link>
        </div>
      </div>
    </DashboardShell>
  );
}
