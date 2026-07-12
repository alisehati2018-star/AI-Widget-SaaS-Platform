"use client";

// Dedicated signup-credit policy: how many credits a brand-new self-serve
// signup receives, separate from any plan's monthly allowance and from the
// per-tenant manual grant/deduct flow on the tenant detail page.

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { useApiErrorMessage } from "@/lib/errors";
import { adminFetch as authFetch } from "@/lib/auth";
import { Alert, Field, Input, Spinner } from "@/components/ui";

interface CreditPolicy {
  auto_grant_enabled: boolean;
  signup_credits: number;
}

export function CreditPolicyCard() {
  const t = useTranslations("admin");
  const apiMsg = useApiErrorMessage();
  const [policy, setPolicy] = useState<CreditPolicy | null>(null);
  const [amount, setAmount] = useState("");
  const [enabled, setEnabled] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [flash, setFlash] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function load() {
    try {
      const r = await authFetch<CreditPolicy>("/admin/credit-policy");
      setPolicy(r);
      setAmount(String(r.signup_credits));
      setEnabled(r.auto_grant_enabled);
    } catch {
      setPolicy(null);
    }
  }

  useEffect(() => { void load(); }, []);

  async function save() {
    setError(null);
    setFlash(null);
    const value = Number(amount);
    if (!Number.isFinite(value) || value < 0) {
      setError(t("plans.creditPolicyInvalid"));
      return;
    }
    setBusy(true);
    try {
      const r = await authFetch<CreditPolicy>("/admin/credit-policy", {
        method: "PUT",
        body: { auto_grant_enabled: enabled, signup_credits: value },
      });
      setPolicy(r);
      setFlash(t("plans.creditPolicySaved"));
    } catch (err) {
      setError(apiMsg(err) ?? t("plans.saveFailed"));
    } finally {
      setBusy(false);
    }
  }

  if (!policy) return null;

  return (
    <div className="card" style={{ marginBottom: "1.5rem" }}>
      <h3>{t("plans.creditPolicyTitle")}</h3>
      <p className="hint">{t("plans.creditPolicyHint")}</p>
      {error ? <Alert kind="error">{error}</Alert> : null}
      {flash ? <Alert kind="success">{flash}</Alert> : null}
      <label className="row" style={{ gap: ".5rem", marginBottom: "1rem" }}>
        <input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} />
        {t("plans.creditPolicyEnabled")}
      </label>
      <Field label={t("plans.creditPolicyAmount")} hint={t("plans.creditPolicyAmountHint")}>
        <Input
          dir="ltr"
          inputMode="decimal"
          disabled={!enabled}
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
        />
      </Field>
      <button className="btn btn-primary" disabled={busy} onClick={() => void save()}>
        {busy ? <Spinner /> : t("plans.creditPolicySave")}
      </button>
    </div>
  );
}
