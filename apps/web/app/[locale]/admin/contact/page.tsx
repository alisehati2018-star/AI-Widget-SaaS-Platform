"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { ApiError } from "@/lib/api";
import { adminFetch as authFetch } from "@/lib/auth";
import { formatDate, formatNumber } from "@/lib/datetime";
import { useAdminResource as useResource } from "@/lib/hooks/useResource";
import type { Locale } from "@/i18n/routing";
import { DashboardShell, useAdminNav } from "@/components/shell";
import { Alert, Badge, Field, Input, Spinner } from "@/components/ui";

interface ContactMessage {
  id: number;
  name: string;
  email: string;
  message: string;
  status: "new" | "read" | "resolved";
  admin_note: string | null;
  created_at: string | null;
  updated_at: string | null;
}
interface InboxPage {
  messages: ContactMessage[];
  total: number;
  counts: { all: number; new: number; read: number; resolved: number };
  limit: number;
  offset: number;
}

const PAGE = 20;
const STATUSES = ["", "new", "read", "resolved"] as const;

export default function AdminContact() {
  const t = useTranslations("admin");
  const locale = useLocale() as Locale;
  const nav = useAdminNav();

  const [q, setQ] = useState("");
  const [debouncedQ, setDebouncedQ] = useState("");
  const [status, setStatus] = useState<(typeof STATUSES)[number]>("");
  const [offset, setOffset] = useState(0);
  const [selected, setSelected] = useState<ContactMessage | null>(null);
  const [note, setNote] = useState("");
  const [flash, setFlash] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const id = setTimeout(() => { setDebouncedQ(q.trim()); setOffset(0); }, 300);
    return () => clearTimeout(id);
  }, [q]);

  const params = new URLSearchParams({ limit: String(PAGE), offset: String(offset) });
  if (debouncedQ) params.set("q", debouncedQ);
  if (status) params.set("status", status);
  const { data, error: loadError, loading, reload } = useResource<InboxPage>(`/admin/contact?${params.toString()}`);
  const messages = loading ? null : (data?.messages ?? []);
  const total = data?.total ?? 0;
  const counts = data?.counts;

  function open(m: ContactMessage) {
    setFlash(null); setError(null); setSelected(m); setNote(m.admin_note ?? "");
    // Opening a fresh message marks it read — the inbox convention.
    if (m.status === "new") void patch(m.id, { status: "read" }, false);
  }

  async function patch(id: number, body: Record<string, unknown>, showFlash = true) {
    setBusy(true);
    setError(null);
    try {
      await authFetch(`/admin/contact/${id}`, { method: "PATCH", body });
      if (showFlash) setFlash(t("contact.savedNote"));
      reload();
      if (selected?.id === id) {
        setSelected((cur) => (cur ? { ...cur, ...body } as ContactMessage : cur));
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("contact.saveFailed"));
    } finally {
      setBusy(false);
    }
  }

  const statusLabel = (s: string) =>
    s === "new" ? t("contact.statusNew") : s === "read" ? t("contact.statusRead") : t("contact.statusResolved");
  const chipLabel = (s: (typeof STATUSES)[number]) => (s === "" ? t("contact.filterAll") : statusLabel(s));
  const chipCount = (s: (typeof STATUSES)[number]) =>
    counts ? (s === "" ? counts.all : counts[s]) : 0;

  return (
    <DashboardShell title={t("contact.title")} nav={nav} requireAdmin loginHref="/admin/login">
      <p style={{ marginTop: "-1rem" }}>{t("contact.intro")}</p>
      {flash ? <Alert kind="success">{flash}</Alert> : null}
      {error ? <Alert kind="error">{error}</Alert> : null}

      <div className="dash-2col">
        <div className="card">
          <div className="row" style={{ flexWrap: "wrap", gap: ".6rem", marginBottom: "1rem" }}>
            {STATUSES.map((s) => (
              <button
                key={s || "all"}
                className={status === s ? "btn btn-primary" : "btn btn-soft"}
                onClick={() => { setStatus(s); setOffset(0); }}
              >
                {chipLabel(s)} ({formatNumber(chipCount(s), locale)})
              </button>
            ))}
          </div>
          <Input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder={t("contact.searchPlaceholder")}
            style={{ marginBottom: "1rem" }}
          />

          {loadError ? <p className="muted">{t("common.loadError")}: {loadError}</p> : null}
          {messages === null ? <Spinner /> : (
            <>
              <table className="table">
                <thead>
                  <tr>
                    <th>{t("contact.colFrom")}</th>
                    <th>{t("contact.colMessage")}</th>
                    <th>{t("contact.colStatus")}</th>
                    <th>{t("common.when")}</th>
                  </tr>
                </thead>
                <tbody>
                  {messages.map((m) => (
                    <tr
                      key={m.id}
                      className={selected?.id === m.id ? "row-selected" : undefined}
                      style={{ cursor: "pointer" }}
                      onClick={() => open(m)}
                    >
                      <td>
                        {m.name}
                        <br />
                        <span className="muted" dir="ltr">{m.email}</span>
                      </td>
                      <td className="muted">{m.message.length > 70 ? `${m.message.slice(0, 70)}…` : m.message}</td>
                      <td>
                        <Badge tone={m.status === "new" ? "warning" : m.status === "resolved" ? "success" : undefined}>
                          {statusLabel(m.status)}
                        </Badge>
                      </td>
                      <td className="muted">{m.created_at ? formatDate(m.created_at, locale) : "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {messages.length === 0 ? <p className="muted">{t("contact.empty")}</p> : null}
              <div className="row-between" style={{ marginTop: "1rem" }}>
                <span className="hint">
                  {t("contact.pageInfo", {
                    from: formatNumber(total === 0 ? 0 : offset + 1, locale),
                    to: formatNumber(Math.min(offset + PAGE, total), locale),
                    total: formatNumber(total, locale),
                  })}
                </span>
                <div className="row" style={{ gap: ".4rem" }}>
                  <button className="btn btn-soft" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE))}>
                    {t("contact.prev")}
                  </button>
                  <button className="btn btn-soft" disabled={offset + PAGE >= total} onClick={() => setOffset(offset + PAGE)}>
                    {t("contact.next")}
                  </button>
                </div>
              </div>
            </>
          )}
        </div>

        <div className="card" style={{ position: "sticky", top: "1.5rem" }}>
          {selected ? (
            <>
              <div className="row-between" style={{ flexWrap: "wrap", gap: ".6rem" }}>
                <h3 style={{ margin: 0 }}>{selected.name}</h3>
                <Badge tone={selected.status === "new" ? "warning" : selected.status === "resolved" ? "success" : undefined}>
                  {statusLabel(selected.status)}
                </Badge>
              </div>
              <p className="muted" dir="ltr" style={{ marginTop: ".35rem" }}>{selected.email}</p>
              <p style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{selected.message}</p>
              <p className="hint">
                {selected.created_at ? formatDate(selected.created_at, locale) : "—"}
              </p>

              <Field label={t("contact.noteLabel")} hint={t("contact.noteHint")}>
                <textarea
                  className="input"
                  rows={4}
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  placeholder={t("contact.notePlaceholder")}
                />
              </Field>
              <div className="row" style={{ flexWrap: "wrap", gap: ".5rem" }}>
                <button
                  className="btn btn-primary"
                  disabled={busy}
                  onClick={() => void patch(selected.id, { admin_note: note })}
                >
                  {busy ? <Spinner /> : t("contact.saveNote")}
                </button>
                {selected.status !== "resolved" ? (
                  <button
                    className="btn btn-soft"
                    disabled={busy}
                    onClick={() => void patch(selected.id, { status: "resolved" })}
                  >
                    {t("contact.markResolved")}
                  </button>
                ) : (
                  <button
                    className="btn btn-soft"
                    disabled={busy}
                    onClick={() => void patch(selected.id, { status: "read" })}
                  >
                    {t("contact.reopen")}
                  </button>
                )}
                <a className="btn btn-ghost" href={`mailto:${selected.email}`}>{t("contact.replyEmail")}</a>
              </div>
            </>
          ) : (
            <div className="state">
              <p>{t("contact.selectHint")}</p>
            </div>
          )}
        </div>
      </div>
    </DashboardShell>
  );
}
