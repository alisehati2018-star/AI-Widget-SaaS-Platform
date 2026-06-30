import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { MarketingFooter, MarketingNav } from "@/components/marketing";
import { Icon, type IconName } from "@/components/icons";

const ICONS: IconName[] = ["search", "conversion", "analytics", "lock", "cost", "integrations"];

export default function FeaturesPage() {
  const t = useTranslations("marketing");
  const sections = t.raw("features.sections") as { title: string; points: string[] }[];

  return (
    <>
      <MarketingNav />
      <section className="section">
        <div className="container">
          <div className="center" style={{ marginBottom: "3rem" }}>
            <h1>{t("features.title")}</h1>
            <p>{t("features.subtitle")}</p>
          </div>
          <div className="feature-grid">
            {sections.map((s, i) => (
              <div className="card" key={s.title}>
                <div className="feature-icon"><Icon name={ICONS[i]} size={22} /></div>
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
            <Link href="/signup" className="btn btn-primary btn-lg">
              {t("features.cta")}
            </Link>
          </div>
        </div>
      </section>
      <MarketingFooter />
    </>
  );
}
