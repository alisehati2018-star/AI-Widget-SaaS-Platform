"use client";

// "Discover models" flow: fetch a provider's live model list (given its
// stored API key) and let the admin search/filter/pick which ones to import
// as ai_models, instead of typing each model id in by hand.

import { useLocale, useTranslations } from "next-intl";
import { useMemo, useState } from "react";
import { ApiError } from "@/lib/api";
import { adminFetch as authFetch } from "@/lib/auth";
import { formatNumber } from "@/lib/datetime";
import type { Locale } from "@/i18n/routing";
import { Alert, Badge, Input, Spinner } from "@/components/ui";
import type { DiscoveredModel } from "./types";

type PriceFilter = "all" | "free" | "paid";

function isFree(m: DiscoveredModel) {
  return m.input_usd_per_1m === 0 && m.output_usd_per_1m === 0;
}

export function DiscoverModelsPanel({
  providerId,
  providerName,
  onClose,
  onImported,
}: {
  providerId: string;
  providerName: string;
  onClose: () => void;
  onImported: () => void;
}) {
  const t = useTranslations("admin");
  const tdp = useTranslations("admin.discoverPicker");
  const locale = useLocale() as Locale;
  const [models, setModels] = useState<DiscoveredModel[] | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [query, setQuery] = useState("");
  const [priceFilter, setPriceFilter] = useState<PriceFilter>("all");

  async function fetchModels() {
    setError(null);
    setBusy(true);
    try {
      const r = await authFetch<{ models: DiscoveredModel[] }>(
        `/admin/ai/providers/${providerId}/discover`,
        { method: "POST" }
      );
      setModels(r.models);
      setSelected(new Set(r.models.filter((m) => !m.already_imported).map((m) => m.model)));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("models.actionFailed"));
    } finally {
      setBusy(false);
    }
  }

  const filtered = useMemo(() => {
    if (!models) return [];
    const q = query.trim().toLowerCase();
    return models.filter((m) => {
      if (priceFilter === "free" && !isFree(m)) return false;
      if (priceFilter === "paid" && isFree(m)) return false;
      if (q && !m.model.toLowerCase().includes(q) && !m.label.toLowerCase().includes(q)) return false;
      return true;
    });
  }, [models, query, priceFilter]);

  const selectableVisible = filtered.filter((m) => !m.already_imported);

  function toggle(model: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(model)) next.delete(model);
      else next.add(model);
      return next;
    });
  }

  function selectAllVisible() {
    setSelected((prev) => {
      const next = new Set(prev);
      for (const m of selectableVisible) next.add(m.model);
      return next;
    });
  }

  async function importSelected() {
    if (!models) return;
    setError(null);
    setBusy(true);
    try {
      const picked = models.filter((m) => selected.has(m.model));
      await authFetch(`/admin/ai/providers/${providerId}/models/import`, {
        body: { models: picked },
      });
      onImported();
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
        <h4 style={{ margin: 0 }}>{t("models.discoverTitle", { name: providerName })}</h4>
        <button className="btn btn-ghost" onClick={onClose}>{t("models.cancel")}</button>
      </div>
      <p className="hint">{t("models.discoverHint")}</p>
      {error ? <Alert kind="error">{error}</Alert> : null}

      {models === null ? (
        <button className="btn btn-primary" disabled={busy} onClick={() => void fetchModels()}>
          {busy ? <Spinner /> : t("models.fetchModels")}
        </button>
      ) : models.length === 0 ? (
        <p className="muted">{t("models.discoverEmpty")}</p>
      ) : (
        <>
          <div className="row" style={{ gap: ".5rem", margin: ".6rem 0", flexWrap: "wrap" }}>
            <Input dir="ltr" style={{ maxWidth: "16rem" }} value={query}
              placeholder={tdp("searchPlaceholder")}
              onChange={(e) => setQuery(e.target.value)} />
            {(["all", "free", "paid"] as const).map((f) => (
              <button key={f} type="button"
                className={`btn ${priceFilter === f ? "btn-primary" : "btn-soft"}`}
                onClick={() => setPriceFilter(f)}>
                {tdp(`filter_${f}`)}
              </button>
            ))}
            <span className="muted" style={{ fontSize: ".8rem", marginInlineStart: "auto" }}>
              {tdp("showingCount", { count: filtered.length, total: models.length })}
            </span>
          </div>
          <div className="row" style={{ gap: ".5rem", marginBottom: ".6rem" }}>
            <button type="button" className="btn" disabled={selectableVisible.length === 0}
              onClick={selectAllVisible}>
              {tdp("selectAllVisible")}
            </button>
            <button type="button" className="btn" disabled={selected.size === 0}
              onClick={() => setSelected(new Set())}>
              {tdp("clearSelection")}
            </button>
            <span className="muted" style={{ fontSize: ".8rem" }}>
              {tdp("selectedCount", { selected: selected.size, total: models.length })}
            </span>
          </div>
          <div style={{ maxHeight: "18rem", overflowY: "auto" }}>
            <table className="table">
              <thead>
                <tr>
                  <th></th>
                  <th>{t("models.colModel")}</th>
                  <th>{t("models.colInPrice")}</th>
                  <th>{t("models.colOutPrice")}</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((m) => (
                  <tr key={m.model}>
                    <td>
                      <input
                        type="checkbox"
                        disabled={m.already_imported}
                        checked={selected.has(m.model)}
                        onChange={() => toggle(m.model)}
                      />
                    </td>
                    <td dir="ltr">
                      {m.label !== m.model ? `${m.label} — ` : ""}{m.model}{" "}
                      {isFree(m) ? (
                        <Badge tone="brand">{t("models.freeTierBadge")}</Badge>
                      ) : (
                        <Badge>{tdp("paidModel")}</Badge>
                      )}{" "}
                      {m.already_imported ? (
                        <Badge tone="success">{t("models.alreadyImported")}</Badge>
                      ) : null}
                    </td>
                    <td>{formatNumber(m.input_usd_per_1m, locale)}</td>
                    <td>{formatNumber(m.output_usd_per_1m, locale)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <button className="btn btn-primary" style={{ marginTop: ".6rem" }}
            disabled={busy || selected.size === 0}
            onClick={() => void importSelected()}>
            {busy ? <Spinner /> : t("models.importSelected", { count: selected.size })}
          </button>
        </>
      )}
    </div>
  );
}
