"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import type { TenantProfile } from "@/lib/api";
import { authFetch } from "@/lib/auth";
import { DashboardShell, useOwnerNav } from "@/components/shell";
import { Alert, Field, Input, Spinner } from "@/components/ui";

export default function AssistantPage() {
  const t = useTranslations("dashboard");
  const tc = useTranslations("common");
  const nav = useOwnerNav();
  const [greeting, setGreeting] = useState("");
  const [loaded, setLoaded] = useState(false);
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    authFetch<TenantProfile>("/tenant/profile")
      .then((p) => setGreeting(p.settings.widget_greeting ?? ""))
      .catch(() => {})
      .finally(() => setLoaded(true));
  }, []);

  async function save() {
    setBusy(true);
    setSaved(false);
    try {
      await authFetch("/tenant/settings", { method: "PATCH", body: { widget_greeting: greeting } });
      setSaved(true);
    } finally {
      setBusy(false);
    }
  }

  const guardrails = [
    t("assistant.guardrail1"),
    t("assistant.guardrail2"),
    t("assistant.guardrail3"),
    t("assistant.guardrail4"),
  ];

  return (
    <DashboardShell title={t("nav.assistant")} nav={nav}>
      <p style={{ marginTop: "-1rem" }}>{t("assistant.intro")}</p>

      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <h3>{t("assistant.greetingTitle")}</h3>
        {saved ? <Alert kind="success">{t("common.saved")}</Alert> : null}
        {loaded ? (
          <Field label={t("assistant.greetingLabel")}>
            <Input
              value={greeting}
              onChange={(e) => setGreeting(e.target.value)}
              placeholder={t("assistant.greetingPlaceholder")}
            />
          </Field>
        ) : (
          <Spinner />
        )}
        <button className="btn btn-primary" onClick={() => void save()} disabled={busy}>
          {busy ? <Spinner /> : tc("actions.save")}
        </button>
      </div>

      <div className="card">
        <h3>{t("assistant.guardrailsTitle")}</h3>
        <ul className="feature-list">
          {guardrails.map((g) => (
            <li key={g}>{g}</li>
          ))}
        </ul>
        <p className="hint">{t("assistant.guardrailsHint")}</p>
      </div>
    </DashboardShell>
  );
}
