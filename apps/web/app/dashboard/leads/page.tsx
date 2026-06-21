"use client";

import { useEffect, useState } from "react";
import type { Lead } from "../../../lib/api";
import { authFetch } from "../../../lib/auth";
import { DashboardShell, OWNER_NAV } from "../../../components/shell";
import { Badge, Spinner, Stat } from "../../../components/ui";

export default function LeadsPage() {
  const [leads, setLeads] = useState<Lead[] | null>(null);

  useEffect(() => {
    authFetch<{ leads: Lead[] }>("/tenant/leads").then((r) => setLeads(r.leads)).catch(() => setLeads([]));
  }, []);

  async function exportData() {
    const data = await authFetch<unknown>("/tenant/export").catch(() => null);
    if (!data) return;
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "vitrin-leads.json";
    a.click();
    URL.revokeObjectURL(url);
  }

  const withIntent = leads?.filter((l) => l.has_intent).length ?? 0;

  return (
    <DashboardShell title="Leads" nav={OWNER_NAV}>
      <p style={{ marginTop: "-1rem" }}>Contacts captured in-conversation by the assistant.</p>

      <div className="stat-grid" style={{ marginBottom: "1.5rem" }}>
        <Stat label="Total leads" value={leads?.length ?? "—"} />
        <Stat label="With buying intent" value={withIntent} />
        <Stat label="From chat" value={leads?.filter((l) => l.source === "chat").length ?? "—"} />
        <Stat label="With email" value={leads?.filter((l) => l.email).length ?? "—"} />
      </div>

      <div className="card">
        <div className="row-between" style={{ marginBottom: "1rem" }}>
          <h3 style={{ margin: 0 }}>Captured leads</h3>
          <button className="btn btn-ghost" onClick={() => void exportData()}>Export JSON</button>
        </div>
        {leads === null ? (
          <Spinner />
        ) : leads.length === 0 ? (
          <p className="muted">No leads captured yet.</p>
        ) : (
          <table className="table">
            <thead><tr><th>Email</th><th>Phone</th><th>Intent</th><th>Source</th><th>When</th></tr></thead>
            <tbody>
              {leads.map((l, i) => (
                <tr key={i}>
                  <td>{l.email ?? "—"}</td>
                  <td>{l.phone ?? "—"}</td>
                  <td>{l.has_intent ? <Badge tone="success">yes</Badge> : <Badge>no</Badge>}</td>
                  <td>{l.source}</td>
                  <td className="muted">{l.created_at?.slice(0, 10) ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </DashboardShell>
  );
}
