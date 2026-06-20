"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiFetch, ApiError } from "../../lib/api";
import { Alert, Brand, Field, Input, Spinner } from "../../components/ui";

export default function ResetPasswordPage() {
  const [token, setToken] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);

  // Read the token from the URL on the client (avoids useSearchParams prerender).
  useEffect(() => {
    const t = new URLSearchParams(window.location.search).get("token");
    if (t) setToken(t);
  }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (password !== confirm) {
      setError("Passwords do not match.");
      return;
    }
    setBusy(true);
    try {
      await apiFetch("/auth/password/reset-confirm", { body: { token, password } });
      setDone(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not reset password.");
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
          <h2 style={{ marginBottom: "0.3rem" }}>Set a new password</h2>
          {done ? (
            <>
              <Alert kind="success">Your password has been set. You can now sign in.</Alert>
              <Link href="/login" className="btn btn-primary btn-block">Go to sign in</Link>
            </>
          ) : (
            <>
              {error ? <Alert kind="error">{error}</Alert> : null}
              <form onSubmit={submit}>
                {!token ? (
                  <Field label="Reset token" hint="Paste the token from your reset/invite link.">
                    <Input value={token} onChange={(e) => setToken(e.target.value)} required />
                  </Field>
                ) : null}
                <Field label="New password" hint="At least 10 characters, mixing letters, digits and symbols.">
                  <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
                </Field>
                <Field label="Confirm password">
                  <Input type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} required />
                </Field>
                <button className="btn btn-primary btn-block btn-lg" disabled={busy}>
                  {busy ? <Spinner /> : "Set password"}
                </button>
              </form>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
