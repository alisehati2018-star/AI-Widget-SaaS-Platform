"use client";

import { useTranslations } from "next-intl";
import { useAdminResource as useResource } from "@/lib/hooks/useResource";
import { DashboardShell, useAdminNav } from "@/components/shell";
import { Spinner } from "@/components/ui";
import type { AiProvider, FinanceData, PricingData, RoutesData } from "../models/types";
import { BindingEditor } from "./binding-editor";
import { FinanceCard } from "./finance-card";
import { GlobalSettingsPanel } from "./global-settings-panel";
import { PricingCard } from "./pricing-card";

export default function AdminAiConfig() {
  const t = useTranslations("admin");
  const ta = useTranslations("admin.aiConfigPage");
  const nav = useAdminNav();
  const routingRes = useResource<{ failover_enabled: boolean }>("/admin/ai/routing-settings");
  const routesRes = useResource<RoutesData>("/admin/ai/routes");
  const providersRes = useResource<{ providers: AiProvider[] }>("/admin/ai/providers");
  const pricingRes = useResource<PricingData>("/admin/ai/pricing");
  const financeRes = useResource<FinanceData>("/admin/ai/finance?days=30");

  if (!routingRes.data || !routesRes.data || !providersRes.data) {
    return (
      <DashboardShell title={ta("title")} nav={nav} requireAdmin loginHref="/admin/login">
        <Spinner />
      </DashboardShell>
    );
  }

  return (
    <DashboardShell title={ta("title")} nav={nav} requireAdmin loginHref="/admin/login">
      <p style={{ marginTop: "-1rem" }}>{ta("description")}</p>

      <GlobalSettingsPanel
        failoverEnabled={routingRes.data.failover_enabled}
        reload={routingRes.reload}
      />

      {routesRes.data.tasks.map((task) => (
        <div key={task} className="card" style={{ marginBottom: "1.5rem" }}>
          <h3>{t(`models.task_${task}`)}</h3>
          <BindingEditor
            task={task}
            chain={routesRes.data!.routes[task] ?? []}
            providers={providersRes.data!.providers}
            reload={routesRes.reload}
          />
        </div>
      ))}

      {pricingRes.data ? (
        <PricingCard pricing={pricingRes.data}
          reload={() => { pricingRes.reload(); financeRes.reload(); }} />
      ) : null}

      {financeRes.data ? <FinanceCard finance={financeRes.data} /> : null}
    </DashboardShell>
  );
}
