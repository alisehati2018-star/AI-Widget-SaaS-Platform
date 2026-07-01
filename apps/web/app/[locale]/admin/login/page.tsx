"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { ApiError } from "@/lib/api";
import { adminLogin, useAdminSession } from "@/lib/auth";
import { useRouter } from "@/i18n/navigation";
import { Alert, Brand, Field, Input, Spinner } from "@/components/ui";

export default function AdminLoginPage() {
  const t = useTranslations("auth");
  const tErrors = useTranslations("errors");
  const router = useRouter();
  const { user, loading } = useAdminSession();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // An operator with a live admin session skips the form entirely.
  useEffect(() => {
    if (!loading && user) router.replace("/admin");
  }, [loading, user, router]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await adminLogin(email, password);
      router.replace("/admin");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : tErrors("generic"));
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
            <h2 style={{ margin: 0 }}>{t("adminLogin.title")}</h2>
            <span className="badge badge-brand">{t("adminLogin.badge")}</span>
          </div>
          <p style={{ fontSize: "0.9rem" }}>{t("adminLogin.subtitle")}</p>
          {error ? <Alert kind="error">{error}</Alert> : null}
          <form onSubmit={submit}>
            <Field label={t("adminLogin.emailLabel")}>
              <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder={t("adminLogin.emailPlaceholder")} required />
            </Field>
            <Field label={t("shared.passwordLabel")}>
              <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder={t("shared.passwordPlaceholder")} required />
            </Field>
            <button className="btn btn-primary btn-block btn-lg" disabled={busy}>
              {busy ? <Spinner /> : t("adminLogin.submit")}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
