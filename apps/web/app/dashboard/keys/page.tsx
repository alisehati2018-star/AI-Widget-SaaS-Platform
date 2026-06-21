"use client";

import { useCallback, useEffect, useState } from "react";
import type { ApiKey } from "../../../lib/api";
import { ApiError } from "../../../lib/api";
import { authFetch } from "../../../lib/auth";
import { DashboardShell, OWNER_NAV } from "../../../components/shell";
import { Alert, Badge, Field, Input, Spinner } from "../../../components/ui";

export default function KeysPage() {
  const [keys, setKeys] = useState<ApiKey[] | null>(null);
  const [scope, setScope] = useState("widget");
  const [label, setLabel] = useState("");
  const [created, setCreated] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    authFetch<{ keys: ApiKey[] }>("/tenant/keys").then((r) => setKeys(r.keys)).catch(() => setKeys([]));
  }, []);
  useEffect(() => load(), [load]);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const r = await authFetch<{ api_key: string }>("/tenant/keys", { body: { scope, label } });
      setCreated(r.api_key);
      setLabel("");
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not create key.");
    } finally {
      setBusy(false);
    }
  }

  async function revoke(id: string) {
    await authFetch(`/tenant/keys/${id}/revoke`, { method: "POST" }).catch(() => {});
    load();
  }

  return (
    <DashboardShell title="API keys" nav={OWNER_NAV}>
      <p style={{ marginTop: "-1rem" }}>Scoped, least-privilege keys connect your store and widget to Vitrin.</p>

      {created ? (
        <Alert kind="success">
          New key (copy it now — it won&apos;t be shown again):
          <br />
          <code style={{ wordBreak: "break-all" }}>{created}</code>
        </Alert>
      ) : null}

      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <h3>Create a key</h3>
        {error ? <Alert kind="error">{error}</Alert> : null}
        <form onSubmit={create} className="row" style={{ alignItems: "flex-end", flexWrap: "wrap" }}>
          <div style={{ minWidth: 180 }}>
            <Field label="Scope">
              <select className="input" value={scope} onChange={(e) => setScope(e.target.value)}>
                <option value="widget">widget (shopper search + chat)</option>
                <option value="sync">sync (catalogue ingest)</option>
              </select>
            </Field>
          </div>
          <div style={{ flex: 1, minWidth: 200 }}>
            <Field label="Label">
              <Input value={label} onChange={(e) => setLabel(e.target.value)} placeholder="e.g. Storefront widget" />
            </Field>
          </div>
          <button className="btn btn-primary" disabled={busy} style={{ marginBottom: "1rem" }}>
            {busy ? <Spinner /> : "Create key"}
          </button>
        </form>
      </div>

      <div className="card">
        <h3>Your keys</h3>
        {keys === null ? (
          <Spinner />
        ) : keys.length === 0 ? (
          <p className="muted">No keys yet.</p>
        ) : (
          <table className="table">
            <thead>
              <tr><th>Label</th><th>Scope</th><th>Created</th><th>Status</th><th></th></tr>
            </thead>
            <tbody>
              {keys.map((k) => (
                <tr key={k.id}>
                  <td>{k.label ?? "—"}</td>
                  <td><Badge tone="brand">{k.scope}</Badge></td>
                  <td className="muted">{k.created_at?.slice(0, 10) ?? "—"}</td>
                  <td>{k.revoked ? <Badge>revoked</Badge> : <Badge tone="success">active</Badge>}</td>
                  <td>
                    {!k.revoked ? (
                      <button className="btn btn-danger" onClick={() => void revoke(k.id)}>Revoke</button>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </DashboardShell>
  );
}
