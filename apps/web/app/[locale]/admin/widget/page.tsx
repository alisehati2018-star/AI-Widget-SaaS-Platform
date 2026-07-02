"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { adminFetch as authFetch } from "@/lib/auth";
import { DashboardShell, useAdminNav } from "@/components/shell";
import { Icon } from "@/components/icons";
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

/** srcdoc that embeds the REAL production loader (`/widget/v1.js`) exactly the
 *  way a store would, inside a sandboxed iframe. The loader pulls the saved
 *  platform defaults from /v1/widget/config, so what renders here is the
 *  genuine widget — not a mock. */
function previewDoc(origin: string, cfg: WidgetDefaults): string {
  return `<!doctype html><html dir="rtl" lang="fa"><head><meta charset="utf-8">
<style>body{margin:0;min-height:320px;background:#f7f7f9;font-family:sans-serif}</style>
</head><body>
<script src="${origin}/api/widget/v1.js"
  data-acip-key="admin-preview"
  data-acip-base="${origin}/api"
  data-acip-color="${cfg.primary_color}"
  data-acip-position="${cfg.position}"
  data-acip-chat="${cfg.chat_enabled}"
  data-acip-search="${cfg.search_enabled}"
  data-acip-greeting="${cfg.greeting.replace(/"/g, "&quot;")}"
  async><\/script>
</body></html>`;
}

export default function AdminWidget() {
  const t = useTranslations("admin");
  const nav = useAdminNav();
  const [cfg, setCfg] = useState<WidgetDefaults | null>(null);
  const [saved, setSaved] = useState(false);
  const [previewNonce, setPreviewNonce] = useState(0);
  const [origin, setOrigin] = useState("");

  useEffect(() => {
    setOrigin(window.location.origin);
    authFetch<{ defaults: WidgetDefaults }>("/admin/widget-defaults")
      .then((r) => setCfg(r.defaults))
      .catch(() => setCfg(null));
  }, []);

  async function save() {
    if (!cfg) return;
    await authFetch("/admin/widget-defaults", { body: cfg });
    setSaved(true);
    // The real preview reads the SAVED config — refresh it after every save.
    setPreviewNonce((n) => n + 1);
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

      <div className="dash-2col">
        <div className="card">
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

        <div className="card-stack">
          <div className="card">
            <div className="row-between" style={{ flexWrap: "wrap", gap: ".6rem" }}>
              <h3 style={{ margin: 0 }}>{t("widget.livePreviewTitle")}</h3>
              <button className="btn btn-ghost" onClick={() => setPreviewNonce((n) => n + 1)}>
                {t("widget.reloadPreview")}
              </button>
            </div>
            <p className="hint">{t("widget.livePreviewHint")}</p>
            {origin ? (
              <iframe
                key={previewNonce}
                title={t("widget.livePreviewTitle")}
                sandbox="allow-scripts"
                srcDoc={previewDoc(origin, cfg)}
                style={{
                  width: "100%", height: 340, border: "1px solid var(--border)",
                  borderRadius: "var(--radius)", background: "#f7f7f9",
                }}
              />
            ) : null}
          </div>

          <div className="card">
          <h3>{t("widget.previewTitle")}</h3>
          <p className="hint">{t("widget.previewHint")}</p>
          <div
            style={{
              position: "relative",
              minHeight: 260,
              border: "1px dashed var(--border)",
              borderRadius: "var(--radius)",
              background: "var(--bg-soft)",
              overflow: "hidden",
            }}
          >
            <div
              style={{
                position: "absolute",
                bottom: 16,
                [cfg.position === "bottom-left" ? "left" : "right"]: 16,
                display: "flex",
                flexDirection: "column",
                alignItems: cfg.position === "bottom-left" ? "flex-start" : "flex-end",
                gap: "0.6rem",
              }}
            >
              {cfg.chat_enabled ? (
                <div className="mock-bubble bot" style={{ maxWidth: 220 }}>{cfg.greeting}</div>
              ) : null}
              <div
                style={{
                  width: 52, height: 52, borderRadius: "50%",
                  background: cfg.primary_color, color: "#fff",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  boxShadow: "var(--shadow)",
                }}
              >
                <Icon name="chat" size={24} />
              </div>
            </div>
          </div>
          </div>
        </div>
      </div>
    </DashboardShell>
  );
}
