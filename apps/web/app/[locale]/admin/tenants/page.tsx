"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { Link } from "@/i18n/navigation";
import { authFetch } from "@/lib/auth";
import { DashboardShell, useAdminNav } from "@/components/shell";
import { Badge } from "@/components/ui";

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
  const nav = useAdminNav();
  const [tenants, setTenants] = useState<Tenant[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    authFetch<{ tenants: Tenant[] }>("/admin/tenants")
      .then((r) => setTenants(r.tenants))
      .catch((e) => setError(String(e.message ?? e)));
  }, []);

  return (
    <DashboardShell title={t("tenants.title")} nav={nav} requireAdmin loginHref="/admin/login">
      <p style={{ marginTop: "-1rem" }}>{t("tenants.intro")}</p>
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
