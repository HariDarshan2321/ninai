import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Choose local or hosted Ninai AI memory",
  description:
    "Choose a private Mac vault or a hosted Ninai workspace. Sign in to access setup and connect Claude Code or Codex.",
  alternates: { canonical: "/install/" },
  openGraph: {
    title: "Choose how to use Ninai",
    description: "Private on your Mac or available through a hosted workspace.",
    url: "/install/",
    images: [
      {
        url: "/assets/og-image.png",
        width: 1200,
        height: 630,
        alt: "Choose a local or hosted Ninai vault",
      },
    ],
  },
};

const signupUrl = "https://app.ninai.io/control/login?screen_hint=signup";
const signinUrl = "https://app.ninai.io/control/login";

export default function InstallPage() {
  return (
    <main id="main-content">
      <section className="page-hero page-hero--install">
        <div className="shell page-hero__grid">
          <div>
            <p className="section-label">Get Ninai</p>
            <h1>Switch agents. Keep the project.</h1>
          </div>
          <div className="page-hero__aside">
            <p>
              Ninai gives Claude Code and Codex the same source-backed project memory. Choose
              where your vault lives, then sign in for the guided setup.
            </p>
            <div className="hero-actions">
              <a className="button button--acid" href={signupUrl}>Create account ↗</a>
              <a className="button button--ink" href={signinUrl}>Sign in</a>
            </div>
          </div>
        </div>
      </section>

      <section className="install-choice shell" aria-label="Choose where Ninai stores your vault">
        <article id="local">
          <span className="status-pill status-pill--ready">macOS · available</span>
          <h2>Keep it local</h2>
          <p>
            Your vault stays in SQLite on this Mac. Best for Claude Code and Codex running
            locally. Ninai never uploads this vault automatically.
          </p>
          <a href={signinUrl}>Sign in for the Mac installer →</a>
        </article>
        <article id="hosted">
          <span className="status-pill">Invitation beta</span>
          <h2>Use a hosted vault</h2>
          <p>
            Create a workspace for approved project memory that supported remote AI clients
            can access through OAuth. Every connection starts with zero project access.
          </p>
          <Link href="/start/">See hosted onboarding →</Link>
        </article>
      </section>

      <section className="beta-trust shell">
        <div>
          <p className="section-label">One account gate</p>
          <h2>Understand it here. Set it up after sign-in.</h2>
        </div>
        <div>
          <p>
            The public site explains the product and its boundaries. Your Ninai account unlocks
            the local installer, hosted connection instructions, permissions, and the handoff test
            in one control center.
          </p>
          <Link href="/privacy/">See how data moves →</Link>
        </div>
      </section>
    </main>
  );
}
