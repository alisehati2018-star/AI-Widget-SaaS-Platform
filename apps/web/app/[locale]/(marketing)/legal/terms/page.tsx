import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { MarketingFooter, MarketingNav } from "@/components/marketing";

export default function TermsPage() {
  const t = useTranslations("marketing");
  const sections = t.raw("legal.terms.sections") as { heading: string; body: string }[];

  return (
    <>
      <MarketingNav />
      <section className="section">
        <div className="container" style={{ maxWidth: 760 }}>
          <h1>{t("legal.terms.title")}</h1>
          <p className="faint">{t("legal.updated")}</p>
          {sections.map((s) => (
            <div key={s.heading}>
              <h3>{s.heading}</h3>
              <p>{s.body}</p>
            </div>
          ))}
          <p>
            {t("legal.contactPrefix")}
            <Link className="grad-text" href="/contact">
              {t("legal.contactLink")}
            </Link>
            {t("legal.contactSuffix")}
          </p>
        </div>
      </section>
      <MarketingFooter />
    </>
  );
}
