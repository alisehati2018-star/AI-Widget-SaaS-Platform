"use client";

// Tenant-detail read/identity sections: profile table, API keys, operator notes.

import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";
import { ApiError } from "@/lib/api";
import { adminFetch as authFetch } from "@/lib/auth";
import { formatDate } from "@/lib/datetime";
import type { Locale } from "@/i18n/routing";
import { Alert, Badge, Field, Input, Spinner } from "@/components/ui";

export interface TenantKey {
  id: string;
  scope: string;
  label: string | null;
  revoked: boolean;
  created_at: string | null;
  last_used_at: string | null;
}

export interface TenantDetail {
  id: string;
  slug: string;
  name: string;
  status: string;
  tracking_enabled: boolean;
  admin_notes: string | null;
  created_at: string | null;
  team_size: number;
  subscription: {
    plan_code: string | null;
    plan_name: string | null;
    price_monthly: number | null;
    currency: string | null;
    status: string;
    current_period_end: string | null;
  };
  credits: { used: number; granted: number; cap: number | null; within_plan: boolean };
  api_keys: TenantKey[];
  sync_state: { source: string; last_run_at: string | null; last_status: string | null }[];
}

export function ProfileCard({ d }: { d: TenantDetail }) {
  const t = useTranslations("admin");
  const locale = useLocale() as Locale;
  return (
    <div className="card">
      <h3>{t("tenantDetail.profileTitle")}</h3>
      <table className="table">
        <tbody>
          <tr><td className="muted">{t("tenantDetail.fName")}</td><td>{d.name}</td></tr>
          <tr><td className="muted">{t("tenantDetail.fSlug")}</td><td><code>{d.slug}</code></td></tr>
          <tr>
            <td className="muted">{t("tenantDetail.fStatus")}</td>
            <td><Badge tone={d.status === "active" ? "success" : "warning"}>{d.status}</Badge></td>
          </tr>
          <tr>
            <td className="muted">{t("tenantDetail.fPlan")}</td>
            <td>
              {d.subscription.plan_name ?? "—"}
              {d.subscription.plan_code ? <> <code>{d.subscription.plan_code}</code></> : null}
              {" "}
              <Badge tone={d.subscription.status === "active" ? "success" : "warning"}>{d.subscription.status}</Badge>
            </td>
          </tr>
          <tr>
            <td className="muted">{t("tenantDetail.fPeriodEnd")}</td>
            <td>{d.subscription.current_period_end ? formatDate(d.subscription.current_period_end, locale) : "—"}</td>
          </tr>
          <tr><td className="muted">{t("tenantDetail.fTeam")}</td><td>{d.team_size}</td></tr>
          <tr>
            <td className="muted">{t("tenantDetail.fTracking")}</td>
            <td>{d.tracking_enabled ? <Badge tone="success">{t("common.on")}</Badge> : <Badge>{t("common.off")}</Badge>}</td>
          </tr>
          <tr>
            <td className="muted">{t("tenantDetail.fCreated")}</td>
            <td>{d.created_at ? formatDate(d.created_at, locale) : "—"}</td>
          </tr>
        </tbody>
      </table>
      {d.sync_state.length > 0 ? (
        <>
          <h4 style={{ marginTop: "1rem" }}>{t("tenantDetail.syncTitle")}</h4>
          <table className="table">
            <tbody>
              {d.sync_state.map((s) => (
                <tr key={s.source}>
                  <td><code>{s.source}</code></td>
                  <td className="muted">{s.last_run_at ? formatDate(s.last_run_at, locale) : "—"}</td>
                  <td>{s.last_status ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      ) : (
        <p className="hint" style={{ marginTop: "1rem" }}>{t("tenantDetail.syncEmpty")}</p>
      )}
    </div>
  );
}

export function KeysCard({ d, onDone }: { d: TenantDetail; onDone: (msg: string) => void }) {
  const t = useTranslations("admin");
  const locale = useLocale() as Locale;
  const [scope, setScope] = useState("widget");
  const [label, setLabel] = useState("");
  const [issued, setIssued] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function issue(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    setBusy(true);
    try {
      const r = await authFetch<{ api_key: string }>(`/admin/tenants/${d.id}/keys`, {
        body: { scope, label },
      });
      setIssued(r.api_key);
      setLabel("");
      onDone(t("tenantDetail.keyIssued"));
    } catch (e2) {
      setErr(e2 instanceof ApiError ? e2.message : t("tenantDetail.actionFailed"));
    } finally {
      setBusy(false);
    }
  }

  async function revoke(keyId: string) {
    if (!window.confirm(t("tenantDetail.keyRevokeConfirm"))) return;
    try {
      await authFetch(`/admin/tenants/${d.id}/keys/${keyId}/revoke`, { method: "POST", body: {} });
      onDone(t("tenantDetail.keyRevoked"));
    } catch (e2) {
      setErr(e2 instanceof ApiError ? e2.message : t("tenantDetail.actionFailed"));
    }
  }

  return (
    <div className="card">
      <h3>{t("tenantDetail.keysTitle")}</h3>
      {err ? <Alert kind="error">{err}</Alert> : null}
      {issued ? (
        <Alert kind="success">
          {t("tenantDetail.keyOneTime")}
          <br />
          <code style={{ wordBreak: "break-all" }}>{issued}</code>
        </Alert>
      ) : null}
      {d.api_keys.length === 0 ? (
        <p className="muted">{t("tenantDetail.keysEmpty")}</p>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>{t("tenantDetail.keyColLabel")}</th>
              <th>{t("tenantDetail.keyColScope")}</th>
              <th>{t("tenantDetail.keyColCreated")}</th>
              <th>{t("tenantDetail.keyColStatus")}</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {d.api_keys.map((k) => (
              <tr key={k.id}>
                <td>{k.label ?? "—"}</td>
                <td><Badge tone="brand">{k.scope}</Badge></td>
                <td className="muted">{k.created_at ? formatDate(k.created_at, locale) : "—"}</td>
                <td>
                  {k.revoked
                    ? <Badge tone="warning">{t("tenantDetail.keyRevokedBadge")}</Badge>
                    : <Badge tone="success">{t("common.active")}</Badge>}
                </td>
                <td>
                  {!k.revoked ? (
                    <button className="btn btn-danger" onClick={() => void revoke(k.id)}>
                      {t("tenantDetail.keyRevoke")}
                    </button>
                  ) : null}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <form onSubmit={issue} className="row" style={{ alignItems: "flex-end", flexWrap: "wrap", marginTop: "1rem" }}>
        <div style={{ minWidth: 150 }}>
          <Field label={t("tenantDetail.keyScope")}>
            <select className="input" value={scope} onChange={(e) => setScope(e.target.value)}>
              <option value="widget">{t("tenants.scopeWidget")}</option>
              <option value="sync">{t("tenants.scopeSync")}</option>
            </select>
          </Field>
        </div>
        <div style={{ flex: 1, minWidth: 160 }}>
          <Field label={t("tenantDetail.keyLabel")}>
            <Input value={label} onChange={(e) => setLabel(e.target.value)} placeholder={t("tenantDetail.keyLabelPlaceholder")} />
          </Field>
        </div>
        <button className="btn btn-primary" disabled={busy} style={{ marginBottom: "1rem" }}>
          {busy ? <Spinner /> : t("tenantDetail.keyIssue")}
        </button>
      </form>
    </div>
  );
}

export function NotesCard({ d, onDone }: { d: TenantDetail; onDone: (msg: string) => void }) {
  const t = useTranslations("admin");
  const [notes, setNotes] = useState(d.admin_notes ?? "");
  const [busy, setBusy] = useState(false);

  async function save() {
    setBusy(true);
    try {
      await authFetch(`/admin/tenants/${d.id}/notes`, { method: "PATCH", body: { notes } });
      onDone(t("tenantDetail.notesSaved"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card">
      <h3>{t("tenantDetail.notesTitle")}</h3>
      <p className="hint">{t("tenantDetail.notesHint")}</p>
      <textarea
        className="input"
        style={{ minHeight: 110 }}
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        placeholder={t("tenantDetail.notesPlaceholder")}
      />
      <div style={{ marginTop: ".75rem" }}>
        <button className="btn btn-primary" disabled={busy} onClick={() => void save()}>
          {busy ? <Spinner /> : t("tenantDetail.notesSave")}
        </button>
      </div>
    </div>
  );
}
