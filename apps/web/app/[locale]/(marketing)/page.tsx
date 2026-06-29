import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { MarketingFooter, MarketingNav } from "@/components/marketing";

const ICONS = ["🔎", "🛒", "📊", "🧠", "💸", "🔒"];

export default function Home() {
  const t = useTranslations("marketing");
  const items = t.raw("home.features.items") as { title: string; body: string }[];

  return (
    <>
      <MarketingNav />
      <header className="hero">
        <div className="container center">
          <div className="eyebrow">{t("home.eyebrow")}</div>
          <h1>
            {t("home.titleLead")} <span className="grad-text">{t("home.titleHighlight")}</span>
            {t("home.titleTail")}
          </h1>
          <p className="hero-sub" style={{ margin: "0 auto 2rem" }}>
            {t("home.subtitle")}
          </p>
          <div className="row" style={{ justifyContent: "center" }}>
            <Link href="/signup" className="btn btn-primary btn-lg">
              {t("home.ctaPrimary")}
            </Link>
            <Link href="/pricing" className="btn btn-ghost btn-lg">
              {t("home.ctaSecondary")}
            </Link>
          </div>
        </div>
      </header>

      <section className="section" id="features">
        <div className="container">
          <div className="center" style={{ marginBottom: "2.5rem" }}>
            <h2>{t("home.features.heading")}</h2>
            <p>{t("home.features.subheading")}</p>
          </div>
          <div className="feature-grid">
            {items.map((f, i) => (
              <div className="card" key={f.title}>
                <div className="feature-icon">{ICONS[i]}</div>
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
            <h2>{t("home.cta.title")}</h2>
            <p>{t("home.cta.subtitle")}</p>
            <Link href="/signup" className="btn btn-primary btn-lg">
              {t("home.cta.button")}
            </Link>
          </div>
        </div>
      </section>

      <MarketingFooter />
    </>
  );
}
