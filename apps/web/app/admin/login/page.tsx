"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { ApiError } from "../../../lib/api";
import { clearTokens, login } from "../../../lib/auth";
import { Alert, Brand, Field, Input, Spinner } from "../../../components/ui";

export default function AdminLoginPage() {
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
      if (user.role !== "platform_admin") {
        clearTokens();
        setError("This account is not a platform administrator.");
        setBusy(false);
        return;
      }
      router.replace("/admin");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong.");
      setBusy(false);
    }
  }

  return (
    <div className="auth-wrap">
      <div className="auth-card">
        <div className="center" style={{ marginBottom: "1.5rem" }}>
          <Brand href="/admin" />
        </div>
        <div className="card card-glow">
          <div className="row" style={{ marginBottom: "0.3rem" }}>
            <h2 style={{ margin: 0 }}>Admin sign in</h2>
            <span className="badge badge-brand">Platform</span>
          </div>
          <p style={{ fontSize: "0.9rem" }}>Restricted to platform administrators.</p>
          {error ? <Alert kind="error">{error}</Alert> : null}
          <form onSubmit={submit}>
            <Field label="Admin email">
              <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="admin@vitrin.ai" required />
            </Field>
            <Field label="Password">
              <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••••" required />
            </Field>
            <button className="btn btn-primary btn-block btn-lg" disabled={busy}>
              {busy ? <Spinner /> : "Sign in to console"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
