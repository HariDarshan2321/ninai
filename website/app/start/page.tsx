import type { Metadata } from "next";
export const metadata: Metadata = {
  title: "Ninai cloud is coming later",
  description: "Ninai is focused on a simple, private Mac experience for Claude Code and Codex. Hosted vaults are coming later.",
  alternates: { canonical: "/start/" },
  openGraph: {
    title: "Ninai cloud is coming later",
    description: "Use the local Mac MVP today.",
    url: "/start/",
    images: [{ url: "/assets/og-image.png", width: 1200, height: 630, alt: "Start with Ninai" }],
  },
};

export default function StartPage() {
  return (
    <main id="main-content">
      <section className="page-hero page-hero--install">
        <div className="shell page-hero__grid">
          <div><p className="section-label">Cloud vault</p><h1>Coming later.</h1></div>
          <div className="page-hero__aside"><p>We are focusing the MVP on one excellent Mac setup. Hosted storage will return after security review and real customer acceptance.</p><div className="hero-actions"><a className="button button--acid" href="/install/">Get Ninai for Mac ↗</a></div></div>
        </div>
      </section>
      <section className="install-choice onboarding-steps shell" aria-label="Available Ninai experience">
        <article><span className="status-pill status-pill--ready">Available</span><h2>Private Mac vault</h2><p>Your memory stays on your Mac and works with detected Claude Code and Codex installations.</p></article>
        <article><span className="status-pill">Later</span><h2>Hosted vault</h2><p>No public cloud onboarding or remote connector setup is offered in this MVP.</p></article>
      </section>
      <section className="privacy-cta"><div className="shell"><h2>Use the working MVP today.</h2><p>Sign in, download, and let the guided installer connect your supported local agents.</p><div><a className="button button--acid" href="https://app.ninai.io/control/login">Sign in for Mac setup ↗</a><a className="button button--dark-line" href="/privacy/">Read privacy details</a></div></div></section>
    </main>
  );
}
