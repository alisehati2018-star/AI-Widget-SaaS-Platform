"use client";

// Master on/off switch for cross-endpoint failover/retry across every task.
// Per-provider retry count/backoff (Providers page) still applies while
// this is on; this is the one switch that turns all of it off at once.

import { useTranslations } from "next-intl";
import { useState } from "react";
import { ApiError } from "@/lib/api";
import { adminFetch as authFetch } from "@/lib/auth";
import { Alert, Spinner } from "@/components/ui";

export function GlobalSettingsPanel({
  failoverEnabled,
  reload,
}: {
  failoverEnabled: boolean;
  reload: () => void;
}) {
  const t = useTranslations("admin");
  const ta = useTranslations("admin.aiConfigPage");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function toggle() {
    setError(null);
    setBusy(true);
    try {
      await authFetch("/admin/ai/routing-settings", {
        method: "PUT",
        body: { failover_enabled: !failoverEnabled },
      });
      reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("models.actionFailed"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card" style={{ marginBottom: "1.5rem" }}>
      <h3>{ta("globalFailover")}</h3>
      <p className="hint">{ta("globalFailoverDesc")}</p>
      {error ? <Alert kind="error">{error}</Alert> : null}
      <label className="row" style={{ gap: ".5rem" }}>
        <input type="checkbox" checked={failoverEnabled} disabled={busy}
          onChange={() => void toggle()} />
        {busy ? <Spinner /> : ta("chatProviderFailover")}
      </label>
      <p className="hint" style={{ marginTop: ".3rem" }}>{ta("chatProviderFailoverHint")}</p>
    </div>
  );
}
