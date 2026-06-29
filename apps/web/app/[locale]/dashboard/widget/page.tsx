"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import type { TenantProfile } from "@/lib/api";
import { authFetch } from "@/lib/auth";
import { DashboardShell, useOwnerNav } from "@/components/shell";
import { Alert, Field, Input, Spinner } from "@/components/ui";

export default function WidgetPage() {
  const t = useTranslations("dashboard");
  const nav = useOwnerNav();
  const [profile, setProfile] = useState<TenantProfile | null>(null);
  const [logo, setLogo] = useState("");
  const [color, setColor] = useState("#7c5cff");
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    authFetch<TenantProfile>("/tenant/profile")
      .then((p) => {
        setProfile(p);
        setLogo(p.settings.logo_url ?? "");
        setColor(p.settings.primary_color ?? "#7c5cff");
      })
      .catch(() => setProfile(null));
  }, []);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setSaved(false);
    try {
      await authFetch("/tenant/settings", { method: "PATCH", body: { logo_url: logo, primary_color: color } });
      setSaved(true);
    } finally {
      setBusy(false);
    }
  }

  const snippet = `<script
  src="https://cdn.vitrin.ai/widget.js"
  data-tenant="${profile?.slug ?? "your-store"}"
  data-key="YOUR_WIDGET_KEY"
  defer></script>`;

  return (
    <DashboardShell title={t("nav.widget")} nav={nav}>
      <p style={{ marginTop: "-1rem" }}>{t("widget.intro")}</p>

      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <h3>{t("widget.snippetTitle")}</h3>
        <p className="hint">{t("widget.snippetHint")}</p>
        <pre className="input" style={{ whiteSpace: "pre-wrap", fontFamily: "monospace", fontSize: "0.82rem" }}>
{snippet}
        </pre>
        <button className="btn btn-ghost" onClick={() => void navigator.clipboard?.writeText(snippet)}>
          {t("widget.copySnippet")}
        </button>
      </div>

      <div className="card">
        <h3>{t("widget.whiteLabelTitle")}</h3>
        <p className="hint">{t("widget.whiteLabelHint")}</p>
        {saved ? <Alert kind="success">{t("widget.saved")}</Alert> : null}
        {profile ? (
          <form onSubmit={save}>
            <Field label={t("widget.logoUrl")}>
              <Input value={logo} onChange={(e) => setLogo(e.target.value)} placeholder="https://.../logo.svg" />
            </Field>
            <Field label={t("widget.primaryColor")}>
              <div className="row">
                <input type="color" value={color} onChange={(e) => setColor(e.target.value)} style={{ width: 48, height: 38, border: "none", background: "none" }} />
                <Input value={color} onChange={(e) => setColor(e.target.value)} style={{ maxWidth: 160 }} />
              </div>
            </Field>
            <button className="btn btn-primary" disabled={busy}>
              {busy ? <Spinner /> : t("widget.saveBranding")}
            </button>
          </form>
        ) : (
          <Spinner />
        )}
      </div>
    </DashboardShell>
  );
}
