"use client";

import { useEffect, useState } from "react";
import { authFetch } from "../../../lib/auth";
import { DashboardShell, OWNER_NAV } from "../../../components/shell";
import { Alert, Spinner } from "../../../components/ui";

export default function SearchTuningPage() {
  const [synonyms, setSynonyms] = useState("");
  const [zero, setZero] = useState<{ term: string; count: number }[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    authFetch<{ synonyms: string[] }>("/tenant/synonyms")
      .then((r) => setSynonyms(r.synonyms.join("\n")))
      .catch(() => {})
      .finally(() => setLoaded(true));
    authFetch<{ terms: { term: string; count: number }[] }>("/tenant/zero-results")
      .then((r) => setZero(r.terms))
      .catch(() => {});
  }, []);

  async function save() {
    setBusy(true);
    setSaved(false);
    try {
      const lines = synonyms.split("\n").map((l) => l.trim()).filter(Boolean);
      await authFetch("/tenant/synonyms", { body: { synonyms: lines } });
      setSaved(true);
    } finally {
      setBusy(false);
    }
  }

  return (
    <DashboardShell title="Search tuning" nav={OWNER_NAV}>
      <p style={{ marginTop: "-1rem" }}>Shape relevance with synonyms and learn what shoppers can&apos;t find.</p>

      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <h3>Synonyms</h3>
        <p className="hint">One rule per line — e.g. <code>laptop, notebook, لپ‌تاپ</code>. Applied to Persian search.</p>
        {saved ? <Alert kind="success">Synonyms saved.</Alert> : null}
        {loaded ? (
          <textarea
            className="input"
            style={{ minHeight: 180, fontFamily: "monospace" }}
            value={synonyms}
            onChange={(e) => setSynonyms(e.target.value)}
            placeholder={"mobile, cellphone, موبایل\ntv, television, تلویزیون"}
          />
        ) : (
          <Spinner />
        )}
        <div style={{ marginTop: "1rem" }}>
          <button className="btn btn-primary" onClick={() => void save()} disabled={busy}>
            {busy ? <Spinner /> : "Save synonyms"}
          </button>
        </div>
      </div>

      <div className="card">
        <h3>Zero-result searches</h3>
        <p className="hint">High-demand queries with no matches — add products or a synonym rule.</p>
        {zero.length ? (
          <table className="table">
            <thead><tr><th>Query</th><th>Count</th></tr></thead>
            <tbody>
              {zero.map((z) => (
                <tr key={z.term}><td>{z.term}</td><td>{z.count}</td></tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="muted">No zero-result data yet.</p>
        )}
      </div>
    </DashboardShell>
  );
}
