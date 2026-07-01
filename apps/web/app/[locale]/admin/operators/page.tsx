"use client";

import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";
import { ApiError } from "@/lib/api";
import { adminFetch as authFetch } from "@/lib/auth";
import { formatDate, formatNumber } from "@/lib/datetime";
import { useAdminResource as useResource } from "@/lib/hooks/useResource";
import type { Locale } from "@/i18n/routing";
import { DashboardShell, useAdminNav } from "@/components/shell";
import { Alert, Badge, Field, Input, Spinner } from "@/components/ui";

interface Operator {
  id: string;
  email: string;
  full_name: string | null;
  status: "active" | "suspended";
  last_login_at: string | null;
  created_at: string | null;
  sessions: number;
}
interface OperatorList {
  operators: Operator[];
  me: string | null;
}

export default function AdminOperators() {
  const t = useTranslations("admin");
  const locale = useLocale() as Locale;
  const nav = useAdminNav();

  const { data, error: loadError, loading, reload } = useResource<OperatorList>("/admin/operators");
  const operators = loading ? null : (data?.operators ?? []);
  const me = data?.me ?? null;

  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [flash, setFlash] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [renaming, setRenaming] = useState<Operator | null>(null);
  const [newName, setNewName] = useState("");

  async function invite(e: React.FormEvent) {
    e.preventDefault();
    setFlash(null);
    setError(null);
    setBusy(true);
    try {
      await authFetch("/admin/operators", {
        body: { email: email.trim(), password, full_name: fullName.trim() },
      });
      setFlash(t("operators.invited", { email: email.trim() }));
      setEmail(""); setFullName(""); setPassword("");
      reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("operators.actionFailed"));
    } finally {
      setBusy(false);
    }
  }

  async function act(fn: () => unknown) {
    setFlash(null);
    setError(null);
    setBusy(true);
    try {
      await fn();
      reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("operators.actionFailed"));
    } finally {
      setBusy(false);
    }
  }

  function toggleStatus(o: Operator) {
    const next = o.status === "active" ? "suspended" : "active";
    if (next === "suspended" && !window.confirm(t("operators.confirmSuspend", { email: o.email }))) return;
    void act(() => authFetch(`/admin/operators/${o.id}/status`, { body: { status: next } }));
  }

  function remove(o: Operator) {
    if (!window.confirm(t("operators.confirmDelete", { email: o.email }))) return;
    void act(() => authFetch(`/admin/operators/${o.id}`, { method: "DELETE" }));
  }

  function saveRename() {
    if (!renaming) return;
    void act(async () => {
      await authFetch(`/admin/operators/${renaming.id}`, { method: "PATCH", body: { full_name: newName.trim() } });
      setRenaming(null);
    });
  }

  return (
    <DashboardShell title={t("operators.title")} nav={nav} requireAdmin loginHref="/admin/login">
      <p style={{ marginTop: "-1rem" }}>{t("operators.intro")}</p>
      {flash ? <Alert kind="success">{flash}</Alert> : null}
      {error ? <Alert kind="error">{error}</Alert> : null}

      <div className="dash-2col">
        <div className="card">
          {loadError ? <p className="muted">{t("common.loadError")}: {loadError}</p> : null}
          {operators === null ? <Spinner /> : (
            <>
              <table className="table">
                <thead>
                  <tr>
                    <th>{t("operators.colOperator")}</th>
                    <th>{t("operators.colStatus")}</th>
                    <th>{t("operators.colSessions")}</th>
                    <th>{t("operators.colLastLogin")}</th>
                    <th>{t("operators.colActions")}</th>
                  </tr>
                </thead>
                <tbody>
                  {operators.map((o) => (
                    <tr key={o.id}>
                      <td>
                        {o.full_name || "—"}
                        {o.id === me ? <> <Badge tone="brand">{t("operators.you")}</Badge></> : null}
                        <br />
                        <span className="muted" dir="ltr">{o.email}</span>
                      </td>
                      <td>
                        {o.status === "active"
                          ? <Badge tone="success">{t("common.active")}</Badge>
                          : <Badge tone="warning">{t("operators.suspended")}</Badge>}
                      </td>
                      <td>{formatNumber(o.sessions, locale)}</td>
                      <td className="muted">{o.last_login_at ? formatDate(o.last_login_at, locale) : "—"}</td>
                      <td>
                        <div className="row" style={{ flexWrap: "wrap", gap: ".4rem" }}>
                          <button
                            className="btn btn-ghost"
                            onClick={() => { setRenaming(o); setNewName(o.full_name ?? ""); }}
                          >
                            {t("operators.rename")}
                          </button>
                          {o.id !== me ? (
                            <>
                              <button
                                className={o.status === "active" ? "btn btn-danger" : "btn btn-soft"}
                                disabled={busy}
                                onClick={() => toggleStatus(o)}
                              >
                                {o.status === "active" ? t("operators.suspend") : t("operators.activate")}
                              </button>
                              <button className="btn btn-danger" disabled={busy} onClick={() => remove(o)}>
                                {t("operators.delete")}
                              </button>
                            </>
                          ) : null}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {operators.length === 0 ? <p className="muted">{t("operators.empty")}</p> : null}
            </>
          )}
          <p className="hint" style={{ marginTop: "1rem" }}>{t("operators.note")}</p>
        </div>

        <div className="card" style={{ position: "sticky", top: "1.5rem" }}>
          {renaming ? (
            <>
              <h3>{t("operators.renameTitle")}</h3>
              <p className="muted" dir="ltr">{renaming.email}</p>
              <Field label={t("operators.fullName")}>
                <Input value={newName} onChange={(e) => setNewName(e.target.value)} />
              </Field>
              <div className="row" style={{ gap: ".5rem" }}>
                <button className="btn btn-primary" disabled={busy} onClick={saveRename}>
                  {busy ? <Spinner /> : t("operators.save")}
                </button>
                <button className="btn btn-soft" onClick={() => setRenaming(null)}>{t("operators.cancel")}</button>
              </div>
            </>
          ) : (
            <>
              <h3>{t("operators.inviteTitle")}</h3>
              <p className="hint">{t("operators.inviteHint")}</p>
              <form onSubmit={invite}>
                <Field label={t("operators.email")}>
                  <Input dir="ltr" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
                </Field>
                <Field label={t("operators.fullName")}>
                  <Input value={fullName} onChange={(e) => setFullName(e.target.value)} />
                </Field>
                <Field label={t("operators.initialPassword")} hint={t("operators.passwordHint")}>
                  <Input dir="ltr" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
                </Field>
                <button className="btn btn-primary" disabled={busy}>
                  {busy ? <Spinner /> : t("operators.invite")}
                </button>
              </form>
            </>
          )}
        </div>
      </div>
    </DashboardShell>
  );
}
