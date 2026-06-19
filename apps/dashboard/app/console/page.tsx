"use client";

// Operator analytics console (M9: REQ-M9-004/005). Renders the four-dimension
// view (relevance · latency · cost · reliability) plus most-wanted and
// zero-result insights from /admin/analytics. Auth via the operator token.

import { useState } from "react";

interface Analytics {
  four_dimensions?: {
    cost?: { total?: number; no_paid_share?: number };
    latency?: { p95_ms?: number | null };
    reliability?: { turns?: number };
  };
  most_wanted?: { term: string; count: number }[];
  zero_results?: { term: string; count: number }[];
}

export default function ConsolePage() {
  const [tenant, setTenant] = useState("");
  const [token, setToken] = useState("");
  const [data, setData] = useState<Analytics | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setError(null);
    try {
      const resp = await fetch(`/admin/analytics?tenant=${encodeURIComponent(tenant)}`, {
        headers: { "x-admin-token": token },
      });
      if (!resp.ok) {
        setError(`Request failed: ${resp.status}`);
        return;
      }
      setData((await resp.json()) as Analytics);
    } catch (e) {
      setError(String(e));
    }
  }

  const fd = data?.four_dimensions;
  return (
    <main style={{ fontFamily: "system-ui, sans-serif", padding: "2rem" }}>
      <h1>ACIP Operator Console</h1>
      <p>Four dimensions: relevance · latency · cost · reliability (§18).</p>
      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1rem" }}>
        <input placeholder="tenant id" value={tenant} onChange={(e) => setTenant(e.target.value)} />
        <input placeholder="admin token" value={token} onChange={(e) => setToken(e.target.value)} />
        <button onClick={() => void load()}>Load</button>
      </div>
      {error && <p style={{ color: "crimson" }}>{error}</p>}
      {fd && (
        <section style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "1rem" }}>
          <Card title="Relevance" value="NDCG@10 (eval)" />
          <Card title="Latency p95" value={`${fd.latency?.p95_ms ?? "—"} ms`} />
          <Card title="Cost total" value={`${fd.cost?.total ?? 0}`} />
          <Card title="Reliability" value={`${fd.reliability?.turns ?? 0} turns`} />
        </section>
      )}
      {data?.zero_results && (
        <section>
          <h2>Zero-result queries</h2>
          <ul>
            {data.zero_results.map((z) => (
              <li key={z.term}>
                {z.term} — {z.count}
              </li>
            ))}
          </ul>
        </section>
      )}
    </main>
  );
}

function Card({ title, value }: { title: string; value: string }) {
  return (
    <div style={{ border: "1px solid #ccc", borderRadius: 8, padding: "1rem" }}>
      <strong>{title}</strong>
      <div>{value}</div>
    </div>
  );
}
