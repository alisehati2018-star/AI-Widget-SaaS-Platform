"use client";

// Local inference infrastructure status (env-configured LLM / embeddings /
// reranker) + reachability ping + per-rung call distribution. Consumes
// GET /admin/models and POST /admin/models/ping — the env-level snapshot,
// distinct from the DB-backed provider registry on /admin/providers.

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { adminFetch as authFetch } from "@/lib/auth";
import { formatNumber } from "@/lib/datetime";
import type { Locale } from "@/i18n/routing";
import { Alert, Badge, Spinner } from "@/components/ui";

interface ModelsInfo {
  embeddings_url: string | null;
  reranker_url: string | null;
  llm_url: string | null;
  llm_model: string | null;
  frontier_enabled: boolean;
  frontier_model: string | null;
  rerank_enabled: boolean;
  by_rung: { rung: string; count: number }[];
}

interface PingResult {
  services: Record<string, { configured: boolean; reachable: boolean; latency_ms: number | null }>;
}

export function LocalInfraCard() {
  const t = useTranslations("admin");
  const locale = useLocale() as Locale;
  const [info, setInfo] = useState<ModelsInfo | null>(null);
  const [loadFailed, setLoadFailed] = useState(false);
  const [ping, setPing] = useState<PingResult | null>(null);
  const [pinging, setPinging] = useState(false);
  const [nonce, setNonce] = useState(0);

  useEffect(() => {
    setLoadFailed(false);
    authFetch<ModelsInfo>("/admin/models")
      .then(setInfo)
      .catch(() => { setInfo(null); setLoadFailed(true); });
  }, [nonce]);

  async function pingAll() {
    setPinging(true);
    try {
      setPing(await authFetch<PingResult>("/admin/models/ping", { method: "POST", body: {} }));
    } catch {
      setPing(null);
    } finally {
      setPinging(false);
    }
  }

  const rows: { key: string; label: string; value: string | null }[] = info
    ? [
        { key: "llm", label: t("models.localLlm"), value: info.llm_url ? `${info.llm_url}${info.llm_model ? ` (${info.llm_model})` : ""}` : null },
        { key: "embeddings", label: t("models.embeddings"), value: info.embeddings_url },
        { key: "reranker", label: t("models.reranker"), value: info.reranker_url },
        { key: "frontier", label: t("models.frontier"), value: info.frontier_enabled ? info.frontier_model : null },
      ]
    : [];

  return (
    <div className="card" style={{ marginTop: "1.5rem" }}>
      <div className="row-between" style={{ flexWrap: "wrap", gap: ".6rem" }}>
        <h3 style={{ margin: 0 }}>{t("models.configTitle")}</h3>
        <button className="btn btn-soft" onClick={() => void pingAll()} disabled={pinging || !info}>
          {pinging ? <Spinner /> : t("models.pingAll")}
        </button>
      </div>
      <p className="hint">{t("models.envConfigHint")}</p>
      {loadFailed ? (
        <>
          <Alert kind="error">{t("common.loadFailed")}</Alert>
          <button className="btn btn-soft" onClick={() => setNonce((n) => n + 1)}>{t("common.retry")}</button>
        </>
      ) : !info ? (
        <Spinner />
      ) : (
        <>
          <table className="table">
            <tbody>
              {rows.map((r) => {
                const p = ping?.services?.[r.key];
                return (
                  <tr key={r.key}>
                    <td>{r.label}</td>
                    <td className="muted" dir="ltr">{r.value ?? t("models.notConfigured")}</td>
                    <td>
                      {p ? (
                        p.reachable ? (
                          <Badge tone="success">
                            {p.latency_ms != null ? `${formatNumber(p.latency_ms, locale)} ${t("common.ms")}` : t("common.on")}
                          </Badge>
                        ) : p.configured ? (
                          <Badge tone="warning">{t("common.off")}</Badge>
                        ) : (
                          <Badge>{t("models.notConfigured")}</Badge>
                        )
                      ) : null}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {ping ? <p className="hint">{t("models.pingHint")}</p> : null}
          {info.by_rung.length > 0 ? (
            <>
              <h4>{t("models.byRung")}</h4>
              <div className="row" style={{ flexWrap: "wrap", gap: ".5rem" }}>
                {info.by_rung.map((r) => (
                  <Badge key={r.rung}>{r.rung}: {formatNumber(r.count, locale)}</Badge>
                ))}
              </div>
            </>
          ) : null}
        </>
      )}
    </div>
  );
}
