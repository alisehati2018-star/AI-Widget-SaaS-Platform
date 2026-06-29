import { defineRouting } from "next-intl/routing";

// Persian-first, locale-routed. `as-needed` keeps the primary locale (fa) at
// clean root URLs (/, /pricing, /dashboard) and prefixes English as /en/*.
export const routing = defineRouting({
  locales: ["fa", "en"],
  defaultLocale: "fa",
  localePrefix: "as-needed",
  localeCookie: { name: "NEXT_LOCALE" },
});

export type Locale = (typeof routing.locales)[number];

// Direction is derived from the locale — the single source of truth for RTL/LTR.
export const LOCALE_DIR: Record<Locale, "rtl" | "ltr"> = {
  fa: "rtl",
  en: "ltr",
};
