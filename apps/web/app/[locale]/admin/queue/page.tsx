"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { adminFetch as authFetch } from "@/lib/auth";
import { formatNumber } from "@/lib/datetime";
import type { Locale } from "@/i18n/routing";
import { DashboardShell, useAdminNav } from "@/components/shell";
import { Alert, Badge, Spinner, Stat } from "@/components/ui";

interface Worker {
  name: string;
  status: string;
  active_tasks: { name: string | null; id: string | null }[];
  active_count: number;
  registered: string[];
}
interface Queue {
  broker: string;
  reachable: boolean;
  pending: number | null;
  workers: Worker[];
}

export default function AdminQueue() {
  const t = useTranslations("admin");
  const locale = useLocale() as Locale;
  const nav = useAdminNav();
  const [data, setData] = useState<Queue | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const load = () =>
      authFetch<Queue>("/admin/queue")
        .then((r) => { setData(r); setFailed(false); })
        .catch(() => { setData(null); setFailed(true); });
    load();
    const id = setInterval(load, 10000);
    return () => clearInterval(id);
  }, []);

  const brokerStat = data ? (
    <Badge tone={data.reachable ? "success" : "warning"}>
      {data.reachable ? t("queue.reachable") : t("queue.down")}
    </Badge>
  ) : failed ? (
    <Badge tone="warning">{t("queue.down")}</Badge>
  ) : (
    <Spinner />
  );

  return (
    <DashboardShell title={t("queue.title")} nav={nav} requireAdmin loginHref="/admin/login">
      <p style={{ marginTop: "-1rem" }}>{t("queue.intro")}</p>
      {failed ? <Alert kind="error">{t("common.loadFailed")}</Alert> : null}
      <div className="stat-grid" style={{ marginBottom: "1.5rem" }}>
        <Stat label={t("queue.broker")} value={brokerStat} />
        <Stat label={t("queue.pendingTasks")} value={data?.pending != null ? formatNumber(data.pending, locale) : "—"} />
        <Stat label={t("queue.workersOnline")} value={data ? formatNumber(data.workers.length, locale) : "—"} />
      </div>

      <div className="dash-2col">
        <div className="card">
          <h3>{t("queue.workersTitle")}</h3>
          {failed ? (
            <p className="muted">{t("common.loadFailed")}</p>
          ) : !data ? <Spinner /> : data.workers.length === 0 ? (
            <p className="muted">{t("queue.noWorkers")}</p>
          ) : (
            <table className="table">
              <thead><tr>
                <th>{t("queue.colWorker")}</th><th>{t("queue.colStatus")}</th>
                <th>{t("queue.colActive")}</th><th>{t("queue.colTasks")}</th>
              </tr></thead>
              <tbody>
                {data.workers.map((w) => (
                  <tr key={w.name}>
                    <td dir="ltr">{w.name}</td>
                    <td><Badge tone="success">{t("queue.online")}</Badge></td>
                    <td>{formatNumber(w.active_count, locale)}</td>
                    <td className="muted" style={{ fontSize: "0.8rem" }} dir="ltr">
                      {w.active_tasks.length
                        ? w.active_tasks.map((task) => task.name).filter(Boolean).join("، ")
                        : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <p className="hint" style={{ marginTop: "1rem" }}>{t("queue.workersHint")}</p>
        </div>

        <div className="card">
          <h3>{t("queue.brokerTitle")}</h3>
          <p className="muted" style={{ wordBreak: "break-all" }} dir="ltr">{data?.broker ?? "—"}</p>
          <p className="hint">{t("queue.hint")}</p>
          {data?.workers.length ? (
            <>
              <h4 style={{ marginTop: "1rem" }}>{t("queue.registeredTitle")}</h4>
              <ul className="feature-list" dir="ltr">
                {data.workers[0].registered.map((name) => <li key={name}>{name}</li>)}
              </ul>
            </>
          ) : null}
        </div>
      </div>
    </DashboardShell>
  );
}
