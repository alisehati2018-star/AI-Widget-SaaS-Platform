"use client";

import { useLocale, useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";
import { adminFetch } from "@/lib/auth";
import { formatNumber } from "@/lib/datetime";
import type { Locale } from "@/i18n/routing";
import { Badge, Spinner } from "@/components/ui";

interface Component {
  component: string;
  status: string;
  latency_ms?: number | null;
  detail?: Record<string, unknown>;
}
interface DeepHealth {
  status: string;
  checked_at: number;
  components: Component[];
}

const STATUS_TONE: Record<string, "success" | "warning" | undefined> = {
  ok: "success",
  configured: "success",
  error: "warning",
  not_configured: undefined,
};

/** Full-system diagnosis: every subsystem probed by /admin/health/deep with
 *  per-component status, latency and failure detail. */
export function DeepHealthCard() {
  const t = useTranslations("admin.health");
  const locale = useLocale() as Locale;
  const [data, setData] = useState<DeepHealth | null>(null);
  const [failed, setFailed] = useState(false);
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    setBusy(true);
    setFailed(false);
    adminFetch<DeepHealth>("/admin/health/deep")
      .then(setData)
      .catch(() => setFailed(true))
      .finally(() => setBusy(false));
  }, []);
  useEffect(() => load(), [load]);

  const compLabel = (key: string) => {
    const known = ["postgres", "redis", "elasticsearch", "queue", "ai_registry", "billing_psp", "email"];
    return known.includes(key) ? t(`comp.${key}`) : key;
  };
  const statusLabel = (s: string) =>
    ["ok", "error", "configured", "not_configured"].includes(s) ? t(`status.${s}`) : s;
  const detailText = (c: Component) =>
    Object.entries(c.detail ?? {})
      .filter(([, v]) => v !== null && v !== undefined)
      .map(([k, v]) => `${k}: ${String(v)}`)
      .join(" · ");

  return (
    <div className="card" style={{ marginTop: "1.5rem" }}>
      <div className="row-between" style={{ flexWrap: "wrap", gap: ".6rem" }}>
        <h3 style={{ margin: 0 }}>{t("deepTitle")}</h3>
        <div className="row" style={{ gap: ".5rem" }}>
          {data ? (
            <Badge tone={data.status === "ok" ? "success" : "warning"}>{statusLabel(data.status === "ok" ? "ok" : "error")}</Badge>
          ) : null}
          <button className="btn btn-soft" disabled={busy} onClick={load}>
            {busy ? <Spinner /> : t("deepRun")}
          </button>
        </div>
      </div>
      <p className="hint">{t("deepHint")}</p>
      {failed ? (
        <p className="muted">{t("deepFailed")}</p>
      ) : data === null ? (
        <Spinner />
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>{t("colComponent")}</th>
              <th>{t("colStatus")}</th>
              <th>{t("colLatency")}</th>
              <th>{t("colDetail")}</th>
            </tr>
          </thead>
          <tbody>
            {data.components.map((c) => (
              <tr key={c.component}>
                <td>{compLabel(c.component)}</td>
                <td><Badge tone={STATUS_TONE[c.status]}>{statusLabel(c.status)}</Badge></td>
                <td className="muted">
                  {c.latency_ms != null ? `${formatNumber(c.latency_ms, locale)} ${t("ms")}` : "—"}
                </td>
                <td className="muted" dir="ltr" style={{ fontSize: ".8rem", textAlign: "left" }}>
                  {detailText(c) || "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
