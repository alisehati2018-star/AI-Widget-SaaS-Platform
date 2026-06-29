import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";

export default function LocaleNotFound() {
  const t = useTranslations("errors");
  return (
    <div className="auth-wrap">
      <div className="state">
        <div className="state-icon" aria-hidden>
          🔍
        </div>
        <h1 style={{ fontSize: "1.6rem" }}>{t("page.notFoundTitle")}</h1>
        <p>{t("page.notFoundBody")}</p>
        <Link href="/" className="btn btn-primary" style={{ marginTop: "1rem" }}>
          {t("page.backHome")}
        </Link>
      </div>
    </div>
  );
}
