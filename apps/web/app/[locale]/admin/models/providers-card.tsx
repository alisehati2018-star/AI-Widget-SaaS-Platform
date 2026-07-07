"use client";

// Provider registry CRUD: vendors, their API keys (write-only), and each
// model's real per-1M-token provider cost — the base of all profit math.

import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";
import { ApiError } from "@/lib/api";
import { adminFetch as authFetch } from "@/lib/auth";
import { formatNumber } from "@/lib/datetime";
import type { Locale } from "@/i18n/routing";
import { Alert, Badge, Field, Input, Spinner } from "@/components/ui";
import type { AiProvider } from "./types";

type AsyncAction = () =>
  Promise<unknown>;

export function ProvidersCard({
  providers,
  reload,
}: {
  providers: AiProvider[];
  reload: () => void;
}) {
  const t = useTranslations("admin");
  const locale = useLocale() as Locale;
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [form, setForm] = useState({ name: "", base_url: "", api_key: "", is_local: false });
  const [modelFor, setModelFor] = useState<string | null>(null);
  const [modelForm, setModelForm] = useState({ model: "", input: "0", output: "0" });
  const [ping, setPing] = useState<Record<string, boolean | null>>({});

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
        },
      });
      setForm({ name: "", base_url: "", api_key: "", is_local: false });
      setShowNew(false);
    });

  const addModel = (providerId: string) =>
    run(async () => {
      await authFetch(`/admin/ai/providers/${providerId}/models`, {
        body: {
          model: modelForm.model.trim(),
          input_usd_per_1m: Number(modelForm.input) || 0,
          output_usd_per_1m: Number(modelForm.output) || 0,
        },
      });
      setModelForm({ model: "", input: "0", output: "0" });
      setModelFor(null);
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
        <h3 style={{ margin: 0 }}>{t("models.providersTitle")}</h3>
        <button className="btn btn-primary" onClick={() => setShowNew((v) => !v)}>
          {showNew ? t("models.cancel") : t("models.addProvider")}
        </button>
      </div>
      <p className="hint">{t("models.providersHint")}</p>
      {error ? <Alert kind="error">{error}</Alert> : null}

      {showNew ? (
        <div className="dash-2col-even" style={{ margin: "0.8rem 0" }}>
          <Field label={t("models.providerName")}>
            <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </Field>
          <Field label={t("models.baseUrl")} hint={t("models.baseUrlHint")}>
            <Input dir="ltr" value={form.base_url}
              onChange={(e) => setForm({ ...form, base_url: e.target.value })} />
          </Field>
          <Field label={t("models.apiKey")} hint={t("models.apiKeyHint")}>
            <Input dir="ltr" type="password" value={form.api_key}
              onChange={(e) => setForm({ ...form, api_key: e.target.value })} />
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
        providers.map((p) => (
          <div key={p.id} className="card" style={{ margin: "0.8rem 0" }}>
            <div className="row-between" style={{ flexWrap: "wrap", gap: ".5rem" }}>
              <div>
                <strong>{p.name}</strong>{" "}
                {p.is_local ? <Badge tone="brand">{t("models.local")}</Badge> : null}{" "}
                {p.enabled ? (
                  <Badge tone="success">{t("common.enabled")}</Badge>
                ) : (
                  <Badge>{t("common.disabled")}</Badge>
                )}{" "}
                {ping[p.id] === true ? <Badge tone="success">{t("models.reachable")}</Badge> : null}
                {ping[p.id] === false ? <Badge tone="warning">{t("models.unreachable")}</Badge> : null}
                <div className="muted" dir="ltr" style={{ fontSize: ".85rem" }}>
                  {p.base_url} {p.has_api_key ? `· ${p.api_key_masked}` : ""}
                </div>
              </div>
              <div style={{ display: "flex", gap: ".4rem", flexWrap: "wrap" }}>
                <button className="btn" disabled={busy} onClick={() => void pingProvider(p.id)}>
                  {t("models.ping")}
                </button>
                <button className="btn" disabled={busy}
                  onClick={() => void run(() => authFetch(`/admin/ai/providers/${p.id}`, {
                    method: "PATCH", body: { enabled: !p.enabled } }))}>
                  {p.enabled ? t("models.disable") : t("models.enable")}
                </button>
                <button className="btn btn-danger" disabled={busy}
                  onClick={() => void run(() => authFetch(`/admin/ai/providers/${p.id}`, {
                    method: "DELETE" }))}>
                  {t("models.delete")}
                </button>
              </div>
            </div>

            {p.models.length ? (
              <table className="table" style={{ marginTop: ".6rem" }}>
                <thead>
                  <tr>
                    <th>{t("models.colModel")}</th>
                    <th>{t("models.colInPrice")}</th>
                    <th>{t("models.colOutPrice")}</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {p.models.map((m) => (
                    <tr key={m.id}>
                      <td dir="ltr">{m.model}</td>
                      <td>{formatNumber(m.input_usd_per_1m, locale)}</td>
                      <td>{formatNumber(m.output_usd_per_1m, locale)}</td>
                      <td>
                        <button className="btn btn-danger" disabled={busy}
                          onClick={() => void run(() => authFetch(`/admin/ai/models/${m.id}`, {
                            method: "DELETE" }))}>
                          {t("models.delete")}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="muted" style={{ marginTop: ".6rem" }}>{t("models.noModels")}</p>
            )}

            {modelFor === p.id ? (
              <div className="dash-2col-even" style={{ marginTop: ".6rem" }}>
                <Field label={t("models.modelName")}>
                  <Input dir="ltr" value={modelForm.model}
                    onChange={(e) => setModelForm({ ...modelForm, model: e.target.value })} />
                </Field>
                <Field label={t("models.colInPrice")} hint={t("models.priceHint")}>
                  <Input dir="ltr" inputMode="decimal" value={modelForm.input}
                    onChange={(e) => setModelForm({ ...modelForm, input: e.target.value })} />
                </Field>
                <Field label={t("models.colOutPrice")}>
                  <Input dir="ltr" inputMode="decimal" value={modelForm.output}
                    onChange={(e) => setModelForm({ ...modelForm, output: e.target.value })} />
                </Field>
                <div>
                  <button className="btn btn-primary" disabled={busy || !modelForm.model}
                    onClick={() => void addModel(p.id)}>
                    {busy ? <Spinner /> : t("models.create")}
                  </button>{" "}
                  <button className="btn" onClick={() => setModelFor(null)}>
                    {t("models.cancel")}
                  </button>
                </div>
              </div>
            ) : (
              <button className="btn" style={{ marginTop: ".6rem" }}
                onClick={() => setModelFor(p.id)}>
                {t("models.addModel")}
              </button>
            )}
          </div>
        ))
      )}
    </div>
  );
}
