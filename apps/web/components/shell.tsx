"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { type ReactNode, useEffect } from "react";
import { logout, useSession } from "../lib/auth";
import { Brand, Spinner } from "./ui";

export interface NavItem {
  href: string;
  label: string;
  icon: string;
}

export const OWNER_NAV: NavItem[] = [
  { href: "/dashboard", label: "Overview", icon: "📊" },
  { href: "/dashboard/keys", label: "API keys", icon: "🔑" },
  { href: "/dashboard/analytics", label: "Analytics", icon: "📈" },
  { href: "/dashboard/billing", label: "Plan & billing", icon: "💳" },
];

export const ADMIN_NAV: NavItem[] = [
  { href: "/admin", label: "Overview", icon: "📊" },
  { href: "/admin/tenants", label: "Tenants", icon: "🏬" },
  { href: "/admin/plans", label: "Plans", icon: "🏷️" },
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

  const allowed = user && (!requireAdmin || user.role === "platform_admin");

  useEffect(() => {
    if (!loading && !allowed) router.replace(loginHref);
  }, [loading, allowed, router, loginHref]);

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

  return (
    <div className="shell">
      <aside className="sidebar">
        <div style={{ marginBottom: "1.6rem" }}>
          <Brand href={requireAdmin ? "/admin" : "/dashboard"} />
        </div>
        <nav style={{ flex: 1 }}>
          {nav.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`side-link${pathname === item.href ? " active" : ""}`}
            >
              <span>{item.icon}</span>
              <span>{item.label}</span>
            </Link>
          ))}
        </nav>
        <div className="divider" />
        <div className="stack" style={{ gap: "0.5rem" }}>
          <small>{user?.email}</small>
          <button className="btn btn-soft" onClick={() => void onLogout()}>
            Sign out
          </button>
        </div>
      </aside>
      <main className="main">
        <div className="topbar">
          <h2 style={{ margin: 0 }}>{title}</h2>
        </div>
        {children}
      </main>
    </div>
  );
}
