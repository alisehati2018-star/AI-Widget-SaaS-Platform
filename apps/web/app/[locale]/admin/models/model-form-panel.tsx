"use client";

// Create/edit form for one catalog model — provider + modality + costs +
// context window + free-tier/active flags. Provider and model id are locked
// once created (they form the unique key the gateway routes against).

import { useTranslations } from "next-intl";
import { useState } from "react";
import { ApiError } from "@/lib/api";
import { adminFetch as authFetch } from "@/lib/auth";
import { Field, Input, Spinner } from "@/components/ui";
import type { AiModel, AiProvider, ModelModality } from "./types";

const MODALITIES: ModelModality[] = ["chat", "embedding", "rerank"];

interface FormState {
  provider_id: string;
  model: string;
  label: string;
  modality: ModelModality;
  context_window: string;
  input: string;
  output: string;
  is_free_tier: boolean;
  enabled: boolean;
}

function emptyForm(providers: AiProvider[]): FormState {
  return {
    provider_id: providers[0]?.id ?? "", model: "", label: "", modality: "chat",
    context_window: "", input: "0", output: "0", is_free_tier: false, enabled: true,
  };
}

function formFromModel(m: AiModel): FormState {
  return {
    provider_id: m.provider_id, model: m.model, label: m.label ?? "", modality: m.modality,
    context_window: m.context_window != null ? String(m.context_window) : "",
    input: String(m.input_usd_per_1m), output: String(m.output_usd_per_1m),
    is_free_tier: m.is_free_tier, enabled: m.enabled,
  };
}

export function ModelFormPanel({
  providers,
  editing,
  onClose,
  onSaved,
}: {
  providers: AiProvider[];
  editing: AiModel | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const t = useTranslations("admin");
  const tm = useTranslations("admin.models");
  const [form, setForm] = useState<FormState>(editing ? formFromModel(editing) : emptyForm(providers));
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function save() {
    if (!editing && (!form.provider_id || !form.model.trim())) {
      setError(t("toast.requiredFields"));
      return;
    }
    setError(null);
    setBusy(true);
    try {
      const body = {
        label: form.label.trim() || form.model,
        modality: form.modality,
        context_window: form.context_window.trim() ? Number(form.context_window) : null,
        input_usd_per_1m: Number(form.input) || 0,
        output_usd_per_1m: Number(form.output) || 0,
        is_free_tier: form.is_free_tier,
        enabled: form.enabled,
      };
      if (editing) {
        await authFetch(`/admin/ai/models/${editing.id}`, { method: "PATCH", body });
      } else {
        await authFetch(`/admin/ai/providers/${form.provider_id}/models`, {
          body: { ...body, model: form.model.trim() },
        });
      }
      onSaved();
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("models.actionFailed"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card" style={{ margin: "0.8rem 0", borderStyle: "dashed" }}>
      <div className="row-between">
        <h4 style={{ margin: 0 }}>{editing ? tm("editModel") : tm("createModel")}</h4>
        <button className="btn btn-ghost" onClick={onClose}>{t("models.cancel")}</button>
      </div>
      {error ? <p className="hint" style={{ color: "#c0392b" }}>{error}</p> : null}
      <div className="dash-2col-even" style={{ marginTop: ".6rem" }}>
        <Field label={tm("provider")}>
          <select className="input" dir="ltr" disabled={Boolean(editing)}
            value={form.provider_id}
            onChange={(e) => setForm({ ...form, provider_id: e.target.value })}>
            {providers.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
        </Field>
        <Field label={tm("modelIdField")}>
          <Input dir="ltr" disabled={Boolean(editing)} value={form.model}
            onChange={(e) => setForm({ ...form, model: e.target.value })}
            placeholder="e.g. openai/gpt-4o-mini" />
        </Field>
        <Field label={t("models.modelName")}>
          <Input value={form.label} onChange={(e) => setForm({ ...form, label: e.target.value })} />
        </Field>
        <Field label={tm("type")}>
          <select className="input" value={form.modality}
            onChange={(e) => setForm({ ...form, modality: e.target.value as ModelModality })}>
            {MODALITIES.map((mod) => (
              <option key={mod} value={mod}>{tm(`type_${mod}`)}</option>
            ))}
          </select>
        </Field>
        <Field label={tm("contextWindow")}>
          <Input dir="ltr" inputMode="numeric" value={form.context_window}
            onChange={(e) => setForm({ ...form, context_window: e.target.value })} />
        </Field>
        <Field label={t("models.colInPrice")} hint={t("models.priceHint")}>
          <Input dir="ltr" inputMode="decimal" value={form.input}
            onChange={(e) => setForm({ ...form, input: e.target.value })} />
        </Field>
        <Field label={t("models.colOutPrice")}>
          <Input dir="ltr" inputMode="decimal" value={form.output}
            onChange={(e) => setForm({ ...form, output: e.target.value })} />
        </Field>
        <label className="row" style={{ gap: ".5rem" }}>
          <input type="checkbox" checked={form.is_free_tier}
            onChange={(e) => setForm({ ...form, is_free_tier: e.target.checked })} />
          {tm("isFreeTier")}
        </label>
        <label className="row" style={{ gap: ".5rem" }}>
          <input type="checkbox" checked={form.enabled}
            onChange={(e) => setForm({ ...form, enabled: e.target.checked })} />
          {t("common.enabled")}
        </label>
      </div>
      <button className="btn btn-primary" style={{ marginTop: ".6rem" }} disabled={busy}
        onClick={() => void save()}>
        {busy ? <Spinner /> : t("plans.save")}
      </button>
    </div>
  );
}
