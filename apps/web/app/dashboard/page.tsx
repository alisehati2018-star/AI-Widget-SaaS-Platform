"use client";

import Link from "next/link";
import { DashboardShell, OWNER_NAV } from "../../components/shell";
import { Stat } from "../../components/ui";
import { useSession } from "../../lib/auth";

export default function DashboardHome() {
  const { user } = useSession();
  return (
    <DashboardShell title="Overview" nav={OWNER_NAV}>
      <p style={{ marginTop: "-1rem" }}>
        Welcome{user?.full_name ? `, ${user.full_name}` : ""}. Here&apos;s your store at a glance.
      </p>
      <div className="stat-grid" style={{ marginBottom: "2rem" }}>
        <Stat label="Searches (30d)" value="—" />
        <Stat label="Assistant chats" value="—" />
        <Stat label="Leads captured" value="—" />
        <Stat label="AI credits left" value="—" />
      </div>

      <div className="card">
        <h3>Finish setting up</h3>
        <p>Connect your store and drop in the search widget to start seeing data.</p>
        <ol className="muted" style={{ paddingLeft: "1.2rem", lineHeight: 2 }}>
          <li>Install the OpenCart / WooCommerce plugin and paste your API key.</li>
          <li>Run the first catalogue sync.</li>
          <li>Embed the Vitrin widget on your storefront.</li>
        </ol>
        <div className="row" style={{ marginTop: "1rem" }}>
          <Link href="/dashboard/keys" className="btn btn-primary">Get your API key</Link>
          <Link href="/dashboard/analytics" className="btn btn-ghost">View analytics</Link>
        </div>
      </div>
    </DashboardShell>
  );
}
