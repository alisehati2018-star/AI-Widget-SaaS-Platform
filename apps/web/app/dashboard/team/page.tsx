"use client";

import { useCallback, useEffect, useState } from "react";
import type { TeamMember } from "../../../lib/api";
import { ApiError } from "../../../lib/api";
import { authFetch } from "../../../lib/auth";
import { DashboardShell, OWNER_NAV } from "../../../components/shell";
import { Alert, Badge, Field, Input, Spinner } from "../../../components/ui";

export default function TeamPage() {
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
      setError(err instanceof ApiError ? err.message : "Could not invite.");
    } finally {
      setBusy(false);
    }
  }

  async function changeRole(memberEmail: string, role: string) {
    await authFetch("/tenant/team/role", { body: { email: memberEmail, role } }).catch(() => {});
    load();
  }

  async function removeMember(memberEmail: string) {
    if (!window.confirm(`Remove ${memberEmail} from the team?`)) return;
    await authFetch("/tenant/team/remove", { body: { email: memberEmail } }).catch(() => {});
    load();
  }

  return (
    <DashboardShell title="Team" nav={OWNER_NAV}>
      <p style={{ marginTop: "-1rem" }}>Invite staff to help manage your store. Staff have reduced privileges.</p>

      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <h3>Invite a teammate</h3>
        {error ? <Alert kind="error">{error}</Alert> : null}
        {invite && invite !== "invited" ? (
          <Alert kind="success">
            Invitation created. Share this setup link (dev mode):
            <br />
            <code style={{ wordBreak: "break-all" }}>{invite}</code>
          </Alert>
        ) : invite === "invited" ? (
          <Alert kind="success">Invitation sent.</Alert>
        ) : null}
        <form onSubmit={submit} className="row" style={{ alignItems: "flex-end", flexWrap: "wrap" }}>
          <div style={{ flex: 1, minWidth: 200 }}>
            <Field label="Email"><Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="teammate@store.com" required /></Field>
          </div>
          <div style={{ flex: 1, minWidth: 160 }}>
            <Field label="Name"><Input value={fullName} onChange={(e) => setFullName(e.target.value)} placeholder="Optional" /></Field>
          </div>
          <button className="btn btn-primary" disabled={busy} style={{ marginBottom: "1rem" }}>{busy ? <Spinner /> : "Send invite"}</button>
        </form>
      </div>

      <div className="card">
        <h3>Members</h3>
        {members === null ? (
          <Spinner />
        ) : (
          <table className="table">
            <thead><tr><th>Email</th><th>Name</th><th>Role</th><th>Status</th><th></th></tr></thead>
            <tbody>
              {members.map((m) => (
                <tr key={m.email}>
                  <td>{m.email}</td>
                  <td>{m.full_name ?? "—"}</td>
                  <td><Badge tone={m.role === "store_owner" ? "brand" : undefined}>{m.role.replace("store_", "")}</Badge></td>
                  <td>{m.status === "active" ? <Badge tone="success">active</Badge> : <Badge tone="warning">{m.status}</Badge>}</td>
                  <td>
                    <div className="row" style={{ gap: "0.4rem" }}>
                      <button className="btn btn-soft" onClick={() => void changeRole(m.email, m.role === "store_owner" ? "store_staff" : "store_owner")}>
                        {m.role === "store_owner" ? "Make staff" : "Make owner"}
                      </button>
                      <button className="btn btn-danger" onClick={() => void removeMember(m.email)}>Remove</button>
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
