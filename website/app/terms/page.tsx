import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Terms of Service",
  description: "Terms governing the Ninai website, account, authenticated Mac installer, and local AI memory software.",
  alternates: { canonical: "/terms/" },
  openGraph: {
    title: "Ninai Terms of Service",
    description: "Terms for the Ninai account, Mac installer, and local AI memory software.",
    url: "/terms/",
    images: [{ url: "/assets/og-image.png", width: 1200, height: 630, alt: "Ninai" }],
  },
};

export default function TermsPage() {
  return (
    <main id="main-content">
      <section className="page-hero page-hero--privacy">
        <div className="shell page-hero__grid">
          <div><p className="section-label section-label--light">Legal</p><h1>Terms of Service.</h1></div>
          <div className="page-hero__aside"><p>These terms apply to the Ninai website, account, authenticated Mac installer, and local software.</p><span className="privacy-version">Effective 1 August 2026</span></div>
        </div>
      </section>

      <section className="privacy-sections shell">
        <article><span className="privacy-index">01</span><div><p className="section-label">Agreement</p><h2>Using Ninai means accepting these terms.</h2><p>You must be legally able to enter this agreement. If you use Ninai for an organization, you confirm that you may bind that organization. Do not use the service if you do not accept these terms.</p></div></article>
        <article><span className="privacy-index">02</span><div><p className="section-label">The service</p><h2>The public MVP runs locally on Mac.</h2><p>Your Ninai vault is stored on your device. An account unlocks the official installer and setup guide; it does not upload your local vault. Cloud-hosted vaults are planned for later and are not offered as part of this public MVP. Features may change during the beta, and uninterrupted availability is not guaranteed.</p></div></article>
        <article><span className="privacy-index">03</span><div><p className="section-label">Your account and content</p><h2>You control what you submit.</h2><p>You are responsible for your account, connected local clients, permissions, and content. You retain rights in your content. Do not submit content you lack permission to use.</p></div></article>
        <article><span className="privacy-index">04</span><div><p className="section-label">Acceptable use</p><h2>Do not misuse the service.</h2><ul><li>Do not store credentials, private keys, access tokens, unlawful content, or high-risk regulated data.</li><li>Do not probe, disrupt, overload, or bypass Ninai&apos;s account and installer protections.</li><li>Do not use Ninai to violate another service&apos;s terms, intellectual-property rights, privacy, or law.</li></ul></div></article>
        <article><span className="privacy-index">05</span><div><p className="section-label">AI providers</p><h2>Provider terms apply after disclosure.</h2><p>When Ninai releases an authorized context packet to OpenAI, Anthropic, or another connected provider, that provider processes the packet under its own terms and privacy policy. Ninai does not control provider outputs and does not guarantee their accuracy.</p></div></article>
        <article><span className="privacy-index">06</span><div><p className="section-label">Beta and warranties</p><h2>Use the beta with appropriate caution.</h2><p>To the maximum extent permitted by law, Ninai is provided “as is” and “as available,” without warranties of uninterrupted operation, fitness for a particular purpose, or error-free AI output. Do not rely on it for medical, legal, financial, safety-critical, or emergency decisions.</p></div></article>
        <article><span className="privacy-index">07</span><div><p className="section-label">Suspension and deletion</p><h2>Access may be limited to protect users.</h2><p>We may suspend abusive, unlawful, insecure, or harmful use. Local vault controls run on your Mac. For an account-data or deletion request, contact us as described in the <Link href="/privacy/">Privacy Policy</Link>.</p></div></article>
        <article><span className="privacy-index">08</span><div><p className="section-label">Liability and contact</p><h2>Reasonable limits apply.</h2><p>To the maximum extent permitted by law, Ninai is not liable for indirect, incidental, special, consequential, or lost-profit damages. Nothing excludes liability that cannot legally be excluded. Questions or legal notices: <a href="mailto:hello@ninai.io">hello@ninai.io</a>.</p></div></article>
      </section>
    </main>
  );
}
