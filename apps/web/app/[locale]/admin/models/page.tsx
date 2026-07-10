"use client";

import { useTranslations } from "next-intl";
import { useAdminResource as useResource } from "@/lib/hooks/useResource";
import { DashboardShell, useAdminNav } from "@/components/shell";
import { Spinner } from "@/components/ui";
import { ModelsTable } from "./models-table";
import type { AiModel, AiProvider } from "./types";

export default function AdminModels() {
  const t = useTranslations("admin");
  const nav = useAdminNav();
  const modelsRes = useResource<{ models: AiModel[] }>("/admin/ai/models?include_inactive=true");
  const providersRes = useResource<{ providers: AiProvider[] }>("/admin/ai/providers");

  if (!modelsRes.data || !providersRes.data) {
    return (
      <DashboardShell title={t("models.title")} nav={nav} requireAdmin loginHref="/admin/login">
        <Spinner />
      </DashboardShell>
    );
  }

  return (
    <DashboardShell title={t("models.title")} nav={nav} requireAdmin loginHref="/admin/login">
      <ModelsTable
        models={modelsRes.data.models}
        providers={providersRes.data.providers}
        reload={() => { modelsRes.reload(); providersRes.reload(); }}
      />
    </DashboardShell>
  );
}
