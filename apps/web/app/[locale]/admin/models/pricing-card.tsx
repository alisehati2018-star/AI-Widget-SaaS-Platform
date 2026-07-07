"use client";

// Platform pricing knobs: what one credit is worth, the markup applied over
// provider cost, the flat search price, and local-model cost attribution.

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { ApiError } from "@/lib/api";
import { adminFetch as authFetch } from "@/lib/auth";
import { Alert, Field, Input, Spinner } from "@/components/ui";
import type { PricingData } from "./types";

const KEYS: (keyof PricingData)[] = [
  "usd_per_credit",
  "margin_percent",
  "search_credits",
  "local_input_usd_per_1m",
  "local_output_usd_per_1m",
];

export function PricingCard({ pricing, reload }: { pricing: PricingData; reload: () => void }) {
  const t = useTranslations("admin");
  const [form, setForm] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [flash, setFlash] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setForm(Object.fromEntries(KEYS.map((k) => [k, String(pricing[k])])));
  }, [pricing]);

  async function save() {
    setError(null);
    setFlash(null);
    setBusy(true);
    try {
      const body: Record<string, number> = {};
      for (const k of KEYS) {
        const v = Number(form[k]);
        if (!Number.isFinite(v)) {
          setError(t("models.pricingInvalid", { field: k }));
          setBusy(false);
          return;
        }
        body[k] = v;
      }
      await authFetch("/admin/ai/pricing", { method: "PUT", body });
      setFlash(t("models.pricingSaved"));
      reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("models.actionFailed"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card" style={{ marginBottom: "1.5rem" }}>
      <h3>{t("models.pricingTitle")}</h3>
      <p className="hint">{t("models.pricingHint")}</p>
      {error ? <Alert kind="error">{error}</Alert> : null}
      {flash ? <Alert kind="success">{flash}</Alert> : null}
      <div className="dash-2col-even">
        <Field label={t("models.usdPerCredit")} hint={t("models.usdPerCreditHint")}>
          <Input dir="ltr" inputMode="decimal" value={form.usd_per_credit ?? ""}
            onChange={(e) => setForm({ ...form, usd_per_credit: e.target.value })} />
        </Field>
        <Field label={t("models.marginPercent")} hint={t("models.marginPercentHint")}>
          <Input dir="ltr" inputMode="decimal" value={form.margin_percent ?? ""}
            onChange={(e) => setForm({ ...form, margin_percent: e.target.value })} />
        </Field>
        <Field label={t("models.searchCredits")} hint={t("models.searchCreditsHint")}>
          <Input dir="ltr" inputMode="decimal" value={form.search_credits ?? ""}
            onChange={(e) => setForm({ ...form, search_credits: e.target.value })} />
        </Field>
        <Field label={t("models.localInPrice")} hint={t("models.localPriceHint")}>
          <Input dir="ltr" inputMode="decimal" value={form.local_input_usd_per_1m ?? ""}
            onChange={(e) => setForm({ ...form, local_input_usd_per_1m: e.target.value })} />
        </Field>
        <Field label={t("models.localOutPrice")}>
          <Input dir="ltr" inputMode="decimal" value={form.local_output_usd_per_1m ?? ""}
            onChange={(e) => setForm({ ...form, local_output_usd_per_1m: e.target.value })} />
        </Field>
      </div>
      <button className="btn btn-primary" disabled={busy} onClick={() => void save()}>
        {busy ? <Spinner /> : t("models.savePricing")}
      </button>
    </div>
  );
}
