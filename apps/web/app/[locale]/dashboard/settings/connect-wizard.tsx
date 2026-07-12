"use client";

import { useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";
import { type TenantProfile } from "@/lib/api";
import { useApiErrorMessage } from "@/lib/errors";
import { authFetch } from "@/lib/auth";
import { Link } from "@/i18n/navigation";
import { Alert, Badge, Field, Input, Spinner } from "@/components/ui";

interface KeyRow { scope: string; revoked?: boolean }
interface SyncStatus {
  sources: { source: string; last_status: string | null }[];
  docs_indexed: number | null;
  degraded: boolean;
}

/** Guided OpenCart/WooCommerce connection wizard. Each step reflects REAL
 *  state (saved settings, issued sync key, recorded sync runs) and ticks
 *  itself off as the store completes it. */
export function ConnectWizard() {
  const t = useTranslations("dashboard");
  const apiMsg = useApiErrorMessage();
  const [platform, setPlatform] = useState("opencart");
  const [storeUrl, setStoreUrl] = useState("");
  const [savedUrl, setSavedUrl] = useState("");
  const [wooCk, setWooCk] = useState("");
  const [wooCs, setWooCs] = useState("");
  const [ocToken, setOcToken] = useState("");
  const [hasSyncKey, setHasSyncKey] = useState(false);
  const [sync, setSync] = useState<SyncStatus | null>(null);
  const [busy, setBusy] = useState(false);
  const [checking, setChecking] = useState(false);
  const [note, setNote] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [profileFailed, setProfileFailed] = useState(false);
  const reload = useCallback(() => {
    setProfileFailed(false);
    authFetch<TenantProfile>("/tenant/profile")
      .then((p) => {
        setPlatform(p.settings.platform ?? "opencart");
        setStoreUrl(p.settings.store_url ?? "");
        setSavedUrl(p.settings.store_url ?? "");
        setWooCk(p.settings.woo_consumer_key ?? "");
        setWooCs(p.settings.woo_consumer_secret ?? "");
        setOcToken(p.settings.oc_export_token ?? "");
      })
      .catch(() => setProfileFailed(true));
    authFetch<{ keys: KeyRow[] }>("/tenant/keys")
      .then((r) => setHasSyncKey(r.keys.some((k) => k.scope === "sync" && !k.revoked)))
      .catch(() => setHasSyncKey(false));
    authFetch<SyncStatus>("/tenant/sync-status").then(setSync).catch(() => setSync(null));
  }, []);
  useEffect(() => reload(), [reload]);

  async function saveStep1(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setNote(null);
    setError(null);
    try {
      await authFetch("/tenant/settings", {
        method: "PATCH",
        body: {
          platform,
          store_url: storeUrl.trim(),
          woo_consumer_key: wooCk.trim(),
          woo_consumer_secret: wooCs.trim(),
          oc_export_token: ocToken.trim(),
        },
      });
      setSavedUrl(storeUrl.trim());
      setNote(t("connect.step1Saved"));
    } catch (err) {
      setError(apiMsg(err) ?? t("common.actionFailed"));
    } finally {
      setBusy(false);
    }
  }

  async function verify() {
    setChecking(true);
    setNote(null);
    setError(null);
    try {
      const source = platform === "custom" ? "rest" : platform;
      await authFetch("/tenant/sync/trigger", { body: { source } });
      const s = await authFetch<SyncStatus>("/tenant/sync-status");
      setSync(s);
      setNote(t("connect.verifyQueued"));
    } catch {
      setError(t("connect.verifyFailed"));
    } finally {
      setChecking(false);
    }
  }

  const step1Done = Boolean(savedUrl);
  const step2Done = hasSyncKey;
  const step3Done = Boolean(
    (sync?.docs_indexed ?? 0) > 0 || sync?.sources.some((s) => s.last_status === "ok"),
  );

  const stepBadge = (done: boolean, n: number) =>
    done ? <Badge tone="success">✓</Badge> : <Badge>{n}</Badge>;

  return (
    <div className="card" style={{ marginBottom: "1.5rem" }}>
      <h3>{t("connect.title")}</h3>
      <p className="hint">{t("connect.hint")}</p>
      {note ? <Alert kind="success">{note}</Alert> : null}
      {error ? <Alert kind="error">{error}</Alert> : null}
      {profileFailed ? (
        <Alert kind="error">
          {t("common.loadFailed")}{" "}
          <button className="btn btn-soft" onClick={reload} style={{ marginInlineStart: ".5rem" }}>
            {t("common.retry")}
          </button>
        </Alert>
      ) : null}

      <div className="row" style={{ gap: ".6rem", alignItems: "flex-start", flexWrap: "wrap" }}>
        <div style={{ flex: 1, minWidth: 260 }}>
          <div className="row" style={{ gap: ".5rem", marginBottom: ".5rem" }}>
            {stepBadge(step1Done, 1)}
            <strong>{t("connect.step1Title")}</strong>
          </div>
          <form onSubmit={saveStep1}>
            <Field label={t("catalog.platform")}>
              <select className="input" aria-label={t("catalog.platform")} value={platform} onChange={(e) => setPlatform(e.target.value)}>
                <option value="opencart">OpenCart</option>
                <option value="woocommerce">WooCommerce</option>
                <option value="custom">{t("catalog.platformCustom")}</option>
              </select>
            </Field>
            <Field label={t("catalog.storeUrl")}>
              <Input dir="ltr" value={storeUrl} onChange={(e) => setStoreUrl(e.target.value)} placeholder="https://shop.example.com" />
            </Field>
            {platform === "woocommerce" ? (
              <>
                <Field label={t("connect.wooCk")}>
                  <Input dir="ltr" value={wooCk} onChange={(e) => setWooCk(e.target.value)} placeholder="ck_..." />
                </Field>
                <Field label={t("connect.wooCs")}>
                  <Input dir="ltr" type="password" value={wooCs} onChange={(e) => setWooCs(e.target.value)} placeholder="cs_..." />
                </Field>
                <p className="muted" style={{ fontSize: ".85rem" }}>{t("connect.pullHintWoo")}</p>
              </>
            ) : null}
            {platform === "opencart" ? (
              <>
                <Field label={t("connect.ocToken")}>
                  <Input dir="ltr" value={ocToken} onChange={(e) => setOcToken(e.target.value)} />
                </Field>
                <p className="muted" style={{ fontSize: ".85rem" }}>{t("connect.pullHintOc")}</p>
              </>
            ) : null}
            {/* Saving over a failed load would overwrite real credentials with blanks. */}
            <button className="btn btn-primary" disabled={busy || profileFailed || !storeUrl.trim()}>
              {busy ? <Spinner /> : t("connect.step1Save")}
            </button>
          </form>
        </div>

        <div style={{ flex: 1, minWidth: 260 }}>
          <div className="row" style={{ gap: ".5rem", marginBottom: ".5rem" }}>
            {stepBadge(step2Done, 2)}
            <strong>{t("connect.step2Title")}</strong>
          </div>
          <p className="muted" style={{ fontSize: ".9rem" }}>
            {platform === "woocommerce" ? t("connect.step2Woo") : t("connect.step2Opencart")}
          </p>
          <p className="muted" style={{ fontSize: ".9rem" }}>{t("connect.step2Key")}</p>
          {step2Done ? (
            <Badge tone="success">{t("connect.step2KeyReady")}</Badge>
          ) : (
            <Link className="btn btn-soft" href="/dashboard/keys">{t("connect.step2KeyCta")}</Link>
          )}
        </div>

        <div style={{ flex: 1, minWidth: 260 }}>
          <div className="row" style={{ gap: ".5rem", marginBottom: ".5rem" }}>
            {stepBadge(step3Done, 3)}
            <strong>{t("connect.step3Title")}</strong>
          </div>
          <p className="muted" style={{ fontSize: ".9rem" }}>{t("connect.step3Body")}</p>
          <div className="row" style={{ gap: ".5rem", flexWrap: "wrap" }}>
            <button className="btn btn-primary" disabled={checking} onClick={() => void verify()}>
              {checking ? <Spinner /> : t("connect.step3Verify")}
            </button>
            {step3Done ? <Badge tone="success">{t("connect.step3Done")}</Badge> : null}
          </div>
        </div>
      </div>
    </div>
  );
}
