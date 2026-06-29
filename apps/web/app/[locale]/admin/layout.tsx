import type { ReactNode } from "react";
import { NextIntlClientProvider } from "next-intl";
import { setRequestLocale } from "next-intl/server";
import { scopedMessages } from "@/lib/messages";

export default async function AdminLayout({
  children,
  params,
}: {
  children: ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);
  // `auth` is included for the admin sign-in page; `billing` for /admin/billing.
  const messages = await scopedMessages([
    "common",
    "errors",
    "validation",
    "admin",
    "billing",
    "auth",
  ]);
  return <NextIntlClientProvider messages={messages}>{children}</NextIntlClientProvider>;
}
