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

      <div className="card">
        <h3>{t("knowledge.articles")}</h3>
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
                  <td><button className="btn btn-danger" onClick={() => void remove(a.id)}>{tc("actions.delete")}</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </DashboardShell>
  );
}
