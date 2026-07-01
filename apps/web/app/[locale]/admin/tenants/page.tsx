"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { ApiError } from "@/lib/api";
import { adminFetch as authFetch } from "@/lib/auth";
import { Link } from "@/i18n/navigation";
import { formatNumber } from "@/lib/datetime";
import { useAdminResource as useResource } from "@/lib/hooks/useResource";
import type { Locale } from "@/i18n/routing";
import { DashboardShell, useAdminNav } from "@/components/shell";
import { Alert, Badge, Field, Input, Spinner } from "@/components/ui";

interface Tenant {
  id: string;
  slug: string;
  name: string;
  status: string;
  plan: string;
  plan_code: string;
  sub_status: string;
  created_at: string | null;
}
interface TenantPage {
  total: number;
  limit: number;
  offset: number;
  tenants: Tenant[];
}
interface PlanOption { code: string; name: string }

const PAGE = 20;

export default function AdminTenants() {
  const t = useTranslations("admin");
  const tErrors = useTranslations("errors");
  const locale = useLocale() as Locale;
  const nav = useAdminNav();

  const [q, setQ] = useState("");
  const [debouncedQ, setDebouncedQ] = useState("");
  const [status, setStatus] = useState("");
  const [plan, setPlan] = useState("");
  const [offset, setOffset] = useState(0);

  useEffect(() => {
    const id = setTimeout(() => { setDebouncedQ(q.trim()); setOffset(0); }, 300);
    return () => clearTimeout(id);
  }, [q]);

  const params = new URLSearchParams({ limit: String(PAGE), offset: String(offset) });
  if (debouncedQ) params.set("q", debouncedQ);
  if (status) params.set("status", status);
  if (plan) params.set("plan", plan);
  const { data, error, loading, reload } = useResource<TenantPage>(`/admin/tenants?${params.toString()}`);
  const { data: planData } = useResource<{ plans: PlanOption[] }>("/admin/plans");
  const tenants = loading ? null : (data?.tenants ?? []);
  const total = data?.total ?? 0;

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
        <div className="row" style={{ flexWrap: "wrap", gap: ".6rem", marginBottom: "1rem" }}>
          <Input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder={t("tenants.searchPlaceholder")}
            style={{ flex: 1, minWidth: 220 }}
          />
          <select className="input" style={{ width: "auto" }} value={status} onChange={(e) => { setStatus(e.target.value); setOffset(0); }}>
            <option value="">{t("tenants.filterAllStatuses")}</option>
            <option value="active">{t("tenants.statusActive")}</option>
            <option value="suspended">{t("tenants.statusSuspended")}</option>
          </select>
          <select className="input" style={{ width: "auto" }} value={plan} onChange={(e) => { setPlan(e.target.value); setOffset(0); }}>
            <option value="">{t("tenants.filterAllPlans")}</option>
            {(planData?.plans ?? []).map((p) => (
              <option key={p.code} value={p.code}>{p.name}</option>
            ))}
          </select>
        </div>

        {error ? <p className="muted">{t("common.loadError")}: {error}</p> : null}
        {tenants === null ? <Spinner /> : (
          <>
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
                {tenants.map((row) => (
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
            {tenants.length === 0 ? <p className="muted">{t("tenants.noMatches")}</p> : null}
            <div className="row-between" style={{ marginTop: "1rem" }}>
              <span className="hint">
                {t("tenants.pageInfo", {
                  from: formatNumber(total === 0 ? 0 : offset + 1, locale),
                  to: formatNumber(Math.min(offset + PAGE, total), locale),
                  total: formatNumber(total, locale),
                })}
              </span>
              <div className="row" style={{ gap: ".4rem" }}>
                <button className="btn btn-soft" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE))}>
                  {t("tenants.prev")}
                </button>
                <button className="btn btn-soft" disabled={offset + PAGE >= total} onClick={() => setOffset(offset + PAGE)}>
                  {t("tenants.next")}
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </DashboardShell>
  );
}
