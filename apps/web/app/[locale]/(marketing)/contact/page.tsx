"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";
import { apiFetch, ApiError } from "@/lib/api";
import { MarketingFooter, MarketingNav } from "@/components/marketing";
import { Alert, Field, Input, Spinner } from "@/components/ui";

export default function ContactPage() {
  const t = useTranslations("marketing");
  const tErrors = useTranslations("errors");
  const [form, setForm] = useState({ name: "", email: "", message: "" });
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  function update(k: keyof typeof form) {
    return (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
      setForm({ ...form, [k]: e.target.value });
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await apiFetch("/contact", { body: form });
      setSent(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : tErrors("sendFailed"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <MarketingNav />
      <section className="section">
        <div className="container" style={{ maxWidth: 640 }}>
          <div className="center" style={{ marginBottom: "2rem" }}>
            <h1>{t("contact.title")}</h1>
            <p>{t("contact.subtitle")}</p>
          </div>
          <div className="card card-glow">
            {sent ? (
              <Alert kind="success">{t("contact.success")}</Alert>
            ) : (
              <form onSubmit={submit}>
                {error ? <Alert kind="error">{error}</Alert> : null}
                <Field label={t("contact.name")}>
                  <Input value={form.name} onChange={update("name")} required />
                </Field>
                <Field label={t("contact.email")}>
                  <Input type="email" value={form.email} onChange={update("email")} required />
                </Field>
                <Field label={t("contact.message")}>
                  <textarea
                    className="input"
                    style={{ minHeight: 140 }}
                    value={form.message}
                    onChange={update("message")}
                    required
                  />
                </Field>
                <button className="btn btn-primary btn-block btn-lg" disabled={busy}>
                  {busy ? <Spinner /> : t("contact.send")}
                </button>
              </form>
            )}
          </div>
        </div>
      </section>
      <MarketingFooter />
    </>
  );
}
