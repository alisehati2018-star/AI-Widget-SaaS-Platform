import type { Metadata } from "next";
import type { ReactNode } from "react";
import { DirectionInit } from "../components/direction";
import "./globals.css";

export const metadata: Metadata = {
  title: "Vitrin — AI Commerce Intelligence Platform",
  description:
    "Persian hybrid search, a grounded shopping assistant, and a business-insight engine for OpenCart & WooCommerce — on-premise and multi-tenant.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <DirectionInit />
        {children}
      </body>
    </html>
  );
}
