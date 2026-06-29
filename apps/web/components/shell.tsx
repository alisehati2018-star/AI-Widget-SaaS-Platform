"use client";

import { useTranslations } from "next-intl";
import { type ReactNode, useEffect, useState } from "react";
import { Link, usePathname, useRouter } from "@/i18n/navigation";
import { logout, useSession } from "@/lib/auth";
import { LocaleSwitch } from "./locale-switch";
import { Brand, Spinner } from "./ui";

export interface NavItem {
  href: string;
  label: string;
  icon: string;
}

/** Store-owner navigation, labels translated from the `dashboard` namespace. */
export function useOwnerNav(): NavItem[] {
  const t = useTranslations("dashboard");
  return [
    { href: "/dashboard", label: t("nav.overview"), icon: "📊" },
    { href: "/dashboard/catalog", label: t("nav.catalog"), icon: "📦" },
    { href: "/dashboard/search", label: t("nav.search"), icon: "🔎" },
    { href: "/dashboard/assistant", label: t("nav.assistant"), icon: "🤖" },
    { href: "/dashboard/knowledge", label: t("nav.knowledge"), icon: "📚" },
    { href: "/dashboard/analytics", label: t("nav.analytics"), icon: "📈" },
    { href: "/dashboard/chat", label: t("nav.chat"), icon: "💬" },
    { href: "/dashboard/sales", label: t("nav.conversion"), icon: "🛒" },
    { href: "/dashboard/leads", label: t("nav.leads"), icon: "🎯" },
    { href: "/dashboard/widget", label: t("nav.widget"), icon: "🎨" },
    { href: "/dashboard/keys", label: t("nav.keys"), icon: "🔑" },
    { href: "/dashboard/team", label: t("nav.team"), icon: "👥" },
    { href: "/dashboard/credits", label: t("nav.credits"), icon: "🎟️" },
    { href: "/dashboard/billing", label: t("nav.billing"), icon: "💳" },
    { href: "/dashboard/audit", label: t("nav.activity"), icon: "📜" },
    { href: "/dashboard/settings", label: t("nav.settings"), icon: "⚙️" },
  ];
}

/** Platform-admin navigation, labels translated from the `admin` namespace. */
export function useAdminNav(): NavItem[] {
  const t = useTranslations("admin");
  return [
    { href: "/admin", label: t("nav.overview"), icon: "📊" },
    { href: "/admin/tenants", label: t("nav.tenants"), icon: "🏬" },
    { href: "/admin/users", label: t("nav.users"), icon: "👤" },
    { href: "/admin/plans", label: t("nav.plans"), icon: "🏷️" },
    { href: "/admin/billing", label: t("nav.billing"), icon: "💳" },
    { href: "/admin/usage", label: t("nav.usage"), icon: "📶" },
    { href: "/admin/analytics", label: t("nav.analytics"), icon: "📈" },
    { href: "/admin/models", label: t("nav.models"), icon: "🧠" },
    { href: "/admin/queue", label: t("nav.queue"), icon: "🧵" },
    { href: "/admin/health", label: t("nav.health"), icon: "❤️" },
    { href: "/admin/security", label: t("nav.security"), icon: "🛡️" },
    { href: "/admin/synonyms", label: t("nav.synonyms"), icon: "🔤" },
    { href: "/admin/flags", label: t("nav.flags"), icon: "🚩" },
    { href: "/admin/audit", label: t("nav.audit"), icon: "📜" },
    { href: "/admin/settings", label: t("nav.settings"), icon: "⚙️" },
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
  nav: NavItem[];
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
          {nav.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              aria-current={pathname === item.href ? "page" : undefined}
              className={`side-link${pathname === item.href ? " active" : ""}`}
            >
              <span aria-hidden>{item.icon}</span>
              <span>{item.label}</span>
            </Link>
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
