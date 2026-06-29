import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { MarketingFooter, MarketingNav } from "@/components/marketing";

const IDS = ["getting-started", "api", "widget", "security"];

export default function DocsPage() {
  const t = useTranslations("marketing");
  const sections = t.raw("docs.sections") as { title: string; items: string[] }[];

  return (
    <>
      <MarketingNav />
      <section className="section">
        <div className="container" style={{ maxWidth: 860 }}>
          <h1>{t("docs.title")}</h1>
          <p>{t("docs.subtitle")}</p>

          <div className="row" style={{ flexWrap: "wrap", gap: "0.5rem", margin: "1rem 0 2rem" }}>
            {sections.map((s, i) => (
              <a key={IDS[i]} href={`#${IDS[i]}`} className="badge">
                {s.title}
              </a>
            ))}
          </div>

          {sections.map((s, i) => (
            <div className="card" key={IDS[i]} id={IDS[i]} style={{ marginBottom: "1.2rem" }}>
              <h3>{s.title}</h3>
              <ul className="feature-list">
                {s.items.map((it) => (
                  <li key={it}>{it}</li>
                ))}
              </ul>
            </div>
          ))}

          <div className="card card-glow center" style={{ marginTop: "1.5rem" }}>
            <h3>{t("docs.ctaTitle")}</h3>
            <p>{t("docs.ctaSubtitle")}</p>
            <Link href="/signup" className="btn btn-primary">
              {t("docs.ctaButton")}
            </Link>
          </div>
        </div>
      </section>
      <MarketingFooter />
    </>
  );
}
