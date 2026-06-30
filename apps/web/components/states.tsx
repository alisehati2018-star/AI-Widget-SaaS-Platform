"use client";

import { useTranslations } from "next-intl";
import { Spinner } from "./ui";

/** Standardized loading state for consistent UX across pages. */
export function Loading({ label }: { label?: string }) {
  const t = useTranslations("common");
  return (
    <div className="state" role="status" aria-live="polite">
      <Spinner />
      <p style={{ marginTop: "0.6rem" }}>{label ?? t("states.loading")}</p>
    </div>
  );
}
