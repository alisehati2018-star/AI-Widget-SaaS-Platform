"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { authFetch } from "@/lib/auth";
import { DashboardShell, useAdminNav } from "@/components/shell";
import { Alert, Badge, Field, Input, Spinner } from "@/components/ui";

interface Plan {
  id: string;
  code: string;
  name: string;
  price_monthly: number;
  currency: string;
  credits_per_month: number;
  monthly_credit_cap: number;
  rate_limit_per_min: number;
  is_public: boolean;
}

export default function AdminPlans() {
  const t = useTranslations("admin");
  const nav = useAdminNav();
  const [plans, setPlans] = useState<Plan[]>([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState<Plan | null>(null);
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);

  async function reload() {
    setLoading(true);
    try {
      const r = await authFetch<{ plans: Plan[] }>("/admin/plans");
      setPlans(r.plans);
    } catch {
      setPlans([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void reload(); }, []);

  async function save() {
    if (!editing) return;
    setBusy(true);
    try {
      await authFetch(`/admin/plans/${editing.id}`, {
        method: "PATCH",
        body: {
          name: editing.name,
          price_monthly: editing.price_monthly,
          credits_per_month: editing.credits_per_month,
          monthly_credit_cap: editing.monthly_credit_cap,
          rate_limit_per_min: editing.rate_limit_per_min,
          is_public: editing.is_public,
        },
      });
      setSaved(true);
      await reload();
      setEditing((cur) => (cur ? plans.find((p) => p.id === cur.id) ?? null : null));
    } finally {
      setBusy(false);
    }
  }

  return (
    <DashboardShell title={t("plans.title")} nav={nav} requireAdmin loginHref="/admin/login">
      <p style={{ marginTop: "-1rem" }}>{t("plans.intro")}</p>
      {saved ? <Alert kind="success">{t("plans.saved")}</Alert> : null}

      <div className="dash-2col">
        <div className="card">
          {loading ? <Spinner /> : (
            <table className="table">
              <thead>
                <tr>
                  <th>{t("plans.colPlan")}</th><th>{t("plans.colPrice")}</th>
                  <th>{t("plans.colCredits")}</th><th>{t("plans.colCap")}</th>
                  <th>{t("plans.colRateLimit")}</th><th>{t("plans.public")}</th><th></th>
                </tr>
              </thead>
              <tbody>
                {plans.map((p) => (
                  <tr key={p.id} className={editing?.id === p.id ? "row-selected" : undefined}>
                    <td>{p.name} <code>{p.code}</code></td>
                    <td>{p.price_monthly} {p.currency}</td>
                    <td>{p.credits_per_month}</td>
                    <td>{p.monthly_credit_cap}</td>
                    <td>{p.rate_limit_per_min}</td>
                    <td>{p.is_public ? <Badge tone="success">{t("plans.public")}</Badge> : <Badge>—</Badge>}</td>
                    <td><button className="btn btn-ghost" onClick={() => { setSaved(false); setEditing({ ...p }); }}>{t("plans.edit")}</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <p className="hint" style={{ marginTop: "1rem" }}>{t("plans.note")}</p>
        </div>

        <div className="card" style={{ position: "sticky", top: "1.5rem" }}>
          {editing ? (
            <>
              <h3>{editing.name} <code>{editing.code}</code></h3>
              <Field label={t("plans.name")}>
                <Input value={editing.name} onChange={(e) => setEditing({ ...editing, name: e.target.value })} />
              </Field>
              <Field label={t("plans.price")}>
                <Input type="number" value={editing.price_monthly} onChange={(e) => setEditing({ ...editing, price_monthly: parseFloat(e.target.value) || 0 })} />
              </Field>
              <Field label={t("plans.credits")}>
                <Input type="number" value={editing.credits_per_month} onChange={(e) => setEditing({ ...editing, credits_per_month: parseFloat(e.target.value) || 0 })} />
              </Field>
              <Field label={t("plans.cap")}>
                <Input type="number" value={editing.monthly_credit_cap} onChange={(e) => setEditing({ ...editing, monthly_credit_cap: parseFloat(e.target.value) || 0 })} />
              </Field>
              <Field label={t("plans.rateLimit")}>
                <Input type="number" value={editing.rate_limit_per_min} onChange={(e) => setEditing({ ...editing, rate_limit_per_min: parseInt(e.target.value, 10) || 0 })} />
              </Field>
              <label className="row" style={{ gap: ".5rem", marginBottom: "1rem" }}>
                <input type="checkbox" checked={editing.is_public} onChange={(e) => setEditing({ ...editing, is_public: e.target.checked })} />
                {t("plans.public")}
              </label>
              <div className="row" style={{ gap: ".5rem" }}>
                <button className="btn btn-primary" disabled={busy} onClick={() => void save()}>
                  {busy ? <Spinner /> : t("plans.save")}
                </button>
                <button className="btn btn-soft" onClick={() => setEditing(null)}>{t("plans.cancel")}</button>
              </div>
            </>
          ) : (
            <div className="state">
              <p>{t("plans.selectHint")}</p>
            </div>
          )}
        </div>
      </div>
    </DashboardShell>
  );
}
