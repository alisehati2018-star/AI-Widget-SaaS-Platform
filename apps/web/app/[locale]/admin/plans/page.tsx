"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { ApiError } from "@/lib/api";
import { adminFetch as authFetch } from "@/lib/auth";
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

const EMPTY: Plan = {
  id: "", code: "", name: "", price_monthly: 0, currency: "USD",
  credits_per_month: 0, monthly_credit_cap: 100000, rate_limit_per_min: 120, is_public: true,
};

const CODE_RE = /^[a-z0-9][a-z0-9_-]{1,30}$/;

export default function AdminPlans() {
  const t = useTranslations("admin");
  const nav = useAdminNav();
  const [plans, setPlans] = useState<Plan[]>([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState<Plan | null>(null);
  const [creating, setCreating] = useState(false);
  const [note, setNote] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
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

  function startCreate() {
    setNote(null); setError(null); setCreating(true); setEditing({ ...EMPTY });
  }
  function startEdit(p: Plan) {
    setNote(null); setError(null); setCreating(false); setEditing({ ...p });
  }

  async function save() {
    if (!editing) return;
    setError(null);
    if (creating && !CODE_RE.test(editing.code)) { setError(t("plans.codeInvalid")); return; }
    if (!editing.name.trim()) { setError(t("plans.nameRequired")); return; }
    if (editing.price_monthly < 0 || editing.credits_per_month < 0 || editing.monthly_credit_cap < 0) {
      setError(t("plans.negativeInvalid"));
      return;
    }
    setBusy(true);
    try {
      const body = {
        name: editing.name.trim(),
        price_monthly: editing.price_monthly,
        credits_per_month: editing.credits_per_month,
        monthly_credit_cap: editing.monthly_credit_cap,
        rate_limit_per_min: editing.rate_limit_per_min,
        is_public: editing.is_public,
      };
      if (creating) {
        await authFetch("/admin/plans", { body: { ...body, code: editing.code.trim() } });
        setNote(t("plans.createdNote"));
      } else {
        await authFetch(`/admin/plans/${editing.id}`, { method: "PATCH", body });
        setNote(t("plans.saved"));
      }
      setEditing(null);
      setCreating(false);
      await reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("plans.saveFailed"));
    } finally {
      setBusy(false);
    }
  }

  async function remove(p: Plan) {
    setNote(null); setError(null);
    if (!window.confirm(t("plans.confirmDelete", { name: p.name }))) return;
    setBusy(true);
    try {
      await authFetch(`/admin/plans/${p.id}`, { method: "DELETE" });
      setNote(t("plans.deletedNote"));
      if (editing?.id === p.id) setEditing(null);
      await reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("plans.deleteFailed"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <DashboardShell title={t("plans.title")} nav={nav} requireAdmin loginHref="/admin/login">
      <div className="row-between" style={{ marginTop: "-1rem", flexWrap: "wrap", gap: ".6rem" }}>
        <p style={{ margin: 0 }}>{t("plans.intro")}</p>
        <button className="btn btn-primary" onClick={startCreate}>{t("plans.newPlan")}</button>
      </div>
      {note ? <Alert kind="success">{note}</Alert> : null}
      {error ? <Alert kind="error">{error}</Alert> : null}

      <div className="dash-2col" style={{ marginTop: "1rem" }}>
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
                    <td>
                      <div className="row" style={{ gap: ".4rem" }}>
                        <button className="btn btn-ghost" onClick={() => startEdit(p)}>{t("plans.edit")}</button>
                        <button className="btn btn-danger" disabled={busy} onClick={() => void remove(p)}>{t("plans.delete")}</button>
                      </div>
                    </td>
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
              <h3>
                {creating ? t("plans.newPlan") : editing.name}{" "}
                {!creating ? <code>{editing.code}</code> : null}
              </h3>
              {creating ? (
                <Field label={t("plans.code")} hint={t("plans.codeHint")}>
                  <Input dir="ltr" value={editing.code} onChange={(e) => setEditing({ ...editing, code: e.target.value.toLowerCase() })} placeholder="growth" />
                </Field>
              ) : null}
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
                  {busy ? <Spinner /> : creating ? t("plans.create") : t("plans.save")}
                </button>
                <button className="btn btn-soft" onClick={() => { setEditing(null); setCreating(false); }}>{t("plans.cancel")}</button>
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
