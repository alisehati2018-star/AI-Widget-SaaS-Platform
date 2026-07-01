"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { ApiError, type TenantProfile } from "@/lib/api";
import { authFetch, useSession } from "@/lib/auth";
import { DashboardShell, useOwnerNav } from "@/components/shell";
import { Alert, Badge, Field, Input, Spinner } from "@/components/ui";

export default function SettingsPage() {
  const t = useTranslations("dashboard");
  const tv = useTranslations("validation");
  const nav = useOwnerNav();
  const { user } = useSession();
  const [profile, setProfile] = useState<TenantProfile | null>(null);
  const [tracking, setTracking] = useState(true);
  const [note, setNote] = useState<string | null>(null);
  const [pw, setPw] = useState({ current: "", next: "", confirm: "" });
  const [pwNote, setPwNote] = useState<string | null>(null);
  const [pwError, setPwError] = useState<string | null>(null);
  const [pwBusy, setPwBusy] = useState(false);
  const [em, setEm] = useState({ password: "", email: "" });
  const [emNote, setEmNote] = useState<string | null>(null);
  const [emError, setEmError] = useState<string | null>(null);
  const [emBusy, setEmBusy] = useState(false);

  useEffect(() => {
    authFetch<TenantProfile>("/tenant/profile")
      .then((p) => {
        setProfile(p);
        setTracking(p.tracking_enabled);
      })
      .catch(() => setProfile(null));
  }, []);

  async function toggleTracking() {
    const next = !tracking;
    setTracking(next);
    await authFetch("/tenant/tracking", { body: { enabled: next } }).catch(() => {});
    setNote(next ? t("settings.trackingEnabled") : t("settings.trackingDisabled"));
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

  async function eraseData() {
    if (!profile) return;
    const confirm = window.prompt(t("settings.erasePrompt", { slug: profile.slug }));
    if (confirm === null) return;
    try {
      await authFetch("/tenant/erase", { body: { confirm } });
      setNote(t("settings.erased"));
    } catch {
      setNote(t("settings.eraseFailed"));
    }
  }

  async function changePassword(e: React.FormEvent) {
    e.preventDefault();
    setPwError(null);
    setPwNote(null);
    if (pw.next !== pw.confirm) {
      setPwError(tv("passwordMismatch"));
      return;
    }
    setPwBusy(true);
    try {
      await authFetch("/auth/change-password", {
        body: { current_password: pw.current, new_password: pw.next },
      });
      setPw({ current: "", next: "", confirm: "" });
      setPwNote(t("settings.pwUpdated"));
    } catch (err) {
      setPwError(err instanceof ApiError ? err.message : t("settings.eraseFailed"));
    } finally {
      setPwBusy(false);
    }
  }

  async function changeEmail(e: React.FormEvent) {
    e.preventDefault();
    setEmError(null);
    setEmNote(null);
    setEmBusy(true);
    try {
      await authFetch("/auth/change-email", {
        body: { current_password: em.password, new_email: em.email },
      });
      setEm({ password: "", email: "" });
      setEmNote(t("settings.emailChanged"));
    } catch (err) {
      setEmError(err instanceof ApiError ? err.message : t("settings.eraseFailed"));
    } finally {
      setEmBusy(false);
    }
  }

  const roleLabel = profile?.role === "store_owner" ? t("settings.roleOwner") : t("settings.roleStaff");

  return (
    <DashboardShell title={t("nav.settings")} nav={nav}>
      {note ? <Alert kind="success">{note}</Alert> : null}

      <div className="dash-2col">
        <div className="card-stack">
          <div className="card">
            <h3>{t("settings.storeTitle")}</h3>
            {profile ? (
              <table className="table">
                <tbody>
                  <tr><td className="muted">{t("settings.storeName")}</td><td>{profile.name}</td></tr>
                  <tr><td className="muted">{t("settings.slug")}</td><td>{profile.slug}</td></tr>
                  <tr><td className="muted">{t("settings.status")}</td><td><Badge tone="success">{profile.status}</Badge></td></tr>
                  <tr><td className="muted">{t("settings.plan")}</td><td>{profile.plan} ({profile.sub_status})</td></tr>
                  <tr><td className="muted">{t("settings.yourRole")}</td><td>{roleLabel}</td></tr>
                  <tr><td className="muted">{t("settings.account")}</td><td>{user?.email}</td></tr>
                </tbody>
              </table>
            ) : (
              <Spinner />
            )}
          </div>

          <div className="card">
            <div className="row-between">
              <div>
                <h3 style={{ margin: 0 }}>{t("settings.trackingTitle")}</h3>
                <p style={{ margin: "0.3rem 0 0" }} className="hint">{t("settings.trackingHint")}</p>
              </div>
              <button className={`btn ${tracking ? "btn-soft" : "btn-primary"}`} onClick={() => void toggleTracking()}>
                {tracking ? t("settings.trackingDisable") : t("settings.trackingEnable")}
              </button>
            </div>
          </div>

          <div className="card">
            <h3>{t("settings.privacyTitle")}</h3>
            <p className="hint">{t("settings.privacyHint")}</p>
            <div className="row" style={{ flexWrap: "wrap" }}>
              <button className="btn btn-ghost" onClick={() => void exportData()}>{t("settings.exportData")}</button>
              <button className="btn btn-danger" onClick={() => void eraseData()}>{t("settings.eraseData")}</button>
            </div>
          </div>
        </div>

        <div className="card-stack">
          <div className="card">
            <h3>{t("settings.changePwTitle")}</h3>
            <p className="hint">{t("settings.changePwHint")}</p>
            {pwNote ? <Alert kind="success">{pwNote}</Alert> : null}
            {pwError ? <Alert kind="error">{pwError}</Alert> : null}
            <form onSubmit={changePassword}>
              <Field label={t("settings.currentPw")}>
                <Input type="password" value={pw.current} onChange={(e) => setPw({ ...pw, current: e.target.value })} required />
              </Field>
              <Field label={t("settings.newPw")}>
                <Input type="password" value={pw.next} onChange={(e) => setPw({ ...pw, next: e.target.value })} required />
              </Field>
              <Field label={t("settings.confirmPw")}>
                <Input type="password" value={pw.confirm} onChange={(e) => setPw({ ...pw, confirm: e.target.value })} required />
              </Field>
              <button className="btn btn-primary" disabled={pwBusy}>
                {pwBusy ? <Spinner /> : t("settings.changePwSubmit")}
              </button>
            </form>
          </div>

          <div className="card">
            <h3>{t("settings.changeEmailTitle")}</h3>
            <p className="hint">{t("settings.changeEmailHint")}</p>
            {emNote ? <Alert kind="success">{emNote}</Alert> : null}
            {emError ? <Alert kind="error">{emError}</Alert> : null}
            <form onSubmit={changeEmail}>
              <Field label={t("settings.newEmail")}>
                <Input type="email" value={em.email} onChange={(e) => setEm({ ...em, email: e.target.value })} required />
              </Field>
              <Field label={t("settings.currentPw")}>
                <Input type="password" value={em.password} onChange={(e) => setEm({ ...em, password: e.target.value })} required />
              </Field>
              <button className="btn btn-primary" disabled={emBusy}>
                {emBusy ? <Spinner /> : t("settings.changeEmailSubmit")}
              </button>
            </form>
          </div>
        </div>
      </div>
    </DashboardShell>
  );
}
