"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { type ReactNode, useEffect, useState } from "react";
import { logout, useSession } from "../lib/auth";
import { DirectionToggle } from "./direction";
import { Brand, Spinner } from "./ui";

export interface NavItem {
  href: string;
  label: string;
  icon: string;
}

export const OWNER_NAV: NavItem[] = [
  { href: "/dashboard", label: "Overview", icon: "📊" },
  { href: "/dashboard/catalog", label: "Catalog & sync", icon: "📦" },
  { href: "/dashboard/search", label: "Search tuning", icon: "🔎" },
  { href: "/dashboard/assistant", label: "Assistant", icon: "🤖" },
  { href: "/dashboard/knowledge", label: "Knowledge base", icon: "📚" },
  { href: "/dashboard/analytics", label: "Search analytics", icon: "📈" },
  { href: "/dashboard/chat", label: "Chat analytics", icon: "💬" },
  { href: "/dashboard/sales", label: "Conversion", icon: "🛒" },
  { href: "/dashboard/leads", label: "Leads", icon: "🎯" },
  { href: "/dashboard/widget", label: "Widget & brand", icon: "🎨" },
  { href: "/dashboard/keys", label: "API keys", icon: "🔑" },
  { href: "/dashboard/team", label: "Team", icon: "👥" },
  { href: "/dashboard/credits", label: "Credits", icon: "🎟️" },
  { href: "/dashboard/billing", label: "Plan & billing", icon: "💳" },
  { href: "/dashboard/audit", label: "Activity log", icon: "📜" },
  { href: "/dashboard/settings", label: "Settings", icon: "⚙️" },
];

export const ADMIN_NAV: NavItem[] = [
  { href: "/admin", label: "Overview", icon: "📊" },
  { href: "/admin/tenants", label: "Tenants", icon: "🏬" },
  { href: "/admin/users", label: "Users", icon: "👤" },
  { href: "/admin/plans", label: "Plans", icon: "🏷️" },
  { href: "/admin/billing", label: "Billing", icon: "💳" },
  { href: "/admin/usage", label: "Usage", icon: "📶" },
  { href: "/admin/analytics", label: "Analytics", icon: "📈" },
  { href: "/admin/models", label: "Models", icon: "🧠" },
  { href: "/admin/queue", label: "Queue", icon: "🧵" },
  { href: "/admin/health", label: "System health", icon: "❤️" },
  { href: "/admin/security", label: "Security", icon: "🛡️" },
  { href: "/admin/synonyms", label: "Synonyms", icon: "🔤" },
  { href: "/admin/flags", label: "Feature flags", icon: "🚩" },
  { href: "/admin/audit", label: "Audit log", icon: "📜" },
  { href: "/admin/settings", label: "Settings", icon: "⚙️" },
];

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
        Skip to content
      </a>
      <div
        className={`sidebar-backdrop${navOpen ? " open" : ""}`}
        onClick={() => setNavOpen(false)}
        aria-hidden
      />
      <aside
        className={`sidebar${navOpen ? " open" : ""}`}
        role="navigation"
        aria-label="Dashboard"
      >
        <div className="row-between" style={{ marginBottom: "1.6rem" }}>
          <Brand href={home} />
          <button
            className="hamburger sidebar-close"
            onClick={() => setNavOpen(false)}
            aria-label="Close menu"
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
          <DirectionToggle className="btn btn-soft" />
          <small>{user?.email}</small>
          <button className="btn btn-soft" onClick={() => void onLogout()}>
            Sign out
          </button>
        </div>
      </aside>
      <main className="main" id="main-content">
        <div className="mobile-topbar">
          <button
            className="hamburger"
            onClick={() => setNavOpen(true)}
            aria-label="Open menu"
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
