"use client";

// Per-task routing: the ordered model chain each feature uses ('chat' = the
// shopper assistant's frontier ladder, 'analyst' = the admin insight engine).
// The gateway always appends the local fallback, so an external-only chain is
// still safe. Changes apply live (no restart).

import { useTranslations } from "next-intl";
import { useState } from "react";
import { ApiError } from "@/lib/api";
import { adminFetch as authFetch } from "@/lib/auth";
import { Alert, Badge, Spinner } from "@/components/ui";
import type { AiProvider, RoutesData } from "./types";

export function RoutesCard({
  routes,
  providers,
  reload,
}: {
  routes: RoutesData;
  providers: AiProvider[];
  reload: () => void;
}) {
  const t = useTranslations("admin");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [picking, setPicking] = useState<Record<string, string>>({});

  const allModels = providers.flatMap((p) =>
    p.models.map((m) => ({ id: m.id, label: `${p.name} / ${m.model}` }))
  );

  async function save(task: string, modelIds: string[]) {
    setError(null);
    setBusy(true);
    try {
      await authFetch(`/admin/ai/routes/${task}`, {
        method: "PUT",
        body: { model_ids: modelIds },
      });
      reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("models.actionFailed"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card" style={{ marginBottom: "1.5rem" }}>
      <h3>{t("models.routesTitle")}</h3>
      <p className="hint">{t("models.routesHint")}</p>
      {error ? <Alert kind="error">{error}</Alert> : null}
      {routes.tasks.map((task) => {
        const chain = routes.routes[task] ?? [];
        const ids = chain.map((c) => c.model_id);
        return (
          <div key={task} style={{ margin: "0.8rem 0" }}>
            <strong>{t(`models.task_${task}`)}</strong>
            {chain.length ? (
              <ol style={{ margin: ".4rem 0", paddingInlineStart: "1.4rem" }}>
                {chain.map((c, i) => (
                  <li key={c.model_id} style={{ margin: ".25rem 0" }}>
                    <span dir="ltr">{c.provider} / {c.model}</span>{" "}
                    {c.is_local ? <Badge tone="brand">{t("models.local")}</Badge> : null}{" "}
                    {i > 0 ? (
                      <button className="btn" disabled={busy} onClick={() => {
                        const next = [...ids];
                        [next[i - 1], next[i]] = [next[i], next[i - 1]];
                        void save(task, next);
                      }}>
                        {t("models.moveUp")}
                      </button>
                    ) : null}{" "}
                    <button className="btn btn-danger" disabled={busy}
                      onClick={() => void save(task, ids.filter((x) => x !== c.model_id))}>
                      {t("models.remove")}
                    </button>
                  </li>
                ))}
              </ol>
            ) : (
              <p className="muted">{t("models.routeEmpty")}</p>
            )}
            <div style={{ display: "flex", gap: ".4rem", flexWrap: "wrap" }}>
              <select className="input" style={{ maxWidth: "22rem" }}
                value={picking[task] ?? ""}
                onChange={(e) => setPicking({ ...picking, [task]: e.target.value })}
                aria-label={t("models.pickModel")}>
                <option value="">{t("models.pickModel")}</option>
                {allModels
                  .filter((m) => !ids.includes(m.id))
                  .map((m) => (
                    <option key={m.id} value={m.id}>{m.label}</option>
                  ))}
              </select>
              <button className="btn btn-primary"
                disabled={busy || !picking[task]}
                onClick={() => {
                  void save(task, [...ids, picking[task]]);
                  setPicking({ ...picking, [task]: "" });
                }}>
                {busy ? <Spinner /> : t("models.addToChain")}
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
}
