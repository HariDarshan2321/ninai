import type { Metadata } from "next";
export const metadata: Metadata = {
  title: "Start with Ninai hosted AI memory",
  description: "Sign in to create a Ninai hosted workspace, connect a supported AI client, and grant one project.",
  alternates: { canonical: "/start/" },
  openGraph: {
    title: "Start with Ninai",
    description: "Create a workspace, connect an AI, and choose what it can remember.",
    url: "/start/",
    images: [{ url: "/assets/og-image.png", width: 1200, height: 630, alt: "Start with Ninai" }],
  },
};

export default function StartPage() {
  return (
    <main id="main-content">
      <section className="page-hero page-hero--install">
        <div className="shell page-hero__grid">
          <div><p className="section-label">Hosted invitation beta</p><h1>One workspace. One project. Your rules.</h1></div>
          <div className="page-hero__aside"><p>Sign in before setup. Each OAuth connection begins with no project access; you choose what it may read or propose.</p><div className="hero-actions"><a className="button button--acid" href="https://app.ninai.io/control/login?screen_hint=signup">Create account ↗</a><a className="button button--ink" href="https://app.ninai.io/control/login">Sign in</a></div></div>
        </div>
      </section>
      <section className="install-choice onboarding-steps shell" aria-label="Hosted onboarding steps">
        <article><span className="status-pill status-pill--ready">Account</span><h2>1. Name one project</h2><p>Create a workspace and the project boundary your AI tools may share.</p></article>
        <article><span className="status-pill">Connection</span><h2>2. Add a supported AI</h2><p>Follow the signed-in guide for Claude Code, Codex, or a supported remote MCP surface.</p></article>
        <article><span className="status-pill">Permission</span><h2>3. Grant, then verify</h2><p>Choose read or propose access, run one safe handoff, and inspect the disclosure receipt.</p></article>
      </section>
      <section className="privacy-cta"><div className="shell"><h2>Prefer a private Mac vault?</h2><p>Your signed-in control center also provides the macOS installer. The local vault stays on your Mac after installation.</p><div><a className="button button--acid" href="https://app.ninai.io/control/login">Sign in for local setup ↗</a><a className="button button--dark-line" href="/privacy/">Read privacy details</a></div></div></section>
    </main>
  );
}
