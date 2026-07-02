"use client";

import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { useEffect, useState } from "react";
import { authFetch } from "@/lib/auth";
import { DashboardShell, useOwnerNav } from "@/components/shell";
import { Icon } from "@/components/icons";
import { Alert, Badge, Field, Input, Spinner } from "@/components/ui";

interface WidgetInfo {
  api_base: string;
  status: string;
  approved: boolean;
  has_widget_key: boolean;
  ready: boolean;
  snippet: string;
  settings: Record<string, unknown>;
}

interface WidgetSettings {
  logo_url: string;
  primary_color: string;
  widget_greeting: string;
  position: string;
  chat_enabled: boolean;
  search_enabled: boolean;
}

export default function WidgetPage() {
  const t = useTranslations("dashboard");
  const nav = useOwnerNav();
  const [info, setInfo] = useState<WidgetInfo | null>(null);
  const [cfg, setCfg] = useState<WidgetSettings>({
    logo_url: "", primary_color: "#1A7A4B", widget_greeting: "",
    position: "bottom-right", chat_enabled: true, search_enabled: true,
  });
  const [savedBranding, setSavedBranding] = useState(false);
  const [savedConfig, setSavedConfig] = useState(false);
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);
  const [testKey, setTestKey] = useState("");
  const [testNonce, setTestNonce] = useState(0);
  const [testOn, setTestOn] = useState(false);

  useEffect(() => {
    authFetch<WidgetInfo>("/tenant/widget")
      .then((w) => {
        setInfo(w);
        const s = w.settings as Partial<WidgetSettings>;
        setCfg({
          logo_url: s.logo_url ?? "",
          primary_color: s.primary_color ?? "#1A7A4B",
          widget_greeting: s.widget_greeting ?? "",
          position: s.position ?? "bottom-right",
          chat_enabled: s.chat_enabled ?? true,
          search_enabled: s.search_enabled ?? true,
        });
      })
      .catch(() => setInfo(null));
  }, []);

  async function saveBranding(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true); setSavedBranding(false);
    try {
      await authFetch("/tenant/settings", {
        method: "PATCH",
        body: { logo_url: cfg.logo_url, primary_color: cfg.primary_color },
      });
      setSavedBranding(true);
    } finally { setBusy(false); }
  }

  async function saveConfig(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true); setSavedConfig(false);
    try {
      await authFetch("/tenant/settings", {
        method: "PATCH",
        body: {
          widget_greeting: cfg.widget_greeting,
          position: cfg.position,
          chat_enabled: cfg.chat_enabled,
          search_enabled: cfg.search_enabled,
        },
      });
      setSavedConfig(true);
    } finally { setBusy(false); }
  }

  function copy() {
    if (info) void navigator.clipboard?.writeText(info.snippet);
    setCopied(true);
  }

  // The REAL production loader inside a sandboxed iframe, exactly as a store
  // page would embed it. With the store's widget key pasted in, search/chat
  // hit the live public API; without it the widget still mounts with defaults.
  function testDoc(): string {
    const origin = window.location.origin;
    const key = testKey.trim() || "dashboard-preview";
    return `<!doctype html><html dir="rtl" lang="fa"><head><meta charset="utf-8">
<style>body{margin:0;min-height:340px;background:#f7f7f9}</style></head><body>
<script src="${origin}/api/widget/v1.js" data-acip-key="${key.replace(/"/g, "")}"
  data-acip-base="${origin}/api" async><\/script></body></html>`;
  }

  return (
    <DashboardShell title={t("nav.widget")} nav={nav}>
      <p style={{ marginTop: "-1rem" }}>{t("widget.intro")}</p>

      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <div className="row-between">
          <h3 style={{ margin: 0 }}>{t("widget.embedTitle")}</h3>
          {info ? (
            info.ready ? <Badge tone="success">{info.status}</Badge>
              : <Badge tone="warning">{t("widget.statusPending")}</Badge>
          ) : null}
        </div>
        {!info ? <Spinner /> : (
          <>
            <p className="hint">{info.ready ? t("widget.embedReady") : t("widget.embedNotReady")}</p>
            <pre className="input" style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere", fontFamily: "monospace", fontSize: "0.82rem", opacity: info.ready ? 1 : 0.6 }}>
{info.snippet}
            </pre>
            <p className="hint">{t("widget.embedKeyHint")}</p>
            <div className="row" style={{ flexWrap: "wrap", gap: ".5rem" }}>
              <button className="btn btn-ghost" onClick={copy}>{t("widget.copySnippet")}</button>
              {!info.has_widget_key ? (
                <Link className="btn btn-soft" href="/dashboard/keys">{t("widget.createKeyCta")}</Link>
              ) : null}
            </div>
            {copied ? <Alert kind="success">{t("common.saved")}</Alert> : null}
          </>
        )}
      </div>

      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <div className="row-between" style={{ flexWrap: "wrap", gap: ".6rem" }}>
          <h3 style={{ margin: 0 }}>{t("widget.liveTestTitle")}</h3>
          {testOn ? (
            <button className="btn btn-ghost" onClick={() => setTestNonce((n) => n + 1)}>
              {t("widget.liveTestReload")}
            </button>
          ) : null}
        </div>
        <p className="hint">{t("widget.liveTestHint")}</p>
        <div className="row" style={{ flexWrap: "wrap", gap: ".6rem", marginBottom: "1rem" }}>
          <Input
            dir="ltr"
            value={testKey}
            onChange={(e) => setTestKey(e.target.value)}
            placeholder={t("widget.liveTestKeyPlaceholder")}
            style={{ flex: 1, minWidth: 240 }}
            aria-label={t("widget.liveTestKeyPlaceholder")}
          />
          <button className="btn btn-primary" onClick={() => { setTestOn(true); setTestNonce((n) => n + 1); }}>
            {t("widget.liveTestRun")}
          </button>
        </div>
        {testOn ? (
          <iframe
            key={testNonce}
            title={t("widget.liveTestTitle")}
            sandbox="allow-scripts"
            srcDoc={testDoc()}
            style={{
              width: "100%", height: 360, border: "1px solid var(--border)",
              borderRadius: "var(--radius)", background: "#f7f7f9",
            }}
          />
        ) : null}
        <p className="hint" style={{ marginTop: ".5rem" }}>{t("widget.liveTestKeyNote")}</p>
      </div>

      <div className="dash-2col">
        <div className="card-stack">
          <div className="card">
            <h3>{t("widget.configTitle")}</h3>
            <p className="hint">{t("widget.configHint")}</p>
            {savedConfig ? <Alert kind="success">{t("widget.configSaved")}</Alert> : null}
            <form onSubmit={saveConfig}>
              <Field label={t("widget.greeting")}>
                <Input value={cfg.widget_greeting} onChange={(e) => setCfg({ ...cfg, widget_greeting: e.target.value })} />
              </Field>
              <Field label={t("widget.position")}>
                <select className="input" value={cfg.position} onChange={(e) => setCfg({ ...cfg, position: e.target.value })}>
                  <option value="bottom-right">{t("widget.positionBottomRight")}</option>
                  <option value="bottom-left">{t("widget.positionBottomLeft")}</option>
                </select>
              </Field>
              <label className="row" style={{ gap: ".5rem", marginBottom: ".5rem" }}>
                <input type="checkbox" checked={cfg.chat_enabled} onChange={(e) => setCfg({ ...cfg, chat_enabled: e.target.checked })} />
                {t("widget.chatEnabled")}
              </label>
              <label className="row" style={{ gap: ".5rem", marginBottom: "1rem" }}>
                <input type="checkbox" checked={cfg.search_enabled} onChange={(e) => setCfg({ ...cfg, search_enabled: e.target.checked })} />
                {t("widget.searchEnabled")}
              </label>
              <button className="btn btn-primary" disabled={busy}>{busy ? <Spinner /> : t("widget.saveConfig")}</button>
            </form>
          </div>

          <div className="card">
            <h3>{t("widget.whiteLabelTitle")}</h3>
            <p className="hint">{t("widget.whiteLabelHint")}</p>
            {savedBranding ? <Alert kind="success">{t("widget.saved")}</Alert> : null}
            <form onSubmit={saveBranding}>
              <Field label={t("widget.logoUrl")}>
                <Input value={cfg.logo_url} onChange={(e) => setCfg({ ...cfg, logo_url: e.target.value })} placeholder="https://.../logo.svg" />
              </Field>
              <Field label={t("widget.primaryColor")}>
                <div className="row">
                  <input type="color" value={cfg.primary_color} onChange={(e) => setCfg({ ...cfg, primary_color: e.target.value })} style={{ width: 48, height: 38, border: "none", background: "none" }} />
                  <Input value={cfg.primary_color} onChange={(e) => setCfg({ ...cfg, primary_color: e.target.value })} style={{ maxWidth: 160 }} />
                </div>
              </Field>
              <button className="btn btn-primary" disabled={busy}>{busy ? <Spinner /> : t("widget.saveBranding")}</button>
            </form>
          </div>
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
                <div className="mock-bubble bot" style={{ maxWidth: 220 }}>{cfg.widget_greeting || t("widget.previewGreetingFallback")}</div>
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
    </DashboardShell>
  );
}
