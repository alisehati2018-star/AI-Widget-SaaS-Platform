import type { ReactNode } from "react";

export const metadata = {
  title: "ACIP Dashboard",
  description: "AI Commerce Intelligence Platform — operator console (foundation).",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
