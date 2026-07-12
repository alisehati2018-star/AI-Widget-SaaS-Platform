"use client";

import { useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";
import { ApiError, type TenantProfile } from "@/lib/api";
import { authFetch } from "@/lib/auth";
import { Link } from "@/i18n/navigation";
import { DashboardShell, useOwnerNav } from "@/components/shell";
import { Alert, Badge, Field, Input, Spinner } from "@/components/ui";

interface AssistantStatus {
  assistant_enabled: boolean;
  llm_configured: boolean;
  docs_indexed: number | null;
  search_degraded: boolean;
}

export default function AssistantPage() {
  const t = useTranslations("dashboard");
  const tc = useTranslations("common");
  const nav = useOwnerNav();
  const [greeting, setGreeting] = useState("");
  const [loaded, setLoaded] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<AssistantStatus | null>(null);
  const [statusFailed, setStatusFailed] = useState(false);

  const loadStatus = useCallback(() => {
    setStatusFailed(false);
    setStatus(null);
    authFetch<AssistantStatus>("/tenant/assistant-status")
      .then(setStatus)
      .catch(() => setStatusFailed(true));
  }, []);

  useEffect(() => {
    authFetch<TenantProfile>("/tenant/profile")
      .then((p) => setGreeting(p.settings.widget_greeting ?? ""))
      .catch(() => {})
      .finally(() => setLoaded(true));
    loadStatus();
  }, [loadStatus]);

  async function save() {
    setBusy(true);
    setSaved(false);
    setError(null);
    try {
      await authFetch("/tenant/settings", { method: "PATCH", body: { widget_greeting: greeting } });
      setSaved(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("common.actionFailed"));
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
        <h3>{t("assistant.statusTitle")}</h3>
        {statusFailed ? (
          <>
            <p className="muted">{t("common.loadFailed")}</p>
            <button className="btn btn-soft" onClick={loadStatus}>{t("common.retry")}</button>
          </>
        ) : status === null ? <Spinner /> : (
          <>
            <div className="stat-grid">
              <div className="stat">
                <span className="stat-label">{t("assistant.statusFlag")}</span>
                <span className="stat-value">
                  <Badge tone={status.assistant_enabled ? "success" : "warning"}>
                    {status.assistant_enabled ? t("assistant.statusOn") : t("assistant.statusOff")}
                  </Badge>
                </span>
              </div>
              <div className="stat">
                <span className="stat-label">{t("assistant.statusLlm")}</span>
                <span className="stat-value">
                  <Badge tone={status.llm_configured ? "success" : "warning"}>
                    {status.llm_configured ? t("assistant.statusReady") : t("assistant.statusNotConfigured")}
                  </Badge>
                </span>
              </div>
              <div className="stat">
                <span className="stat-label">{t("assistant.statusDocs")}</span>
                <span className="stat-value">
                  {status.search_degraded
                    ? <Badge tone="warning">{t("assistant.statusSearchDown")}</Badge>
                    : status.docs_indexed ?? "—"}
                </span>
              </div>
            </div>
            {!status.search_degraded && (status.docs_indexed ?? 0) === 0 ? (
              <div className="alert alert-warning" role="status" style={{ marginTop: "1rem" }}>
                {t("assistant.emptyGuide")}{" "}
                <Link className="btn btn-soft" href="/dashboard/catalog" style={{ marginInlineStart: ".5rem" }}>
                  {t("assistant.emptyGuideCta")}
                </Link>
              </div>
            ) : null}
          </>
        )}
      </div>

      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <h3>{t("assistant.greetingTitle")}</h3>
        {saved ? <Alert kind="success">{t("common.saved")}</Alert> : null}
        {error ? <Alert kind="error">{error}</Alert> : null}
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
