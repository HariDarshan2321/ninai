import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Start with Ninai hosted AI memory",
  description: "Create a Ninai hosted workspace, connect Claude or ChatGPT, and grant one project in a few steps.",
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
          <div><p className="section-label">Hosted onboarding</p><h1>Create a vault. Connect one AI. Choose one project.</h1></div>
          <div className="page-hero__aside"><p>Ninai denies access by default. Connecting creates an empty-permission client; you decide which project it can read or propose to.</p><div className="hero-actions"><a className="button button--acid" href="https://ninai-cloud.onrender.com/control/login?screen_hint=signup">Create account ↗</a><a className="button button--ink" href="https://ninai-cloud.onrender.com/control/login">Sign in</a></div></div>
        </div>
      </section>
      <section className="install-choice onboarding-steps shell" aria-label="Hosted onboarding steps">
        <article><span className="status-pill status-pill--ready">Account setup</span><h2>1. Create a workspace</h2><p>Sign up, name your workspace, and create the first project. Local Mac memory is not uploaded.</p></article>
        <article><span className="status-pill">Zero access initially</span><h2>2. Connect an AI</h2><p>Choose Ninai in Claude or ChatGPT when listed, or add the hosted MCP endpoint during beta.</p></article>
        <article><span className="status-pill">Explicit grant</span><h2>3. Select a project</h2><p>Open Connections, grant read and propose access to one project, then test a safe synthetic memory.</p></article>
      </section>
      <section className="privacy-cta"><div className="shell"><h2>Prefer a private Mac vault?</h2><p>Install local mode without creating an account.</p><div><Link className="button button--acid" href="/install/#local-install">Install locally ↗</Link><Link className="button button--dark-line" href="/privacy/">Read privacy details</Link></div></div></section>
    </main>
  );
}
