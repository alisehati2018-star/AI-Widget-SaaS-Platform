"use client";

import { useEffect, useState } from "react";
import type { TenantProfile } from "../../../lib/api";
import { authFetch, useSession } from "../../../lib/auth";
import { DashboardShell, OWNER_NAV } from "../../../components/shell";
import { Alert, Badge, Spinner } from "../../../components/ui";

export default function SettingsPage() {
  const { user } = useSession();
  const [profile, setProfile] = useState<TenantProfile | null>(null);
  const [tracking, setTracking] = useState(true);
  const [note, setNote] = useState<string | null>(null);

  useEffect(() => {
    authFetch<TenantProfile>("/tenant/profile").then((p) => {
      setProfile(p);
      setTracking(p.tracking_enabled);
    }).catch(() => setProfile(null));
  }, []);

  async function toggleTracking() {
    const next = !tracking;
    setTracking(next);
    await authFetch("/tenant/tracking", { body: { enabled: next } }).catch(() => {});
    setNote(next ? "Behavioural tracking enabled." : "Behavioural tracking disabled.");
  }

  async function exportData() {
    const data = await authFetch<unknown>("/tenant/export").catch(() => null);
    if (!data) return;
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "vitrin-export.json";
    a.click();
  }

  return (
    <DashboardShell title="Settings" nav={OWNER_NAV}>
      {note ? <Alert kind="success">{note}</Alert> : null}

      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <h3>Store</h3>
        {profile ? (
          <table className="table">
            <tbody>
              <tr><td className="muted">Store name</td><td>{profile.name}</td></tr>
              <tr><td className="muted">Slug</td><td>{profile.slug}</td></tr>
              <tr><td className="muted">Status</td><td><Badge tone="success">{profile.status}</Badge></td></tr>
              <tr><td className="muted">Plan</td><td>{profile.plan} ({profile.sub_status})</td></tr>
              <tr><td className="muted">Your role</td><td>{profile.role.replace("store_", "")}</td></tr>
              <tr><td className="muted">Account</td><td>{user?.email}</td></tr>
            </tbody>
          </table>
        ) : (
          <Spinner />
        )}
      </div>

      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <div className="row-between">
          <div>
            <h3 style={{ margin: 0 }}>Behavioural tracking</h3>
            <p style={{ margin: "0.3rem 0 0" }} className="hint">
              Controls whether shopper behaviour is captured for analytics (GDPR).
            </p>
          </div>
          <button className={`btn ${tracking ? "btn-soft" : "btn-primary"}`} onClick={() => void toggleTracking()}>
            {tracking ? "Disable tracking" : "Enable tracking"}
          </button>
        </div>
      </div>

      <div className="card">
        <h3>Data &amp; privacy</h3>
        <p className="hint">Export your tenant&apos;s portable data. To erase all data, contact platform support.</p>
        <button className="btn btn-ghost" onClick={() => void exportData()}>Export my data (JSON)</button>
      </div>
    </DashboardShell>
  );
}
