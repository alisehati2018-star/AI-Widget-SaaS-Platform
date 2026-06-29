"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { apiFetch, ApiError } from "@/lib/api";
import { Link } from "@/i18n/navigation";
import { Alert, Brand, Field, Input, Spinner } from "@/components/ui";

export default function ResetPasswordPage() {
  const t = useTranslations("auth");
  const tValidation = useTranslations("validation");
  const tErrors = useTranslations("errors");
  const [token, setToken] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);

  // Read the token from the URL on the client (avoids useSearchParams prerender).
  useEffect(() => {
    const tk = new URLSearchParams(window.location.search).get("token");
    if (tk) setToken(tk);
  }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (password !== confirm) {
      setError(tValidation("passwordMismatch"));
      return;
    }
    setBusy(true);
    try {
      await apiFetch("/auth/password/reset-confirm", { body: { token, password } });
      setDone(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : tErrors("saveFailed"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-wrap">
      <div className="auth-card">
        <div className="center" style={{ marginBottom: "1.5rem" }}>
          <Brand />
        </div>
        <div className="card card-glow">
          <h2 style={{ marginBottom: "0.3rem" }}>{t("reset.title")}</h2>
          {done ? (
            <>
              <Alert kind="success">{t("reset.success")}</Alert>
              <Link href="/login" className="btn btn-primary btn-block">
                {t("reset.goSignIn")}
              </Link>
            </>
          ) : (
            <>
              {error ? <Alert kind="error">{error}</Alert> : null}
              <form onSubmit={submit}>
                {!token ? (
                  <Field label={t("reset.tokenLabel")} hint={t("reset.tokenHint")}>
                    <Input value={token} onChange={(e) => setToken(e.target.value)} required />
                  </Field>
                ) : null}
                <Field label={t("reset.newPassword")} hint={t("shared.passwordHint")}>
                  <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
                </Field>
                <Field label={t("reset.confirmPassword")}>
                  <Input type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} required />
                </Field>
                <button className="btn btn-primary btn-block btn-lg" disabled={busy}>
                  {busy ? <Spinner /> : t("reset.submit")}
                </button>
              </form>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
