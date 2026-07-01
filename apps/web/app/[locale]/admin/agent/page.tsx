"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { ApiError } from "@/lib/api";
import { authFetch } from "@/lib/auth";
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

export default function AdminAgent() {
  const t = useTranslations("admin");
  const nav = useAdminNav();
  const [tenants, setTenants] = useState<TenantRow[]>([]);
  const [selected, setSelected] = useState("");
  const [tab, setTab] = useState<"chat" | "search">("chat");
  const [message, setMessage] = useState("");
  const [query, setQuery] = useState("");
  const [busy, setBusy] = useState(false);
  const [turn, setTurn] = useState<ChatTurn | null>(null);
  const [results, setResults] = useState<Citation[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [docCount, setDocCount] = useState<number | null>(null);

  useEffect(() => {
    authFetch<{ tenants: TenantRow[] }>("/admin/tenants")
      .then((r) => { setTenants(r.tenants); if (r.tenants[0]) setSelected(r.tenants[0].id); })
      .catch(() => setTenants([]));
  }, []);

  useEffect(() => {
    if (!selected) return;
    setDocCount(null);
    setTurn(null);
    setResults(null);
    authFetch<{ docs: number }>(`/admin/es/tenant-count?tenant=${encodeURIComponent(selected)}`)
      .then((r) => setDocCount(r.docs))
      .catch(() => setDocCount(null));
  }, [selected]);

  async function send() {
    if (!selected || !message.trim()) return;
    setBusy(true); setErr(null); setTurn(null);
    try {
      const r = await authFetch<ChatTurn>("/admin/agent/test", {
        body: { tenant_id: selected, message: message.trim() },
      });
      setTurn(r);
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : t("agent.failed"));
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
      setErr(e instanceof ApiError ? e.message : t("agent.failed"));
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
        <select className="input" style={{ maxWidth: 260 }} value={selected} onChange={(e) => setSelected(e.target.value)}>
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
              <Field label={t("agent.messageLabel")}>
                <Input value={message} onChange={(e) => setMessage(e.target.value)}
                  onKeyDown={(e) => { if (e.key === "Enter") void send(); }}
                  placeholder={t("agent.messagePlaceholder")} />
              </Field>
              <button className="btn btn-primary" disabled={busy || !selected} onClick={() => void send()}>
                {busy ? <Spinner /> : t("agent.send")}
              </button>
              {turn ? (
                <div style={{ marginTop: "1.25rem" }}>
                  <div className="row" style={{ gap: ".5rem", flexWrap: "wrap", marginBottom: ".75rem" }}>
                    <Badge tone="brand">{t("agent.rung")}: {turn.rung}</Badge>
                    {turn.latency_ms != null ? <Badge>{t("agent.latency")}: {turn.latency_ms} ms</Badge> : null}
                    {turn.cached ? <Badge tone="success">{t("agent.cached")}</Badge> : null}
                  </div>
                  <h4>{t("agent.answer")}</h4>
                  <p style={{ whiteSpace: "pre-wrap" }}>{turn.answer}</p>
                  <h4>{t("agent.citations")}</h4>
                  {citationList(turn.citations ?? [])}
                </div>
              ) : <p className="muted" style={{ marginTop: "1rem" }}>{t("agent.empty")}</p>}
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
                  <td>{docCount == null ? t("agent.docsLoading") : docCount}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div className="card">
            <h3>{t("agent.sessionTitle")}</h3>
            <p className="hint">{t("agent.sessionHint")}</p>
          </div>
        </div>
      </div>
    </DashboardShell>
  );
}
