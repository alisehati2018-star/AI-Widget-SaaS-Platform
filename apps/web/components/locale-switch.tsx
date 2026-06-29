"use client";

// Real locale switch (replaces the old direction-only toggle). Navigates between
// the routed locales while preserving the current path; direction follows the
// locale automatically (set on <html> by the server layout). next-intl persists
// the choice via the NEXT_LOCALE cookie.

import { useLocale, useTranslations } from "next-intl";
import { usePathname, useRouter } from "@/i18n/navigation";
import type { Locale } from "@/i18n/routing";

export function LocaleSwitch({ className = "btn btn-ghost" }: { className?: string }) {
  const t = useTranslations("common");
  const locale = useLocale() as Locale;
  const router = useRouter();
  const pathname = usePathname();
  const next: Locale = locale === "fa" ? "en" : "fa";

  function switchTo() {
    router.replace(pathname, { locale: next });
  }

  return (
    <button
      className={className}
      onClick={switchTo}
      aria-label={t("locale.label")}
      title={t("locale.label")}
    >
      {next === "fa" ? t("locale.switchToFa") : t("locale.switchToEn")}
    </button>
  );
}
