"use client";

import { useEffect, useState } from "react";
import { authFetch } from "../../../lib/auth";
import { DashboardShell, OWNER_NAV } from "../../../components/shell";
import { Badge, Spinner, Stat } from "../../../components/ui";

interface LedgerEntry {
  delta: number;
  rung: string | null;
  reason: string | null;
  created_at: string | null;
}
interface CreditsResp {
  used: number;
  granted: number;
  cap: number | null;
  within_plan: boolean;
  ledger: LedgerEntry[];
}

export default function CreditsPage() {
  const [data, setData] = useState<CreditsResp | null>(null);

  useEffect(() => {
    authFetch<CreditsResp>("/tenant/credits").then(setData).catch(() => setData(null));
  }, []);

  const remaining = data?.cap != null ? Math.max(0, data.cap - data.used) : null;

  return (
    <DashboardShell title="Credits" nav={OWNER_NAV}>
      <p style={{ marginTop: "-1rem" }}>AI credits power search, the assistant, and analytics.</p>
      <div className="stat-grid" style={{ marginBottom: "2rem" }}>
        <Stat label="Used" value={data ? Math.round(data.used).toLocaleString() : "—"} />
        <Stat label="Granted" value={data ? Math.round(data.granted).toLocaleString() : "—"} />
        <Stat label="Monthly cap" value={data?.cap != null ? Math.round(data.cap).toLocaleString() : "—"} />
        <Stat label="Remaining" value={remaining != null ? Math.round(remaining).toLocaleString() : "—"} />
      </div>

      <div className="card">
        <h3>Ledger</h3>
        {data === null ? (
          <Spinner />
        ) : data.ledger.length === 0 ? (
          <p className="muted">No credit activity yet.</p>
        ) : (
          <table className="table">
            <thead><tr><th>When</th><th>Reason</th><th>Rung</th><th>Δ</th></tr></thead>
            <tbody>
              {data.ledger.map((e, i) => (
                <tr key={i}>
                  <td className="muted">{e.created_at?.replace("T", " ").slice(0, 16) ?? "—"}</td>
                  <td>{e.reason ?? "—"}</td>
                  <td>{e.rung ?? "—"}</td>
                  <td>
                    <Badge tone={e.delta >= 0 ? "success" : "warning"}>
                      {e.delta >= 0 ? "+" : ""}{Math.round(e.delta).toLocaleString()}
                    </Badge>
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
