import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { LocaleSwitch } from "./locale-switch";
import { Brand } from "./ui";

export function MarketingNav() {
  const t = useTranslations("common");
  return (
    <nav className="nav">
      <div className="container nav-inner">
        <Brand />
        <div className="nav-links">
          <Link href="/features">{t("nav.features")}</Link>
          <Link href="/pricing">{t("nav.pricing")}</Link>
          <Link href="/docs">{t("nav.docs")}</Link>
          <Link href="/contact">{t("nav.contact")}</Link>
          <Link href="/login">{t("nav.signIn")}</Link>
          <LocaleSwitch className="btn btn-ghost" />
          <Link href="/signup" className="btn btn-primary">
            {t("nav.startFree")}
          </Link>
        </div>
      </div>
    </nav>
  );
}

export function MarketingFooter() {
  const t = useTranslations("common");
  return (
    <footer className="footer">
      <div className="container row-between">
        <Brand />
        <div className="row" style={{ gap: "1.5rem", flexWrap: "wrap" }}>
          <Link href="/features">{t("nav.features")}</Link>
          <Link href="/pricing">{t("nav.pricing")}</Link>
          <Link href="/docs">{t("nav.docs")}</Link>
          <Link href="/contact">{t("nav.contact")}</Link>
          <Link href="/legal/terms">{t("footer.terms")}</Link>
          <Link href="/legal/privacy">{t("footer.privacy")}</Link>
          <Link href="/admin/login">{t("footer.admin")}</Link>
        </div>
      </div>
      <div className="container" style={{ marginTop: "1rem" }}>
        <small>{t("footer.copyright", { year: new Date().getFullYear() })}</small>
      </div>
    </footer>
  );
}
