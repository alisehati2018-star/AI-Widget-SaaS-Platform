"use client";

import { useCallback, useEffect, useState } from "react";
import { ApiError } from "../../../lib/api";
import { authFetch } from "../../../lib/auth";
import { DashboardShell, OWNER_NAV } from "../../../components/shell";
import { Alert, Badge, Field, Input, Spinner } from "../../../components/ui";

interface Article {
  id: string;
  title: string;
  body: string;
  published: boolean;
  updated_at: string | null;
}

export default function KnowledgePage() {
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
      setError(err instanceof ApiError ? err.message : "Could not save.");
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: string) {
    await authFetch(`/tenant/kb/${id}`, { method: "DELETE" }).catch(() => {});
    load();
  }

  return (
    <DashboardShell title="Knowledge base" nav={OWNER_NAV}>
      <p style={{ marginTop: "-1rem" }}>
        FAQ &amp; policy articles the assistant can ground answers on — alongside your catalogue.
      </p>

      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <h3>Add an article</h3>
        {error ? <Alert kind="error">{error}</Alert> : null}
        <form onSubmit={create}>
          <Field label="Title">
            <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Returns & refunds" required />
          </Field>
          <Field label="Body">
            <textarea className="input" style={{ minHeight: 120 }} value={body} onChange={(e) => setBody(e.target.value)} placeholder="We accept returns within 30 days…" required />
          </Field>
          <button className="btn btn-primary" disabled={busy}>{busy ? <Spinner /> : "Add article"}</button>
        </form>
      </div>

      <div className="card">
        <h3>Articles</h3>
        {articles === null ? (
          <Spinner />
        ) : articles.length === 0 ? (
          <p className="muted">No articles yet.</p>
        ) : (
          <table className="table">
            <thead><tr><th>Title</th><th>Status</th><th>Updated</th><th></th></tr></thead>
            <tbody>
              {articles.map((a) => (
                <tr key={a.id}>
                  <td>{a.title}</td>
                  <td>{a.published ? <Badge tone="success">published</Badge> : <Badge>draft</Badge>}</td>
                  <td className="muted">{a.updated_at?.slice(0, 10) ?? "—"}</td>
                  <td><button className="btn btn-danger" onClick={() => void remove(a.id)}>Delete</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </DashboardShell>
  );
}
