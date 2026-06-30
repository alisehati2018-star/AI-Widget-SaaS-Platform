"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { authFetch } from "@/lib/auth";
import { DashboardShell, useAdminNav } from "@/components/shell";
import { Alert, Field, Input, Spinner } from "@/components/ui";

interface WidgetDefaults {
  primary_color: string;
  greeting: string;
  position: string;
  chat_enabled: boolean;
  search_enabled: boolean;
  platform_brand: boolean;
  max_results: number;
}

export default function AdminWidget() {
  const t = useTranslations("admin");
  const nav = useAdminNav();
  const [cfg, setCfg] = useState<WidgetDefaults | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    authFetch<{ defaults: WidgetDefaults }>("/admin/widget-defaults")
      .then((r) => setCfg(r.defaults))
      .catch(() => setCfg(null));
  }, []);

  async function save() {
    if (!cfg) return;
    await authFetch("/admin/widget-defaults", { body: cfg });
    setSaved(true);
  }

  function set<K extends keyof WidgetDefaults>(k: K, v: WidgetDefaults[K]) {
    setSaved(false);
    setCfg((c) => (c ? { ...c, [k]: v } : c));
  }

  if (!cfg) {
    return (
      <DashboardShell title={t("widget.title")} nav={nav} requireAdmin loginHref="/admin/login">
        <Spinner />
      </DashboardShell>
    );
  }

  return (
    <DashboardShell title={t("widget.title")} nav={nav} requireAdmin loginHref="/admin/login">
      <p style={{ marginTop: "-1rem" }}>{t("widget.intro")}</p>
      {saved ? <Alert kind="success">{t("widget.saved")}</Alert> : null}
      <div className="card" style={{ maxWidth: 520 }}>
        <Field label={t("widget.primaryColor")}>
          <Input type="color" value={cfg.primary_color} onChange={(e) => set("primary_color", e.target.value)} style={{ width: 64, padding: 4 }} />
        </Field>
        <Field label={t("widget.greeting")}>
          <Input value={cfg.greeting} onChange={(e) => set("greeting", e.target.value)} />
        </Field>
        <Field label={t("widget.position")}>
          <select className="input" value={cfg.position} onChange={(e) => set("position", e.target.value)}>
            <option value="bottom-right">{t("widget.positionBottomRight")}</option>
            <option value="bottom-left">{t("widget.positionBottomLeft")}</option>
          </select>
        </Field>
        <Field label={t("widget.maxResults")}>
          <Input type="number" min={1} max={50} value={cfg.max_results}
            onChange={(e) => set("max_results", parseInt(e.target.value, 10) || 1)} />
        </Field>
        <label className="row" style={{ gap: ".5rem", marginBottom: ".5rem" }}>
          <input type="checkbox" checked={cfg.chat_enabled} onChange={(e) => set("chat_enabled", e.target.checked)} />
          {t("widget.chatEnabled")}
        </label>
        <label className="row" style={{ gap: ".5rem", marginBottom: ".5rem" }}>
          <input type="checkbox" checked={cfg.search_enabled} onChange={(e) => set("search_enabled", e.target.checked)} />
          {t("widget.searchEnabled")}
        </label>
        <label className="row" style={{ gap: ".5rem", marginBottom: "1rem" }}>
          <input type="checkbox" checked={cfg.platform_brand} onChange={(e) => set("platform_brand", e.target.checked)} />
          {t("widget.platformBrand")}
        </label>
        <button className="btn btn-primary" onClick={() => void save()}>{t("widget.save")}</button>
      </div>
    </DashboardShell>
  );
}
