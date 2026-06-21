"use client";

import { useEffect, useState } from "react";
import { authFetch } from "../../../lib/auth";
import { ADMIN_NAV, DashboardShell } from "../../../components/shell";
import { Badge, Spinner, Stat } from "../../../components/ui";

interface Queue { broker: string; reachable: boolean; pending: number | null }

export default function AdminQueue() {
  const [data, setData] = useState<Queue | null>(null);

  useEffect(() => {
    const load = () => authFetch<Queue>("/admin/queue").then(setData).catch(() => setData(null));
    load();
    const id = setInterval(load, 10000);
    return () => clearInterval(id);
  }, []);

  return (
    <DashboardShell title="Queue monitoring" nav={ADMIN_NAV} requireAdmin loginHref="/admin/login">
      <p style={{ marginTop: "-1rem" }}>Celery broker status and pending background work.</p>
      <div className="stat-grid" style={{ marginBottom: "1.5rem" }}>
        <Stat label="Broker" value={data ? <Badge tone={data.reachable ? "success" : "warning"}>{data.reachable ? "reachable" : "down"}</Badge> : <Spinner />} />
        <Stat label="Pending tasks" value={data?.pending ?? "—"} />
      </div>
      <div className="card">
        <h3>Broker</h3>
        <p className="muted" style={{ marginBottom: 0, wordBreak: "break-all" }}>{data?.broker ?? "—"}</p>
        <p className="hint">Worker-level inspection (active/scheduled) is added with the observability stack.</p>
      </div>
    </DashboardShell>
  );
}
