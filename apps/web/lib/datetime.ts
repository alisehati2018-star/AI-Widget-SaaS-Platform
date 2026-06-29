// Unified date/number formatting — the ONLY place date logic lives.
//
// Persian (fa) renders in the Jalali (Shamsi) calendar; English (en) in the
// Gregorian calendar. We rely on the platform's ICU implementation
// (`Intl.DateTimeFormat` with `calendar: "persian"`) rather than any hand-rolled
// conversion — that is the "proper Jalali-capable library" the spec mandates,
// shipped natively with the JS engine (no extra dependency, correct month names
// and Persian digits). To swap the engine later, change ONLY this module.

import type { Locale } from "../i18n/routing";

type DateInput = Date | string | number | null | undefined;

function toDate(value: DateInput): Date | null {
  if (value == null || value === "") return null;
  const d = value instanceof Date ? value : new Date(value);
  return Number.isNaN(d.getTime()) ? null : d;
}

function calendarFor(locale: Locale): string {
  // `fa-IR-u-ca-persian` selects the Jalali calendar with Persian digits.
  return locale === "fa" ? "fa-IR-u-ca-persian" : "en-US";
}

/** Date only, e.g. «۱۴۰۳ تیر ۸» (fa) / "Jun 28, 2026" (en). */
export function formatDate(value: DateInput, locale: Locale): string {
  const d = toDate(value);
  if (!d) return "—";
  return new Intl.DateTimeFormat(calendarFor(locale), {
    year: "numeric",
    month: "short",
    day: "numeric",
  }).format(d);
}

/** Date + time, used for logs / audit trails. */
export function formatDateTime(value: DateInput, locale: Locale): string {
  const d = toDate(value);
  if (!d) return "—";
  return new Intl.DateTimeFormat(calendarFor(locale), {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(d);
}

/** Locale-aware integer/decimal formatting (Persian digits for fa). */
export function formatNumber(
  value: number,
  locale: Locale,
  options?: Intl.NumberFormatOptions,
): string {
  return new Intl.NumberFormat(locale === "fa" ? "fa-IR" : "en-US", options).format(
    value,
  );
}

/** Currency formatting that keeps the amount localized but the code explicit. */
export function formatCurrency(
  amount: number,
  currency: string,
  locale: Locale,
): string {
  const formatted = formatNumber(amount, locale, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  return `${currency} ${formatted}`;
}
