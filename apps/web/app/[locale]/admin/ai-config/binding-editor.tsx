"use client";

// Per-task ("use case") ordered model chain editor: primary + failover
// badges, ineligible-binding warnings (inactive model/provider, missing
// key), and a provider→model draft picker restricted to that task's
// required modality. One instance renders per task (chat/analyst/
// embedding/rerank).

import { useTranslations } from "next-intl";
import { useState } from "react";
import { ApiError } from "@/lib/api";
import { adminFetch as authFetch } from "@/lib/auth";
import { Alert, Badge, Spinner } from "@/components/ui";
import type { AiProvider, IneligibleReason, ModelModality, RouteEntry } from "../models/types";

const TASK_MODALITY: Record<string, ModelModality> = {
  chat: "chat", analyst: "chat", embedding: "embedding", rerank: "rerank",
};

const REASON_KEYS: Record<IneligibleReason, string> = {
  MODEL_INACTIVE: "issueModelInactive",
  PROVIDER_INACTIVE: "issueProviderInactive",
  PROVIDER_NO_API_KEY: "issueProviderNoKey",
};

export function BindingEditor({
  task,
  chain,
  providers,
  reload,
}: {
  task: string;
  chain: RouteEntry[];
  providers: AiProvider[];
  reload: () => void;
}) {
  const t = useTranslations("admin");
  const ta = useTranslations("admin.aiConfigPage");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [draftProviderId, setDraftProviderId] = useState("");
  const [draftModelId, setDraftModelId] = useState("");

  const modality = TASK_MODALITY[task] ?? "chat";
  const ids = chain.map((c) => c.model_id);

  const eligibleProviders = providers.filter((p) => p.enabled && p.has_api_key);
  const draftModels = draftProviderId
    ? (providers.find((p) => p.id === draftProviderId)?.models ?? [])
        .filter((m) => m.modality === modality && m.enabled && !ids.includes(m.id))
    : [];

  async function save(modelIds: string[]) {
    setError(null);
    setBusy(true);
    try {
      await authFetch(`/admin/ai/routes/${task}`, { method: "PUT", body: { model_ids: modelIds } });
      reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("models.actionFailed"));
    } finally {
      setBusy(false);
    }
  }

  function move(index: number, dir: -1 | 1) {
    const next = [...ids];
    const target = index + dir;
    if (target < 0 || target >= next.length) return;
    [next[index], next[target]] = [next[target], next[index]];
    void save(next);
  }

  function addBinding() {
    if (!draftModelId) return;
    void save([...ids, draftModelId]);
    setDraftProviderId("");
    setDraftModelId("");
  }

  return (
    <div>
      {error ? <Alert kind="error">{error}</Alert> : null}
      {task === "rerank" ? (
        <p className="hint" style={{ marginBottom: ".5rem" }}>
          <Badge tone="warning">{t("models.rerankNotLive")}</Badge>
        </p>
      ) : null}

      {chain.length === 0 ? (
        <p className="muted">{ta("noBindings")}</p>
      ) : (
        <ol style={{ margin: 0, paddingInlineStart: "1.4rem" }}>
          {chain.map((c, i) => (
            <li key={`${c.model_id}-${i}`} style={{ margin: ".4rem 0" }}>
              <div className={`card ${c.is_eligible ? "" : "card-danger"}`}
                style={{
                  padding: ".5rem .7rem",
                  borderColor: c.is_eligible ? undefined : "var(--danger, #c0392b)",
                }}>
                <div className="row-between" style={{ flexWrap: "wrap", gap: ".4rem" }}>
                  <span dir="ltr">{c.provider} / {c.label ?? c.model}</span>
                  <div className="row" style={{ gap: ".3rem" }}>
                    {i === 0 ? <Badge tone="brand">{ta("primaryBadge")}</Badge> : <Badge>{ta("failoverBadge")}</Badge>}
                    {c.is_local ? <Badge tone="success">{t("models.local")}</Badge> : null}
                    {i > 0 ? (
                      <button className="btn" disabled={busy} onClick={() => move(i, -1)}>{t("models.moveUp")}</button>
                    ) : null}
                    <button className="btn btn-danger" disabled={busy}
                      onClick={() => void save(ids.filter((x) => x !== c.model_id))}>
                      {t("models.remove")}
                    </button>
                  </div>
                </div>
                {!c.is_eligible ? (
                  <p style={{ color: "var(--danger, #c0392b)", fontSize: ".8rem", margin: ".3rem 0 0" }}>
                    {ta(c.ineligible_reason ? REASON_KEYS[c.ineligible_reason] : "issueModelInactive")}
                  </p>
                ) : null}
              </div>
            </li>
          ))}
        </ol>
      )}

      {eligibleProviders.length === 0 ? (
        <p className="hint" style={{ marginTop: ".5rem" }}>{ta("noEligibleProviders")}</p>
      ) : (
        <div className="row" style={{ gap: ".4rem", marginTop: ".6rem", flexWrap: "wrap" }}>
          <select className="input" dir="ltr" style={{ maxWidth: "12rem" }}
            aria-label={ta("chooseProvider")}
            value={draftProviderId}
            onChange={(e) => { setDraftProviderId(e.target.value); setDraftModelId(""); }}>
            <option value="">{ta("chooseProvider")}</option>
            {eligibleProviders.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
          <select className="input" dir="ltr" style={{ maxWidth: "16rem" }}
            aria-label={ta("chooseModel")}
            disabled={!draftProviderId || draftModels.length === 0}
            value={draftModelId} onChange={(e) => setDraftModelId(e.target.value)}>
            <option value="">
              {draftProviderId ? (draftModels.length ? ta("chooseModel") : ta("noModelsForProvider")) : ta("chooseProviderFirst")}
            </option>
            {draftModels.map((m) => <option key={m.id} value={m.id}>{m.label ?? m.model}</option>)}
          </select>
          <button className="btn btn-primary" disabled={busy || !draftModelId} onClick={addBinding}>
            {busy ? <Spinner /> : ta("addToChain")}
          </button>
        </div>
      )}
    </div>
  );
}
