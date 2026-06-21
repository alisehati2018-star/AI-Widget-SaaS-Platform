import type { ReactNode } from "react";
import { Spinner } from "./ui";

/** Standardized loading / empty / error states for consistent UX across pages. */

export function Loading({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="state" role="status" aria-live="polite">
      <Spinner />
      <p style={{ marginTop: "0.6rem" }}>{label}</p>
    </div>
  );
}

export function EmptyState({
  icon = "📭",
  title,
  hint,
  action,
}: {
  icon?: string;
  title: string;
  hint?: string;
  action?: ReactNode;
}) {
  return (
    <div className="state">
      <div className="state-icon" aria-hidden>
        {icon}
      </div>
      <strong style={{ color: "var(--text)" }}>{title}</strong>
      {hint ? <p style={{ marginTop: "0.4rem" }}>{hint}</p> : null}
      {action ? <div style={{ marginTop: "1rem" }}>{action}</div> : null}
    </div>
  );
}

export function ErrorState({ message }: { message?: string }) {
  return (
    <div className="state" role="alert">
      <div className="state-icon" aria-hidden>
        ⚠️
      </div>
      <strong style={{ color: "var(--danger)" }}>Something went wrong</strong>
      {message ? <p style={{ marginTop: "0.4rem" }}>{message}</p> : null}
    </div>
  );
}
