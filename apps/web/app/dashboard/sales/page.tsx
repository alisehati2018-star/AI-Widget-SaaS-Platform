"use client";

import { useEffect, useState } from "react";
import type { AnalyticsBundle } from "../../../lib/api";
import { authFetch } from "../../../lib/auth";
import { DashboardShell, OWNER_NAV } from "../../../components/shell";
import { Stat } from "../../../components/ui";

export default function ConversionPage() {
  const [data, setData] = useState<AnalyticsBundle | null>(null);

  useEffect(() => {
    authFetch<AnalyticsBundle>("/tenant/analytics").then(setData).catch(() => setData(null));
  }, []);

  const funnel = data?.funnel ?? {};
  const keys = Object.keys(funnel);

  return (
    <DashboardShell title="Conversion" nav={OWNER_NAV}>
      <p style={{ marginTop: "-1rem" }}>
        Search → click → add-to-cart funnel. Powered by storefront events from the widget.
      </p>
      <div className="stat-grid" style={{ marginBottom: "2rem" }}>
        <Stat label="Searches" value={funnel.search ?? funnel.searches ?? "—"} />
        <Stat label="Clicks" value={funnel.click ?? funnel.clicks ?? "—"} />
        <Stat label="Add-to-cart" value={funnel.add_to_cart ?? funnel.cart ?? "—"} />
        <Stat label="CTR" value={
          funnel.search && funnel.click ? `${Math.round((funnel.click / funnel.search) * 100)}%` : "—"
        } />
      </div>
      <div className="card">
        <h3>Funnel breakdown</h3>
        {keys.length ? (
          <table className="table">
            <thead><tr><th>Stage</th><th>Count</th></tr></thead>
            <tbody>{keys.map((k) => <tr key={k}><td>{k}</td><td>{funnel[k]}</td></tr>)}</tbody>
          </table>
        ) : (
          <p className="muted">
            No conversion events yet. Embed the widget and emit click / add-to-cart events to
            populate this funnel.
          </p>
        )}
      </div>
    </DashboardShell>
  );
}
