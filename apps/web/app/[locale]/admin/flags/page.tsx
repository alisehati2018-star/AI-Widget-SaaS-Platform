"use client";

import { useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";
import { adminFetch as authFetch } from "@/lib/auth";
import { DashboardShell, useAdminNav } from "@/components/shell";
import { Badge, Spinner } from "@/components/ui";

interface Flag { key: string; enabled: boolean; description: string | null }

export default function AdminFlags() {
  const t = useTranslations("admin");
  const nav = useAdminNav();
  const [flags, setFlags] = useState<Flag[] | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(() => {
    authFetch<{ flags: Flag[] }>("/admin/feature-flags").then((r) => setFlags(r.flags)).catch(() => setFlags([]));
  }, []);
  useEffect(() => load(), [load]);

  async function toggle(key: string, enabled: boolean) {
    setBusy(key);
    try {
      await authFetch(`/admin/feature-flags/${key}`, { body: { enabled } });
      load();
    } finally {
      setBusy(null);
    }
  }

  return (
    <DashboardShell title={t("flags.title")} nav={nav} requireAdmin loginHref="/admin/login">
      <p style={{ marginTop: "-1rem" }}>{t("flags.intro")}</p>
      <div className="card">
        {flags === null ? (
          <Spinner />
        ) : (
          <table className="table">
            <thead><tr><th>{t("flags.colFlag")}</th><th>{t("flags.colDescription")}</th><th>{t("flags.colState")}</th><th></th></tr></thead>
            <tbody>
              {flags.map((f) => (
                <tr key={f.key}>
                  <td><code>{f.key}</code></td>
                  <td className="muted">{f.description ?? "—"}</td>
                  <td>{f.enabled ? <Badge tone="success">{t("common.on")}</Badge> : <Badge>{t("common.off")}</Badge>}</td>
                  <td>
                    <button className="btn btn-soft" disabled={busy === f.key} onClick={() => void toggle(f.key, !f.enabled)}>
                      {busy === f.key ? <Spinner /> : f.enabled ? t("common.disable") : t("common.enable")}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </DashboardShell>
  );
}
