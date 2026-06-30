"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { getPlans, type PlanInfo } from "@/lib/api";
import { formatNumber } from "@/lib/datetime";
import type { Locale } from "@/i18n/routing";
import { Link } from "@/i18n/navigation";
import { MarketingFooter, MarketingNav } from "@/components/marketing";
import { Icon, type IconName } from "@/components/icons";
import { Spinner } from "@/components/ui";

export default function PricingPage() {
  const t = useTranslations("marketing");
  const locale = useLocale() as Locale;
  const [plans, setPlans] = useState<PlanInfo[] | null>(null);

  useEffect(() => {
    // Fallback so the page is never empty if the backend isn't reachable yet.
    const fb = t.raw("pricing.fallback") as Record<
      string,
      { name: string; description: string; features: string[] }
    >;
    const fallback: PlanInfo[] = [
      { code: "free", ...fb.free, price_monthly: 0, currency: "USD", credits_per_month: 5000, rate_limit_per_min: 60 },
      { code: "starter", ...fb.starter, price_monthly: 49, currency: "USD", credits_per_month: 50000, rate_limit_per_min: 120 },
      { code: "pro", ...fb.pro, price_monthly: 149, currency: "USD", credits_per_month: 250000, rate_limit_per_min: 600 },
      { code: "enterprise", ...fb.enterprise, price_monthly: 0, currency: "USD", credits_per_month: 0, rate_limit_per_min: 2000 },
    ];
    getPlans()
      .then((r) => setPlans(r.plans.length ? r.plans : fallback))
      .catch(() => setPlans(fallback));
  }, [t]);

  return (
    <>
      <MarketingNav />
      <section className="section">
        <div className="container">
          <div className="center" style={{ marginBottom: "2.5rem" }}>
            <h1 style={{ fontSize: "2.6rem" }}>{t("pricing.title")}</h1>
            <p>{t("pricing.subtitle")}</p>
          </div>

          {!plans ? (
            <div className="center">
              <Spinner />
            </div>
          ) : (
            <div className="pricing-grid">
              {plans.map((p) => {
                const featured = p.code === "pro";
                const custom = p.code === "enterprise";
                return (
                  <div className={`card price-card${featured ? " featured" : ""}`} key={p.code}>
                    {featured ? <span className="badge badge-brand">{t("pricing.mostPopular")}</span> : null}
                    <h3 style={{ marginTop: "0.6rem" }}>{p.name}</h3>
                    <div className="price">
                      {custom
                        ? t("pricing.custom")
                        : p.price_monthly === 0
                          ? t("pricing.free")
                          : `$${formatNumber(p.price_monthly, locale)}`}
                      {!custom && p.price_monthly > 0 ? <small> {t("pricing.perMonth")}</small> : null}
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
                      {custom ? t("pricing.contactSales") : t("pricing.getStarted")}
                    </Link>
                  </div>
                );
              })}
            </div>
          )}

          <div className="included-strip">
            <h2 className="center" style={{ fontSize: "1.2rem" }}>{t("pricing.includedTitle")}</h2>
            <div className="included-grid">
              {(t.raw("pricing.included") as { icon: string; text: string }[]).map((it) => (
                <div className="included-item" key={it.text}>
                  <Icon name={it.icon as IconName} size={18} />
                  <span>{it.text}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>
      <MarketingFooter />
    </>
  );
}
