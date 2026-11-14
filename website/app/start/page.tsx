import type { Metadata } from "next";
export const metadata: Metadata = {
  title: "Choose your Ninai setup",
  description: "Choose local memory on your Mac or a separate, opt-in Ninai Cloud workspace. Local memory is never uploaded automatically.",
  alternates: { canonical: "/start/" },
  robots: { index: false, follow: true },
  openGraph: {
    title: "Choose your Ninai setup",
    description: "Local and hosted memory are separate choices.",
    url: "/start/",
    images: [{ url: "/assets/og-image.png", width: 1200, height: 630, alt: "Start with Ninai" }],
  },
};

export default function StartPage() {
  return (
    <main id="main-content">
      <section className="page-hero page-hero--install">
        <div className="shell page-hero__grid">
          <div><p className="section-label">Choose your setup</p><h1>Your memory.<br />Your choice.</h1></div>
          <div className="page-hero__aside"><p>Keep memory on your Mac, or choose a separate Ninai Cloud workspace. Signing in does not upload or synchronize your local memory.</p><div className="hero-actions"><a className="button button--acid" href="https://app.ninai.io/control/login">Sign in for setup ↗</a></div></div>
        </div>
      </section>
      <section className="install-choice onboarding-steps shell" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 320px), 1fr))" }} aria-label="Available Ninai experience">
        <article><span className="status-pill">On your Mac</span><h2>Local memory</h2><p>Use the Mac source installer with supported assistants. Your local memory stays on your computer; you choose what an assistant can access.</p></article>
        <article><span className="status-pill">Optional cloud</span><h2>Hosted memory</h2><p>Connect an assistant to a separate hosted workspace and choose its project access. Memory submitted there is stored in Ninai Cloud. Local memory is not transferred automatically.</p></article>
      </section>
      <section className="privacy-cta"><div className="shell"><h2>Verify your first handoff.</h2><p>Review installation requirements and compatibility, then test a real memory recall and revocation before relying on either setup.</p><div><a className="button button--acid" href="/install/">See installation options ↗</a><a className="button button--dark-line" href="/privacy/">Read privacy details</a></div></div></section>
    </main>
  );
}
