import { MarketingFooter, MarketingNav } from "../../../components/marketing";

export const metadata = { title: "Privacy Policy — Vitrin" };

export default function PrivacyPage() {
  return (
    <>
      <MarketingNav />
      <section className="section">
        <div className="container" style={{ maxWidth: 760 }}>
          <h1>Privacy Policy</h1>
          <p className="faint">Last updated: 2026-06-21</p>

          <h3>1. Who we are</h3>
          <p>
            Vitrin is an on-premise, multi-tenant AI commerce intelligence platform. This policy
            explains what we process and your rights. For self-hosted deployments, the store
            operator is the data controller.
          </p>

          <h3>2. What we process</h3>
          <p>
            Account data (name, email, hashed password), tenant/store settings, catalogue data you
            sync, search and chat events, and in-conversation leads. Passwords are stored only as
            salted PBKDF2 hashes; API keys only as hashes.
          </p>

          <h3>3. How we use it</h3>
          <p>
            To provide search, the assistant, analytics, and billing; to secure the Service; and to
            communicate essential account notices (verification, password resets, invoices).
          </p>

          <h3>4. Tenant isolation</h3>
          <p>
            Every query is scoped to your tenant. Data is never shared across tenants. Access is
            governed by scoped least-privilege API keys and role-based controls.
          </p>

          <h3>5. Your rights (GDPR)</h3>
          <p>
            You can export your tenant&apos;s data, disable behavioural tracking, and request
            erasure from your dashboard settings or via support. We honor access, rectification,
            and deletion requests.
          </p>

          <h3>6. Retention</h3>
          <p>
            We retain data for the life of your account and a limited period afterward for legal and
            operational needs, then erase or anonymize it.
          </p>

          <h3>7. Sub-processors &amp; AI</h3>
          <p>
            The platform is local-first: most traffic is served by self-hosted models and cache. Any
            external AI provider is used only as a fallback and receives the minimum necessary
            context.
          </p>

          <h3>8. Contact</h3>
          <p>Privacy questions? Reach us via the <a className="grad-text" href="/contact">contact page</a>.</p>
        </div>
      </section>
      <MarketingFooter />
    </>
  );
}
