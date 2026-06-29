"use client";

import { useTranslations } from "next-intl";
import { useSession } from "@/lib/auth";
import { DashboardShell, useAdminNav } from "@/components/shell";
import { Badge } from "@/components/ui";

export default function AdminSettings() {
  const t = useTranslations("admin");
  const nav = useAdminNav();
  const { user } = useSession();
  const security = [t("settings.sec1"), t("settings.sec2"), t("settings.sec3"), t("settings.sec4")];

  return (
    <DashboardShell title={t("settings.title")} nav={nav} requireAdmin loginHref="/admin/login">
      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <h3>{t("settings.accountTitle")}</h3>
        <table className="table">
          <tbody>
            <tr><td className="muted">{t("settings.email")}</td><td>{user?.email ?? "—"}</td></tr>
            <tr><td className="muted">{t("settings.role")}</td><td><Badge tone="brand">{t("settings.platformAdmin")}</Badge></td></tr>
          </tbody>
        </table>
      </div>

      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <h3>{t("settings.securityTitle")}</h3>
        <ul className="feature-list">
          {security.map((s) => (
            <li key={s}>{s}</li>
          ))}
        </ul>
        <p className="hint">{t("settings.securityHint")}</p>
      </div>

      <div className="card">
        <h3>{t("settings.platformTitle")}</h3>
        <p className="muted" style={{ marginBottom: 0 }}>{t("settings.platformBody")}</p>
      </div>
    </DashboardShell>
  );
}
