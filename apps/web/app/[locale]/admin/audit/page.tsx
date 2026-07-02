"use client";

import { useLocale, useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";
import { adminFetch as authFetch } from "@/lib/auth";
import { formatDateTime } from "@/lib/datetime";
import type { Locale } from "@/i18n/routing";
import { DashboardShell, useAdminNav } from "@/components/shell";
import { Badge, Input, Spinner } from "@/components/ui";

interface Entry {
  id: number;
  actor: string;
  action: string;
  tenant: string | null;
  detail: Record<string, unknown>;
  created_at: string | null;
}
interface AuditPage {
  entries: Entry[];
  next_cursor: number | null;
}

export default function AdminAudit() {
  const t = useTranslations("admin");
  const locale = useLocale() as Locale;
  const nav = useAdminNav();

  const [actor, setActor] = useState("");
  const [action, setAction] = useState("");
  const [tenant, setTenant] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [applied, setApplied] = useState({ actor: "", action: "", tenant: "", dateFrom: "", dateTo: "" });

  const [entries, setEntries] = useState<Entry[] | null>(null);
  const [cursor, setCursor] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const id = setTimeout(
      () => setApplied({ actor: actor.trim(), action: action.trim(), tenant: tenant.trim(), dateFrom, dateTo }),
      300,
    );
    return () => clearTimeout(id);
  }, [actor, action, tenant, dateFrom, dateTo]);

  const buildParams = useCallback((cur?: number | null) => {
    const p = new URLSearchParams();
    if (applied.actor) p.set("actor", applied.actor);
    if (applied.action) p.set("action", applied.action);
    if (applied.tenant) p.set("tenant", applied.tenant);
    if (applied.dateFrom) p.set("date_from", applied.dateFrom);
    if (applied.dateTo) p.set("date_to", applied.dateTo);
    if (cur != null) p.set("cursor", String(cur));
    return p;
  }, [applied]);

  useEffect(() => {
    setEntries(null);
    setError(null);
    authFetch<AuditPage>(`/admin/audit?${buildParams().toString()}`)
      .then((r) => { setEntries(r.entries); setCursor(r.next_cursor); })
      .catch((e) => setError(String(e.message ?? e)));
  }, [buildParams]);

  async function loadMore() {
    if (cursor == null) return;
    setBusy(true);
    try {
      const r = await authFetch<AuditPage>(`/admin/audit?${buildParams(cursor).toString()}`);
      setEntries((cur) => [...(cur ?? []), ...r.entries]);
      setCursor(r.next_cursor);
    } finally {
      setBusy(false);
    }
  }

  const csvHref = `/api/admin/audit?${buildParams().toString()}&fmt=csv`;

  return (
    <DashboardShell title={t("audit.title")} nav={nav} requireAdmin loginHref="/admin/login">
      <p style={{ marginTop: "-1rem" }}>{t("audit.intro")}</p>
      <div className="card">
        <div className="row" style={{ flexWrap: "wrap", gap: ".6rem", marginBottom: "1rem" }}>
          <Input value={actor} onChange={(e) => setActor(e.target.value)} placeholder={t("audit.filterActor")} style={{ flex: 1, minWidth: 150 }} />
          <Input value={action} onChange={(e) => setAction(e.target.value)} placeholder={t("audit.filterAction")} style={{ flex: 1, minWidth: 150 }} dir="ltr" />
          <Input value={tenant} onChange={(e) => setTenant(e.target.value)} placeholder={t("audit.filterTenant")} style={{ flex: 1, minWidth: 150 }} />
          <Input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} style={{ width: "auto" }} aria-label={t("audit.filterFrom")} />
          <Input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} style={{ width: "auto" }} aria-label={t("audit.filterTo")} />
          <a className="btn btn-soft" href={csvHref} download>{t("audit.exportCsv")}</a>
        </div>

        {error ? <p className="muted">{t("common.loadError")}: {error}</p> : null}
        {entries === null ? (
          <Spinner />
        ) : entries.length === 0 ? (
          <p className="muted">{t("audit.empty")}</p>
        ) : (
          <>
            <table className="table">
              <thead><tr><th>{t("common.when")}</th><th>{t("common.actor")}</th><th>{t("common.action")}</th><th>{t("audit.colTenant")}</th><th>{t("audit.colDetail")}</th></tr></thead>
              <tbody>
                {entries.map((e) => (
                  <tr key={e.id}>
                    <td className="muted">{formatDateTime(e.created_at, locale)}</td>
                    <td>{e.actor}</td>
                    <td><Badge>{e.action}</Badge></td>
                    <td className="muted">{e.tenant ?? "—"}</td>
                    <td className="muted" style={{ fontSize: "0.8rem", overflowWrap: "anywhere" }}>
                      {Object.keys(e.detail).length ? JSON.stringify(e.detail) : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {cursor != null ? (
              <div className="center" style={{ marginTop: "1rem" }}>
                <button className="btn btn-soft" disabled={busy} onClick={() => void loadMore()}>
                  {busy ? <Spinner /> : t("audit.loadMore")}
                </button>
              </div>
            ) : null}
          </>
        )}
      </div>
    </DashboardShell>
  );
}
