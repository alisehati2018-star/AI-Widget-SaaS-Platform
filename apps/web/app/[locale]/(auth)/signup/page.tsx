"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";
import { ApiError } from "@/lib/api";
import { signup } from "@/lib/auth";
import { Link, useRouter } from "@/i18n/navigation";
import { Alert, Brand, Field, Input, Spinner } from "@/components/ui";

export default function SignupPage() {
  const t = useTranslations("auth");
  const tErrors = useTranslations("errors");
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
      router.replace(user.role === "platform_admin" ? "/admin" : "/onboarding");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : tErrors("generic"));
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
          <h2 style={{ marginBottom: "0.3rem" }}>{t("signup.title")}</h2>
          <p style={{ fontSize: "0.9rem" }}>{t("signup.subtitle")}</p>
          {error ? <Alert kind="error">{error}</Alert> : null}
          <form onSubmit={submit}>
            <Field label={t("signup.storeName")}>
              <Input value={form.store_name} onChange={update("store_name")} placeholder={t("signup.storeNamePlaceholder")} required />
            </Field>
            <Field label={t("signup.fullName")}>
              <Input value={form.full_name} onChange={update("full_name")} placeholder={t("signup.fullNamePlaceholder")} />
            </Field>
            <Field label={t("signup.workEmail")}>
              <Input type="email" value={form.email} onChange={update("email")} placeholder={t("shared.emailPlaceholder")} required />
            </Field>
            <Field label={t("shared.passwordLabel")} hint={t("shared.passwordHint")}>
              <Input type="password" value={form.password} onChange={update("password")} placeholder={t("shared.passwordPlaceholder")} required />
            </Field>
            <button className="btn btn-primary btn-block btn-lg" disabled={busy}>
              {busy ? <Spinner /> : t("signup.submit")}
            </button>
          </form>
          <p className="hint center" style={{ marginTop: "0.8rem" }}>
            {t("signup.agreePrefix")}
            <Link href="/legal/terms" className="grad-text">
              {t("signup.agreeTerms")}
            </Link>
            {t("signup.agreeMiddle")}
            <Link href="/legal/privacy" className="grad-text">
              {t("signup.agreePrivacy")}
            </Link>
            {t("signup.agreeSuffix")}
          </p>
          <p className="center" style={{ marginTop: "1rem", marginBottom: 0, fontSize: "0.9rem" }}>
            {t("signup.haveAccount")}{" "}
            <Link href="/login" className="grad-text">
              {t("signup.signIn")}
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
