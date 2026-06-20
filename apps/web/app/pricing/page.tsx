"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getPlans, type PlanInfo } from "../../lib/api";
import { MarketingFooter, MarketingNav } from "../../components/marketing";
import { Spinner } from "../../components/ui";

// Fallback so the page is never empty if the backend isn't reachable yet.
const FALLBACK: PlanInfo[] = [
  { code: "free", name: "Free", description: "Try Persian hybrid search on one store.", price_monthly: 0, currency: "USD", credits_per_month: 5000, rate_limit_per_min: 60, features: ["1 store", "Hybrid Persian search", "5k AI credits/mo", "Community support"] },
  { code: "starter", name: "Starter", description: "For growing stores that want the assistant.", price_monthly: 49, currency: "USD", credits_per_month: 50000, rate_limit_per_min: 120, features: ["1 store", "Search + RAG assistant", "50k AI credits/mo", "Analytics dashboard", "Email support"] },
  { code: "pro", name: "Pro", description: "Full intelligence layer with insight + leads.", price_monthly: 149, currency: "USD", credits_per_month: 250000, rate_limit_per_min: 600, features: ["3 stores", "Everything in Starter", "Insight & lead engine", "250k AI credits/mo", "Priority support"] },
  { code: "enterprise", name: "Enterprise", description: "On-prem, SSO, custom limits and SLA.", price_monthly: 0, currency: "USD", credits_per_month: 0, rate_limit_per_min: 2000, features: ["Unlimited stores", "Self-hosted models", "SSO + audit", "Custom SLA", "Dedicated support"] },
];

export default function PricingPage() {
  const [plans, setPlans] = useState<PlanInfo[] | null>(null);

  useEffect(() => {
    getPlans()
      .then((r) => setPlans(r.plans.length ? r.plans : FALLBACK))
      .catch(() => setPlans(FALLBACK));
  }, []);

  return (
    <>
      <MarketingNav />
      <section className="section">
        <div className="container">
          <div className="center" style={{ marginBottom: "2.5rem" }}>
            <h1 style={{ fontSize: "2.6rem" }}>Simple, usage-based pricing</h1>
            <p>Start free. Upgrade when your store grows. Cancel anytime.</p>
          </div>

          {!plans ? (
            <div className="center"><Spinner /></div>
          ) : (
            <div className="pricing-grid">
              {plans.map((p) => {
                const featured = p.code === "pro";
                const custom = p.code === "enterprise";
                return (
                  <div className={`card price-card${featured ? " featured" : ""}`} key={p.code}>
                    {featured ? <span className="badge badge-brand">Most popular</span> : null}
                    <h3 style={{ marginTop: "0.6rem" }}>{p.name}</h3>
                    <div className="price">
                      {custom ? "Custom" : p.price_monthly === 0 ? "Free" : `$${p.price_monthly}`}
                      {!custom && p.price_monthly > 0 ? <small> /mo</small> : null}
                    </div>
                    <p style={{ minHeight: "2.6rem", fontSize: "0.88rem" }}>{p.description}</p>
                    <ul className="feature-list">
                      {p.features.map((f) => (
                        <li key={f}>{f}</li>
                      ))}
                    </ul>
                    <Link
                      href={custom ? "/signup" : `/signup?plan=${p.code}`}
                      className={`btn ${featured ? "btn-primary" : "btn-ghost"} btn-block`}
                      style={{ marginTop: "auto" }}
                    >
                      {custom ? "Contact sales" : "Get started"}
                    </Link>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </section>
      <MarketingFooter />
    </>
  );
}
