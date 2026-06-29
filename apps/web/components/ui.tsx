import { useTranslations } from "next-intl";
import type { InputHTMLAttributes, ReactNode } from "react";
import { Link } from "@/i18n/navigation";

export function Brand({ href = "/" }: { href?: string }) {
  const t = useTranslations("common");
  return (
    <Link href={href} className="brand">
      <span className="brand-mark">V</span>
      <span>{t("brand.name")}</span>
    </Link>
  );
}

export function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <div className="field">
      <label className="label">{label}</label>
      {children}
      {hint ? <span className="hint">{hint}</span> : null}
    </div>
  );
}

export function Input(props: InputHTMLAttributes<HTMLInputElement>) {
  return <input className="input" {...props} />;
}

export function Alert({ kind, children }: { kind: "error" | "success"; children: ReactNode }) {
  return <div className={`alert alert-${kind}`}>{children}</div>;
}

export function Spinner() {
  const t = useTranslations("common");
  return <span className="spinner" role="status" aria-label={t("states.loading")} />;
}

export function Badge({
  children,
  tone,
}: {
  children: ReactNode;
  tone?: "success" | "warning" | "brand";
}) {
  return <span className={`badge${tone ? ` badge-${tone}` : ""}`}>{children}</span>;
}

export function Stat({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="card stat">
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
    </div>
  );
}
