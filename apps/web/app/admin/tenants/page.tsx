"use client";

import { useEffect, useState } from "react";
import { ADMIN_NAV, DashboardShell } from "../../../components/shell";
import { Badge } from "../../../components/ui";
import { authFetch } from "../../../lib/auth";

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
  const [tenants, setTenants] = useState<Tenant[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    authFetch<{ tenants: Tenant[] }>("/admin/tenants")
      .then((r) => setTenants(r.tenants))
      .catch((e) => setError(String(e.message ?? e)));
  }, []);

  return (
    <DashboardShell title="Tenants" nav={ADMIN_NAV} requireAdmin loginHref="/admin/login">
      <p style={{ marginTop: "-1rem" }}>Every store on the platform.</p>
      <div className="card">
        {error ? <p className="muted">Couldn&apos;t load tenants: {error}</p> : null}
        <table className="table">
          <thead>
            <tr>
              <th>Store</th>
              <th>Slug</th>
              <th>Plan</th>
              <th>Subscription</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {(tenants ?? []).map((t) => (
              <tr key={t.id}>
                <td>{t.name}</td>
                <td className="muted">{t.slug}</td>
                <td>{t.plan}</td>
                <td><Badge tone={t.sub_status === "active" ? "success" : "warning"}>{t.sub_status}</Badge></td>
                <td><Badge tone={t.status === "active" ? "success" : undefined}>{t.status}</Badge></td>
              </tr>
            ))}
          </tbody>
        </table>
        {tenants && tenants.length === 0 ? <p className="muted">No tenants yet.</p> : null}
      </div>
    </DashboardShell>
  );
}
