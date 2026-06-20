"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { ApiError } from "../../lib/api";
import { login } from "../../lib/auth";
import { Alert, Brand, Field, Input, Spinner } from "../../components/ui";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const user = await login(email, password);
      router.replace(user.role === "platform_admin" ? "/admin" : "/dashboard");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong.");
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
          <h2 style={{ marginBottom: "0.3rem" }}>Welcome back</h2>
          <p style={{ fontSize: "0.9rem" }}>Sign in to your store dashboard.</p>
          {error ? <Alert kind="error">{error}</Alert> : null}
          <form onSubmit={submit}>
            <Field label="Email">
              <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@store.com" required />
            </Field>
            <Field label="Password">
              <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••••" required />
            </Field>
            <button className="btn btn-primary btn-block btn-lg" disabled={busy}>
              {busy ? <Spinner /> : "Sign in"}
            </button>
          </form>
          <div className="row-between" style={{ marginTop: "1rem", fontSize: "0.9rem" }}>
            <Link href="/forgot-password" className="muted">Forgot password?</Link>
            <Link href="/signup" className="grad-text">Create account</Link>
          </div>
        </div>
      </div>
    </div>
  );
}
