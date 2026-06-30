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

export default function KnowledgePage() {
  const t = useTranslations("dashboard");
  const tc = useTranslations("common");
  const tErrors = useTranslations("errors");
  const locale = useLocale() as Locale;
  const nav = useOwnerNav();
  const [articles, setArticles] = useState<Article[] | null>(null);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState<Article | null>(null);
  const [note, setNote] = useState<string | null>(null);

  const load = useCallback(() => {
    authFetch<{ articles: Article[] }>("/tenant/kb").then((r) => setArticles(r.articles)).catch(() => setArticles([]));
  }, []);
  useEffect(() => load(), [load]);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await authFetch("/tenant/kb", { body: { title, body } });
      setTitle("");
      setBody("");
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : tErrors("saveFailed"));
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: string) {
    await authFetch(`/tenant/kb/${id}`, { method: "DELETE" }).catch(() => {});
    load();
  }

  async function saveEdit() {
    if (!editing) return;
    setNote(null);
    await authFetch(`/tenant/kb/${editing.id}`, {
      method: "PATCH",
      body: { title: editing.title, body: editing.body, published: editing.published },
    }).catch(() => {});
    setEditing(null);
    setNote(t("knowledge.updated"));
    load();
  }

  return (
    <DashboardShell title={t("nav.knowledge")} nav={nav}>
      <p style={{ marginTop: "-1rem" }}>{t("knowledge.intro")}</p>

      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <h3>{t("knowledge.addTitle")}</h3>
        {error ? <Alert kind="error">{error}</Alert> : null}
        <form onSubmit={create}>
          <Field label={t("knowledge.titleLabel")}>
            <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder={t("knowledge.titlePlaceholder")} required />
          </Field>
          <Field label={t("knowledge.bodyLabel")}>
            <textarea className="input" style={{ minHeight: 120 }} value={body} onChange={(e) => setBody(e.target.value)} placeholder={t("knowledge.bodyPlaceholder")} required />
          </Field>
          <button className="btn btn-primary" disabled={busy}>
            {busy ? <Spinner /> : t("knowledge.addArticle")}
          </button>
        </form>
      </div>

      {editing ? (
        <div className="card" style={{ marginBottom: "1.5rem" }}>
          <h3>{t("knowledge.editTitle")}</h3>
          <Field label={t("knowledge.titleLabel")}>
            <Input value={editing.title} onChange={(e) => setEditing({ ...editing, title: e.target.value })} />
          </Field>
          <Field label={t("knowledge.bodyLabel")}>
            <textarea className="input" style={{ minHeight: 120 }} value={editing.body} onChange={(e) => setEditing({ ...editing, body: e.target.value })} />
          </Field>
          <div className="row" style={{ gap: ".5rem", flexWrap: "wrap" }}>
            <button className="btn btn-primary" onClick={() => void saveEdit()}>{tc("actions.save")}</button>
            <button className="btn btn-soft" onClick={() => setEditing({ ...editing, published: !editing.published })}>
              {editing.published ? t("knowledge.unpublish") : t("knowledge.publish")}
            </button>
            <button className="btn btn-ghost" onClick={() => setEditing(null)}>{tc("actions.cancel")}</button>
          </div>
        </div>
      ) : null}

      <div className="card">
        <h3>{t("knowledge.articles")}</h3>
        {note ? <Alert kind="success">{note}</Alert> : null}
        {articles === null ? (
          <Spinner />
        ) : articles.length === 0 ? (
          <p className="muted">{t("knowledge.empty")}</p>
        ) : (
          <table className="table">
            <thead><tr><th>{t("knowledge.colTitle")}</th><th>{t("common.status")}</th><th>{t("knowledge.colUpdated")}</th><th></th></tr></thead>
            <tbody>
              {articles.map((a) => (
                <tr key={a.id}>
                  <td>{a.title}</td>
                  <td>{a.published ? <Badge tone="success">{t("knowledge.published")}</Badge> : <Badge>{t("common.draft")}</Badge>}</td>
                  <td className="muted">{formatDate(a.updated_at, locale)}</td>
                  <td>
                    <div className="row" style={{ gap: ".3rem", flexWrap: "wrap" }}>
                      <button className="btn btn-ghost" onClick={() => { setNote(null); setEditing({ ...a }); }}>{tc("actions.edit")}</button>
                      <button className="btn btn-danger" onClick={() => void remove(a.id)}>{tc("actions.delete")}</button>
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
