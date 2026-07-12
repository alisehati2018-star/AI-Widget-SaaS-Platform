"use client";

// Dedicated provider registry: CRUD, quick-add templates, discovery, and
// external credit/key-health checks. Model management itself lives on the
// Models page — this page only shows a model COUNT per provider.

import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";
import { ApiError } from "@/lib/api";
import { adminFetch as authFetch } from "@/lib/auth";
import { formatNumber } from "@/lib/datetime";
import { Link } from "@/i18n/navigation";
import type { Locale } from "@/i18n/routing";
import { Alert, Badge, Field, Input, Spinner } from "@/components/ui";
import { DiscoverModelsPanel } from "../models/discover-models-modal";
import { ProviderTemplatesPanel } from "../models/provider-templates-panel";
import type { AiProvider } from "../models/types";
import { CheckCreditPanel } from "./check-credit-panel";

type AsyncAction = { (): Promise<unknown> };

const EMPTY_FORM = {
  name: "", base_url: "", api_key: "", is_local: false, priority: "0",
  max_retries: "0", retry_backoff_ms: "250",
};

export function ProvidersTable({
  providers,
  reload,
}: {
  providers: AiProvider[];
  reload: () => void;
}) {
  const t = useTranslations("admin");
  const tp = useTranslations("admin.providersPage");
  const locale = useLocale() as Locale;
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState(EMPTY_FORM);
  const [ping, setPing] = useState<Record<string, boolean | null>>({});
  const [discoverFor, setDiscoverFor] = useState<string | null>(null);
  const [creditFor, setCreditFor] = useState<string | null>(null);

  async function run(fn: AsyncAction) {
    setError(null);
    setBusy(true);
    try {
      await fn();
      reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("models.actionFailed"));
    } finally {
      setBusy(false);
    }
  }

  const createProvider = () =>
    run(async () => {
      await authFetch("/admin/ai/providers", {
        body: {
          name: form.name.trim(),
          base_url: form.base_url.trim(),
          api_key: form.api_key.trim(),
          is_local: form.is_local,
          kind: form.is_local ? "local" : "openai-compatible",
          priority: Number(form.priority) || 0,
        },
      });
      setForm(EMPTY_FORM);
      setShowNew(false);
    });

  function startEdit(p: AiProvider) {
    setEditingId(p.id);
    setEditForm({
      name: p.name, base_url: p.base_url, api_key: "", is_local: p.is_local,
      priority: String(p.priority),
      max_retries: String(p.max_retries), retry_backoff_ms: String(p.retry_backoff_ms),
    });
  }

  const saveEdit = (id: string) =>
    run(async () => {
      const body: Record<string, unknown> = {
        base_url: editForm.base_url.trim(),
        is_local: editForm.is_local,
        priority: Number(editForm.priority) || 0,
        max_retries: Number(editForm.max_retries) || 0,
        retry_backoff_ms: Number(editForm.retry_backoff_ms) || 0,
      };
      if (editForm.api_key.trim()) body.api_key = editForm.api_key.trim();
      await authFetch(`/admin/ai/providers/${id}`, { method: "PATCH", body });
      setEditingId(null);
    });

  async function pingProvider(id: string) {
    setPing((p) => ({ ...p, [id]: null }));
    try {
      const r = await authFetch<{ reachable: boolean }>(`/admin/ai/providers/${id}/ping`, {
        method: "POST",
      });
      setPing((p) => ({ ...p, [id]: r.reachable }));
    } catch {
      setPing((p) => ({ ...p, [id]: false }));
    }
  }

  return (
    <div className="card" style={{ marginBottom: "1.5rem" }}>
      <div className="row-between" style={{ flexWrap: "wrap", gap: ".6rem" }}>
        <h3 style={{ margin: 0 }}>{tp("title")}</h3>
        <button className="btn btn-primary" onClick={() => setShowNew((v) => !v)}>
          {showNew ? t("models.cancel") : tp("newProvider")}
        </button>
      </div>
      <p className="hint">{tp("description")}</p>
      {error ? <Alert kind="error">{error}</Alert> : null}

      <ProviderTemplatesPanel onCreated={reload} />

      {showNew ? (
        <div className="dash-2col-even" style={{ margin: "0.8rem 0" }}>
          <Field label={tp("systemName")}>
            <Input dir="ltr" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </Field>
          <Field label={t("models.baseUrl")} hint={t("models.baseUrlHint")}>
            <Input dir="ltr" value={form.base_url}
              onChange={(e) => setForm({ ...form, base_url: e.target.value })} />
          </Field>
          <Field label={t("models.apiKey")} hint={t("models.apiKeyHint")}>
            <Input dir="ltr" type="password" value={form.api_key}
              onChange={(e) => setForm({ ...form, api_key: e.target.value })} />
          </Field>
          <Field label={tp("priorityHint")}>
            <Input dir="ltr" inputMode="numeric" value={form.priority}
              onChange={(e) => setForm({ ...form, priority: e.target.value })} />
          </Field>
          <Field label={t("models.isLocal")} hint={t("models.isLocalHint")}>
            <input type="checkbox" checked={form.is_local}
              onChange={(e) => setForm({ ...form, is_local: e.target.checked })} />
          </Field>
          <div>
            <button className="btn btn-primary" disabled={busy || !form.name || !form.base_url}
              onClick={() => void createProvider()}>
              {busy ? <Spinner /> : t("models.create")}
            </button>
          </div>
        </div>
      ) : null}

      {providers.length === 0 ? (
        <p className="muted">{t("models.noProviders")}</p>
      ) : (
        <table className="table" style={{ marginTop: "1rem" }}>
          <thead>
            <tr>
              <th>{tp("colName")}</th>
              <th>{tp("colBaseUrl")}</th>
              <th>{tp("colApiKey")}</th>
              <th>{tp("colModelCount")}</th>
              <th>{tp("colPlatformUsage")}</th>
              <th>{tp("colPriority")}</th>
              <th>{tp("colStatus")}</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {providers.map((p) => (
              <tr key={p.id}>
                <td>
                  <strong>{p.name}</strong>{" "}
                  {p.is_local ? <Badge tone="brand">{t("models.local")}</Badge> : null}
                  {ping[p.id] === true ? <Badge tone="success">{t("models.reachable")}</Badge> : null}
                  {ping[p.id] === false ? <Badge tone="warning">{t("models.unreachable")}</Badge> : null}
                </td>
                <td className="muted" dir="ltr" style={{ fontSize: ".8rem" }}>{p.base_url}</td>
                <td className="muted" style={{ fontSize: ".8rem" }}>
                  {p.has_api_key ? p.api_key_masked : tp("notSet")}
                </td>
                <td>
                  <Link href={`/admin/models?provider=${p.id}`}>{p.models.length}</Link>
                </td>
                <td style={{ fontSize: ".8rem" }}>
                  <div className="muted">
                    {formatNumber(p.platform_usage.platform_credits, locale)} {tp("creditsShort")}
                  </div>
                  <div className="muted">
                    ${p.platform_usage.estimated_cost_usd.toFixed(4)} · {p.platform_usage.call_count} {tp("callsShort")}
                  </div>
                </td>
                <td>{p.priority}</td>
                <td>
                  {p.enabled ? (
                    <Badge tone="success">{t("common.enabled")}</Badge>
                  ) : (
                    <Badge>{t("common.disabled")}</Badge>
                  )}
                </td>
                <td>
                  <div style={{ display: "flex", gap: ".3rem", flexWrap: "wrap" }}>
                    <button className="btn" disabled={busy} onClick={() => void pingProvider(p.id)}>
                      {t("models.ping")}
                    </button>
                    <button className="btn" disabled={busy}
                      onClick={() => setDiscoverFor(discoverFor === p.id ? null : p.id)}>
                      {t("models.discoverModels")}
                    </button>
                    <button className="btn" disabled={busy}
                      onClick={() => setCreditFor(creditFor === p.id ? null : p.id)}>
                      {tp("checkCredit")}
                    </button>
                    <button className="btn" disabled={busy}
                      onClick={() => void run(() => authFetch(`/admin/ai/providers/${p.id}`, {
                        method: "PATCH", body: { enabled: !p.enabled } }))}>
                      {p.enabled ? t("models.disable") : t("models.enable")}
                    </button>
                    <button className="btn" disabled={busy} onClick={() => startEdit(p)}>
                      {tp("editProvider")}
                    </button>
                    <button className="btn btn-danger" disabled={busy}
                      onClick={() => {
                        if (!window.confirm(tp("deleteConfirm", { name: p.name }))) return;
                        void run(() => authFetch(`/admin/ai/providers/${p.id}`, { method: "DELETE" }));
                      }}>
                      {t("models.delete")}
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {providers.map((p) =>
        discoverFor === p.id ? (
          <DiscoverModelsPanel key={`d-${p.id}`} providerId={p.id} providerName={p.name}
            onClose={() => setDiscoverFor(null)} onImported={reload} />
        ) : null
      )}
      {providers.map((p) =>
        creditFor === p.id ? (
          <CheckCreditPanel key={`c-${p.id}`} provider={p} onClose={() => setCreditFor(null)} />
        ) : null
      )}
      {providers.map((p) =>
        editingId === p.id ? (
          <div key={`e-${p.id}`} className="card" style={{ margin: "0.8rem 0", borderStyle: "dashed" }}>
            <div className="row-between">
              <h4 style={{ margin: 0 }}>{tp("editProvider")}: {p.name}</h4>
              <button className="btn btn-ghost" onClick={() => setEditingId(null)}>{t("models.cancel")}</button>
            </div>
            <div className="dash-2col-even" style={{ marginTop: ".6rem" }}>
              <Field label={t("models.baseUrl")}>
                <Input dir="ltr" value={editForm.base_url}
                  onChange={(e) => setEditForm({ ...editForm, base_url: e.target.value })} />
              </Field>
              <Field label={tp("apiKeyNew")} hint={t("models.apiKeyHint")}>
                <Input dir="ltr" type="password" value={editForm.api_key}
                  onChange={(e) => setEditForm({ ...editForm, api_key: e.target.value })} />
              </Field>
              <Field label={tp("priorityHint")}>
                <Input dir="ltr" inputMode="numeric" value={editForm.priority}
                  onChange={(e) => setEditForm({ ...editForm, priority: e.target.value })} />
              </Field>
              <Field label={t("models.isLocal")}>
                <input type="checkbox" checked={editForm.is_local}
                  onChange={(e) => setEditForm({ ...editForm, is_local: e.target.checked })} />
              </Field>
              <Field label={t("models.maxRetries")} hint={t("models.maxRetriesHint")}>
                <Input dir="ltr" inputMode="numeric" value={editForm.max_retries}
                  onChange={(e) => setEditForm({ ...editForm, max_retries: e.target.value })} />
              </Field>
              <Field label={t("models.retryBackoffMs")}>
                <Input dir="ltr" inputMode="numeric" value={editForm.retry_backoff_ms}
                  onChange={(e) => setEditForm({ ...editForm, retry_backoff_ms: e.target.value })} />
              </Field>
            </div>
            <button className="btn btn-primary" disabled={busy} onClick={() => void saveEdit(p.id)}>
              {busy ? <Spinner /> : t("plans.save")}
            </button>
          </div>
        ) : null
      )}
    </div>
  );
}
