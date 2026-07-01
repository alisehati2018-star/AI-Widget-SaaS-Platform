"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { adminFetch as authFetch } from "@/lib/auth";
import { Link } from "@/i18n/navigation";
import { DashboardShell, useAdminNav } from "@/components/shell";
import { Badge, Spinner } from "@/components/ui";

interface Health { status: string; dependencies: Record<string, string> }

export default function AdminHealth() {
  const t = useTranslations("admin");
  const nav = useAdminNav();
  const [data, setData] = useState<Health | null>(null);

  useEffect(() => {
    const load = () => authFetch<Health>("/admin/health").then(setData).catch(() => setData(null));
    load();
    const id = setInterval(load, 10000);
    return () => clearInterval(id);
  }, []);

  return (
    <DashboardShell title={t("health.title")} nav={nav} requireAdmin loginHref="/admin/login">
      <p style={{ marginTop: "-1rem" }}>{t("health.intro")}</p>
      <div className="dash-2col-even">
        <div className="card">
          <div className="row-between" style={{ marginBottom: "1rem" }}>
            <h3 style={{ margin: 0 }}>{t("health.overall")}</h3>
            {data ? (
              <Badge tone={data.status === "ok" ? "success" : "warning"}>{data.status}</Badge>
            ) : <Spinner />}
          </div>
          {data ? (
            <table className="table">
              <tbody>
                {Object.entries(data.dependencies).map(([k, v]) => (
                  <tr key={k}>
                    <td style={{ textTransform: "capitalize" }}>{k}</td>
                    <td><Badge tone={v === "ok" ? "success" : "warning"}>{v}</Badge></td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : null}
        </div>

        <div className="card">
          <h3>{t("health.quickLinksTitle")}</h3>
          <div className="stack">
            <Link className="btn btn-soft btn-block" href="/admin/queue">{t("health.linkQueue")}</Link>
            <Link className="btn btn-soft btn-block" href="/admin/elasticsearch">{t("health.linkElasticsearch")}</Link>
            <Link className="btn btn-soft btn-block" href="/admin/models">{t("health.linkModels")}</Link>
            <Link className="btn btn-soft btn-block" href="/admin/security">{t("health.linkSecurity")}</Link>
          </div>
        </div>
      </div>
    </DashboardShell>
  );
}
