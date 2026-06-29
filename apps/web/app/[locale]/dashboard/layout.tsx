import type { ReactNode } from "react";
import { NextIntlClientProvider } from "next-intl";
import { setRequestLocale } from "next-intl/server";
import { scopedMessages } from "@/lib/messages";

export default async function DashboardLayout({
  children,
  params,
}: {
  children: ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);
  const messages = await scopedMessages([
    "common",
    "errors",
    "validation",
    "dashboard",
    "billing",
  ]);
  return <NextIntlClientProvider messages={messages}>{children}</NextIntlClientProvider>;
}
