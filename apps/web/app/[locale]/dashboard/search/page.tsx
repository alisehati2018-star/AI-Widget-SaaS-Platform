"use client";

import { useLocale, useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";
import { useApiErrorMessage } from "@/lib/errors";
import { authFetch } from "@/lib/auth";
import { formatNumber } from "@/lib/datetime";
import type { Locale } from "@/i18n/routing";
import { DashboardShell, useOwnerNav } from "@/components/shell";
import { Alert, Field, Input, Spinner } from "@/components/ui";

interface SearchHit { product_id?: string; title?: string; brand?: string; price?: number }
interface SearchTest {
  results?: SearchHit[];
  total?: number;
  degraded: boolean;
}

export default function SearchTuningPage() {
  const t = useTranslations("dashboard");
  const apiMsg = useApiErrorMessage();
  const locale = useLocale() as Locale;
  const nav = useOwnerNav();
  const [synonyms, setSynonyms] = useState("");
  const [zero, setZero] = useState<{ term: string; count: number }[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [loadFailed, setLoadFailed] = useState(false);
  const [saved, setSaved] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [query, setQuery] = useState("");
  const [testBusy, setTestBusy] = useState(false);
  const [test, setTest] = useState<SearchTest | null>(null);
  const [testError, setTestError] = useState<string | null>(null);

  // If the synonyms load fails we must NOT show an empty editor — saving it
  // would silently wipe the tenant's real synonym list.
  const loadSynonyms = useCallback(() => {
    setLoaded(false);
    setLoadFailed(false);
    authFetch<{ synonyms: string[] }>("/tenant/synonyms")
      .then((r) => {
        setSynonyms(r.synonyms.join("\n"));
        setLoaded(true);
      })
      .catch(() => setLoadFailed(true));
  }, []);

  useEffect(() => {
    loadSynonyms();
    authFetch<{ terms: { term: string; count: number }[] }>("/tenant/zero-results")
      .then((r) => setZero(r.terms))
      .catch(() => {});
  }, [loadSynonyms]);

  async function save() {
    setBusy(true);
    setSaved(false);
    setSaveError(null);
    try {
      const lines = synonyms.split("\n").map((l) => l.trim()).filter(Boolean);
      await authFetch("/tenant/synonyms", { body: { synonyms: lines } });
      setSaved(true);
    } catch (e) {
      setSaveError(apiMsg(e) ?? t("common.actionFailed"));
    } finally {
      setBusy(false);
    }
  }

  async function runTest(term?: string) {
    const q = (term ?? query).trim();
    if (!q) return;
    setTestBusy(true);
    setTest(null);
    setTestError(null);
    try {
      const r = await authFetch<SearchTest>("/tenant/search-test", { body: { query: q } });
      setTest(r);
    } catch (e) {
      setTestError(apiMsg(e) ?? t("search.testFailed"));
    } finally {
      setTestBusy(false);
    }
  }

  return (
    <DashboardShell title={t("nav.search")} nav={nav}>
      <p style={{ marginTop: "-1rem" }}>{t("search.intro")}</p>

      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <h3>{t("search.testTitle")}</h3>
        <p className="hint">{t("search.testHint")}</p>
        {testError ? <Alert kind="error">{testError}</Alert> : null}
        <div className="row" style={{ flexWrap: "wrap", gap: ".6rem" }}>
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") void runTest(); }}
            placeholder={t("search.testPlaceholder")}
            style={{ flex: 1, minWidth: 240 }}
          />
          <button className="btn btn-primary" disabled={testBusy || !query.trim()} onClick={() => void runTest()}>
            {testBusy ? <Spinner /> : t("search.testRun")}
          </button>
        </div>
        {test ? (
          test.degraded ? (
            <div className="alert alert-warning" role="status" style={{ marginTop: "1rem" }}>
              {t("search.testDegraded")}
            </div>
          ) : test.results?.length ? (
            <table className="table" style={{ marginTop: "1rem" }}>
              <thead><tr>
                <th>{t("search.colProduct")}</th><th>{t("search.colBrand")}</th><th>{t("search.colPrice")}</th>
              </tr></thead>
              <tbody>
                {test.results.map((h, i) => (
                  <tr key={h.product_id ?? i}>
                    <td>{h.title ?? h.product_id}</td>
                    <td className="muted">{h.brand ?? "—"}</td>
                    <td>{h.price != null ? formatNumber(h.price, locale) : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="muted" style={{ marginTop: "1rem" }}>{t("search.testNoResults")}</p>
          )
        ) : null}
      </div>

      <div className="dash-2col">
        <div className="card">
          <h3>{t("search.synonyms")}</h3>
          <p className="hint">{t("search.synonymsHint")}</p>
          {saved ? <Alert kind="success">{t("search.synonymsSaved")}</Alert> : null}
          {saveError ? <Alert kind="error">{saveError}</Alert> : null}
          {loadFailed ? (
            <>
              <p className="muted">{t("common.loadFailed")}</p>
              <button className="btn btn-soft" onClick={loadSynonyms}>{t("common.retry")}</button>
            </>
          ) : loaded ? (
            <>
              <textarea
                className="input"
                aria-label={t("search.synonyms")}
                style={{ minHeight: 180, fontFamily: "monospace" }}
                value={synonyms}
                onChange={(e) => setSynonyms(e.target.value)}
                placeholder={t("search.synonymsPlaceholder")}
              />
              <div style={{ marginTop: "1rem" }}>
                <button className="btn btn-primary" onClick={() => void save()} disabled={busy}>
                  {busy ? <Spinner /> : t("search.saveSynonyms")}
                </button>
              </div>
            </>
          ) : (
            <Spinner />
          )}
        </div>

        <div className="card">
          <h3>{t("search.zeroTitle")}</h3>
          <p className="hint">{t("search.zeroHint")}</p>
          {zero.length ? (
            <table className="table">
              <thead><tr><th>{t("common.query")}</th><th>{t("common.count")}</th><th></th></tr></thead>
              <tbody>
                {zero.map((z) => (
                  <tr key={z.term}>
                    <td>{z.term}</td>
                    <td>{formatNumber(z.count, locale)}</td>
                    <td>
                      <button
                        className="btn btn-ghost"
                        onClick={() => { setQuery(z.term); void runTest(z.term); }}
                      >
                        {t("search.zeroTryIt")}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="muted">{t("search.zeroEmpty")}</p>
          )}
        </div>
      </div>
    </DashboardShell>
  );
}
