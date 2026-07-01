"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { ApiError } from "@/lib/api";
import { authFetch } from "@/lib/auth";
import { DashboardShell, useAdminNav } from "@/components/shell";
import { Alert, Badge, Field, Input, Spinner } from "@/components/ui";

interface Health {
  reachable: boolean;
  status?: string;
  number_of_nodes?: number;
  nodes_total?: number;
  es_version?: string;
  docs_total?: number;
  store_size_bytes?: number;
  active_shards?: number;
  error?: string;
}
interface IndexRow {
  index: string;
  health: string;
  status: string;
  docs: number | null;
  size_bytes: number | null;
  shards: number | null;
  replicas: number | null;
  created: string | null;
}
interface AliasRow { alias: string; index: string }
interface TenantRow { id: string; name: string }

type EsAction = () => unknown;

function bytes(n?: number | null): string {
  if (!n && n !== 0) return "—";
  const u = ["B", "KB", "MB", "GB", "TB"];
  let i = 0;
  let v = n;
  while (v >= 1024 && i < u.length - 1) { v /= 1024; i++; }
  return `${v.toFixed(i ? 1 : 0)} ${u[i]}`;
}

export default function AdminElasticsearch() {
  const t = useTranslations("admin");
  const nav = useAdminNav();
  const [health, setHealth] = useState<Health | null>(null);
  const [indices, setIndices] = useState<IndexRow[]>([]);
  const [aliases, setAliases] = useState<AliasRow[]>([]);
  const [aliasName, setAliasName] = useState("");
  const [loading, setLoading] = useState(true);
  const [note, setNote] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [source, setSource] = useState("");
  const [mapping, setMapping] = useState<{ index: string; body: string } | null>(null);
  const [tenants, setTenants] = useState<TenantRow[]>([]);
  const [tenantSel, setTenantSel] = useState("");
  const [tenantDocs, setTenantDocs] = useState<number | null>(null);
  const [countBusy, setCountBusy] = useState(false);

  useEffect(() => {
    authFetch<{ tenants: TenantRow[] }>("/admin/tenants")
      .then((r) => { setTenants(r.tenants); if (r.tenants[0]) setTenantSel(r.tenants[0].id); })
      .catch(() => setTenants([]));
  }, []);

  async function countDocs() {
    if (!tenantSel) return;
    setCountBusy(true);
    setTenantDocs(null);
    try {
      const r = await authFetch<{ docs: number }>(`/admin/es/tenant-count?tenant=${encodeURIComponent(tenantSel)}`);
      setTenantDocs(r.docs);
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : t("elasticsearch.actionFailed"));
    } finally {
      setCountBusy(false);
    }
  }

  async function reload() {
    setLoading(true);
    try {
      const [h, idx] = await Promise.all([
        authFetch<Health>("/admin/es/health"),
        authFetch<{ alias: string; indices: IndexRow[]; aliases: AliasRow[] }>("/admin/es/indices"),
      ]);
      setHealth(h);
      setIndices(idx.indices);
      setAliases(idx.aliases);
      setAliasName(idx.alias);
    } catch {
      setHealth({ reachable: false });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void reload(); }, []);

  async function act(fn: EsAction, ok: string) {
    setNote(null);
    setErr(null);
    try {
      await fn();
      setNote(ok);
      await reload();
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : t("elasticsearch.actionFailed"));
    }
  }

  async function viewMapping(index: string) {
    setErr(null);
    try {
      const m = await authFetch<{ index: string; mapping: unknown; settings: unknown }>(
        `/admin/es/mapping?index=${encodeURIComponent(index)}`,
      );
      setMapping({ index, body: JSON.stringify({ mapping: m.mapping, settings: m.settings }, null, 2) });
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : t("elasticsearch.actionFailed"));
    }
  }

  return (
    <DashboardShell title={t("elasticsearch.title")} nav={nav} requireAdmin loginHref="/admin/login">
      <p style={{ marginTop: "-1rem" }}>{t("elasticsearch.intro")}</p>
      {note ? <Alert kind="success">{note}</Alert> : null}
      {err ? <Alert kind="error">{err}</Alert> : null}

      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <h3>{t("elasticsearch.clusterTitle")}</h3>
        {loading ? <Spinner /> : !health?.reachable ? (
          <Alert kind="error">{t("elasticsearch.unreachable")}{health?.error ? `: ${health.error}` : ""}</Alert>
        ) : (
          <div className="stat-grid">
            <div className="stat"><span className="stat-label">{t("elasticsearch.status")}</span>
              <span className="stat-value"><Badge tone={health.status === "green" ? "success" : health.status === "yellow" ? "warning" : "warning"}>{health.status}</Badge></span></div>
            <div className="stat"><span className="stat-label">{t("elasticsearch.nodes")}</span><span className="stat-value">{health.nodes_total ?? health.number_of_nodes ?? "—"}</span></div>
            <div className="stat"><span className="stat-label">{t("elasticsearch.version")}</span><span className="stat-value">{health.es_version ?? "—"}</span></div>
            <div className="stat"><span className="stat-label">{t("elasticsearch.docsTotal")}</span><span className="stat-value">{health.docs_total ?? "—"}</span></div>
            <div className="stat"><span className="stat-label">{t("elasticsearch.storeSize")}</span><span className="stat-value">{bytes(health.store_size_bytes)}</span></div>
            <div className="stat"><span className="stat-label">{t("elasticsearch.shards")}</span><span className="stat-value">{health.active_shards ?? "—"}</span></div>
          </div>
        )}
      </div>

      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <div className="row-between">
          <h3 style={{ margin: 0 }}>{t("elasticsearch.indicesTitle")}</h3>
          <button className="btn btn-soft" onClick={() => void act(() => authFetch("/admin/es/ensure-index", { body: {} }), t("elasticsearch.ensured"))}>
            {t("elasticsearch.ensureIndex")}
          </button>
        </div>
        <p className="hint">{t("elasticsearch.aliasTitle")}: <code>{aliasName}</code>
          {aliases.map((a) => <span key={a.alias}> → <code>{a.index}</code></span>)}</p>
        {indices.length === 0 ? <p className="muted">{t("elasticsearch.noIndices")}</p> : (
          <table className="table">
            <thead><tr>
              <th>{t("elasticsearch.colIndex")}</th><th>{t("elasticsearch.colHealth")}</th>
              <th>{t("elasticsearch.colDocs")}</th><th>{t("elasticsearch.colSize")}</th>
              <th>{t("elasticsearch.colShards")}</th><th>{t("elasticsearch.colCreated")}</th>
              <th>{t("elasticsearch.colActions")}</th>
            </tr></thead>
            <tbody>
              {indices.map((r) => {
                const live = aliases.some((a) => a.index === r.index);
                return (
                  <tr key={r.index}>
                    <td><code>{r.index}</code>{live ? <> <Badge tone="success">{t("elasticsearch.live")}</Badge></> : null}</td>
                    <td><Badge tone={r.health === "green" ? "success" : r.health === "yellow" ? "warning" : "warning"}>{r.health}</Badge></td>
                    <td>{r.docs ?? "—"}</td>
                    <td>{bytes(r.size_bytes)}</td>
                    <td>{r.shards}/{r.replicas}</td>
                    <td className="muted">{r.created ?? "—"}</td>
                    <td>
                      <div className="row" style={{ flexWrap: "wrap", gap: ".3rem" }}>
                        <button className="btn btn-ghost" onClick={() => void viewMapping(r.index)}>{t("elasticsearch.viewMapping")}</button>
                        {!live ? <button className="btn btn-ghost" onClick={() => void act(() => authFetch("/admin/es/alias", { body: { index: r.index } }), t("elasticsearch.swapped"))}>{t("elasticsearch.swapHere")}</button> : null}
                        {!live ? <button className="btn btn-danger" onClick={() => { if (window.confirm(t("elasticsearch.deleteConfirm", { index: r.index }))) void act(() => authFetch("/admin/es/delete-index", { body: { index: r.index } }), t("elasticsearch.deleted")); }}>{t("elasticsearch.deleteIndex")}</button> : null}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      <div className="dash-2col-even" style={{ marginBottom: "1.5rem" }}>
        <div className="card">
          <h3>{t("elasticsearch.reindexTitle")}</h3>
          <p className="hint">{t("elasticsearch.reindexHint")}</p>
          <div className="row" style={{ flexWrap: "wrap", alignItems: "flex-end", gap: ".75rem" }}>
            <Field label={t("elasticsearch.sourceIndex")}>
              <Input value={source} onChange={(e) => setSource(e.target.value)} placeholder={aliases[0]?.index ?? ""} />
            </Field>
            <button className="btn btn-primary" disabled={!source.trim()}
              onClick={() => void act(() => authFetch("/admin/es/reindex", { body: { source_index: source.trim() } }), t("elasticsearch.reindexed"))}>
              {t("elasticsearch.reindexBtn")}
            </button>
          </div>
        </div>

        <div className="card">
          <h3>{t("elasticsearch.tenantCountTitle")}</h3>
          <div className="row" style={{ flexWrap: "wrap", alignItems: "flex-end", gap: ".75rem" }}>
            <Field label={t("common.tenant")}>
              <select className="input" value={tenantSel} onChange={(e) => { setTenantSel(e.target.value); setTenantDocs(null); }}>
                {tenants.length === 0 ? <option value="">{t("common.noTenants")}</option> : null}
                {tenants.map((tn) => <option key={tn.id} value={tn.id}>{tn.name}</option>)}
              </select>
            </Field>
            <button className="btn btn-soft" disabled={!tenantSel || countBusy} onClick={() => void countDocs()}>
              {countBusy ? <Spinner /> : t("elasticsearch.tenantCountBtn")}
            </button>
          </div>
          {tenantDocs != null ? (
            <p style={{ marginTop: "1rem" }}>{t("elasticsearch.docsForTenant")}: <strong>{tenantDocs}</strong></p>
          ) : null}
        </div>
      </div>

      {mapping ? (
        <div className="card">
          <h3>{t("elasticsearch.mappingTitle")} — <code>{mapping.index}</code></h3>
          <pre style={{ maxHeight: 360, overflow: "auto", fontSize: ".8rem" }}>{mapping.body}</pre>
        </div>
      ) : null}
    </DashboardShell>
  );
}
