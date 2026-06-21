"use client";

import { useEffect, useState } from "react";
import type { AnalyticsBundle } from "../../../lib/api";
import { authFetch } from "../../../lib/auth";
import { DashboardShell, OWNER_NAV } from "../../../components/shell";
import { Stat } from "../../../components/ui";

export default function ChatAnalyticsPage() {
  const [data, setData] = useState<AnalyticsBundle | null>(null);

  useEffect(() => {
    authFetch<AnalyticsBundle>("/tenant/analytics").then(setData).catch(() => setData(null));
  }, []);

  const fd = data?.four_dimensions;
  return (
    <DashboardShell title="Chat analytics" nav={OWNER_NAV}>
      <p style={{ marginTop: "-1rem" }}>How shoppers engage with the AI assistant.</p>
      <div className="stat-grid" style={{ marginBottom: "2rem" }}>
        <Stat label="Assistant turns" value={fd?.reliability?.turns ?? "—"} />
        <Stat label="No-paid share" value={fd?.cost?.no_paid_share != null ? `${Math.round(fd.cost.no_paid_share * 100)}%` : "—"} />
        <Stat label="First-token p95" value={fd?.latency?.p95_ms != null ? `${fd.latency.p95_ms} ms` : "—"} />
        <Stat label="Credits (chat)" value={fd?.cost?.total ?? "—"} />
      </div>
      <div className="card">
        <h3>Conversation topics</h3>
        <p className="hint">
          Most-discussed product queries from chat. Populated once the assistant serves live traffic
          (needs the inference profile + synced catalogue).
        </p>
        {data?.most_wanted?.length ? (
          <table className="table">
            <thead><tr><th>Topic</th><th>Mentions</th></tr></thead>
            <tbody>{data.most_wanted.map((m) => <tr key={m.term}><td>{m.term}</td><td>{m.count}</td></tr>)}</tbody>
          </table>
        ) : (
          <p className="muted">No chat data yet.</p>
        )}
      </div>
    </DashboardShell>
  );
}
