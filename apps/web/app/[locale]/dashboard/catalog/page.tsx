"use client";

import { useLocale, useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";
import { ApiError, type TenantProfile } from "@/lib/api";
import { authFetch } from "@/lib/auth";
import { formatDateTime, formatNumber } from "@/lib/datetime";
import type { Locale } from "@/i18n/routing";
import { DashboardShell, useOwnerNav } from "@/components/shell";
import { Alert, Badge, Field, Input, Spinner } from "@/components/ui";

interface SyncSource {
  source: string;
  high_watermark: string | null;
  last_run_at: string | null;
  last_status: string | null;
}
interface SyncStatus {
  sources: SyncSource[];
  docs_indexed: number | null;
  degraded: boolean;
}

export default function CatalogPage() {
  const t = useTranslations("dashboard");
  const locale = useLocale() as Locale;
  const nav = useOwnerNav();
  const [profile, setProfile] = useState<TenantProfile | null>(null);
  const [profileFailed, setProfileFailed] = useState(false);
  const [platform, setPlatform] = useState("woocommerce");
  const [storeUrl, setStoreUrl] = useState("");
  const [saved, setSaved] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [sync, setSync] = useState<SyncStatus | null>(null);
  const [syncFailed, setSyncFailed] = useState(false);
  const [syncBusy, setSyncBusy] = useState(false);
  const [syncNote, setSyncNote] = useState<string | null>(null);
  const [syncError, setSyncError] = useState<string | null>(null);

  const loadSync = useCallback(() => {
    setSyncFailed(false);
    authFetch<SyncStatus>("/tenant/sync-status")
      .then(setSync)
      .catch(() => {
        setSync(null);
        setSyncFailed(true);
      });
  }, []);

  const loadProfile = useCallback(() => {
    setProfileFailed(false);
    authFetch<TenantProfile>("/tenant/profile")
      .then((p) => {
        setProfile(p);
        setPlatform(p.settings.platform ?? "woocommerce");
        setStoreUrl(p.settings.store_url ?? "");
      })
      .catch(() => setProfileFailed(true));
  }, []);

  useEffect(() => {
    loadProfile();
    loadSync();
  }, [loadProfile, loadSync]);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setSaved(false);
    setSaveError(null);
    try {
      await authFetch("/tenant/settings", { method: "PATCH", body: { platform, store_url: storeUrl } });
      setSaved(true);
    } catch (err) {
      setSaveError(err instanceof ApiError ? err.message : t("common.actionFailed"));
    } finally {
      setBusy(false);
    }
  }

  async function syncNow() {
    setSyncBusy(true);
    setSyncNote(null);
    setSyncError(null);
    try {
      const source = platform === "custom" ? "rest" : platform;
      await authFetch("/tenant/sync/trigger", { body: { source } });
      setSyncNote(t("catalog.syncQueued"));
      loadSync();
    } catch (e) {
      setSyncError(e instanceof ApiError ? e.message : t("catalog.syncFailed"));
    } finally {
      setSyncBusy(false);
    }
  }

  const connected = Boolean(profile?.settings.store_url);
  const platformLabel = platform === "custom" ? t("catalog.platformCustom") : platform;
  const statusTone = (s: string | null) =>
    s === "ok" ? "success" : s === "queued" ? "warning" : undefined;

  return (
    <DashboardShell title={t("nav.catalog")} nav={nav}>
      <p style={{ marginTop: "-1rem" }}>{t("catalog.intro")}</p>

      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <div className="row-between" style={{ flexWrap: "wrap", gap: ".6rem" }}>
          <h3 style={{ margin: 0 }}>{t("catalog.syncTitle")}</h3>
          <button className="btn btn-primary" disabled={syncBusy} onClick={() => void syncNow()}>
            {syncBusy ? <Spinner /> : t("catalog.syncNow")}
          </button>
        </div>
        {syncNote ? <Alert kind="success">{syncNote}</Alert> : null}
        {syncError ? <Alert kind="error">{syncError}</Alert> : null}
        {syncFailed ? (
          <div className="alert alert-warning" role="status">
            {t("common.loadFailed")}{" "}
            <button className="btn btn-soft" onClick={loadSync} style={{ marginInlineStart: ".5rem" }}>
              {t("common.retry")}
            </button>
          </div>
        ) : null}
        <div className="stat-grid" style={{ margin: "1rem 0" }}>
          <div className="stat">
            <span className="stat-label">{t("catalog.docsIndexed")}</span>
            <span className="stat-value">
              {sync == null ? (syncFailed ? "—" : <Spinner />) : sync.docs_indexed != null
                ? formatNumber(sync.docs_indexed, locale)
                : <Badge tone="warning">{t("catalog.docsUnavailable")}</Badge>}
            </span>
          </div>
          <div className="stat">
            <span className="stat-label">{t("catalog.lastSync")}</span>
            <span className="stat-value" style={{ fontSize: "1rem" }}>
              {sync?.sources.length
                ? formatDateTime(sync.sources[0].last_run_at, locale)
                : "—"}
            </span>
          </div>
        </div>
        {sync?.degraded ? (
          <div className="alert alert-warning" role="status">{t("catalog.esDegraded")}</div>
        ) : null}
        {sync?.sources.length ? (
          <table className="table">
            <thead><tr>
              <th>{t("catalog.colSource")}</th><th>{t("catalog.colLastRun")}</th>
              <th>{t("catalog.colStatus")}</th>
            </tr></thead>
            <tbody>
              {sync.sources.map((s) => (
                <tr key={s.source}>
                  <td>{s.source}</td>
                  <td className="muted">{formatDateTime(s.last_run_at, locale)}</td>
                  <td><Badge tone={statusTone(s.last_status)}>{s.last_status ?? "—"}</Badge></td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="muted">{t("catalog.noSyncYet")}</p>
        )}
      </div>

      <div className="dash-2col">
        <div className="card">
          <div className="row-between">
            <h3 style={{ margin: 0 }}>{t("catalog.connection")}</h3>
            <Badge tone={connected ? "success" : "warning"}>
              {connected ? t("catalog.connected") : t("catalog.notConnected")}
            </Badge>
          </div>
          {saved ? <Alert kind="success">{t("common.saved")}</Alert> : null}
          {saveError ? <Alert kind="error">{saveError}</Alert> : null}
          {profileFailed && !profile ? (
            // Don't render the form over unknown state — saving defaults here
            // would silently overwrite the store's real connection settings.
            <>
              <p className="muted">{t("common.loadFailed")}</p>
              <button className="btn btn-soft" onClick={loadProfile}>{t("common.retry")}</button>
            </>
          ) : !profile ? (
            <Spinner />
          ) : (
            <form onSubmit={save}>
              <Field label={t("catalog.platform")}>
                <select className="input" aria-label={t("catalog.platform")} value={platform} onChange={(e) => setPlatform(e.target.value)}>
                  <option value="woocommerce">WooCommerce</option>
                  <option value="opencart">OpenCart</option>
                  <option value="custom">{t("catalog.platformCustom")}</option>
                </select>
              </Field>
              <Field label={t("catalog.storeUrl")} hint={t("catalog.storeUrlHint")}>
                <Input value={storeUrl} onChange={(e) => setStoreUrl(e.target.value)} placeholder="https://shop.example.com" dir="ltr" />
              </Field>
              <button className="btn btn-primary" disabled={busy}>
                {busy ? <Spinner /> : t("catalog.saveConnection")}
              </button>
            </form>
          )}
        </div>

        <div className="card">
          <h3>{t("catalog.howTitle")}</h3>
          <ol className="muted" style={{ paddingInlineStart: "1.2rem", lineHeight: 2 }}>
            <li>{t("catalog.howStep1", { platform: platformLabel })}</li>
            <li>{t("catalog.howStep2")}</li>
            <li>{t("catalog.howStep3")}</li>
          </ol>
          <p className="hint">{t("catalog.resyncHint")}</p>
        </div>
      </div>
    </DashboardShell>
  );
}
