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
        <article>
          <span className="status-pill status-pill--ready">1 · Sign in</span>
          <h2>Create an account</h2>
          <p>This unlocks the official installer. Your local vault is not uploaded.</p>
        </article>
        <article>
          <span className="status-pill status-pill--ready">2 · Download</span>
          <h2>Get Ninai for Mac</h2>
          <p>Your signed-in setup page gives you the installer and one command.</p>
        </article>
        <article>
          <span className="status-pill status-pill--ready">3 · Continue</span>
          <h2>Open Ninai</h2>
          <p>The installer finds Claude Code and Codex, connects them, and opens your vault.</p>
        </article>
      </section>

      <section className="beta-trust shell">
        <div>
          <p className="section-label">The MVP path</p>
          <h2>That is the whole setup.</h2>
        </div>
        <div>
          <p>
            The MVP supports Claude Code and Codex on Mac. Cloud-hosted vaults are coming later.
          </p>
          <a href="/privacy/">See how data moves →</a>
        </div>
      </section>
    </main>
  );
}
