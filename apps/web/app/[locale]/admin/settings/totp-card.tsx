"use client";

import { useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";
import { ApiError } from "@/lib/api";
import { adminFetch } from "@/lib/auth";
import { Alert, Badge, Field, Input, Spinner } from "@/components/ui";

interface Enrollment { secret: string; otpauth_uri: string }

/** Two-factor auth (TOTP) card for the signed-in platform admin: enroll with
 *  password → scan/import the secret → confirm a live code → enforced at
 *  login. Disabling requires the password AND a live code. */
export function TotpCard() {
  const t = useTranslations("admin");
  const [enabled, setEnabled] = useState<boolean | null>(null);
  const [enrollment, setEnrollment] = useState<Enrollment | null>(null);
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [note, setNote] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [loadFailed, setLoadFailed] = useState(false);
  const reload = useCallback(() => {
    setLoadFailed(false);
    adminFetch<{ totp_enabled: boolean }>("/admin/auth/totp", { method: "GET" })
      .then((r) => setEnabled(r.totp_enabled))
      .catch(() => {
        setEnabled(null);
        setLoadFailed(true);
      });
  }, []);
  useEffect(() => reload(), [reload]);

  function fail(err: unknown) {
    setError(err instanceof ApiError ? err.message : t("settings.genericError"));
  }

  async function enroll(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true); setError(null); setNote(null);
    try {
      const r = await adminFetch<Enrollment>("/admin/auth/totp/enroll", {
        body: { current_password: password },
      });
      setEnrollment(r);
      setPassword("");
    } catch (err) { fail(err); } finally { setBusy(false); }
  }

  async function confirm(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true); setError(null);
    try {
      await adminFetch("/admin/auth/totp/confirm", { body: { totp_code: code.trim() } });
      setEnrollment(null); setCode(""); setNote(t("settings.totpEnabledNote"));
      reload();
    } catch (err) { fail(err); } finally { setBusy(false); }
  }

  async function disable(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true); setError(null); setNote(null);
    try {
      await adminFetch("/admin/auth/totp/disable", {
        body: { current_password: password, totp_code: code.trim() },
      });
      setPassword(""); setCode(""); setNote(t("settings.totpDisabledNote"));
      reload();
    } catch (err) { fail(err); } finally { setBusy(false); }
  }

  return (
    <div className="card">
      <div className="row" style={{ gap: ".5rem" }}>
        <h3 style={{ margin: 0 }}>{t("settings.totpTitle")}</h3>
        {enabled === null ? null : enabled
          ? <Badge tone="success">{t("settings.totpOn")}</Badge>
          : <Badge>{t("settings.totpOff")}</Badge>}
      </div>
      <p className="muted" style={{ fontSize: ".9rem" }}>{t("settings.totpBody")}</p>
      {note ? <Alert kind="success">{note}</Alert> : null}
      {error ? <Alert kind="error">{error}</Alert> : null}

      {loadFailed ? (
        <>
          <p className="muted">{t("common.loadFailed")}</p>
          <button className="btn btn-soft" onClick={reload}>{t("common.retry")}</button>
        </>
      ) : enabled === null ? (
        <Spinner />
      ) : null}

      {enabled === false && !enrollment ? (
        <form onSubmit={enroll}>
          <Field label={t("settings.currentPw")}>
            <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          </Field>
          <button className="btn btn-primary" disabled={busy}>
            {busy ? <Spinner /> : t("settings.totpEnroll")}
          </button>
        </form>
      ) : null}

      {enrollment ? (
        <form onSubmit={confirm}>
          <p className="hint">{t("settings.totpScanHint")}</p>
          <Field label={t("settings.totpSecret")}>
            <Input dir="ltr" readOnly value={enrollment.secret} onFocus={(e) => e.target.select()} />
          </Field>
          <Field label={t("settings.totpUri")}>
            <Input dir="ltr" readOnly value={enrollment.otpauth_uri} onFocus={(e) => e.target.select()} />
          </Field>
          <Field label={t("settings.totpCode")}>
            <Input dir="ltr" inputMode="numeric" maxLength={6} value={code}
              onChange={(e) => setCode(e.target.value)} placeholder="123456" required />
          </Field>
          <button className="btn btn-primary" disabled={busy}>
            {busy ? <Spinner /> : t("settings.totpConfirm")}
          </button>
        </form>
      ) : null}

      {enabled ? (
        <form onSubmit={disable}>
          <Field label={t("settings.currentPw")}>
            <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          </Field>
          <Field label={t("settings.totpCode")}>
            <Input dir="ltr" inputMode="numeric" maxLength={6} value={code}
              onChange={(e) => setCode(e.target.value)} placeholder="123456" required />
          </Field>
          <button className="btn btn-danger" disabled={busy}>
            {busy ? <Spinner /> : t("settings.totpDisable")}
          </button>
        </form>
      ) : null}
    </div>
  );
}
