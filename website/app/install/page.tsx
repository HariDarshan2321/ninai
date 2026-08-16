import type { Metadata } from "next";
export const metadata: Metadata = {
  title: "Install Ninai for Mac",
  description:
    "Sign in, download Ninai for Mac, and connect Claude Code and Codex with one guided installer.",
  alternates: { canonical: "/install/" },
  openGraph: {
    title: "Install Ninai for Mac",
    description: "One local vault for Claude Code and Codex.",
    url: "/install/",
    images: [
      {
        url: "/assets/og-image.png",
        width: 1200,
        height: 630,
        alt: "Install the Ninai local AI memory vault for Mac",
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
              Sign in, download, and run one command. Ninai detects supported agents, connects
              them, and opens your private local vault.
            </p>
            <div className="hero-actions">
              <a className="button button--acid" href={signupUrl}>Create account ↗</a>
              <a className="button button--ink" href={signinUrl}>Sign in</a>
            </div>
          </div>
        </div>
      </section>

      <section className="install-choice shell" aria-label="Ninai Mac setup">
        <article id="local">
          <span className="status-pill status-pill--ready">1 · Sign in</span>
          <h2>Create your Ninai account</h2>
          <p>Your account unlocks the official installer and lets us count beta users. Your memory vault is not uploaded.</p>
          <a href={signinUrl}>Sign in for the Mac installer →</a>
        </article>
        <article>
          <span className="status-pill status-pill--ready">2 · Install</span>
          <h2>Run one guided installer</h2>
          <p>It installs Ninai, detects Claude Code and Codex, connects every detected supported agent, and opens the app.</p>
          <a href={signinUrl}>Open signed-in setup →</a>
        </article>
      </section>

      <section className="beta-trust shell">
        <div>
          <p className="section-label">The MVP path</p>
          <h2>No cloud choices. No connector forms.</h2>
        </div>
        <div>
          <p>
            Ninai supports local Claude Code and Codex today. Cloud-hosted vaults are coming later,
            after the security and acceptance gates are complete.
          </p>
          <a href="/privacy/">See how data moves →</a>
        </div>
      </section>
    </main>
  );
}
