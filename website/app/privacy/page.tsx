import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Privacy Policy",
  description: "How Ninai handles account data, authenticated installer access, local Mac vaults, connected AI providers, deletion, and security.",
  alternates: { canonical: "/privacy/" },
  openGraph: { title: "Ninai Privacy Policy", description: "The local Mac vault and account boundary, stated plainly.", url: "/privacy/", images: [{ url: "/assets/og-image.png", width: 1200, height: 630, alt: "Ninai privacy" }] },
};

export default function PrivacyPage() {
  return <main id="main-content">
    <section className="page-hero page-hero--privacy"><div className="shell page-hero__grid">
      <div><p className="section-label section-label--light">Privacy Policy</p><h1>Your memory.<br />A visible boundary.</h1></div>
      <div className="page-hero__aside"><p>Your Ninai vault stays on your Mac. Signing in unlocks the official installer; it does not upload your vault.</p><span className="privacy-version">Effective 1 August 2026</span></div>
    </div></section>

    <section className="mode-section shell"><div className="mode-grid">
      <article className="mode-card"><span className="status-pill status-pill--ready">Local</span><h2>Stored on your Mac</h2><p>Sign-in is required to access the installer and setup guide. After installation, the SQLite vault, sources, grants, and logs remain on your device and no automatic cloud sync runs.</p><p>If you ask a cloud AI to use selected context, that packet leaves the device and the provider&apos;s policy applies.</p></article>
      <article className="mode-card mode-card--future"><span className="status-pill">Coming later</span><h2>Hosted vault</h2><p>Public hosted storage and remote connectors are not offered in the MVP.</p><p>The infrastructure remains under evaluation until security and external acceptance gates are complete.</p></article>
    </div></section>

    <section className="privacy-sections shell">
      <article><span className="privacy-index">01</span><div><p className="section-label">Account data</p><h2>What we process.</h2><ul><li>Account identifiers supplied by Auth0, such as email, display name, and identity subject.</li><li>A minimal internal setup record used to unlock the authenticated installer.</li><li>An installer-download receipt containing your account, platform, installer hash, and time. We do not store an IP address or browser fingerprint with this receipt.</li><li>Limited operational and security logs needed to run and protect the service.</li></ul><p>We use this data only to provide, secure, troubleshoot, and improve Ninai. Ninai does not sell personal data, run behavioral advertising, or train a Ninai model on your local vault.</p></div></article>
      <article><span className="privacy-index">02</span><div><p className="section-label">Service providers</p><h2>Who helps operate the service.</h2><p>Auth0 provides authentication, Render hosts the account service and authenticated installer, Vercel hosts the public website, and GitHub hosts the public source repository. Their processing is governed by their own terms.</p><p>OpenAI or Anthropic receives selected local context only when a connected agent requests it. Provider retention and model-training choices are controlled by your provider account and its policy, not by Ninai.</p></div></article>
      <article><span className="privacy-index">03</span><div><p className="section-label">Local permissions</p><h2>Connected does not mean unlimited.</h2><p>Ninai connects supported agents to the local engine. Project grants and approvals determine which memory an agent can read or propose. You can revoke access from the local app.</p></div></article>
      <article><span className="privacy-index">04</span><div><p className="section-label">Retention and control</p><h2>Your vault stays under your control.</h2><p>The local vault remains on your Mac until you delete it. Account and installer-download records remain in the account service while the account is active and may remain temporarily in infrastructure backups after deletion until those backups rotate.</p><p>For access, correction, portability, deletion, or objection requests, email <a href="mailto:privacy@ninai.io">privacy@ninai.io</a>. We may need to verify the request.</p></div></article>
      <article><span className="privacy-index">05</span><div><p className="section-label">Safety</p><h2>Credentials are not memory.</h2><p>Ninai blocks common secret patterns and applies local authorization. These controls reduce risk but do not make the beta suitable for passwords, private keys, health records, payment-card data, government identifiers, children&apos;s data, or other high-risk regulated information.</p></div></article>
      <article><span className="privacy-index">06</span><div><p className="section-label">International processing</p><h2>Account data may cross borders.</h2><p>Our account, website, and source-hosting providers may process account and operational data in countries different from yours. The Ninai vault itself remains on your Mac unless you deliberately disclose selected context to an AI provider.</p></div></article>
      <article><span className="privacy-index">07</span><div><p className="section-label">Security and changes</p><h2>An MVP, not a certification.</h2><ul><li>No signed and notarized desktop package yet.</li><li>No independent security audit or compliance certification yet.</li><li>No prompt-injection classifier or guarantee that an AI provider will interpret context correctly.</li></ul><p>We may update this policy as the service changes. Material updates will receive a new effective date on this page. Security reports: <a href="mailto:security@ninai.io">security@ninai.io</a>.</p></div></article>
    </section>
    <section className="privacy-cta"><div className="shell"><h2>Keep the vault on your Mac.</h2><p>The MVP is local-first. Cloud-hosted vaults are coming later.</p><div><a className="button button--acid" href="https://app.ninai.io/control/login">Sign in for Mac setup ↗</a></div><Link href="/terms/">Read the Terms of Service →</Link></div></section>
  </main>;
}
