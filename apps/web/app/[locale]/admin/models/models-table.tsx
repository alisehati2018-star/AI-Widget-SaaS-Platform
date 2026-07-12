"use client";

// Flat model catalog across every provider: tabs to filter by provider,
// bulk select/delete, a standalone "discover from API" flow (pick any
// provider, no need to go to the Providers page), and full create/edit.

import { useTranslations } from "next-intl";
import { useEffect, useMemo, useState } from "react";
import { useApiErrorMessage } from "@/lib/errors";
import { adminFetch as authFetch } from "@/lib/auth";
import { Alert, Badge } from "@/components/ui";
import { DiscoverModelsPanel } from "./discover-models-modal";
import { ModelFormPanel } from "./model-form-panel";
import type { AiModel, AiProvider } from "./types";

export function ModelsTable({
  models,
  providers,
  reload,
}: {
  models: AiModel[];
  providers: AiProvider[];
  reload: () => void;
}) {
  const t = useTranslations("admin");
  const apiMsg = useApiErrorMessage();
  const tm = useTranslations("admin.models");
  const [activeTab, setActiveTab] = useState("all");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<AiModel | null>(null);
  const [discoverOpen, setDiscoverOpen] = useState(false);
  const [discoverProviderId, setDiscoverProviderId] = useState("");
  const [confirmBulkDelete, setConfirmBulkDelete] = useState(false);

  useEffect(() => {
    const fromUrl = new URLSearchParams(window.location.search).get("provider");
    if (fromUrl) setActiveTab(fromUrl);
  }, []);

  const tabs = useMemo(
    () => [
      { id: "all", label: tm("tabAllProviders"), count: models.length },
      ...providers.map((p) => ({
        id: p.id,
        label: p.name,
        count: models.filter((m) => m.provider_id === p.id).length,
      })),
    ],
    [models, providers, tm]
  );

  const visible = useMemo(
    () => (activeTab === "all" ? models : models.filter((m) => m.provider_id === activeTab)),
    [models, activeTab]
  );

  const visibleIds = visible.map((m) => m.id);
  const allVisibleSelected = visibleIds.length > 0 && visibleIds.every((id) => selected.has(id));

  function toggleOne(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleAllVisible() {
    setSelected((prev) => {
      const next = new Set(prev);
      if (allVisibleSelected) {
        for (const id of visibleIds) next.delete(id);
      } else {
        for (const id of visibleIds) next.add(id);
      }
      return next;
    });
  }

  async function deleteOne(m: AiModel) {
    if (!window.confirm(tm("deleteModelDesc", { name: m.label ?? m.model }))) return;
    setError(null);
    setBusy(true);
    try {
      await authFetch(`/admin/ai/models/${m.id}`, { method: "DELETE" });
      reload();
    } catch (err) {
      setError(apiMsg(err) ?? t("models.actionFailed"));
    } finally {
      setBusy(false);
    }
  }

  async function bulkDelete() {
    setError(null);
    setBusy(true);
    try {
      const r = await authFetch<{ deleted: number; blocked: { model: string }[] }>(
        "/admin/ai/models/bulk-delete",
        { body: { ids: [...selected] } }
      );
      setConfirmBulkDelete(false);
      setSelected(new Set());
      if (r.blocked.length) {
        setError(tm("bulkDeletePartial", { deleted: r.deleted, blocked: r.blocked.length }));
      }
      reload();
    } catch (err) {
      setError(apiMsg(err) ?? tm("bulkDeleteError"));
    } finally {
      setBusy(false);
    }
  }

  const providerName = (id: string) => providers.find((p) => p.id === id)?.name ?? "—";

  return (
    <div className="card">
      <div className="row-between" style={{ flexWrap: "wrap", gap: ".6rem" }}>
        <h3 style={{ margin: 0 }}>{tm("title")}</h3>
        <div className="row" style={{ gap: ".5rem" }}>
          <button className="btn btn-soft" disabled={providers.length === 0}
            onClick={() => {
              setDiscoverProviderId(activeTab !== "all" ? activeTab : providers[0]?.id ?? "");
              setDiscoverOpen((v) => !v);
            }}>
            {tm("discoverFromApi")}
          </button>
          <button className="btn btn-primary" disabled={providers.length === 0}
            onClick={() => { setEditing(null); setFormOpen((v) => !v); }}>
            {formOpen && !editing ? t("models.cancel") : tm("createModel")}
          </button>
        </div>
      </div>
      <p className="hint">{tm("intro")}</p>
      {error ? <Alert kind="error">{error}</Alert> : null}

      <div className="row" style={{ gap: ".4rem", flexWrap: "wrap", margin: ".8rem 0" }}>
        {tabs.map((tab) => (
          <button key={tab.id}
            className={`btn ${activeTab === tab.id ? "btn-primary" : "btn-soft"}`}
            onClick={() => setActiveTab(tab.id)}>
            {tab.label} <span className="muted">({tab.count})</span>
          </button>
        ))}
      </div>

      {discoverOpen ? (
        <div className="row" style={{ gap: ".5rem", marginBottom: ".6rem", alignItems: "center" }}>
          <select className="input" dir="ltr" style={{ maxWidth: "14rem" }}
            value={discoverProviderId} onChange={(e) => setDiscoverProviderId(e.target.value)}>
            {providers.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
        </div>
      ) : null}
      {discoverOpen && discoverProviderId ? (
        <DiscoverModelsPanel providerId={discoverProviderId} providerName={providerName(discoverProviderId)}
          onClose={() => setDiscoverOpen(false)} onImported={reload} />
      ) : null}

      {formOpen ? (
        <ModelFormPanel providers={providers} editing={editing}
          onClose={() => { setFormOpen(false); setEditing(null); }} onSaved={reload} />
      ) : null}

      {visible.length ? (
        <>
          <div className="row" style={{ gap: ".5rem", margin: ".6rem 0", flexWrap: "wrap" }}>
            <span className="muted" style={{ fontSize: ".8rem" }}>
              {tm("selectedCount", { count: selected.size })}
            </span>
            <button className="btn" onClick={toggleAllVisible}>
              {allVisibleSelected ? tm("clearVisibleSelection") : tm("selectAllVisible")}
            </button>
            <button className="btn btn-danger" disabled={selected.size === 0 || busy}
              onClick={() => setConfirmBulkDelete(true)}
              style={{ marginInlineStart: "auto" }}>
              {tm("bulkDelete", { count: selected.size })}
            </button>
          </div>
          <table className="table">
            <thead>
              <tr>
                <th></th>
                <th>{t("models.colModel")}</th>
                <th>{tm("provider")}</th>
                <th>{tm("type")}</th>
                <th>{t("models.colInPrice")} / {t("models.colOutPrice")}</th>
                <th>{tm("colFree")}</th>
                <th>{tm("colStatus")}</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {visible.map((m) => (
                <tr key={m.id}>
                  <td><input type="checkbox" checked={selected.has(m.id)} onChange={() => toggleOne(m.id)} /></td>
                  <td>
                    <div>{m.label ?? m.model}</div>
                    <div className="muted" dir="ltr" style={{ fontSize: ".75rem" }}>{m.model}</div>
                  </td>
                  <td className="muted" style={{ fontSize: ".85rem" }}>{m.provider_name ?? providerName(m.provider_id)}</td>
                  <td className="muted" style={{ fontSize: ".85rem" }}>{tm(`type_${m.modality}`)}</td>
                  <td dir="ltr" className="muted" style={{ fontSize: ".8rem" }}>
                    ${m.input_usd_per_1m} / ${m.output_usd_per_1m}
                  </td>
                  <td>{m.is_free_tier ? <Badge tone="brand">{tm("colFree")}</Badge> : "—"}</td>
                  <td>
                    {m.enabled ? <Badge tone="success">{t("common.enabled")}</Badge> : <Badge>{t("common.disabled")}</Badge>}
                  </td>
                  <td>
                    <div className="row" style={{ gap: ".3rem" }}>
                      <button className="btn" onClick={() => { setEditing(m); setFormOpen(true); }}>
                        {tm("editModel")}
                      </button>
                      <button className="btn btn-danger" disabled={busy} onClick={() => void deleteOne(m)}>
                        {t("models.delete")}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      ) : (
        <p className="muted">{t("models.noModels")}</p>
      )}

      {confirmBulkDelete ? (
        <div className="card" style={{ margin: "0.8rem 0", borderStyle: "dashed" }}>
          <p>{tm("bulkDeleteDesc", { count: selected.size })}</p>
          <div className="row" style={{ gap: ".5rem" }}>
            <button className="btn btn-danger" disabled={busy} onClick={() => void bulkDelete()}>
              {tm("bulkDeleteTitle")}
            </button>
            <button className="btn" onClick={() => setConfirmBulkDelete(false)}>{t("models.cancel")}</button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
