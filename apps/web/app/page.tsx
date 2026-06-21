import Link from "next/link";
import { MarketingFooter, MarketingNav } from "../components/marketing";

const FEATURES = [
  {
    icon: "🔎",
    title: "Persian hybrid search",
    body: "BM25 + dense vectors fused with RRF, ZWNJ-aware analysis and synonyms — search that actually understands Farsi.",
  },
  {
    icon: "🛒",
    title: "Grounded shopping assistant",
    body: "A RAG assistant that answers only from the store's own catalogue — no hallucinated products, with streaming replies.",
  },
  {
    icon: "📊",
    title: "AI business analyst",
    body: "Ask 'why did sales drop?' in plain language and get grounded answers from your real store data.",
  },
  {
    icon: "🧠",
    title: "Customer insight engine",
    body: "Demand gaps, zero-result mining, lead capture and AI-attributed revenue — turn search into growth.",
  },
  {
    icon: "💸",
    title: "Cost-controlled AI",
    body: "A local-first gateway (cache → route → compress) keeps most traffic off paid APIs with credit-based billing.",
  },
  {
    icon: "🔒",
    title: "Secure multi-tenancy",
    body: "Hard tenant isolation, scoped API keys, audit logging and GDPR controls — built for on-premise.",
  },
];

export default function Home() {
  return (
    <>
      <MarketingNav />
      <header className="hero">
        <div className="container center">
          <div className="eyebrow">◆ AI Revenue &amp; Intelligence Layer for E-Commerce</div>
          <h1>
            Make your store <span className="grad-text">intelligent</span>.
          </h1>
          <p className="hero-sub" style={{ margin: "0 auto 2rem" }}>
            Vitrin adds Persian hybrid search, a grounded shopping assistant, and a
            business-insight engine to OpenCart &amp; WooCommerce — on-premise,
            multi-tenant, and cost-controlled.
          </p>
          <div className="row" style={{ justifyContent: "center" }}>
            <Link href="/signup" className="btn btn-primary btn-lg">
              Start free →
            </Link>
            <Link href="/pricing" className="btn btn-ghost btn-lg">
              See pricing
            </Link>
          </div>
        </div>
      </header>

      <section className="section" id="features">
        <div className="container">
          <div className="center" style={{ marginBottom: "2.5rem" }}>
            <h2>Not a chat widget. A revenue layer.</h2>
            <p>Three AI roles in one system: sales assistant, business analyst, and insight engine.</p>
          </div>
          <div className="feature-grid">
            {FEATURES.map((f) => (
              <div className="card" key={f.title}>
                <div className="feature-icon">{f.icon}</div>
                <h3 style={{ fontSize: "1.1rem" }}>{f.title}</h3>
                <p style={{ marginBottom: 0 }}>{f.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="section">
        <div className="container">
          <div className="card card-glow center" style={{ padding: "3rem 2rem" }}>
            <h2>Ready to upgrade your store search?</h2>
            <p>Spin up a free tenant in seconds. No credit card required.</p>
            <Link href="/signup" className="btn btn-primary btn-lg">
              Create your store →
            </Link>
          </div>
        </div>
      </section>

      <MarketingFooter />
    </>
  );
}
