"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiFetch, ApiError } from "../../lib/api";
import { Alert, Brand, Field, Input, Spinner } from "../../components/ui";

type State = "working" | "ok" | "error" | "manual";

export default function VerifyEmailPage() {
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
        setMessage(e instanceof ApiError ? e.message : "Verification failed.");
      });
  }, []);

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
          <h2 style={{ marginBottom: "0.3rem" }}>Email verification</h2>

          {state === "working" ? (
            <div className="center" style={{ padding: "1rem" }}><Spinner /></div>
          ) : null}

          {state === "ok" ? (
            <>
              <Alert kind="success">Your email is verified. You&apos;re all set!</Alert>
              <Link href="/dashboard" className="btn btn-primary btn-block">Go to dashboard</Link>
            </>
          ) : null}

          {state === "error" ? <Alert kind="error">{message}</Alert> : null}

          {state === "manual" || state === "error" ? (
            <>
              <p style={{ fontSize: "0.9rem" }}>
                Need a new verification link? Enter your email and we&apos;ll resend it.
              </p>
              {resent ? (
                <Alert kind="success">If that account exists and is unverified, a new link is on its way.</Alert>
              ) : (
                <form onSubmit={resend}>
                  <Field label="Email">
                    <Input type="email" value={resendEmail} onChange={(e) => setResendEmail(e.target.value)} placeholder="you@store.com" required />
                  </Field>
                  <button className="btn btn-primary btn-block">Resend verification</button>
                </form>
              )}
              <p className="center" style={{ marginTop: "1rem", marginBottom: 0, fontSize: "0.9rem" }}>
                <Link href="/login" className="grad-text">Back to sign in</Link>
              </p>
            </>
          ) : null}
        </div>
      </div>
    </div>
  );
}
