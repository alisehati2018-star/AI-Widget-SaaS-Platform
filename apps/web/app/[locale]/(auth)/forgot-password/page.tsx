"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";
import { apiFetch } from "@/lib/api";
import { Link } from "@/i18n/navigation";
import { Alert, Brand, Field, Input, Spinner } from "@/components/ui";

export default function ForgotPasswordPage() {
  const t = useTranslations("auth");
  const [email, setEmail] = useState("");
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await apiFetch("/auth/password/reset-request", { body: { email } });
    } catch {
      /* generic by design — never reveal whether the email exists */
    } finally {
      setDone(true);
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
          <h2 style={{ marginBottom: "0.3rem" }}>{t("forgot.title")}</h2>
          {done ? (
            <Alert kind="success">{t("forgot.success")}</Alert>
          ) : (
            <>
              <p style={{ fontSize: "0.9rem" }}>{t("forgot.intro")}</p>
              <form onSubmit={submit}>
                <Field label={t("shared.emailLabel")}>
                  <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder={t("shared.emailPlaceholder")} required />
                </Field>
                <button className="btn btn-primary btn-block" disabled={busy}>
                  {busy ? <Spinner /> : t("forgot.submit")}
                </button>
              </form>
            </>
          )}
          <p className="center" style={{ marginTop: "1rem", marginBottom: 0, fontSize: "0.9rem" }}>
            <Link href="/login" className="grad-text">
              {t("forgot.backToSignIn")}
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
