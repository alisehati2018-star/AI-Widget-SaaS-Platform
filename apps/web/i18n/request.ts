import { hasLocale } from "next-intl";
import { getRequestConfig } from "next-intl/server";
import { routing } from "./routing";

// Domain-based namespaces (no monolithic fa.json/en.json). Loaded on the server
// per request; client components receive only the namespaces their route needs
// via scoped NextIntlClientProvider boundaries (see app/[locale]/*/layout.tsx).
export const NAMESPACES = [
  "common",
  "marketing",
  "auth",
  "dashboard",
  "admin",
  "billing",
  "errors",
  "validation",
] as const;

export type Namespace = (typeof NAMESPACES)[number];

export default getRequestConfig(async ({ requestLocale }) => {
  const requested = await requestLocale;
  const locale = hasLocale(routing.locales, requested)
    ? requested
    : routing.defaultLocale;

  const entries = await Promise.all(
    NAMESPACES.map(
      async (ns) =>
        [ns, (await import(`../messages/${locale}/${ns}.json`)).default] as const,
    ),
  );

  return { locale, messages: Object.fromEntries(entries) };
});
