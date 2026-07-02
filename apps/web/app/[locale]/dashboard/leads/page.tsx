"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import type { Lead } from "@/lib/api";
import { authFetch } from "@/lib/auth";
import { formatDate, formatNumber } from "@/lib/datetime";
import type { Locale } from "@/i18n/routing";
import { DashboardShell, useOwnerNav } from "@/components/shell";
import { Alert, Badge, Spinner, Stat } from "@/components/ui";

const STATUSES = ["new", "contacted", "qualified", "won", "lost"] as const;

export default function LeadsPage() {
  const t = useTranslations("dashboard");
  const locale = useLocale() as Locale;
  const nav = useOwnerNav();
  const [leads, setLeads] = useState<Lead[] | null>(null);
  const [filter, setFilter] = useState<string>("");
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [bulkStatus, setBulkStatus] = useState<string>("contacted");
  const [bulkBusy, setBulkBusy] = useState(false);
  const [note, setNote] = useState<string | null>(null);

  useEffect(() => {
    authFetch<{ leads: Lead[] }>("/tenant/leads")
      .then((r) => setLeads(r.leads))
      .catch(() => setLeads([]));
  }, []);

  async function setStatus(lead: Lead, status: string) {
    if (lead.id == null) return;
    setLeads((rows) => rows?.map((r) => (r.id === lead.id ? { ...r, status } : r)) ?? rows);
    await authFetch(`/tenant/leads/${lead.id}`, { body: { status } }).catch(() => {});
  }

  function toggle(id: number) {
    setSelected((cur) => {
      const next = new Set(cur);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function applyBulk() {
    if (!selected.size) return;
    setBulkBusy(true);
    setNote(null);
    try {
      // The single-lead endpoint is the mutation unit; bulk fans out over it.
      await Promise.all(
        [...selected].map((id) => authFetch(`/tenant/leads/${id}`, { body: { status: bulkStatus } })),
      );
      setLeads((rows) =>
        rows?.map((r) => (r.id != null && selected.has(r.id) ? { ...r, status: bulkStatus } : r)) ?? rows,
      );
      setNote(t("leads.bulkApplied", { n: formatNumber(selected.size, locale) }));
      setSelected(new Set());
    } finally {
      setBulkBusy(false);
    }
  }

  const statusLabels: Record<string, string> = {
    new: t("leads.statusNew"),
    contacted: t("leads.statusContacted"),
    qualified: t("leads.statusQualified"),
    won: t("leads.statusWon"),
    lost: t("leads.statusLost"),
  };
  const statusLabel = (s: string | undefined) => statusLabels[s ?? "new"] ?? statusLabels.new;

  async function exportData() {
    const data = await authFetch<unknown>("/tenant/export").catch(() => null);
    if (!data) return;
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "vitrin-leads.json";
    a.click();
    URL.revokeObjectURL(url);
  }

  const visible = (leads ?? []).filter((l) => !filter || (l.status ?? "new") === filter);
  const selectableIds = visible.filter((l) => l.id != null).map((l) => l.id as number);
  const allSelected = selectableIds.length > 0 && selectableIds.every((id) => selected.has(id));
  const withIntent = leads?.filter((l) => l.has_intent).length ?? 0;
  const num = (v: number | undefined) => (v != null ? formatNumber(v, locale) : "—");
  const countFor = (s: string) => (leads ?? []).filter((l) => (l.status ?? "new") === s).length;

  return (
    <DashboardShell title={t("nav.leads")} nav={nav}>
      <p style={{ marginTop: "-1rem" }}>{t("leads.intro")}</p>

      <div className="stat-grid" style={{ marginBottom: "1.5rem" }}>
        <Stat label={t("leads.total")} value={num(leads?.length)} />
        <Stat label={t("leads.withIntent")} value={formatNumber(withIntent, locale)} />
        <Stat label={t("leads.fromChat")} value={num(leads?.filter((l) => l.source === "chat").length)} />
        <Stat label={t("leads.withEmail")} value={num(leads?.filter((l) => l.email).length)} />
      </div>

      <div className="card">
        <div className="row-between" style={{ marginBottom: "1rem", flexWrap: "wrap", gap: ".6rem" }}>
          <h3 style={{ margin: 0 }}>{t("leads.captured")}</h3>
          <button className="btn btn-ghost" onClick={() => void exportData()}>
            {t("leads.exportJson")}
          </button>
        </div>
        {note ? <Alert kind="success">{note}</Alert> : null}

        <div className="row" style={{ flexWrap: "wrap", gap: ".4rem", marginBottom: "1rem" }}>
          <button className={filter === "" ? "btn btn-primary" : "btn btn-soft"} onClick={() => setFilter("")}>
            {t("leads.filterAll")} ({num(leads?.length)})
          </button>
          {STATUSES.map((s) => (
            <button key={s} className={filter === s ? "btn btn-primary" : "btn btn-soft"} onClick={() => setFilter(s)}>
              {statusLabel(s)} ({formatNumber(countFor(s), locale)})
            </button>
          ))}
        </div>

        {selected.size ? (
          <div className="row" style={{ flexWrap: "wrap", gap: ".6rem", alignItems: "center", marginBottom: "1rem" }}>
            <span className="hint">{t("leads.bulkSelected", { n: formatNumber(selected.size, locale) })}</span>
            <select className="input" style={{ width: "auto" }} aria-label={t("leads.colStatus")} value={bulkStatus} onChange={(e) => setBulkStatus(e.target.value)}>
              {STATUSES.map((s) => <option key={s} value={s}>{statusLabel(s)}</option>)}
            </select>
            <button className="btn btn-primary" disabled={bulkBusy} onClick={() => void applyBulk()}>
              {bulkBusy ? <Spinner /> : t("leads.bulkApply")}
            </button>
            <button className="btn btn-ghost" onClick={() => setSelected(new Set())}>{t("leads.bulkClear")}</button>
          </div>
        ) : null}

        {leads === null ? (
          <Spinner />
        ) : visible.length === 0 ? (
          <p className="muted">{filter ? t("leads.noMatches") : t("leads.empty")}</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th style={{ width: 32 }}>
                  <input
                    type="checkbox"
                    aria-label={t("leads.bulkSelectAll")}
                    checked={allSelected}
                    onChange={() =>
                      setSelected(allSelected ? new Set() : new Set(selectableIds))
                    }
                  />
                </th>
                <th>{t("leads.colEmail")}</th><th>{t("leads.colPhone")}</th><th>{t("leads.colIntent")}</th>
                <th>{t("leads.colStatus")}</th><th>{t("leads.colSource")}</th><th>{t("common.when")}</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((l, i) => (
                <tr key={l.id ?? i}>
                  <td>
                    {l.id != null ? (
                      <input
                        type="checkbox"
                        aria-label={t("leads.bulkSelectRow")}
                        checked={selected.has(l.id)}
                        onChange={() => toggle(l.id as number)}
                      />
                    ) : null}
                  </td>
                  <td>{l.email ?? "—"}</td>
                  <td>{l.phone ?? "—"}</td>
                  <td>{l.has_intent ? <Badge tone="success">{t("common.yes")}</Badge> : <Badge>{t("common.no")}</Badge>}</td>
                  <td>
                    {l.id != null ? (
                      <select className="input" aria-label={t("leads.colStatus")} value={l.status ?? "new"} onChange={(e) => void setStatus(l, e.target.value)}>
                        {STATUSES.map((s) => <option key={s} value={s}>{statusLabel(s)}</option>)}
                      </select>
                    ) : <Badge>{statusLabel(l.status)}</Badge>}
                  </td>
                  <td>{l.source}</td>
                  <td className="muted">{formatDate(l.created_at, locale)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </DashboardShell>
  );
}
