"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";
import { ApiError } from "@/lib/api";
import { authFetch, useSession } from "@/lib/auth";
import { DashboardShell, useAdminNav } from "@/components/shell";
import { Alert, Badge, Field, Input, Spinner } from "@/components/ui";

export default function AdminSettings() {
  const t = useTranslations("admin");
  const tv = useTranslations("validation");
  const nav = useAdminNav();
  const { user } = useSession();
  const security = [t("settings.sec1"), t("settings.sec2"), t("settings.sec3"), t("settings.sec4")];

  const [pw, setPw] = useState({ current: "", next: "", confirm: "" });
  const [pwNote, setPwNote] = useState<string | null>(null);
  const [pwError, setPwError] = useState<string | null>(null);
  const [pwBusy, setPwBusy] = useState(false);

  const [em, setEm] = useState({ password: "", email: "" });
  const [emNote, setEmNote] = useState<string | null>(null);
  const [emError, setEmError] = useState<string | null>(null);
  const [emBusy, setEmBusy] = useState(false);

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
      setPwError(err instanceof ApiError ? err.message : t("settings.genericError"));
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
      setEmError(err instanceof ApiError ? err.message : t("settings.genericError"));
    } finally {
      setEmBusy(false);
    }
  }

  return (
    <DashboardShell title={t("settings.title")} nav={nav} requireAdmin loginHref="/admin/login">
      <div className="dash-2col">
        <div className="card-stack">
          <div className="card">
            <h3>{t("settings.accountTitle")}</h3>
            <table className="table">
              <tbody>
                <tr><td className="muted">{t("settings.email")}</td><td>{user?.email ?? "—"}</td></tr>
                <tr><td className="muted">{t("settings.role")}</td><td><Badge tone="brand">{t("settings.platformAdmin")}</Badge></td></tr>
              </tbody>
            </table>
          </div>

          <div className="card">
            <h3>{t("settings.changePwTitle")}</h3>
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

        <div className="card-stack">
          <div className="card">
            <h3>{t("settings.securityTitle")}</h3>
            <ul className="feature-list">
              {security.map((s) => (
                <li key={s}>{s}</li>
              ))}
            </ul>
            <p className="hint">{t("settings.securityHint")}</p>
          </div>

          <div className="card">
            <h3>{t("settings.platformTitle")}</h3>
            <p className="muted" style={{ marginBottom: 0 }}>{t("settings.platformBody")}</p>
          </div>
        </div>
      </div>
    </DashboardShell>
  );
}
