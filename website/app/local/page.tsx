import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Local AI memory for Claude Code and Codex",
  description: "Install Ninai once and give Claude Code and Codex the same private project memory on your Mac.",
  alternates: { canonical: "/local/" },
  openGraph: { title: "Ninai local engine", description: "Open-source, local-first AI memory with explicit boundaries.", url: "/local/", images: [{ url: "/assets/og-image.png", width: 1200, height: 630, alt: "Ninai local engine" }] },
};

export default function LocalPage() {
  return <main id="main-content">
    <section className="page-hero"><div className="shell page-hero__grid"><div><p className="section-label">Available now for Mac</p><h1>Your project memory stays with you.</h1></div><div className="page-hero__aside"><p>Install Ninai once. It connects detected Claude Code and Codex installations and keeps the complete memory vault on your Mac.</p><div className="requirement-row"><span>Works with</span><strong>Claude Code + Codex</strong><span>Storage</span><strong>On your Mac</strong><span>Setup</span><strong>One installer</strong></div></div></div></section>
    <section className="mode-section shell"><div className="section-intro"><p className="section-label">What you get</p><h2>Continue without repeating yourself.</h2><p>Ninai keeps useful project decisions ready when you switch agents.</p></div><div className="lifecycle-grid"><article><span>01</span><h3>Install once</h3><p>Ninai finds and connects supported agents.</p></article><article><span>02</span><h3>Switch agents</h3><p>Claude Code and Codex can continue with the same project decisions.</p></article><article><span>03</span><h3>Stay in control</h3><p>See sources and turn future access off from the local app.</p></article></div></section>
    <section className="beta-trust shell"><div><p className="section-label">Honest limits</p><h2>Local-first does not mean nothing leaves.</h2></div><div><p>The complete vault stays local. When an AI uses a selected context packet, that packet is sent to the provider and its data policy applies. The MVP does not claim database encryption, signed desktop releases, or an independent security audit.</p><Link href="/privacy/">Read the privacy architecture →</Link></div></section>
    <section className="beta-cta"><div className="shell"><h2>Get Ninai for Mac.</h2><p>Sign in, download, and run one command.</p><a className="button button--acid" href="https://app.ninai.io/control/login">Sign in to install ↗</a></div></section>
  </main>;
}
