"use client";

import { useEffect, useState } from "react";
import { getPlans, type PlanInfo } from "../../../lib/api";
import { ADMIN_NAV, DashboardShell } from "../../../components/shell";

export default function AdminPlans() {
  const [plans, setPlans] = useState<PlanInfo[]>([]);
  useEffect(() => {
    getPlans().then((r) => setPlans(r.plans)).catch(() => setPlans([]));
  }, []);

  return (
    <DashboardShell title="Plans" nav={ADMIN_NAV} requireAdmin loginHref="/admin/login">
      <p style={{ marginTop: "-1rem" }}>The public pricing catalogue.</p>
      <div className="card">
        <table className="table">
          <thead>
            <tr>
              <th>Plan</th>
              <th>Price</th>
              <th>Credits/mo</th>
              <th>Rate limit</th>
            </tr>
          </thead>
          <tbody>
            {plans.map((p) => (
              <tr key={p.code}>
                <td>{p.name}</td>
                <td>{p.price_monthly === 0 ? "Free / Custom" : `$${p.price_monthly}/mo`}</td>
                <td>{p.credits_per_month.toLocaleString()}</td>
                <td>{p.rate_limit_per_min}/min</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="hint" style={{ marginTop: "1rem" }}>Plan editing UI ships with the billing release.</p>
      </div>
    </DashboardShell>
  );
}
