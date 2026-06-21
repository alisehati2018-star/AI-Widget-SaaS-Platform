import Link from "next/link";
import { MarketingFooter, MarketingNav } from "../../components/marketing";

export const metadata = { title: "Documentation — Vitrin" };

const SECTIONS = [
  {
    id: "getting-started",
    title: "Getting started",
    items: [
      "Create an account and verify your email.",
      "Open your dashboard → create a sync-scoped API key.",
      "Connect your store (WooCommerce / OpenCart) and run the first import.",
      "Add a widget-scoped key and embed the search + chat widget.",
    ],
  },
  {
    id: "api",
    title: "API surface",
    items: [
      "POST /v1/search — hybrid Persian search (filters + pagination).",
      "GET /v1/suggest — instant autocomplete.",
      "POST /v1/chat (+ /chat/stream) — grounded RAG assistant.",
      "POST /v1/sync/webhook — push catalogue changes.",
      "All /v1 calls authenticate with an x-api-key and are tenant-scoped.",
    ],
  },
  {
    id: "widget",
    title: "Widget",
    items: [
      "Embed the loader snippet before </body> with your widget key.",
      "Customize logo and accent color under Widget & brand.",
      "The widget calls /v1/search and /v1/chat on the shopper's behalf.",
    ],
  },
  {
    id: "security",
    title: "Security & data",
    items: [
      "Hard tenant isolation: every query carries a mandatory tenant filter.",
      "Scoped least-privilege API keys; only hashes are stored.",
      "GDPR: export, erase, and disable tracking from dashboard settings.",
    ],
  },
];

export default function DocsPage() {
  return (
    <>
      <MarketingNav />
      <section className="section">
        <div className="container" style={{ maxWidth: 860 }}>
          <h1>Documentation</h1>
          <p>Everything you need to integrate Vitrin into your store.</p>

          <div className="row" style={{ flexWrap: "wrap", gap: "0.5rem", margin: "1rem 0 2rem" }}>
            {SECTIONS.map((s) => (
              <a key={s.id} href={`#${s.id}`} className="badge">{s.title}</a>
            ))}
          </div>

          {SECTIONS.map((s) => (
            <div className="card" key={s.id} id={s.id} style={{ marginBottom: "1.2rem" }}>
              <h3>{s.title}</h3>
              <ul className="feature-list">
                {s.items.map((it) => <li key={it}>{it}</li>)}
              </ul>
            </div>
          ))}

          <div className="card card-glow center" style={{ marginTop: "1.5rem" }}>
            <h3>Ready to build?</h3>
            <p>Create your store and grab an API key in minutes.</p>
            <Link href="/signup" className="btn btn-primary">Start free →</Link>
          </div>
        </div>
      </section>
      <MarketingFooter />
    </>
  );
}
