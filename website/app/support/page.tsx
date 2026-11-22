import Link from "next/link";

import { pageMetadata } from "../site-metadata";

export const metadata = pageMetadata({
  path: "/support/",
  title: "Help and Support",
  description: "Get help installing Ninai, connecting Claude Code and Codex, managing project access, and reporting security issues.",
});

export default function SupportPage() {
  return (
    <main id="main-content" tabIndex={-1}>
      <section className="page-hero page-hero--privacy">
        <div className="shell page-hero__grid">
          <h1>Help and support</h1>
          <div className="page-hero__aside">
            <p>Get help with installation, assistant connections, and memory access.</p>
            <a className="button button--acid" href="mailto:hello@ninai.io?subject=Ninai%20support">
              Email support <span aria-hidden="true">↗</span>
            </a>
          </div>
        </div>
      </section>

      <section className="privacy-sections support-topics shell" aria-label="Support topics">
        <article>
          <div>
            <h2>Install or update Ninai</h2>
            <p>Follow the <Link href="/install/">installation guide</Link> for current requirements. In the desktop app, open Help &amp; feedback for version and recovery information. Keep your memory folder when troubleshooting an update.</p>
          </div>
        </article>
        <article>
          <div>
            <h2>Connect an assistant</h2>
            <p>Grant the assistant access to the project you want it to use, then start a fresh session. If a memory is missing, check its project, the assistant&apos;s Read access, and whether the memory has been approved.</p>
            <p>For hosted setup, use the same account and sign-in method in your dashboard and assistant. Google sign-in and email/password can create separate accounts even when the email address matches.</p>
            <p>For a disconnected hosted assistant, choose Reconnect on its connection card, grant project access again, and try a fresh recall. If you removed the connection from the assistant or sign-in provider, reconnect it there too.</p>
          </div>
        </article>
        <article>
          <div>
            <h2>Send feedback</h2>
            <p>Email <a href="mailto:hello@ninai.io?subject=Ninai%20feedback">hello@ninai.io</a> with your operating system, Ninai version, assistant, and the steps you tried. Share screenshots only after removing private information. Keep credentials, private memories, and full conversation exports out of the message.</p>
          </div>
        </article>
        <article id="security">
          <div>
            <h2>Report a security issue</h2>
            <p>Email <a href="mailto:hello@ninai.io?subject=Ninai%20security%20report">hello@ninai.io</a> with the subject “Ninai security report”. Name the affected feature and explain how to reproduce the issue with sample data. Leave out real credentials and other people&apos;s data.</p>
            <p>For access to or deletion of your data, see the <Link href="/privacy/">privacy policy</Link>. We may need to verify account ownership.</p>
          </div>
        </article>
      </section>
    </main>
  );
}
