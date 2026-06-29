"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";
import { ApiError } from "@/lib/api";
import { login } from "@/lib/auth";
import { Link, useRouter } from "@/i18n/navigation";
import { Alert, Brand, Field, Input, Spinner } from "@/components/ui";

export default function LoginPage() {
  const t = useTranslations("auth");
  const tErrors = useTranslations("errors");
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
      setError(err instanceof ApiError ? err.message : tErrors("generic"));
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
          <h2 style={{ marginBottom: "0.3rem" }}>{t("login.title")}</h2>
          <p style={{ fontSize: "0.9rem" }}>{t("login.subtitle")}</p>
          {error ? <Alert kind="error">{error}</Alert> : null}
          <form onSubmit={submit}>
            <Field label={t("shared.emailLabel")}>
              <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder={t("shared.emailPlaceholder")} required />
            </Field>
            <Field label={t("shared.passwordLabel")}>
              <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder={t("shared.passwordPlaceholder")} required />
            </Field>
            <button className="btn btn-primary btn-block btn-lg" disabled={busy}>
              {busy ? <Spinner /> : t("login.submit")}
            </button>
          </form>
          <div className="row-between" style={{ marginTop: "1rem", fontSize: "0.9rem" }}>
            <Link href="/forgot-password" className="muted">
              {t("login.forgot")}
            </Link>
            <Link href="/signup" className="grad-text">
              {t("login.createAccount")}
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
