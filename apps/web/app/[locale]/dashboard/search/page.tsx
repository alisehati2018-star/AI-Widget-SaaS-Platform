"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { authFetch } from "@/lib/auth";
import { formatNumber } from "@/lib/datetime";
import type { Locale } from "@/i18n/routing";
import { DashboardShell, useOwnerNav } from "@/components/shell";
import { Alert, Spinner } from "@/components/ui";

export default function SearchTuningPage() {
  const t = useTranslations("dashboard");
  const locale = useLocale() as Locale;
  const nav = useOwnerNav();
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
    <DashboardShell title={t("nav.search")} nav={nav}>
      <p style={{ marginTop: "-1rem" }}>{t("search.intro")}</p>

      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <h3>{t("search.synonyms")}</h3>
        <p className="hint">{t("search.synonymsHint")}</p>
        {saved ? <Alert kind="success">{t("search.synonymsSaved")}</Alert> : null}
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
            {busy ? <Spinner /> : t("search.saveSynonyms")}
          </button>
        </div>
      </div>

      <div className="card">
        <h3>{t("search.zeroTitle")}</h3>
        <p className="hint">{t("search.zeroHint")}</p>
        {zero.length ? (
          <table className="table">
            <thead><tr><th>{t("common.query")}</th><th>{t("common.count")}</th></tr></thead>
            <tbody>
              {zero.map((z) => (
                <tr key={z.term}><td>{z.term}</td><td>{formatNumber(z.count, locale)}</td></tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="muted">{t("search.zeroEmpty")}</p>
        )}
      </div>
    </DashboardShell>
  );
}
