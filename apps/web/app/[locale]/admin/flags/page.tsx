"use client";

import { useLocale, useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";
import { ApiError } from "@/lib/api";
import { adminFetch as authFetch } from "@/lib/auth";
import { formatDateTime } from "@/lib/datetime";
import type { Locale } from "@/i18n/routing";
import { DashboardShell, useAdminNav } from "@/components/shell";
import { Alert, Badge, Spinner } from "@/components/ui";

interface Flag {
  key: string;
  enabled: boolean;
  description: string | null;
  updated_at: string | null;
  updated_by: string | null;
}


export default function AdminFlags() {
  const t = useTranslations("admin");
  const locale = useLocale() as Locale;
  const nav = useAdminNav();
  const [flags, setFlags] = useState<Flag[] | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(() => {
    authFetch<{ flags: Flag[] }>("/admin/feature-flags").then((r) => setFlags(r.flags)).catch(() => setFlags([]));
  }, []);
  useEffect(() => load(), [load]);

  async function toggle(key: string, enabled: boolean) {
    setBusy(key);
    setErr(null);
    try {
      await authFetch(`/admin/feature-flags/${key}`, { body: { enabled } });
      load();
    } catch (e2) {
      setErr(e2 instanceof ApiError ? e2.message : t("common.actionFailed"));
    } finally {
      setBusy(null);
    }
  }

  // Localized explanation of what flipping each known flag actually does;
  // unknown flags fall back to their DB description.
  function effect(f: Flag) {
    switch (f.key) {
      case "assistant_enabled": return t("flags.effectAssistant");
      case "insight_engine": return t("flags.effectInsight");
      case "lead_capture": return t("flags.effectLeads");
      case "agent_actions": return t("flags.effectAgentActions");
      default: return f.description ?? "—";
    }
  }

  return (
    <DashboardShell title={t("flags.title")} nav={nav} requireAdmin loginHref="/admin/login">
      <p style={{ marginTop: "-1rem" }}>{t("flags.intro")}</p>
      <div className="card">
        {err ? <Alert kind="error">{err}</Alert> : null}
        {flags === null ? (
          <Spinner />
        ) : flags.length === 0 ? (
          <p className="muted">{t("flags.empty")}</p>
        ) : (
          <table className="table">
            <thead><tr>
              <th>{t("flags.colFlag")}</th><th>{t("flags.colEffect")}</th>
              <th>{t("flags.colState")}</th><th>{t("flags.colLastChanged")}</th><th></th>
            </tr></thead>
            <tbody>
              {flags.map((f) => (
                <tr key={f.key}>
                  <td><code>{f.key}</code></td>
                  <td className="muted" style={{ maxWidth: 380 }}>{effect(f)}</td>
                  <td>{f.enabled ? <Badge tone="success">{t("common.on")}</Badge> : <Badge>{t("common.off")}</Badge>}</td>
                  <td className="muted">
                    {f.updated_by ? (
                      <>
                        <span dir="ltr">{f.updated_by}</span>
                        <br />
                        <span className="hint">{formatDateTime(f.updated_at, locale)}</span>
                      </>
                    ) : "—"}
                  </td>
                  <td>
                    <button className="btn btn-soft" disabled={busy === f.key} onClick={() => void toggle(f.key, !f.enabled)}>
                      {busy === f.key ? <Spinner /> : f.enabled ? t("common.disable") : t("common.enable")}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <p className="hint" style={{ marginTop: "1rem" }}>{t("flags.hint")}</p>
      </div>
    </DashboardShell>
  );
}
