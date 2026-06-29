"use client";

import { useLocale, useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";
import type { ApiKey } from "@/lib/api";
import { ApiError } from "@/lib/api";
import { authFetch } from "@/lib/auth";
import { formatDate } from "@/lib/datetime";
import type { Locale } from "@/i18n/routing";
import { DashboardShell, useOwnerNav } from "@/components/shell";
import { Alert, Badge, Field, Input, Spinner } from "@/components/ui";

export default function KeysPage() {
  const t = useTranslations("dashboard");
  const tErrors = useTranslations("errors");
  const locale = useLocale() as Locale;
  const nav = useOwnerNav();
  const [keys, setKeys] = useState<ApiKey[] | null>(null);
  const [scope, setScope] = useState("widget");
  const [label, setLabel] = useState("");
  const [created, setCreated] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    authFetch<{ keys: ApiKey[] }>("/tenant/keys").then((r) => setKeys(r.keys)).catch(() => setKeys([]));
  }, []);
  useEffect(() => load(), [load]);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const r = await authFetch<{ api_key: string }>("/tenant/keys", { body: { scope, label } });
      setCreated(r.api_key);
      setLabel("");
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : tErrors("saveFailed"));
    } finally {
      setBusy(false);
    }
  }

  async function revoke(id: string) {
    await authFetch(`/tenant/keys/${id}/revoke`, { method: "POST" }).catch(() => {});
    load();
  }

  return (
    <DashboardShell title={t("nav.keys")} nav={nav}>
      <p style={{ marginTop: "-1rem" }}>{t("keys.intro")}</p>

      {created ? (
        <Alert kind="success">
          {t("keys.newKeyNotice")}
          <br />
          <code style={{ wordBreak: "break-all" }}>{created}</code>
        </Alert>
      ) : null}

      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <h3>{t("keys.createTitle")}</h3>
        {error ? <Alert kind="error">{error}</Alert> : null}
        <form onSubmit={create} className="row" style={{ alignItems: "flex-end", flexWrap: "wrap" }}>
          <div style={{ minWidth: 180 }}>
            <Field label={t("keys.scope")}>
              <select className="input" value={scope} onChange={(e) => setScope(e.target.value)}>
                <option value="widget">{t("keys.scopeWidget")}</option>
                <option value="sync">{t("keys.scopeSync")}</option>
              </select>
            </Field>
          </div>
          <div style={{ flex: 1, minWidth: 200 }}>
            <Field label={t("keys.label")}>
              <Input value={label} onChange={(e) => setLabel(e.target.value)} placeholder={t("keys.labelPlaceholder")} />
            </Field>
          </div>
          <button className="btn btn-primary" disabled={busy} style={{ marginBottom: "1rem" }}>
            {busy ? <Spinner /> : t("keys.createKey")}
          </button>
        </form>
      </div>

      <div className="card">
        <h3>{t("keys.yourKeys")}</h3>
        {keys === null ? (
          <Spinner />
        ) : keys.length === 0 ? (
          <p className="muted">{t("keys.empty")}</p>
        ) : (
          <table className="table">
            <thead>
              <tr><th>{t("keys.colLabel")}</th><th>{t("keys.colScope")}</th><th>{t("keys.colCreated")}</th><th>{t("common.status")}</th><th></th></tr>
            </thead>
            <tbody>
              {keys.map((k) => (
                <tr key={k.id}>
                  <td>{k.label ?? "—"}</td>
                  <td><Badge tone="brand">{k.scope}</Badge></td>
                  <td className="muted">{formatDate(k.created_at, locale)}</td>
                  <td>{k.revoked ? <Badge>{t("keys.revoked")}</Badge> : <Badge tone="success">{t("keys.active")}</Badge>}</td>
                  <td>
                    {!k.revoked ? (
                      <button className="btn btn-danger" onClick={() => void revoke(k.id)}>{t("keys.revoke")}</button>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </DashboardShell>
  );
}
