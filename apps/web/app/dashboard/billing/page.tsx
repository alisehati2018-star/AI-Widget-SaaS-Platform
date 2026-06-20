"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getPlans, type PlanInfo } from "../../../lib/api";
import { DashboardShell, OWNER_NAV } from "../../../components/shell";
import { Badge } from "../../../components/ui";

export default function BillingPage() {
  const [plans, setPlans] = useState<PlanInfo[]>([]);
  useEffect(() => {
    getPlans().then((r) => setPlans(r.plans)).catch(() => setPlans([]));
  }, []);

  return (
    <DashboardShell title="Plan & billing" nav={OWNER_NAV}>
      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <div className="row-between">
          <div>
            <small className="faint">Current plan</small>
            <h3 style={{ margin: "0.2rem 0" }}>Free <Badge tone="warning">trial</Badge></h3>
            <p style={{ margin: 0 }}>Your 14-day trial includes hybrid search and the assistant.</p>
          </div>
          <Link href="/pricing" className="btn btn-primary">Upgrade plan</Link>
        </div>
      </div>

      <h3>Available plans</h3>
      <div className="pricing-grid">
        {plans.filter((p) => p.code !== "free").map((p) => (
          <div className="card price-card" key={p.code}>
            <h4 style={{ margin: 0 }}>{p.name}</h4>
            <div className="price">
              {p.code === "enterprise" ? "Custom" : `$${p.price_monthly}`}
              {p.price_monthly > 0 ? <small> /mo</small> : null}
            </div>
            <button className="btn btn-ghost btn-block" disabled>Choose {p.name}</button>
          </div>
        ))}
      </div>
      <p className="hint" style={{ marginTop: "1rem" }}>
        Checkout activates with the billing release (provider-agnostic: Stripe / ZarinPal / invoice).
      </p>
    </DashboardShell>
  );
}
