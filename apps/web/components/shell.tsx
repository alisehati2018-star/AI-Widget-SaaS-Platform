"use client";

import { useTranslations } from "next-intl";
import { type ReactNode, useEffect, useState } from "react";
import { Link, usePathname, useRouter } from "@/i18n/navigation";
import { logout, useSession } from "@/lib/auth";
import { Icon, type IconName } from "./icons";
import { LocaleSwitch } from "./locale-switch";
import { Brand, Spinner } from "./ui";

export interface NavItem {
  href: string;
  label: string;
  icon: IconName;
}

/** A labelled group of nav items (heading omitted for the top/un-grouped set). */
export interface NavSection {
  heading?: string;
  items: NavItem[];
}

/** Store-owner navigation, grouped into focused sections (Phase 4). */
export function useOwnerNav(): NavSection[] {
  const t = useTranslations("dashboard");
  return [
    {
      items: [{ href: "/dashboard", label: t("nav.overview"), icon: "overview" }],
    },
    {
      heading: t("nav.groupStore"),
      items: [
        { href: "/dashboard/catalog", label: t("nav.catalog"), icon: "catalog" },
        { href: "/dashboard/search", label: t("nav.search"), icon: "search" },
        { href: "/dashboard/widget", label: t("nav.widget"), icon: "widget" },
      ],
    },
    {
      heading: t("nav.groupAssistant"),
      items: [
        { href: "/dashboard/assistant", label: t("nav.assistant"), icon: "assistant" },
        { href: "/dashboard/knowledge", label: t("nav.knowledge"), icon: "knowledge" },
      ],
    },
    {
      heading: t("nav.groupInsights"),
      items: [
        { href: "/dashboard/analytics", label: t("nav.analytics"), icon: "analytics" },
        { href: "/dashboard/chat", label: t("nav.chat"), icon: "chat" },
        { href: "/dashboard/sales", label: t("nav.conversion"), icon: "conversion" },
        { href: "/dashboard/leads", label: t("nav.leads"), icon: "leads" },
      ],
    },
    {
      heading: t("nav.groupAccount"),
      items: [
        { href: "/dashboard/keys", label: t("nav.keys"), icon: "keys" },
        { href: "/dashboard/team", label: t("nav.team"), icon: "team" },
        { href: "/dashboard/credits", label: t("nav.credits"), icon: "credits" },
        { href: "/dashboard/billing", label: t("nav.billing"), icon: "billing" },
        { href: "/dashboard/audit", label: t("nav.activity"), icon: "activity" },
        { href: "/dashboard/settings", label: t("nav.settings"), icon: "settings" },
      ],
    },
  ];
}

/** Platform-admin navigation, grouped into focused sections. */
export function useAdminNav(): NavSection[] {
  const t = useTranslations("admin");
  return [
    {
      items: [{ href: "/admin", label: t("nav.overview"), icon: "overview" }],
    },
    {
      heading: t("nav.groupCustomers"),
      items: [
        { href: "/admin/tenants", label: t("nav.tenants"), icon: "tenants" },
        { href: "/admin/users", label: t("nav.users"), icon: "users" },
      ],
    },
    {
      heading: t("nav.groupRevenue"),
      items: [
        { href: "/admin/plans", label: t("nav.plans"), icon: "plans" },
        { href: "/admin/billing", label: t("nav.billing"), icon: "billing" },
        { href: "/admin/usage", label: t("nav.usage"), icon: "usage" },
        { href: "/admin/analytics", label: t("nav.analytics"), icon: "analytics" },
      ],
    },
    {
      heading: t("nav.groupPlatform"),
      items: [
        { href: "/admin/models", label: t("nav.models"), icon: "models" },
        { href: "/admin/queue", label: t("nav.queue"), icon: "queue" },
        { href: "/admin/health", label: t("nav.health"), icon: "health" },
        { href: "/admin/security", label: t("nav.security"), icon: "security" },
        { href: "/admin/synonyms", label: t("nav.synonyms"), icon: "synonyms" },
        { href: "/admin/flags", label: t("nav.flags"), icon: "flags" },
        { href: "/admin/audit", label: t("nav.audit"), icon: "activity" },
        { href: "/admin/settings", label: t("nav.settings"), icon: "settings" },
      ],
    },
  ];
}

/**
 * Guards a logged-in surface. `requireAdmin` enforces the platform-admin role;
 * otherwise any authenticated user is allowed. Redirects to `loginHref` when
 * unauthenticated or under-privileged.
 */
export function DashboardShell({
  title,
  nav,
  requireAdmin = false,
  loginHref = "/login",
  children,
}: {
  title: string;
  nav: NavSection[];
  requireAdmin?: boolean;
  loginHref?: string;
  children: ReactNode;
}) {
  const t = useTranslations("common");
  const { user, loading } = useSession();
  const router = useRouter();
  const pathname = usePathname();
  const [navOpen, setNavOpen] = useState(false);

  const allowed = user && (!requireAdmin || user.role === "platform_admin");

  useEffect(() => {
    if (!loading && !allowed) router.replace(loginHref);
  }, [loading, allowed, router, loginHref]);

  // Close the mobile drawer on route change.
  useEffect(() => {
    setNavOpen(false);
  }, [pathname]);

  if (loading || !allowed) {
    return (
      <div className="auth-wrap">
        <Spinner />
      </div>
    );
  }

  async function onLogout() {
    await logout();
    router.replace(loginHref);
  }

  const home = requireAdmin ? "/admin" : "/dashboard";

  return (
    <div className="shell">
      <a href="#main-content" className="skip-link">
        {t("a11y.skipToContent")}
      </a>
      <div
        className={`sidebar-backdrop${navOpen ? " open" : ""}`}
        onClick={() => setNavOpen(false)}
        aria-hidden
      />
      <aside
        className={`sidebar${navOpen ? " open" : ""}`}
        role="navigation"
        aria-label={title}
      >
        <div className="row-between" style={{ marginBottom: "1.6rem" }}>
          <Brand href={home} />
          <button
            className="hamburger sidebar-close"
            onClick={() => setNavOpen(false)}
            aria-label={t("a11y.closeMenu")}
          >
            ✕
          </button>
        </div>
        <nav style={{ flex: 1 }}>
          {nav.map((section, si) => (
            <div className="side-group" key={section.heading ?? `g${si}`}>
              {section.heading ? (
                <div className="side-section-title">{section.heading}</div>
              ) : null}
              {section.items.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-current={pathname === item.href ? "page" : undefined}
                  className={`side-link${pathname === item.href ? " active" : ""}`}
                >
                  <Icon name={item.icon} />
                  <span>{item.label}</span>
                </Link>
              ))}
            </div>
          ))}
        </nav>
        <div className="divider" />
        <div className="stack" style={{ gap: "0.5rem" }}>
          <LocaleSwitch className="btn btn-soft" />
          <small>{user?.email}</small>
          <button className="btn btn-soft" onClick={() => void onLogout()}>
            {t("actions.signOut")}
          </button>
        </div>
      </aside>
      <main className="main" id="main-content">
        <div className="mobile-topbar">
          <button
            className="hamburger"
            onClick={() => setNavOpen(true)}
            aria-label={t("a11y.openMenu")}
            aria-expanded={navOpen}
          >
            ☰
          </button>
          <Brand href={home} />
          <span style={{ width: 40 }} />
        </div>
        <div className="topbar">
          <h2 style={{ margin: 0 }}>{title}</h2>
        </div>
        {children}
      </main>
    </div>
  );
}
