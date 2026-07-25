import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Shared AI memory, with clear boundaries",
  description:
    "Ninai is building permissioned, source-backed memory for supported OpenAI and Anthropic clients, with an open-source local engine available today.",
  alternates: { canonical: "/" },
  openGraph: {
    title: "Ninai — shared AI memory, with clear boundaries",
    description:
      "Explore the hosted cross-provider beta in development or run Ninai's open-source local engine today.",
    url: "/",
    images: [{ url: "/assets/og-image.png", width: 1200, height: 630, alt: "Ninai — permissioned AI memory" }],
  },
};

const lifecycle = [
  ["01", "Save", "A client proposes a durable decision with its source and scope."],
  ["02", "Approve", "Review mode keeps proposed memory out of recall until you approve it."],
  ["03", "Recall", "Authorized clients receive only relevant, in-scope memories."],
  ["04", "Revoke", "Remove a client's future access without deleting the underlying memory."],
];

export default function HomePage() {
  return (
    <main id="main-content">
      <section className="beta-hero" id="product">
        <div className="shell beta-hero__inner">
          <p className="section-label">Public Beta · in development</p>
          <h1>One memory for OpenAI and Claude.</h1>
          <p className="beta-hero__lead">
            Stop re-explaining project decisions when you switch AI tools. Ninai is building
            shared, permissioned memory with a source attached to every result.
          </p>
          <div className="beta-actions">
            <Link className="button button--ink" href="/install/">Choose how to run Ninai ↗</Link>
            <Link className="button" href="/compatibility/">See compatibility</Link>
          </div>
          <p className="beta-status">Hosted cross-provider access is not yet generally available or release-tested. The local engine is available now.</p>
        </div>
      </section>

      <section className="mode-section shell" id="how-it-works">
        <div className="section-intro">
          <p className="section-label">Two deployment modes</p>
          <h2>Choose the boundary that fits your work.</h2>
        </div>
        <div className="mode-grid">
          <article className="mode-card mode-card--future">
            <span className="status-pill">Under development</span>
            <h3>Hosted Beta</h3>
            <p>Planned for one workspace shared by supported OpenAI and Anthropic clients, available while your laptop is off.</p>
            <ul><li>Explicit client grants</li><li>Source-backed memory</li><li>Disclosure and revocation controls</li></ul>
            <Link href="/compatibility/">Check tested-client status →</Link>
          </article>
          <article className="mode-card">
            <span className="status-pill status-pill--ready">Available now</span>
            <h3>Local Engine</h3>
            <p>Open-source Python MCP server with a SQLite vault on your machine. No account or cloud sync is required.</p>
            <ul><li>Local SQLite storage</li><li>Explicit per-client scopes</li><li>Provenance and disclosure logs</li></ul>
            <Link href="/local/">Explore local mode →</Link>
          </article>
        </div>
      </section>

      <section className="lifecycle-section">
        <div className="shell">
          <div className="section-intro"><p className="section-label">Memory lifecycle</p><h2>Useful context stays accountable.</h2></div>
          <div className="lifecycle-grid">
            {lifecycle.map(([index, title, copy]) => <article key={index}><span>{index}</span><h3>{title}</h3><p>{copy}</p></article>)}
          </div>
          <p className="truth-note">The Claude → OpenAI → Claude round trip described here is the release gate, not a claim of current tested support.</p>
        </div>
      </section>

      <section className="beta-trust shell">
        <div><p className="section-label">Permission before retrieval</p><h2>A client sees only what its scopes allow.</h2></div>
        <div><p>Every stored memory requires provenance. Every disclosure is logged. Revoking one client does not remove memory from other authorized clients.</p><Link href="/privacy/">Compare local and hosted trust boundaries →</Link></div>
      </section>

      <section className="beta-cta">
        <div className="shell"><p className="section-label section-label--light">Founding Public Beta</p><h2>Help prove cross-provider memory.</h2><p>The hosted beta is still being built. If you want to test it when the acceptance gate passes, contact the founder.</p><a className="button button--acid" href="mailto:hello@ninai.io?subject=Ninai%20Public%20Beta">Join the tester list ↗</a></div>
      </section>
    </main>
  );
}
