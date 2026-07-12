"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { useApiErrorMessage } from "@/lib/errors";
import { adminFetch as authFetch } from "@/lib/auth";
import { DashboardShell, useAdminNav } from "@/components/shell";
import { Alert, Badge, Field, Input, Spinner } from "@/components/ui";

interface TenantRow { id: string; name: string }
interface Citation { product_id?: string; title?: string; brand?: string; price?: number }
interface ChatTurn {
  answer?: string;
  rung?: string;
  citations?: Citation[];
  cached?: boolean;
  latency_ms?: number;
}
interface SearchResult { results?: Citation[] }
interface HistoryEntry {
  role: "user" | "assistant";
  text: string;
  rung?: string;
  latency_ms?: number;
  cached?: boolean;
  citations?: Citation[];
}

const HISTORY_KEY = (tenant: string) => `vitrin.agent.history.${tenant}`;

function loadHistory(tenant: string): HistoryEntry[] {
  try {
    return JSON.parse(window.localStorage.getItem(HISTORY_KEY(tenant)) ?? "[]") as HistoryEntry[];
  } catch {
    return [];
  }
}

function saveHistory(tenant: string, turns: HistoryEntry[]) {
  try {
    window.localStorage.setItem(HISTORY_KEY(tenant), JSON.stringify(turns.slice(-40)));
  } catch {
    // storage full/blocked — history is a convenience, never an error
  }
}

export default function AdminAgent() {
  const t = useTranslations("admin");
  const apiMsg = useApiErrorMessage();
  const nav = useAdminNav();
  const [tenants, setTenants] = useState<TenantRow[]>([]);
  const [selected, setSelected] = useState("");
  const [tab, setTab] = useState<"chat" | "search">("chat");
  const [message, setMessage] = useState("");
  const [query, setQuery] = useState("");
  const [busy, setBusy] = useState(false);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [results, setResults] = useState<Citation[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [docCount, setDocCount] = useState<number | null>(null);
  const [docCountFailed, setDocCountFailed] = useState(false);

  useEffect(() => {
    authFetch<{ tenants: TenantRow[] }>("/admin/tenants")
      .then((r) => { setTenants(r.tenants); if (r.tenants[0]) setSelected(r.tenants[0].id); })
      .catch(() => setTenants([]));
  }, []);

  useEffect(() => {
    if (!selected) return;
    setDocCount(null);
    setDocCountFailed(false);
    setResults(null);
    // Each tenant keeps its own console history (locally, per browser).
    setHistory(loadHistory(selected));
    authFetch<{ docs: number }>(`/admin/es/tenant-count?tenant=${encodeURIComponent(selected)}`)
      .then((r) => setDocCount(r.docs))
      .catch(() => setDocCountFailed(true));
  }, [selected]);

  function pushTurns(...entries: HistoryEntry[]) {
    setHistory((cur) => {
      const next = [...cur, ...entries];
      saveHistory(selected, next);
      return next;
    });
  }

  function clearHistory() {
    setHistory([]);
    saveHistory(selected, []);
  }

  async function send() {
    if (!selected || !message.trim()) return;
    const question = message.trim();
    setBusy(true); setErr(null);
    setMessage("");
    pushTurns({ role: "user", text: question });
    try {
      const r = await authFetch<ChatTurn>("/admin/agent/test", {
        body: { tenant_id: selected, message: question },
      });
      pushTurns({
        role: "assistant",
        text: r.answer ?? "",
        rung: r.rung,
        latency_ms: r.latency_ms,
        cached: r.cached,
        citations: r.citations,
      });
    } catch (e) {
      setErr(apiMsg(e) ?? t("agent.failed"));
    } finally { setBusy(false); }
  }

  async function runSearch() {
    if (!selected || !query.trim()) return;
    setBusy(true); setErr(null); setResults(null);
    try {
      const r = await authFetch<SearchResult>("/admin/agent/search", {
        body: { tenant_id: selected, query: query.trim() },
      });
      setResults(r.results ?? []);
    } catch (e) {
      setErr(apiMsg(e) ?? t("agent.failed"));
    } finally { setBusy(false); }
  }

  function citationList(items: Citation[]) {
    if (!items.length) return <p className="muted">{t("agent.noResults")}</p>;
    return (
      <table className="table">
        <tbody>
          {items.map((c, i) => (
            <tr key={c.product_id ?? i}>
              <td>{c.title ?? c.product_id}</td>
              <td className="muted">{c.brand ?? ""}</td>
              <td>{c.price != null ? c.price : ""}</td>
            </tr>
          ))}
        </tbody>
      </table>
    );
  }

  return (
    <DashboardShell title={t("agent.title")} nav={nav} requireAdmin loginHref="/admin/login">
      <div className="row-between" style={{ marginTop: "-1rem", marginBottom: "1.5rem", flexWrap: "wrap", gap: ".75rem" }}>
        <p style={{ margin: 0 }}>{t("agent.intro")}</p>
        <select className="input" style={{ maxWidth: 260 }} aria-label={t("common.tenant")} value={selected} onChange={(e) => setSelected(e.target.value)}>
          {tenants.length === 0 ? <option value="">{t("common.noTenants")}</option> : null}
          {tenants.map((tn) => <option key={tn.id} value={tn.id}>{tn.name}</option>)}
        </select>
      </div>
      {err ? <Alert kind="error">{err}</Alert> : null}

      <div className="dash-2col">
        <div className="card-stack">
          <div className="row" style={{ gap: ".5rem" }}>
            <button className={`btn ${tab === "chat" ? "btn-primary" : "btn-soft"}`} onClick={() => setTab("chat")}>{t("agent.tabChat")}</button>
            <button className={`btn ${tab === "search" ? "btn-primary" : "btn-soft"}`} onClick={() => setTab("search")}>{t("agent.tabSearch")}</button>
          </div>

          {tab === "chat" ? (
            <div className="card">
              {history.length === 0 ? (
                <p className="muted">{t("agent.empty")}</p>
              ) : (
                <div style={{ maxHeight: 420, overflowY: "auto", display: "flex", flexDirection: "column", gap: ".75rem", marginBottom: "1rem" }}>
                  {history.map((h, i) => (
                    <div key={i} className={`mock-bubble ${h.role === "user" ? "user" : "bot"}`}>
                      <p style={{ whiteSpace: "pre-wrap", margin: 0 }}>{h.text}</p>
                      {h.role === "assistant" ? (
                        <div className="row" style={{ gap: ".4rem", flexWrap: "wrap", marginTop: ".5rem" }}>
                          {h.rung ? <Badge tone="brand">{t("agent.rung")}: {h.rung}</Badge> : null}
                          {h.latency_ms != null ? <Badge>{t("agent.latency")}: {h.latency_ms} ms</Badge> : null}
                          {h.cached ? <Badge tone="success">{t("agent.cached")}</Badge> : null}
                          {h.citations?.length ? <Badge>{t("agent.citations")}: {h.citations.length}</Badge> : null}
                        </div>
                      ) : null}
                    </div>
                  ))}
                </div>
              )}
              <Field label={t("agent.messageLabel")}>
                <Input value={message} onChange={(e) => setMessage(e.target.value)}
                  onKeyDown={(e) => { if (e.key === "Enter") void send(); }}
                  placeholder={t("agent.messagePlaceholder")} />
              </Field>
              <div className="row" style={{ gap: ".5rem", flexWrap: "wrap" }}>
                <button className="btn btn-primary" disabled={busy || !selected} onClick={() => void send()}>
                  {busy ? <Spinner /> : t("agent.send")}
                </button>
                {history.length ? (
                  <button className="btn btn-ghost" onClick={clearHistory}>{t("agent.clearHistory")}</button>
                ) : null}
              </div>
              {history.at(-1)?.role === "assistant" && history.at(-1)?.citations?.length ? (
                <div style={{ marginTop: "1.25rem" }}>
                  <h4>{t("agent.citations")}</h4>
                  {citationList(history.at(-1)?.citations ?? [])}
                </div>
              ) : null}
            </div>
          ) : (
            <div className="card">
              <Field label={t("agent.tabSearch")}>
                <Input value={query} onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={(e) => { if (e.key === "Enter") void runSearch(); }}
                  placeholder={t("agent.queryPlaceholder")} />
              </Field>
              <button className="btn btn-primary" disabled={busy || !selected} onClick={() => void runSearch()}>
                {busy ? <Spinner /> : t("agent.runSearch")}
              </button>
              {results ? <div style={{ marginTop: "1.25rem" }}><h4>{t("agent.results")}</h4>{citationList(results)}</div> : null}
            </div>
          )}
        </div>

        <div className="card-stack">
          <div className="card">
            <h3>{t("agent.contextTitle")}</h3>
            <table className="table">
              <tbody>
                <tr><td className="muted">{t("common.tenant")}</td><td><code>{selected || "—"}</code></td></tr>
                <tr>
                  <td className="muted">{t("agent.indexedDocs")}</td>
                  <td>{docCountFailed ? "—" : docCount == null ? t("agent.docsLoading") : docCount}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div className="card">
            <h3>{t("agent.sessionTitle")}</h3>
            <p className="hint">{t("agent.sessionHint")}</p>
            <table className="table">
              <tbody>
                <tr>
                  <td className="muted">{t("agent.historyCount")}</td>
                  <td>{history.length}</td>
                </tr>
              </tbody>
            </table>
            {history.length ? (
              <button className="btn btn-soft" onClick={clearHistory}>{t("agent.clearHistory")}</button>
            ) : null}
          </div>
        </div>
      </div>
    </DashboardShell>
  );
}
