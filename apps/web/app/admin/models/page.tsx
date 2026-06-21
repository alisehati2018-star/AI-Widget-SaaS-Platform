"use client";

import { useEffect, useState } from "react";
import { authFetch } from "../../../lib/auth";
import { ADMIN_NAV, DashboardShell } from "../../../components/shell";
import { Badge, Spinner } from "../../../components/ui";

interface Models {
  embeddings_url: string;
  reranker_url: string;
  llm_url: string;
  llm_model: string;
  frontier_enabled: boolean;
  frontier_model: string | null;
  rerank_enabled: boolean;
  by_rung: { rung: string; count: number }[];
}

export default function AdminModels() {
  const [data, setData] = useState<Models | null>(null);

  useEffect(() => {
    authFetch<Models>("/admin/models").then(setData).catch(() => setData(null));
  }, []);

  if (!data) {
    return (
      <DashboardShell title="Models & gateway" nav={ADMIN_NAV} requireAdmin loginHref="/admin/login">
        <Spinner />
      </DashboardShell>
    );
  }

  return (
    <DashboardShell title="Models & gateway" nav={ADMIN_NAV} requireAdmin loginHref="/admin/login">
      <p style={{ marginTop: "-1rem" }}>Inference endpoints, routing config, and call distribution.</p>
      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <h3>Configuration</h3>
        <table className="table">
          <tbody>
            <tr><td className="muted">Local LLM</td><td>{data.llm_model} <span className="muted">({data.llm_url})</span></td></tr>
            <tr><td className="muted">Embeddings</td><td className="muted">{data.embeddings_url}</td></tr>
            <tr><td className="muted">Reranker</td><td>{data.rerank_enabled ? <Badge tone="success">on</Badge> : <Badge>off</Badge>} <span className="muted">{data.reranker_url}</span></td></tr>
            <tr><td className="muted">Frontier fallback</td><td>{data.frontier_enabled ? <Badge tone="warning">{data.frontier_model ?? "enabled"}</Badge> : <Badge>disabled</Badge>}</td></tr>
          </tbody>
        </table>
      </div>
      <div className="card">
        <h3>Calls by rung</h3>
        {data.by_rung.length ? (
          <table className="table">
            <thead><tr><th>Rung</th><th>Calls</th></tr></thead>
            <tbody>{data.by_rung.map((r) => <tr key={r.rung}><td>{r.rung}</td><td>{r.count}</td></tr>)}</tbody>
          </table>
        ) : (
          <p className="muted">No routing data yet (needs live gateway traffic).</p>
        )}
      </div>
    </DashboardShell>
  );
}
