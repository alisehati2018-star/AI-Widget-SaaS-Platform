"use client";

import { useEffect, useState } from "react";
import type { TenantProfile } from "../../../lib/api";
import { authFetch } from "../../../lib/auth";
import { DashboardShell, OWNER_NAV } from "../../../components/shell";
import { Alert, Field, Input, Spinner } from "../../../components/ui";

export default function WidgetPage() {
  const [profile, setProfile] = useState<TenantProfile | null>(null);
  const [logo, setLogo] = useState("");
  const [color, setColor] = useState("#7c5cff");
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    authFetch<TenantProfile>("/tenant/profile").then((p) => {
      setProfile(p);
      setLogo(p.settings.logo_url ?? "");
      setColor(p.settings.primary_color ?? "#7c5cff");
    }).catch(() => setProfile(null));
  }, []);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setSaved(false);
    try {
      await authFetch("/tenant/settings", { method: "PATCH", body: { logo_url: logo, primary_color: color } });
      setSaved(true);
    } finally {
      setBusy(false);
    }
  }

  const snippet = `<script
  src="https://cdn.vitrin.ai/widget.js"
  data-tenant="${profile?.slug ?? "your-store"}"
  data-key="YOUR_WIDGET_KEY"
  defer></script>`;

  return (
    <DashboardShell title="Widget & branding" nav={OWNER_NAV}>
      <p style={{ marginTop: "-1rem" }}>Embed the search + chat widget and match it to your brand.</p>

      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <h3>Install snippet</h3>
        <p className="hint">Paste before <code>&lt;/body&gt;</code>. Use a <strong>widget</strong>-scoped API key.</p>
        <pre className="input" style={{ whiteSpace: "pre-wrap", fontFamily: "monospace", fontSize: "0.82rem" }}>
{snippet}
        </pre>
        <button className="btn btn-ghost" onClick={() => void navigator.clipboard?.writeText(snippet)}>
          Copy snippet
        </button>
      </div>

      <div className="card">
        <h3>White-label</h3>
        <p className="hint">Custom logo &amp; accent colour. Platform branding remains visible.</p>
        {saved ? <Alert kind="success">Branding saved.</Alert> : null}
        {profile ? (
          <form onSubmit={save}>
            <Field label="Logo URL">
              <Input value={logo} onChange={(e) => setLogo(e.target.value)} placeholder="https://.../logo.svg" />
            </Field>
            <Field label="Primary colour">
              <div className="row">
                <input type="color" value={color} onChange={(e) => setColor(e.target.value)} style={{ width: 48, height: 38, border: "none", background: "none" }} />
                <Input value={color} onChange={(e) => setColor(e.target.value)} style={{ maxWidth: 160 }} />
              </div>
            </Field>
            <button className="btn btn-primary" disabled={busy}>{busy ? <Spinner /> : "Save branding"}</button>
          </form>
        ) : (
          <Spinner />
        )}
      </div>
    </DashboardShell>
  );
}
