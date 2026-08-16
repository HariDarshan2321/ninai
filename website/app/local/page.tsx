import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Local AI memory for Claude Code and Codex",
  description: "Run Ninai's permissioned MCP memory engine locally with SQLite, provenance, explicit scopes, disclosure logs, and no automatic cloud sync.",
  alternates: { canonical: "/local/" },
  openGraph: { title: "Ninai local engine", description: "Open-source, local-first AI memory with explicit boundaries.", url: "/local/", images: [{ url: "/assets/og-image.png", width: 1200, height: 630, alt: "Ninai local engine" }] },
};

export default function LocalPage() {
  return <main id="main-content">
    <section className="page-hero"><div className="shell page-hero__grid"><div><p className="section-label">Local engine · available now</p><h1>Your vault. Your machine.</h1></div><div className="page-hero__aside"><p>Ninai local mode is an open-source Python MCP server backed by SQLite. It does not automatically upload or sync your vault.</p><div className="requirement-row"><span>Runtime</span><strong>Python 3.11+</strong><span>Storage</span><strong>Local SQLite</strong><span>Setup</span><strong>Ninai sign-in</strong></div></div></div></section>
    <section className="mode-section shell"><div className="section-intro"><p className="section-label">Implemented boundaries</p><h2>Small, inspectable, and permissioned.</h2><p>The local engine stores compact durable memories, requires a source URI, filters recall by explicit client scopes, observes token budgets, and records disclosures.</p></div><div className="lifecycle-grid"><article><span>01</span><h3>Capture with consent</h3><p>Optional lifecycle hooks archive local Claude Code and Codex sessions. Browser chats are not passively captured.</p></article><article><span>02</span><h3>Recall narrowly</h3><p>Only current memories in a requesting client&apos;s granted scopes are eligible.</p></article><article><span>03</span><h3>Audit release</h3><p>Inspect which memory was disclosed, to which client, and why.</p></article><article><span>04</span><h3>Revoke safely</h3><p>Remove future access without erasing memory authorized clients may still need.</p></article></div></section>
    <section className="beta-trust shell"><div><p className="section-label">Honest limits</p><h2>Local-first does not mean nothing leaves.</h2></div><div><p>The complete vault stays local. When an AI uses a selected context packet, that packet is sent to the provider and its data policy applies. The MVP does not claim database encryption, signed desktop releases, or an independent security audit.</p><Link href="/privacy/">Read the privacy architecture →</Link></div></section>
    <section className="beta-cta"><div className="shell"><h2>Run the local engine today.</h2><p>Sign in for the guided Mac installer. After setup, the vault runs locally without automatic cloud sync.</p><a className="button button--acid" href="https://app.ninai.io/control/login">Sign in for Mac setup ↗</a></div></section>
  </main>;
}
