import Link from "next/link";

export default function Home() {
  // Operator dashboard home. The console (four-dimension analytics) and synonym
  // tools are the M9 surfaces; the embeddable shopper widget lives in
  // `widget/acip-widget.ts` (M8).
  return (
    <main style={{ fontFamily: "system-ui, sans-serif", padding: "2rem" }}>
      <h1>ACIP</h1>
      <p>AI Commerce Intelligence Platform — operator dashboard.</p>
      <ul>
        <li>
          <Link href="/console">Analytics console (relevance · latency · cost · reliability)</Link>
        </li>
        <li>
          <Link href="/synonyms">Synonym &amp; suggestion management</Link>
        </li>
      </ul>
    </main>
  );
}
