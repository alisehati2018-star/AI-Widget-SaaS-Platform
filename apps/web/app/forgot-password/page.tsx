"use client";

import Link from "next/link";
import { useState } from "react";
import { apiFetch } from "../../lib/api";
import { Alert, Brand, Field, Input, Spinner } from "../../components/ui";

export default function ForgotPasswordPage() {
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
          <h2 style={{ marginBottom: "0.3rem" }}>Reset your password</h2>
          {done ? (
            <Alert kind="success">
              If an account exists for that email, we&apos;ve sent reset instructions.
            </Alert>
          ) : (
            <>
              <p style={{ fontSize: "0.9rem" }}>Enter your email and we&apos;ll send a reset link.</p>
              <form onSubmit={submit}>
                <Field label="Email">
                  <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@store.com" required />
                </Field>
                <button className="btn btn-primary btn-block" disabled={busy}>
                  {busy ? <Spinner /> : "Send reset link"}
                </button>
              </form>
            </>
          )}
          <p className="center" style={{ marginTop: "1rem", marginBottom: 0, fontSize: "0.9rem" }}>
            <Link href="/login" className="grad-text">Back to sign in</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
