"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { apiFetch, ApiError } from "@/lib/api";
import { Link } from "@/i18n/navigation";
import { Alert, Brand, Field, Input, Spinner } from "@/components/ui";

type State = "working" | "ok" | "error" | "manual";

export default function VerifyEmailPage() {
  const t = useTranslations("auth");
  const tErrors = useTranslations("errors");
  const [state, setState] = useState<State>("manual");
  const [message, setMessage] = useState("");
  const [resendEmail, setResendEmail] = useState("");
  const [resent, setResent] = useState(false);

  useEffect(() => {
    const token = new URLSearchParams(window.location.search).get("token");
    if (!token) {
      setState("manual");
      return;
    }
    setState("working");
    apiFetch("/auth/verify-confirm", { body: { token } })
      .then(() => setState("ok"))
      .catch((e) => {
        setState("error");
        setMessage(e instanceof ApiError ? e.message : tErrors("generic"));
      });
  }, [tErrors]);

  async function resend(e: React.FormEvent) {
    e.preventDefault();
    try {
      await apiFetch("/auth/verify-request", { body: { email: resendEmail } });
    } catch {
      /* generic by design */
    } finally {
      setResent(true);
    }
  }

  return (
    <div className="auth-wrap">
      <div className="auth-card">
        <div className="center" style={{ marginBottom: "1.5rem" }}>
          <Brand />
        </div>
        <div className="card card-glow">
          <h2 style={{ marginBottom: "0.3rem" }}>{t("verify.title")}</h2>

          {state === "working" ? (
            <div className="center" style={{ padding: "1rem" }}>
              <Spinner />
            </div>
          ) : null}

          {state === "ok" ? (
            <>
              <Alert kind="success">{t("verify.success")}</Alert>
              <Link href="/dashboard" className="btn btn-primary btn-block">
                {t("verify.goDashboard")}
              </Link>
            </>
          ) : null}

          {state === "error" ? <Alert kind="error">{message}</Alert> : null}

          {state === "manual" || state === "error" ? (
            <>
              <p style={{ fontSize: "0.9rem" }}>{t("verify.manualIntro")}</p>
              {resent ? (
                <Alert kind="success">{t("verify.resent")}</Alert>
              ) : (
                <form onSubmit={resend}>
                  <Field label={t("shared.emailLabel")}>
                    <Input type="email" value={resendEmail} onChange={(e) => setResendEmail(e.target.value)} placeholder={t("shared.emailPlaceholder")} required />
                  </Field>
                  <button className="btn btn-primary btn-block">{t("verify.resend")}</button>
                </form>
              )}
              <p className="center" style={{ marginTop: "1rem", marginBottom: 0, fontSize: "0.9rem" }}>
                <Link href="/login" className="grad-text">
                  {t("verify.backToSignIn")}
                </Link>
              </p>
            </>
          ) : null}
        </div>
      </div>
    </div>
  );
}
