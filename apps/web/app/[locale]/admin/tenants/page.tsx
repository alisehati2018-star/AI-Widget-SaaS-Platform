"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";
import { ApiError } from "@/lib/api";
import { authFetch } from "@/lib/auth";
import { Link } from "@/i18n/navigation";
import { useResource } from "@/lib/hooks/useResource";
import { DashboardShell, useAdminNav } from "@/components/shell";
import { Alert, Badge, Field, Input, Spinner } from "@/components/ui";

interface Tenant {
  id: string;
  slug: string;
  name: string;
  status: string;
  plan: string;
  sub_status: string;
  created_at: string | null;
}

export default function AdminTenants() {
  const t = useTranslations("admin");
  const tErrors = useTranslations("errors");
  const nav = useAdminNav();
  const { data, error, loading, reload } = useResource<{ tenants: Tenant[] }>("/admin/tenants");
  const tenants = loading ? null : (data?.tenants ?? []);

  const [slug, setSlug] = useState("");
  const [name, setName] = useState("");
  const [scope, setScope] = useState("widget");
  const [created, setCreated] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);
    setCreated(null);
    setBusy(true);
    try {
      const r = await authFetch<{ api_key: string }>("/admin/tenants", {
        body: { slug, name: name || slug, scope },
      });
      setCreated(r.api_key);
      setSlug("");
      setName("");
      reload();
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : tErrors("saveFailed"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <DashboardShell title={t("tenants.title")} nav={nav} requireAdmin loginHref="/admin/login">
      <p style={{ marginTop: "-1rem" }}>{t("tenants.intro")}</p>

      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <h3>{t("tenants.createTitle")}</h3>
        {formError ? <Alert kind="error">{formError}</Alert> : null}
        {created ? (
          <Alert kind="success">
            {t("tenants.created")}
            <br />
            <code style={{ wordBreak: "break-all" }}>{created}</code>
          </Alert>
        ) : null}
        <form onSubmit={create} className="row" style={{ alignItems: "flex-end", flexWrap: "wrap" }}>
          <div style={{ minWidth: 160 }}>
            <Field label={t("tenants.slug")}>
              <Input value={slug} onChange={(e) => setSlug(e.target.value)} placeholder={t("tenants.slugPlaceholder")} required />
            </Field>
          </div>
          <div style={{ flex: 1, minWidth: 180 }}>
            <Field label={t("tenants.name")}>
              <Input value={name} onChange={(e) => setName(e.target.value)} placeholder={t("tenants.namePlaceholder")} />
            </Field>
          </div>
          <div style={{ minWidth: 150 }}>
            <Field label={t("tenants.scope")}>
              <select className="input" value={scope} onChange={(e) => setScope(e.target.value)}>
                <option value="widget">{t("tenants.scopeWidget")}</option>
                <option value="sync">{t("tenants.scopeSync")}</option>
              </select>
            </Field>
          </div>
          <button className="btn btn-primary" disabled={busy} style={{ marginBottom: "1rem" }}>
            {busy ? <Spinner /> : t("tenants.create")}
          </button>
        </form>
      </div>

      <div className="card">
        {error ? <p className="muted">{t("common.loadError")}: {error}</p> : null}
        <table className="table">
          <thead>
            <tr>
              <th>{t("tenants.colStore")}</th>
              <th>{t("tenants.colSlug")}</th>
              <th>{t("tenants.colPlan")}</th>
              <th>{t("tenants.colSubscription")}</th>
              <th>{t("tenants.colStatus")}</th>
            </tr>
          </thead>
          <tbody>
            {(tenants ?? []).map((row) => (
              <tr key={row.id}>
                <td><Link href={`/admin/tenants/${row.id}`} className="grad-text">{row.name}</Link></td>
                <td className="muted">{row.slug}</td>
                <td>{row.plan}</td>
                <td><Badge tone={row.sub_status === "active" ? "success" : "warning"}>{row.sub_status}</Badge></td>
                <td><Badge tone={row.status === "active" ? "success" : undefined}>{row.status}</Badge></td>
              </tr>
            ))}
          </tbody>
        </table>
        {tenants && tenants.length === 0 ? <p className="muted">{t("tenants.empty")}</p> : null}
      </div>
    </DashboardShell>
  );
}
