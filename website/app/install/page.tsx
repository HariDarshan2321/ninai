import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Install Ninai",
  description: "Install Ninai, connect your AI assistants, and keep project context private on your computer.",
  alternates: { canonical: "/install/" },
  openGraph: {
    title: "Install Ninai",
    description: "Private, permissioned memory shared by your AI assistants.",
    url: "/install/",
    images: [{ url: "/assets/og-image.png", width: 1200, height: 630, alt: "Install Ninai" }],
  },
};

const signupUrl = "https://app.ninai.io/control/login?screen_hint=signup";
const signinUrl = "https://app.ninai.io/control/login";

export default function InstallPage() {
  return (
    <main id="main-content">
      <section className="page-hero page-hero--install">
        <div className="shell page-hero__grid">
          <div><p className="section-label">Install Ninai</p><h1>Connect your assistants in one guided setup.</h1></div>
          <div className="page-hero__aside">
            <p>Ninai checks which supported AI assistants are already on your computer, connects the ones you choose, and keeps their shared memory on your device.</p>
            <div className="hero-actions">
              <a className="button button--acid" href={signupUrl}>Get the Mac installer ↗</a>
              <a className="button button--ink" href={signinUrl}>I already have an account</a>
            </div>
            <p className="install-note">Your account provides the official installer and product updates. Your local memories are not uploaded to the account.</p>
          </div>
        </div>
      </section>

      <section className="platform-choice shell" aria-labelledby="platform-title">
        <div className="platform-choice__intro"><p className="section-label">Choose your computer</p><h2 id="platform-title">Start on Mac</h2><p>Claude Code and Codex are the verified local handoff path today.</p></div>
        <div className="platform-choice__items">
          <article><span className="status-pill status-pill--ready">Available</span><h3>macOS</h3><p>Works with Claude Code, Codex, and Gemini CLI beta.</p><a className="text-link" href={signupUrl}>Get the Mac installer ↗</a></article>
          <article className="platform-choice__future"><span className="status-pill">In development</span><h3>Windows</h3><p>A signed Windows installer is being built and tested. It is not available today.</p><a className="text-link" href="mailto:hello@ninai.io?subject=Ninai%20for%20Windows">Join the Windows test group</a></article>
        </div>
      </section>

      <section className="install-choice shell" aria-label="Ninai setup steps">
        <article><span className="status-pill status-pill--ready">1 · Install</span><h2>Open the installer</h2><p>Download the version for your computer and follow the prompts.</p></article>
        <article><span className="status-pill status-pill--ready">2 · Connect</span><h2>Choose your assistants</h2><p>Ninai shows what it found. You decide which assistants to connect.</p></article>
        <article><span className="status-pill status-pill--ready">3 · Check</span><h2>Run a private test</h2><p>Save one sample decision, open another assistant, and confirm that it can recall it.</p></article>
      </section>

      <section className="install-video shell" aria-labelledby="video-title">
        <div><p className="section-label">Installation concept</p><h2 id="video-title">Preview the planned setup</h2><p>This concept guide shows the experience we are building. A real installation recording will replace it after the signed installer is ready.</p></div>
        <video controls preload="metadata" poster="/assets/og-image.png"><source src="/assets/ninai-install-guide.mp4" type="video/mp4" />Your browser does not support embedded video.</video>
      </section>

      <section className="beta-trust shell">
        <div><p className="section-label">What stays private</p><h2>Your complete memory stays on your computer.</h2></div>
        <div><p>Each connected assistant receives only the relevant memories allowed for it. Ninai records what was shared, and you can remove access at any time.</p><a href="/privacy/">See how information moves →</a></div>
      </section>
    </main>
  );
}
