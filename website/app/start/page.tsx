import type { Metadata } from "next";
export const metadata: Metadata = {
  title: "Ninai cloud is coming later",
  description: "Ninai is focused on a simple, private Mac experience for Claude Code and Codex. Hosted vaults are coming later.",
  alternates: { canonical: "/start/" },
  robots: { index: false, follow: true },
  openGraph: {
    title: "Ninai cloud is coming later",
    description: "Use the private Mac release today.",
    url: "/start/",
    images: [{ url: "/assets/og-image.png", width: 1200, height: 630, alt: "Start with Ninai" }],
  },
};

export default function StartPage() {
  return (
    <main id="main-content">
      <section className="page-hero page-hero--install">
        <div className="shell page-hero__grid">
          <div><p className="section-label">Hosted memory</p><h1>Coming later.</h1></div>
          <div className="page-hero__aside"><p>We are focusing on one excellent computer-based setup. Hosted storage will return after security review and real customer acceptance.</p><div className="hero-actions"><a className="button button--acid" href="/install/">See installation options ↗</a></div></div>
        </div>
      </section>
      <section className="install-choice onboarding-steps shell" aria-label="Available Ninai experience">
        <article><span className="status-pill status-pill--ready">Available</span><h2>Private Mac vault</h2><p>Your memory stays on your Mac and works with detected Claude Code and Codex installations.</p></article>
        <article><span className="status-pill">Later</span><h2>Hosted memory</h2><p>Public cloud storage and remote connector setup are not offered today.</p></article>
      </section>
      <section className="privacy-cta"><div className="shell"><h2>Start with the private Mac release.</h2><p>Review the setup, choose your supported assistants, and test one memory handoff.</p><div><a className="button button--acid" href="/install/">See installation options ↗</a><a className="button button--dark-line" href="/privacy/">Read privacy details</a></div></div></section>
    </main>
  );
}
