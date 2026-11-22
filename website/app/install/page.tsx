import Link from "next/link";

import InstallWalkthrough from "../../components/InstallWalkthrough";
import EmailContact from "../../components/email-contact";
import { pageMetadata } from "../site-metadata";

export const metadata = pageMetadata({
  path: "/install/",
  title: "Mac Setup for Claude Code and Codex",
  description: "Follow the Ninai Mac source setup, connect Claude Code and Codex, and test project memory with separate permissions for each assistant.",
});

const signupUrl = "https://app.ninai.io/control/login?screen_hint=signup";
const signinUrl = "https://app.ninai.io/control/login";

export default function InstallPage() {
  return (
    <main id="main-content" tabIndex={-1}>
      <section className="page-hero page-hero--install">
        <div className="shell page-hero__grid">
          <div><h1>Install Ninai on Mac.</h1></div>
          <div className="page-hero__aside">
            <p>Sign in to get the Mac installer. It connects Claude Code and Codex when it finds them on your Mac. You choose each assistant’s project permissions afterward.</p>
            <div className="hero-actions">
              <a className="button button--acid" href={signupUrl}>Create account for Mac setup <span aria-hidden="true">↗</span></a>
              <a className="button button--ink" href={signinUrl}>Sign in for Mac setup</a>
            </div>
            <p className="install-note">The official installer builds Ninai from source. It requires Python 3.11 or newer and Apple Command Line Tools. A signed, notarized package is pending. Signing in neither uploads nor syncs your local vault.</p>
          </div>
        </div>
      </section>

      <section className="platform-choice shell" aria-labelledby="platform-title">
        <div className="platform-choice__intro"><h2 id="platform-title">Supported platforms</h2><p>See <Link href="/compatibility/">assistant compatibility</Link> for tested and preview integrations.</p></div>
        <div className="platform-choice__items">
          <article><span className="status-pill status-pill--ready">Source setup available</span><h3>macOS</h3><p>Local handoff from Claude Code to Codex is verified.</p></article>
          <article className="platform-choice__future"><span className="status-pill">Preview only</span><h3>Windows</h3><p>A source setup script is available for testing. A signed Windows installer and clean-machine verification are still pending.</p><EmailContact label="Ask about Windows testing" subject="Ninai for Windows" /></article>
        </div>
      </section>

      <section className="install-choice shell" aria-label="Ninai setup steps">
        <article><span className="status-pill status-pill--ready">1 · Install</span><h2>Follow the Mac setup</h2><p>Check the prerequisites, then run the source installer. Review the command before running it.</p></article>
        <article><span className="status-pill status-pill--ready">2 · Connect</span><h2>Choose project access</h2><p>Ninai configures detected supported assistants. In the app, choose which project memories each one may read or save.</p></article>
        <article><span className="status-pill status-pill--ready">3 · Check</span><h2>Test with a sample project</h2><p>Save a sample decision, start a fresh assistant session, and ask it to recall the decision.</p></article>
      </section>

      <InstallWalkthrough />

      <section className="beta-trust shell">
        <div><p className="section-label">What stays private</p><h2>With local setup, your memory stays on your computer.</h2></div>
        <div><p>Ninai returns project memory according to the permissions you grant. You can review what Ninai shared and turn off future access.</p><Link href="/governance/">See how project permissions work <span aria-hidden="true">↗</span></Link></div>
      </section>
    </main>
  );
}
