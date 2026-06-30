import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { Icon, type IconName } from "../icons";

// Server-rendered marketing sections for the landing page. All copy comes from
// the `marketing` namespace; each section is a small, reusable building block.

export function HeroSection() {
  const t = useTranslations("marketing");
  return (
    <header className="hero hero-split">
      <div className="container hero-grid">
        <div className="hero-copy">
          <div className="eyebrow">{t("home.eyebrow")}</div>
          <h1>
            {t("home.titleLead")} <span className="grad-text">{t("home.titleHighlight")}</span>
            {t("home.titleTail")}
          </h1>
          <p className="hero-sub">{t("home.subtitle")}</p>
          <div className="row" style={{ flexWrap: "wrap" }}>
            <Link href="/signup" className="btn btn-primary btn-lg">
              {t("home.ctaPrimary")}
            </Link>
            <Link href="/pricing" className="btn btn-ghost btn-lg">
              {t("home.ctaSecondary")}
            </Link>
          </div>
        </div>
        <HeroVisual />
      </div>
    </header>
  );
}

function HeroVisual() {
  const t = useTranslations("marketing");
  return (
    <div className="app-mock" aria-hidden>
      <div className="app-mock-bar">
        <span className="dot" />
        <span className="dot" />
        <span className="dot" />
        <span className="app-mock-tag">{t("landing.heroVisual.tag")}</span>
      </div>
      <div className="app-mock-body">
        <div className="mock-search">
          <Icon name="search" size={16} className="mock-search-icon" />
          <span className="mock-search-text">{t("landing.heroVisual.searchQuery")}</span>
        </div>
        <div className="mock-result">{t("landing.heroVisual.result1")}</div>
        <div className="mock-result">{t("landing.heroVisual.result2")}</div>
        <div className="mock-chat">
          <div className="mock-bubble user">{t("landing.heroVisual.chatUser")}</div>
          <div className="mock-bubble bot">{t("landing.heroVisual.chatBot")}</div>
        </div>
      </div>
    </div>
  );
}

export function StatsBand() {
  const t = useTranslations("marketing");
  const items = t.raw("landing.stats.items") as { value: string; label: string }[];
  return (
    <section className="section-tight">
      <div className="container">
        <div className="stats-band">
          {items.map((s) => (
            <div className="stats-item" key={s.label}>
              <div className="stats-value grad-text">{s.value}</div>
              <div className="stats-label">{s.label}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

export function FeatureCards() {
  const t = useTranslations("marketing");
  const items = t.raw("home.features.items") as { title: string; body: string }[];
  const icons: IconName[] = ["search", "conversion", "analytics", "insight", "cost", "lock"];
  return (
    <section className="section" id="features">
      <div className="container">
        <div className="center section-head">
          <h2>{t("home.features.heading")}</h2>
          <p>{t("home.features.subheading")}</p>
        </div>
        <div className="feature-grid">
          {items.map((f, i) => (
            <div className="card" key={f.title}>
              <div className="feature-icon"><Icon name={icons[i]} size={22} /></div>
              <h3 style={{ fontSize: "1.1rem" }}>{f.title}</h3>
              <p style={{ marginBottom: 0 }}>{f.body}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

export function DeepDives() {
  const t = useTranslations("marketing");
  const items = t.raw("landing.deepDives.items") as {
    eyebrow: string;
    title: string;
    body: string;
    points: string[];
  }[];
  return (
    <section className="section">
      <div className="container">
        <div className="center section-head">
          <h2>{t("landing.deepDives.title")}</h2>
          <p>{t("landing.deepDives.subtitle")}</p>
        </div>
        <div className="stack" style={{ gap: "1.5rem" }}>
          {items.map((d, i) => (
            <div className={`deep-row${i % 2 ? " reverse" : ""}`} key={d.title}>
              <div className="deep-copy">
                <span className="eyebrow">{d.eyebrow}</span>
                <h3>{d.title}</h3>
                <p>{d.body}</p>
                <ul className="feature-list">
                  {d.points.map((p) => (
                    <li key={p}>{p}</li>
                  ))}
                </ul>
              </div>
              <div className="deep-visual card">
                <span className="deep-glyph">
                  <Icon name={(["search", "conversion", "analytics"] as IconName[])[i] ?? "overview"} size={52} />
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

export function AnalyticsPreview() {
  const t = useTranslations("marketing");
  return (
    <section className="section">
      <div className="container">
        <div className="analytics-preview card card-glow">
          <div className="analytics-copy">
            <span className="eyebrow">{t("landing.analytics.eyebrow")}</span>
            <h2>{t("landing.analytics.title")}</h2>
            <p>{t("landing.analytics.subtitle")}</p>
          </div>
          <div className="analytics-mock">
            <div className="mini-stat-grid">
              <div className="mini-stat">
                <div className="mini-stat-label">{t("landing.analytics.cardCost")}</div>
                <div className="mini-stat-value">{t("landing.analytics.cardCostValue")}</div>
              </div>
              <div className="mini-stat">
                <div className="mini-stat-label">{t("landing.analytics.cardLatency")}</div>
                <div className="mini-stat-value">{t("landing.analytics.cardLatencyValue")}</div>
              </div>
              <div className="mini-stat">
                <div className="mini-stat-label">{t("landing.analytics.cardTurns")}</div>
                <div className="mini-stat-value">{t("landing.analytics.cardTurnsValue")}</div>
              </div>
            </div>
            <div className="mini-list">
              <div className="mini-list-title">{t("landing.analytics.mostWanted")}</div>
              <div className="mini-list-row"><span>{t("landing.analytics.row1")}</span><span className="bar" style={{ width: "90%" }} /></div>
              <div className="mini-list-row"><span>{t("landing.analytics.row2")}</span><span className="bar" style={{ width: "64%" }} /></div>
              <div className="mini-list-row"><span>{t("landing.analytics.row3")}</span><span className="bar" style={{ width: "41%" }} /></div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

export function UseCases() {
  const t = useTranslations("marketing");
  const items = t.raw("landing.useCases.items") as { icon: string; title: string; body: string }[];
  return (
    <section className="section">
      <div className="container">
        <div className="center section-head">
          <h2>{t("landing.useCases.title")}</h2>
        </div>
        <div className="feature-grid">
          {items.map((u) => (
            <div className="card" key={u.title}>
              <div className="feature-icon"><Icon name={u.icon as IconName} size={22} /></div>
              <h3 style={{ fontSize: "1.05rem" }}>{u.title}</h3>
              <p style={{ marginBottom: 0 }}>{u.body}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

export function HowItWorks() {
  const t = useTranslations("marketing");
  const items = t.raw("landing.how.items") as { title: string; body: string }[];
  return (
    <section className="section">
      <div className="container">
        <div className="center section-head">
          <h2>{t("landing.how.title")}</h2>
        </div>
        <div className="how-grid">
          {items.map((s, i) => (
            <div className="how-step" key={s.title}>
              <span className="how-num">{i + 1}</span>
              <h3 style={{ fontSize: "1.05rem" }}>{s.title}</h3>
              <p style={{ marginBottom: 0 }}>{s.body}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

export function Testimonials() {
  const t = useTranslations("marketing");
  const items = t.raw("landing.testimonials.items") as {
    quote: string;
    name: string;
    role: string;
  }[];
  return (
    <section className="section">
      <div className="container">
        <div className="center section-head">
          <h2>{t("landing.testimonials.title")}</h2>
        </div>
        <div className="feature-grid">
          {items.map((q) => (
            <figure className="card quote-card" key={q.name}>
              <blockquote>“{q.quote}”</blockquote>
              <figcaption>
                <strong>{q.name}</strong>
                <span className="muted">{q.role}</span>
              </figcaption>
            </figure>
          ))}
        </div>
      </div>
    </section>
  );
}

export function FinalCta() {
  const t = useTranslations("marketing");
  return (
    <section className="section">
      <div className="container">
        <div className="card card-glow center final-cta">
          <h2>{t("landing.finalCta.title")}</h2>
          <p>{t("landing.finalCta.subtitle")}</p>
          <div className="row" style={{ justifyContent: "center", flexWrap: "wrap" }}>
            <Link href="/signup" className="btn btn-primary btn-lg">
              {t("landing.finalCta.primary")}
            </Link>
            <Link href="/contact" className="btn btn-ghost btn-lg">
              {t("landing.finalCta.secondary")}
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}
