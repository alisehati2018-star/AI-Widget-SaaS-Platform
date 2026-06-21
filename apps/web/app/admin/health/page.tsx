"use client";

import { useEffect, useState } from "react";
import { authFetch } from "../../../lib/auth";
import { ADMIN_NAV, DashboardShell } from "../../../components/shell";
import { Badge, Spinner } from "../../../components/ui";

interface Health { status: string; dependencies: Record<string, string> }

export default function AdminHealth() {
  const [data, setData] = useState<Health | null>(null);

  useEffect(() => {
    const load = () => authFetch<Health>("/admin/health").then(setData).catch(() => setData(null));
    load();
    const id = setInterval(load, 10000);
    return () => clearInterval(id);
  }, []);

  return (
    <DashboardShell title="System health" nav={ADMIN_NAV} requireAdmin loginHref="/admin/login">
      <p style={{ marginTop: "-1rem" }}>Live dependency status (auto-refreshes every 10s).</p>
      <div className="card" style={{ maxWidth: 520 }}>
        <div className="row-between" style={{ marginBottom: "1rem" }}>
          <h3 style={{ margin: 0 }}>Overall</h3>
          {data ? (
            <Badge tone={data.status === "ok" ? "success" : "warning"}>{data.status}</Badge>
          ) : <Spinner />}
        </div>
        {data ? (
          <table className="table">
            <tbody>
              {Object.entries(data.dependencies).map(([k, v]) => (
                <tr key={k}>
                  <td style={{ textTransform: "capitalize" }}>{k}</td>
                  <td><Badge tone={v === "ok" ? "success" : "warning"}>{v}</Badge></td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : null}
      </div>
    </DashboardShell>
  );
}
