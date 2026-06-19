"use client";

// Synonym & curated-suggestion management (M9: REQ-M9-002). Edits the tenant's
// updateable synonym set without a reindex (blueprint §6.1). Auth via the
// operator token.

import { useState } from "react";

export default function SynonymsPage() {
  const [tenant, setTenant] = useState("");
  const [token, setToken] = useState("");
  const [text, setText] = useState("");
  const [status, setStatus] = useState<string | null>(null);

  async function load() {
    const resp = await fetch(`/admin/synonyms?tenant=${encodeURIComponent(tenant)}`, {
      headers: { "x-admin-token": token },
    });
    if (!resp.ok) {
      setStatus(`Load failed: ${resp.status}`);
      return;
    }
    const data = (await resp.json()) as { synonyms?: string[] };
    setText((data.synonyms ?? []).join("\n"));
    setStatus("Loaded");
  }

  async function save() {
    const resp = await fetch(`/admin/synonyms?tenant=${encodeURIComponent(tenant)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "x-admin-token": token },
      body: JSON.stringify({ synonyms: text.split("\n").filter((l) => l.trim().length > 0) }),
    });
    setStatus(resp.ok ? "Saved" : `Save failed: ${resp.status}`);
  }

  return (
    <main style={{ fontFamily: "system-ui, sans-serif", padding: "2rem" }}>
      <h1>Synonyms</h1>
      <p>One rule per line, e.g. <code>تلفن همراه, موبایل =&gt; گوشی</code></p>
      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1rem" }}>
        <input placeholder="tenant id" value={tenant} onChange={(e) => setTenant(e.target.value)} />
        <input placeholder="admin token" value={token} onChange={(e) => setToken(e.target.value)} />
        <button onClick={() => void load()}>Load</button>
        <button onClick={() => void save()}>Save</button>
      </div>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        rows={12}
        style={{ width: "100%", fontFamily: "monospace" }}
      />
      {status && <p>{status}</p>}
    </main>
  );
}
