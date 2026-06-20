"use client";

import { DashboardShell, OWNER_NAV } from "../../../components/shell";
import { Badge } from "../../../components/ui";

export default function KeysPage() {
  return (
    <DashboardShell title="API keys" nav={OWNER_NAV}>
      <p style={{ marginTop: "-1rem" }}>
        Scoped, least-privilege keys connect your store and widget to Vitrin.
      </p>
      <div className="card">
        <div className="row-between" style={{ marginBottom: "1rem" }}>
          <h3 style={{ margin: 0 }}>Your keys</h3>
          <button className="btn btn-primary" disabled>+ New key</button>
        </div>
        <table className="table">
          <thead>
            <tr>
              <th>Label</th>
              <th>Scope</th>
              <th>Created</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Storefront widget</td>
              <td><Badge tone="brand">widget</Badge></td>
              <td className="muted">—</td>
              <td><Badge tone="success">active</Badge></td>
            </tr>
            <tr>
              <td>Catalogue sync</td>
              <td><Badge>sync</Badge></td>
              <td className="muted">—</td>
              <td><Badge tone="success">active</Badge></td>
            </tr>
          </tbody>
        </table>
        <p className="hint" style={{ marginTop: "1rem" }}>
          Key issuance &amp; rotation goes live with the billing release. A raw key is shown only once at creation.
        </p>
      </div>
    </DashboardShell>
  );
}
