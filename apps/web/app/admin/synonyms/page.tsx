"use client";

import { useEffect, useState } from "react";
import { authFetch } from "../../../lib/auth";
import { ADMIN_NAV, DashboardShell } from "../../../components/shell";
import { Alert, Field, Spinner } from "../../../components/ui";

interface TenantRow { id: string; name: string }

export default function AdminSynonyms() {
  const [tenants, setTenants] = useState<TenantRow[]>([]);
  const [selected, setSelected] = useState("");
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    authFetch<{ tenants: TenantRow[] }>("/admin/tenants")
      .then((r) => {
        setTenants(r.tenants);
        if (r.tenants[0]) setSelected(r.tenants[0].id);
      })
      .catch(() => setTenants([]));
  }, []);

  useEffect(() => {
    if (!selected) return;
    setLoading(true);
    setSaved(false);
    authFetch<{ synonyms: string[] }>(`/admin/synonyms?tenant=${encodeURIComponent(selected)}`)
      .then((r) => setText(r.synonyms.join("\n")))
      .catch(() => setText(""))
      .finally(() => setLoading(false));
  }, [selected]);

  async function save() {
    const lines = text.split("\n").map((l) => l.trim()).filter(Boolean);
    await authFetch(`/admin/synonyms?tenant=${encodeURIComponent(selected)}`, { body: { synonyms: lines } });
    setSaved(true);
  }

  return (
    <DashboardShell title="Synonyms" nav={ADMIN_NAV} requireAdmin loginHref="/admin/login">
      <p style={{ marginTop: "-1rem" }}>Curate the per-tenant synonym set used by Persian search.</p>
      <div className="card" style={{ maxWidth: 420, marginBottom: "1.5rem" }}>
        <Field label="Tenant">
          <select className="input" value={selected} onChange={(e) => setSelected(e.target.value)}>
            {tenants.length === 0 ? <option value="">No tenants</option> : null}
            {tenants.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
          </select>
        </Field>
      </div>
      <div className="card">
        <h3>Synonyms</h3>
        {saved ? <Alert kind="success">Saved.</Alert> : null}
        {loading ? (
          <Spinner />
        ) : (
          <textarea
            className="input"
            style={{ minHeight: 200, fontFamily: "monospace" }}
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder={"laptop, notebook, لپ‌تاپ\nmobile, cellphone, موبایل"}
          />
        )}
        <div style={{ marginTop: "1rem" }}>
          <button className="btn btn-primary" onClick={() => void save()} disabled={!selected}>Save synonyms</button>
        </div>
      </div>
    </DashboardShell>
  );
}
