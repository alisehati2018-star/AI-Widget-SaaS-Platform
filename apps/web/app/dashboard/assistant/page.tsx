"use client";

import { useEffect, useState } from "react";
import type { TenantProfile } from "../../../lib/api";
import { authFetch } from "../../../lib/auth";
import { DashboardShell, OWNER_NAV } from "../../../components/shell";
import { Alert, Field, Input, Spinner } from "../../../components/ui";

export default function AssistantPage() {
  const [greeting, setGreeting] = useState("");
  const [loaded, setLoaded] = useState(false);
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    authFetch<TenantProfile>("/tenant/profile")
      .then((p) => setGreeting(p.settings.widget_greeting ?? ""))
      .catch(() => {})
      .finally(() => setLoaded(true));
  }, []);

  async function save() {
    setBusy(true);
    setSaved(false);
    try {
      await authFetch("/tenant/settings", { method: "PATCH", body: { widget_greeting: greeting } });
      setSaved(true);
    } finally {
      setBusy(false);
    }
  }

  return (
    <DashboardShell title="Shopping assistant" nav={OWNER_NAV}>
      <p style={{ marginTop: "-1rem" }}>
        A grounded RAG assistant that answers only from your catalogue — no invented products.
      </p>

      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <h3>Greeting</h3>
        {saved ? <Alert kind="success">Saved.</Alert> : null}
        {loaded ? (
          <Field label="Opening message shown in the chat widget">
            <Input
              value={greeting}
              onChange={(e) => setGreeting(e.target.value)}
              placeholder="سلام! چطور می‌تونم در پیدا کردن محصول کمکتون کنم؟"
            />
          </Field>
        ) : (
          <Spinner />
        )}
        <button className="btn btn-primary" onClick={() => void save()} disabled={busy}>
          {busy ? <Spinner /> : "Save"}
        </button>
      </div>

      <div className="card">
        <h3>Guardrails</h3>
        <ul className="feature-list">
          <li>Answers are grounded in your synced catalogue only (no hallucinated products).</li>
          <li>Prompt-injection defences and a release-blocking guardrail test protect every turn.</li>
          <li>The cost ladder (cache → search → small model → large model) keeps spend low.</li>
          <li>Out-of-scope questions are politely declined rather than answered from the open web.</li>
        </ul>
        <p className="hint">Model routing &amp; budget caps are managed by the platform AI gateway.</p>
      </div>
    </DashboardShell>
  );
}
