import Link from "next/link";
import { MarketingFooter, MarketingNav } from "../../components/marketing";

const SECTIONS = [
  {
    icon: "🔎",
    title: "Persian hybrid search",
    points: [
      "BM25 keyword + dense-vector semantic search fused with RRF.",
      "ZWNJ/نیم‌فاصله normalization, Persian analyzer, and editable synonyms.",
      "Sub-150ms p95 latency with DiskBBQ vector compression.",
    ],
  },
  {
    icon: "🛒",
    title: "Grounded shopping assistant",
    points: [
      "RAG over your own catalogue — never invents products.",
      "Streaming replies with prompt-injection guardrails.",
      "Multilingual: Persian, English, German, Arabic.",
    ],
  },
  {
    icon: "📊",
    title: "Business analyst & insight engine",
    points: [
      "Ask 'why did sales drop?' in natural language.",
      "Most-wanted, zero-result mining, and demand-gap discovery.",
      "Lead capture, intent detection, and AI-attributed revenue.",
    ],
  },
  {
    icon: "🔒",
    title: "Secure, on-premise multi-tenancy",
    points: [
      "Hard tenant isolation enforced on every query.",
      "Scoped least-privilege API keys + full audit log.",
      "GDPR controls: export, erase, and tracking toggles.",
    ],
  },
  {
    icon: "💸",
    title: "Cost-controlled AI gateway",
    points: [
      "Cache → route → compress ladder keeps traffic off paid APIs.",
      "Credit-based billing with per-model multipliers.",
      "Multi-provider failover ending at a local model.",
    ],
  },
  {
    icon: "🔌",
    title: "Drop-in integrations",
    points: [
      "OpenCart module + WooCommerce plugin.",
      "Event-driven incremental sync — only deltas are sent.",
      "Custom REST / webhook / bulk-import APIs.",
    ],
  },
];

export default function FeaturesPage() {
  return (
    <>
      <MarketingNav />
      <section className="section">
        <div className="container">
          <div className="center" style={{ marginBottom: "3rem" }}>
            <h1>Everything your store needs to get intelligent</h1>
            <p>Search, assistant, and analytics — one on-premise platform.</p>
          </div>
          <div className="feature-grid">
            {SECTIONS.map((s) => (
              <div className="card" key={s.title}>
                <div className="feature-icon">{s.icon}</div>
                <h3 style={{ fontSize: "1.15rem" }}>{s.title}</h3>
                <ul className="feature-list">
                  {s.points.map((p) => (
                    <li key={p}>{p}</li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
          <div className="center" style={{ marginTop: "3rem" }}>
            <Link href="/signup" className="btn btn-primary btn-lg">Start free →</Link>
          </div>
        </div>
      </section>
      <MarketingFooter />
    </>
  );
}
