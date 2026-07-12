"use client";

// Inline "check credit" result panel: fetches external balance / key-health
// for a provider (most vendors don't expose a real balance API — see
// packages/acip_gateway/provider_credit.py) alongside its internal 30-day
// platform usage.

import { useTranslations } from "next-intl";
import { useState } from "react";
import { useApiErrorMessage } from "@/lib/errors";
import { adminFetch as authFetch } from "@/lib/auth";
import { Alert, Spinner } from "@/components/ui";
import type { AiProvider, CreditCheckResult } from "../models/types";

export function CheckCreditPanel({
  provider,
  onClose,
}: {
  provider: AiProvider;
  onClose: () => void;
}) {
  const t = useTranslations("admin");
  const apiMsg = useApiErrorMessage();
  const tp = useTranslations("admin.providersPage");
  const [result, setResult] = useState<CreditCheckResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function run() {
    setError(null);
    setBusy(true);
    try {
      const r = await authFetch<CreditCheckResult>(
        `/admin/ai/providers/${provider.id}/check-credit`,
        { method: "POST" }
      );
      setResult(r);
    } catch (err) {
      setError(apiMsg(err) ?? tp("checkCreditError"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card" style={{ margin: "0.8rem 0", borderStyle: "dashed" }}>
      <div className="row-between">
        <h4 style={{ margin: 0 }}>{tp("checkCreditTitle", { name: provider.name })}</h4>
        <button className="btn btn-ghost" onClick={onClose}>{t("models.cancel")}</button>
      </div>
      {error ? <Alert kind="error">{error}</Alert> : null}
      {result === null ? (
        <button className="btn btn-primary" disabled={busy} onClick={() => void run()}>
          {busy ? <Spinner /> : tp("checkCredit")}
        </button>
      ) : (
        <div className="dash-2col-even" style={{ marginTop: ".6rem" }}>
          <div>
            <p className="hint" style={{ marginBottom: ".3rem" }}>{tp("externalBalance")}</p>
            {result.credit.source === "external_api" ? (
              <ul style={{ margin: 0, paddingInlineStart: "1.2rem" }}>
                <li>{tp("usage")}: {result.credit.usage} {result.credit.currency}</li>
                <li>{tp("limit")}: {result.credit.limit ?? "—"}</li>
                <li>{tp("remaining")}: {result.credit.remaining ?? "—"}</li>
              </ul>
            ) : (
              <>
                <p className="muted" style={{ fontSize: ".85rem" }}>{result.credit.note}</p>
                {result.credit.dashboard_url ? (
                  <a href={result.credit.dashboard_url} target="_blank" rel="noreferrer"
                    className="muted" dir="ltr" style={{ fontSize: ".8rem" }}>
                    {result.credit.dashboard_url}
                  </a>
                ) : null}
              </>
            )}
          </div>
          <div>
            <p className="hint" style={{ marginBottom: ".3rem" }}>{tp("platformUsage30d")}</p>
            <ul style={{ margin: 0, paddingInlineStart: "1.2rem" }}>
              <li>{tp("callsShort")}: {result.platform_usage.call_count}</li>
              <li>{tp("creditsShort")}: {result.platform_usage.platform_credits}</li>
              <li>${result.platform_usage.estimated_cost_usd.toFixed(4)}</li>
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
