"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import type { TenantProfile } from "@/lib/api";
import { authFetch } from "@/lib/auth";
import { DashboardShell, useOwnerNav } from "@/components/shell";
import { Alert, Badge, Field, Input, Spinner } from "@/components/ui";

export default function CatalogPage() {
  const t = useTranslations("dashboard");
  const nav = useOwnerNav();
  const [profile, setProfile] = useState<TenantProfile | null>(null);
  const [platform, setPlatform] = useState("woocommerce");
  const [storeUrl, setStoreUrl] = useState("");
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    authFetch<TenantProfile>("/tenant/profile")
      .then((p) => {
        setProfile(p);
        setPlatform(p.settings.platform ?? "woocommerce");
        setStoreUrl(p.settings.store_url ?? "");
      })
      .catch(() => setProfile(null));
  }, []);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setSaved(false);
    try {
      await authFetch("/tenant/settings", { method: "PATCH", body: { platform, store_url: storeUrl } });
      setSaved(true);
    } finally {
      setBusy(false);
    }
  }

  const connected = Boolean(profile?.settings.store_url);
  const platformLabel = platform === "custom" ? t("catalog.platformCustom") : platform;

  return (
    <DashboardShell title={t("nav.catalog")} nav={nav}>
      <p style={{ marginTop: "-1rem" }}>{t("catalog.intro")}</p>

      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <div className="row-between">
          <h3 style={{ margin: 0 }}>{t("catalog.connection")}</h3>
          <Badge tone={connected ? "success" : "warning"}>
            {connected ? t("catalog.connected") : t("catalog.notConnected")}
          </Badge>
        </div>
        {saved ? <Alert kind="success">{t("common.saved")}</Alert> : null}
        <form onSubmit={save}>
          <Field label={t("catalog.platform")}>
            <select className="input" value={platform} onChange={(e) => setPlatform(e.target.value)}>
              <option value="woocommerce">WooCommerce</option>
              <option value="opencart">OpenCart</option>
              <option value="custom">{t("catalog.platformCustom")}</option>
            </select>
          </Field>
          <Field label={t("catalog.storeUrl")} hint={t("catalog.storeUrlHint")}>
            <Input value={storeUrl} onChange={(e) => setStoreUrl(e.target.value)} placeholder="https://shop.example.com" />
          </Field>
          <button className="btn btn-primary" disabled={busy}>
            {busy ? <Spinner /> : t("catalog.saveConnection")}
          </button>
        </form>
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
    </DashboardShell>
  );
}
