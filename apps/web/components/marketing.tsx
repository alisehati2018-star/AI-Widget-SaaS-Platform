import Link from "next/link";
import { Brand } from "./ui";

export function MarketingNav() {
  return (
    <nav className="nav">
      <div className="container nav-inner">
        <Brand />
        <div className="nav-links">
          <Link href="/features">Features</Link>
          <Link href="/pricing">Pricing</Link>
          <Link href="/contact">Contact</Link>
          <Link href="/login">Sign in</Link>
          <Link href="/signup" className="btn btn-primary">
            Start free
          </Link>
        </div>
      </div>
    </nav>
  );
}

export function MarketingFooter() {
  return (
    <footer className="footer">
      <div className="container row-between">
        <Brand />
        <div className="row" style={{ gap: "1.5rem", flexWrap: "wrap" }}>
          <Link href="/features">Features</Link>
          <Link href="/pricing">Pricing</Link>
          <Link href="/contact">Contact</Link>
          <Link href="/login">Sign in</Link>
          <Link href="/admin/login">Admin</Link>
        </div>
      </div>
      <div className="container" style={{ marginTop: "1rem" }}>
        <small>© {new Date().getFullYear()} Vitrin — AI Commerce Intelligence Platform. On-premise &amp; multi-tenant.</small>
      </div>
    </footer>
  );
}
