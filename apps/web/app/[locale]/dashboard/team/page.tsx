"use client";

import { useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";
import type { TeamMember } from "@/lib/api";
import { ApiError } from "@/lib/api";
import { authFetch } from "@/lib/auth";
import { DashboardShell, useOwnerNav } from "@/components/shell";
import { Alert, Badge, Field, Input, Spinner } from "@/components/ui";

export default function TeamPage() {
  const t = useTranslations("dashboard");
  const tErrors = useTranslations("errors");
  const nav = useOwnerNav();
  const [members, setMembers] = useState<TeamMember[] | null>(null);
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [invite, setInvite] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    authFetch<{ members: TeamMember[] }>("/tenant/team").then((r) => setMembers(r.members)).catch(() => setMembers([]));
  }, []);
  useEffect(() => load(), [load]);

  const roleLabel = (role: string) => (role === "store_owner" ? t("team.roleOwner") : t("team.roleStaff"));

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setInvite(null);
    setBusy(true);
    try {
      const r = await authFetch<{ setup_token?: string }>("/tenant/team/invite", { body: { email, full_name: fullName } });
      setEmail("");
      setFullName("");
      if (r.setup_token) {
        setInvite(`${window.location.origin}/reset-password?token=${r.setup_token}`);
      } else {
        setInvite("invited");
      }
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : tErrors("saveFailed"));
    } finally {
      setBusy(false);
    }
  }

  async function changeRole(memberEmail: string, role: string) {
    await authFetch("/tenant/team/role", { body: { email: memberEmail, role } }).catch(() => {});
    load();
  }

  async function removeMember(memberEmail: string) {
    if (!window.confirm(t("team.removeConfirm", { email: memberEmail }))) return;
    await authFetch("/tenant/team/remove", { body: { email: memberEmail } }).catch(() => {});
    load();
  }

  return (
    <DashboardShell title={t("nav.team")} nav={nav}>
      <p style={{ marginTop: "-1rem" }}>{t("team.intro")}</p>

      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <h3>{t("team.inviteTitle")}</h3>
        {error ? <Alert kind="error">{error}</Alert> : null}
        {invite && invite !== "invited" ? (
          <Alert kind="success">
            {t("team.inviteCreated")}
            <br />
            <code style={{ wordBreak: "break-all" }}>{invite}</code>
          </Alert>
        ) : invite === "invited" ? (
          <Alert kind="success">{t("team.inviteSent")}</Alert>
        ) : null}
        <form onSubmit={submit} className="row" style={{ alignItems: "flex-end", flexWrap: "wrap" }}>
          <div style={{ flex: 1, minWidth: 200 }}>
            <Field label={t("team.email")}><Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder={t("team.emailPlaceholder")} required /></Field>
          </div>
          <div style={{ flex: 1, minWidth: 160 }}>
            <Field label={t("team.name")}><Input value={fullName} onChange={(e) => setFullName(e.target.value)} placeholder={t("team.namePlaceholder")} /></Field>
          </div>
          <button className="btn btn-primary" disabled={busy} style={{ marginBottom: "1rem" }}>
            {busy ? <Spinner /> : t("team.sendInvite")}
          </button>
        </form>
      </div>

      <div className="card">
        <h3>{t("team.members")}</h3>
        {members === null ? (
          <Spinner />
        ) : (
          <table className="table">
            <thead><tr><th>{t("team.email")}</th><th>{t("team.colName")}</th><th>{t("team.colRole")}</th><th>{t("common.status")}</th><th></th></tr></thead>
            <tbody>
              {members.map((m) => (
                <tr key={m.email}>
                  <td>{m.email}</td>
                  <td>{m.full_name ?? "—"}</td>
                  <td><Badge tone={m.role === "store_owner" ? "brand" : undefined}>{roleLabel(m.role)}</Badge></td>
                  <td>{m.status === "active" ? <Badge tone="success">{t("team.active")}</Badge> : <Badge tone="warning">{m.status}</Badge>}</td>
                  <td>
                    <div className="row" style={{ gap: "0.4rem" }}>
                      <button className="btn btn-soft" onClick={() => void changeRole(m.email, m.role === "store_owner" ? "store_staff" : "store_owner")}>
                        {m.role === "store_owner" ? t("team.makeStaff") : t("team.makeOwner")}
                      </button>
                      <button className="btn btn-danger" onClick={() => void removeMember(m.email)}>{t("team.remove")}</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </DashboardShell>
  );
}
