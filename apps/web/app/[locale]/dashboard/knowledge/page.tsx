"use client";

import { useLocale, useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";
import { ApiError } from "@/lib/api";
import { authFetch } from "@/lib/auth";
import { formatDate } from "@/lib/datetime";
import type { Locale } from "@/i18n/routing";
import { DashboardShell, useOwnerNav } from "@/components/shell";
import { Alert, Badge, Field, Input, Spinner } from "@/components/ui";

interface Article {
  id: string;
  title: string;
  body: string;
  published: boolean;
  updated_at: string | null;
}

const EMPTY_DRAFT = { title: "", body: "" };

export default function KnowledgePage() {
  const t = useTranslations("dashboard");
  const tc = useTranslations("common");
  const tErrors = useTranslations("errors");
  const locale = useLocale() as Locale;
  const nav = useOwnerNav();
  const [articles, setArticles] = useState<Article[] | null>(null);
  const [editing, setEditing] = useState<Article | null>(null);
  const [draft, setDraft] = useState(EMPTY_DRAFT);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState<string | null>(null);

  const load = useCallback(() => {
    authFetch<{ articles: Article[] }>("/tenant/kb").then((r) => setArticles(r.articles)).catch(() => setArticles([]));
  }, []);
  useEffect(() => load(), [load]);

  function startCreate() {
    setError(null);
    setNote(null);
    setEditing(null);
    setDraft(EMPTY_DRAFT);
  }

  function startEdit(a: Article) {
    setError(null);
    setNote(null);
    setEditing(a);
  }

  async function create(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await authFetch("/tenant/kb", { body: { title: draft.title, body: draft.body } });
      setDraft(EMPTY_DRAFT);
      setNote(t("knowledge.updated"));
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : tErrors("saveFailed"));
    } finally {
      setBusy(false);
    }
  }

  async function saveEdit(e: React.FormEvent) {
    e.preventDefault();
    if (!editing) return;
    setError(null);
    setBusy(true);
    try {
      await authFetch(`/tenant/kb/${editing.id}`, {
        method: "PATCH",
        body: { title: editing.title, body: editing.body, published: editing.published },
      });
      setNote(t("knowledge.updated"));
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : tErrors("saveFailed"));
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: string) {
    await authFetch(`/tenant/kb/${id}`, { method: "DELETE" }).catch(() => {});
    if (editing?.id === id) setEditing(null);
    load();
  }

  return (
    <DashboardShell title={t("nav.knowledge")} nav={nav}>
      <p style={{ marginTop: "-1rem" }}>{t("knowledge.intro")}</p>
      {note ? <Alert kind="success">{note}</Alert> : null}

      <div className="dash-2col">
        <div className="card">
          <div className="row-between" style={{ marginBottom: "1rem" }}>
            <h3 style={{ margin: 0 }}>{t("knowledge.articles")}</h3>
            <button className="btn btn-soft" onClick={startCreate}>{t("knowledge.addArticle")}</button>
          </div>
          {articles === null ? (
            <Spinner />
          ) : articles.length === 0 ? (
            <p className="muted">{t("knowledge.empty")}</p>
          ) : (
            <table className="table">
              <thead><tr><th>{t("knowledge.colTitle")}</th><th>{t("common.status")}</th><th>{t("knowledge.colUpdated")}</th><th></th></tr></thead>
              <tbody>
                {articles.map((a) => (
                  <tr key={a.id} className={editing?.id === a.id ? "row-selected" : undefined}>
                    <td>{a.title}</td>
                    <td>{a.published ? <Badge tone="success">{t("knowledge.published")}</Badge> : <Badge>{t("common.draft")}</Badge>}</td>
                    <td className="muted">{formatDate(a.updated_at, locale)}</td>
                    <td>
                      <div className="row" style={{ gap: ".3rem", flexWrap: "wrap" }}>
                        <button className="btn btn-ghost" onClick={() => startEdit(a)}>{tc("actions.edit")}</button>
                        <button className="btn btn-danger" onClick={() => void remove(a.id)}>{tc("actions.delete")}</button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <div className="card" style={{ position: "sticky", top: "1.5rem" }}>
          {error ? <Alert kind="error">{error}</Alert> : null}
          {editing ? (
            <form onSubmit={saveEdit}>
              <h3>{t("knowledge.editTitle")}</h3>
              <Field label={t("knowledge.titleLabel")}>
                <Input value={editing.title} onChange={(e) => setEditing({ ...editing, title: e.target.value })} required />
              </Field>
              <Field label={t("knowledge.bodyLabel")}>
                <textarea className="input" style={{ minHeight: 180 }} value={editing.body} onChange={(e) => setEditing({ ...editing, body: e.target.value })} required />
              </Field>
              <div className="row" style={{ gap: ".5rem", flexWrap: "wrap" }}>
                <button className="btn btn-primary" disabled={busy}>{busy ? <Spinner /> : tc("actions.save")}</button>
                <button type="button" className="btn btn-soft" onClick={() => setEditing({ ...editing, published: !editing.published })}>
                  {editing.published ? t("knowledge.unpublish") : t("knowledge.publish")}
                </button>
                <button type="button" className="btn btn-ghost" onClick={() => setEditing(null)}>{tc("actions.cancel")}</button>
              </div>
            </form>
          ) : (
            <form onSubmit={create}>
              <h3>{t("knowledge.addTitle")}</h3>
              <Field label={t("knowledge.titleLabel")}>
                <Input value={draft.title} onChange={(e) => setDraft({ ...draft, title: e.target.value })} placeholder={t("knowledge.titlePlaceholder")} required />
              </Field>
              <Field label={t("knowledge.bodyLabel")}>
                <textarea className="input" style={{ minHeight: 180 }} value={draft.body} onChange={(e) => setDraft({ ...draft, body: e.target.value })} placeholder={t("knowledge.bodyPlaceholder")} required />
              </Field>
              <button className="btn btn-primary" disabled={busy}>
                {busy ? <Spinner /> : t("knowledge.addArticle")}
              </button>
            </form>
          )}
        </div>
      </div>
    </DashboardShell>
  );
}
