"use client";

import { useEffect, useState } from "react";
import type { TenantProfile } from "../../../lib/api";
import { authFetch } from "../../../lib/auth";
import { DashboardShell, OWNER_NAV } from "../../../components/shell";
import { Alert, Badge, Field, Input, Spinner } from "../../../components/ui";

export default function CatalogPage() {
  const [profile, setProfile] = useState<TenantProfile | null>(null);
  const [platform, setPlatform] = useState("woocommerce");
  const [storeUrl, setStoreUrl] = useState("");
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    authFetch<TenantProfile>("/tenant/profile").then((p) => {
      setProfile(p);
      setPlatform(p.settings.platform ?? "woocommerce");
      setStoreUrl(p.settings.store_url ?? "");
    }).catch(() => setProfile(null));
  }, []);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setSaved(false);
    try {
      await authFetch("/tenant/settings", { method: "PATCH", body: { platform, store_url: storeUrl } });
      setSaved(true);
    } finally {
      setBusy(false);
    }
  }

  const connected = Boolean(profile?.settings.store_url);

  return (
    <DashboardShell title="Catalog & sync" nav={OWNER_NAV}>
      <p style={{ marginTop: "-1rem" }}>
        Connect your store so Vitrin can index your catalogue and keep it fresh via event-driven sync.
      </p>

      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <div className="row-between">
          <h3 style={{ margin: 0 }}>Connection</h3>
          <Badge tone={connected ? "success" : "warning"}>{connected ? "connected" : "not connected"}</Badge>
        </div>
        {saved ? <Alert kind="success">Saved.</Alert> : null}
        <form onSubmit={save}>
          <Field label="Platform">
            <select className="input" value={platform} onChange={(e) => setPlatform(e.target.value)}>
              <option value="woocommerce">WooCommerce</option>
              <option value="opencart">OpenCart</option>
              <option value="custom">Custom (REST)</option>
            </select>
          </Field>
          <Field label="Store URL" hint="Where your storefront lives, e.g. https://shop.example.com">
            <Input value={storeUrl} onChange={(e) => setStoreUrl(e.target.value)} placeholder="https://shop.example.com" />
          </Field>
          <button className="btn btn-primary" disabled={busy}>{busy ? <Spinner /> : "Save connection"}</button>
        </form>
      </div>

      <div className="card">
        <h3>How sync works</h3>
        <ol className="muted" style={{ paddingLeft: "1.2rem", lineHeight: 2 }}>
          <li>Install the {platform} plugin and paste a <strong>sync</strong>-scoped API key.</li>
          <li>The plugin runs an initial bulk import, then posts a webhook on every product change.</li>
          <li>Only the delta is sent — prices, stock and new products stay fresh automatically.</li>
        </ol>
        <p className="hint">A manual re-sync button appears here once a sync key has been used.</p>
      </div>
    </DashboardShell>
  );
}
