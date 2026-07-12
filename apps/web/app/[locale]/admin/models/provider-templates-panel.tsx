"use client";

// Quick-add row: pick a known vendor template, paste its API key, done —
// instead of filling in base_url/kind by hand for every common provider.

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { useApiErrorMessage } from "@/lib/errors";
import { adminFetch as authFetch } from "@/lib/auth";
import { Field, Input, Spinner } from "@/components/ui";
import type { ProviderTemplate } from "./types";

export function ProviderTemplatesPanel({ onCreated }: { onCreated: () => void }) {
  const t = useTranslations("admin");
  const apiMsg = useApiErrorMessage();
  const [templates, setTemplates] = useState<ProviderTemplate[] | null>(null);
  const [picked, setPicked] = useState<ProviderTemplate | null>(null);
  const [apiKey, setApiKey] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    authFetch<{ templates: ProviderTemplate[] }>("/admin/ai/provider-templates")
      .then((r) => setTemplates(r.templates))
      .catch(() => setTemplates([]));
  }, []);

  async function createFromTemplate() {
    if (!picked) return;
    setError(null);
    setBusy(true);
    try {
      await authFetch("/admin/ai/providers/from-template", {
        body: { template_key: picked.key, api_key: apiKey.trim() },
      });
      setPicked(null);
      setApiKey("");
      onCreated();
    } catch (err) {
      setError(apiMsg(err) ?? t("models.actionFailed"));
    } finally {
      setBusy(false);
    }
  }

  if (!templates || !templates.length) return null;

  return (
    <div style={{ margin: "0.8rem 0" }}>
      <p className="hint" style={{ marginBottom: ".4rem" }}>{t("models.templatesHint")}</p>
      {error ? <p className="hint" style={{ color: "var(--danger, #c0392b)" }}>{error}</p> : null}
      <div style={{ display: "flex", gap: ".4rem", flexWrap: "wrap" }}>
        {templates.map((tpl) => (
          <button key={tpl.key} className="btn btn-soft" disabled={tpl.already_created}
            onClick={() => { setPicked(tpl); setApiKey(""); }}>
            {tpl.display_name}
            {tpl.already_created ? ` (${t("common.enabled")})` : ""}
          </button>
        ))}
      </div>
      {picked ? (
        <div className="dash-2col-even" style={{ marginTop: ".6rem" }}>
          <Field label={t("models.apiKey")} hint={picked.description}>
            <Input dir="ltr" type="password" value={apiKey}
              onChange={(e) => setApiKey(e.target.value)} />
          </Field>
          <div>
            <button className="btn btn-primary" disabled={busy || !apiKey.trim()}
              onClick={() => void createFromTemplate()}>
              {busy ? <Spinner /> : t("models.addFromTemplate", { name: picked.display_name })}
            </button>{" "}
            <button className="btn" onClick={() => setPicked(null)}>
              {t("models.cancel")}
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
