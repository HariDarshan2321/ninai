import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Help and support",
  description: "Get help with Ninai setup, assistant connections, memory access, updates, and security reports.",
  alternates: { canonical: "/support/" },
  openGraph: {
    title: "Ninai help and support",
    description: "Clear steps for setup, connections, updates, and safe feedback.",
    url: "/support/",
    images: [{ url: "/assets/og-image.png", width: 1200, height: 630, alt: "Ninai support" }],
  },
};

export default function SupportPage() {
  return <main id="main-content">
    <section className="page-hero page-hero--privacy"><div className="shell page-hero__grid">
      <div><p className="section-label section-label--light">Help and support</p><h1>Get back to<br />your work.</h1></div>
      <div className="page-hero__aside"><p>Start with the steps below. If you still need help, tell us what you tried and what happened.</p><a className="button button--acid" href="mailto:hello@ninai.io?subject=Ninai%20support">Email Ninai support ↗</a></div>
    </div></section>
    <section className="privacy-sections shell">
      <article><span className="privacy-index">01</span><div><h2>Install or update Ninai</h2><p>Use the <Link href="/install/">installation guide</Link> for the current setup path and platform status. Existing desktop apps need an app update to receive interface changes. Do not uninstall or delete your memory folder to troubleshoot an update.</p><p>In the updated desktop app, open Help &amp; feedback for version checks and recovery guidance. Signed installer availability is a separate release step; a working source installation does not establish signing or platform certification.</p></div></article>
      <article><span className="privacy-index">02</span><div><h2>Connect an assistant</h2><p>A configured connection and memory access are separate. Choose the project and access you want the assistant to have, then start a new chat after changing its connection. New project access stays off until you grant it.</p><p>If a memory is missing, check its project, the assistant&apos;s Read access, and whether the memory is active. A proposal awaiting review will not be recalled. A connection alone does not guarantee that every assistant will automatically retrieve or save memories.</p><p>Local memory and an explicitly enabled cloud connection are separate stores. Ninai does not silently upload your local memory.</p></div></article>
      <article><span className="privacy-index">03</span><div><h2>Send useful feedback</h2><p>Email <a href="mailto:hello@ninai.io?subject=Ninai%20feedback">hello@ninai.io</a> with your operating system, Ninai version, assistant, the step you tried, and what you expected. Include a screenshot only after removing private information.</p><p>Do not send passwords, access tokens, database addresses containing credentials, private memories, or full conversation exports. Nothing is sent automatically from this page.</p></div></article>
      <article><span className="privacy-index">04</span><div><h2>Report a security concern</h2><p>Use <a href="mailto:hello@ninai.io?subject=Ninai%20security%20report">hello@ninai.io</a> with the subject “Ninai security report”. Describe the affected feature and steps to reproduce using synthetic examples. Do not include real credentials or another person&apos;s data.</p><p>For data access or deletion requests, see the <Link href="/privacy/">privacy policy</Link>. We may need to verify account ownership before acting.</p></div></article>
    </section>
  </main>;
}
