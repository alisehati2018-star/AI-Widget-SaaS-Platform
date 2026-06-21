"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { ApiError } from "../../lib/api";
import { signup } from "../../lib/auth";
import { Alert, Brand, Field, Input, Spinner } from "../../components/ui";

export default function SignupPage() {
  const router = useRouter();
  const [form, setForm] = useState({ store_name: "", full_name: "", email: "", password: "" });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  function update(k: keyof typeof form) {
    return (e: React.ChangeEvent<HTMLInputElement>) => setForm({ ...form, [k]: e.target.value });
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const user = await signup(form);
      router.replace(user.role === "platform_admin" ? "/admin" : "/dashboard");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong.");
      setBusy(false);
    }
  }

  return (
    <div className="auth-wrap">
      <div className="auth-card wide">
        <div className="center" style={{ marginBottom: "1.5rem" }}>
          <Brand />
        </div>
        <div className="card card-glow">
          <h2 style={{ marginBottom: "0.3rem" }}>Create your store</h2>
          <p style={{ fontSize: "0.9rem" }}>Start free — no credit card required.</p>
          {error ? <Alert kind="error">{error}</Alert> : null}
          <form onSubmit={submit}>
            <Field label="Store name">
              <Input value={form.store_name} onChange={update("store_name")} placeholder="Acme Shop" required />
            </Field>
            <Field label="Your name">
              <Input value={form.full_name} onChange={update("full_name")} placeholder="Jane Doe" />
            </Field>
            <Field label="Work email">
              <Input type="email" value={form.email} onChange={update("email")} placeholder="you@store.com" required />
            </Field>
            <Field label="Password" hint="At least 10 characters, mixing letters, digits and symbols.">
              <Input type="password" value={form.password} onChange={update("password")} placeholder="••••••••••" required />
            </Field>
            <button className="btn btn-primary btn-block btn-lg" disabled={busy}>
              {busy ? <Spinner /> : "Create account"}
            </button>
          </form>
          <p className="hint center" style={{ marginTop: "0.8rem" }}>
            By creating an account you agree to our{" "}
            <Link href="/legal/terms" className="grad-text">Terms</Link> and{" "}
            <Link href="/legal/privacy" className="grad-text">Privacy Policy</Link>.
          </p>
          <p className="center" style={{ marginTop: "1rem", marginBottom: 0, fontSize: "0.9rem" }}>
            Already have an account? <Link href="/login" className="grad-text">Sign in</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
