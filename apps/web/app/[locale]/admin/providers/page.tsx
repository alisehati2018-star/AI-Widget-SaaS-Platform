"use client";

import { useTranslations } from "next-intl";
import { useAdminResource as useResource } from "@/lib/hooks/useResource";
import { DashboardShell, useAdminNav } from "@/components/shell";
import { Spinner } from "@/components/ui";
import { ProvidersTable } from "./providers-table";
import type { AiProvider } from "../models/types";

export default function AdminProviders() {
  const t = useTranslations("admin.providersPage");
  const nav = useAdminNav();
  const providersRes = useResource<{ providers: AiProvider[] }>("/admin/ai/providers");

  if (!providersRes.data) {
    return (
      <DashboardShell title={t("title")} nav={nav} requireAdmin loginHref="/admin/login">
        <Spinner />
      </DashboardShell>
    );
  }

  return (
    <DashboardShell title={t("title")} nav={nav} requireAdmin loginHref="/admin/login">
      <ProvidersTable providers={providersRes.data.providers} reload={providersRes.reload} />
    </DashboardShell>
  );
}
