import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Privacy architecture",
  description:
    "Compare Ninai's local and hosted AI-memory trust boundaries, permissions, disclosure logs, and current security limitations.",
  alternates: { canonical: "/privacy/" },
  openGraph: {
    title: "Ninai privacy architecture",
    description: "Separate local and hosted trust boundaries, stated plainly.",
    url: "/privacy/",
    images: [
      {
        url: "/assets/og-image.png",
        width: 1200,
        height: 630,
        alt: "Ninai local-first privacy architecture",
      },
    ],
  },
};

export default function PrivacyPage() {
  return (
    <main id="main-content">
      <section className="page-hero page-hero--privacy">
        <div className="shell page-hero__grid">
          <div>
            <p className="section-label section-label--light">Privacy architecture</p>
            <h1>Two modes.<br />Two trust boundaries.</h1>
          </div>
          <div className="page-hero__aside">
            <p>
              Local mode keeps its vault on your machine. The separate hosted invitation beta
              stores workspace memory in managed cloud infrastructure and never syncs local data automatically.
            </p>
            <span className="privacy-version">Current product model · July 2026</span>
          </div>
        </div>
      </section>

      <section className="mode-section shell">
        <div className="mode-grid">
          <article className="mode-card"><span className="status-pill status-pill--ready">Implemented</span><h2>Local trust boundary</h2><p>The complete SQLite vault, grants, sources, and logs remain on your machine. There is no automatic cloud upload or sync.</p><p>When you send a selected context packet to a cloud AI, that packet leaves the device and the provider's policy applies.</p></article>
          <article className="mode-card mode-card--future"><span className="status-pill">Invitation beta</span><h2>Hosted trust boundary</h2><p>Hosted workspaces persist memory in managed PostgreSQL so explicitly authorized clients can connect remotely.</p><p>OAuth login, tenant isolation, review, export, disclosure logging, and revocation are implemented. External acceptance and operational hardening remain incomplete; no hosted security certification is claimed.</p></article>
        </div>
      </section>

      <section className="privacy-boundary shell">
        <p className="section-label">The boundary / 01</p>
        <div className="boundary-diagram">
          <div className="boundary-zone boundary-zone--local">
            <span className="boundary-zone__tag">YOUR MACHINE</span>
            <div className="boundary-vault">
              <img src="/assets/ninai-app-icon.svg" alt="" width="44" height="44" />
              <strong>Complete Ninai vault</strong>
              <p>Memories · sources · scopes · logs</p>
            </div>
            <div className="boundary-policy">permission + retrieval + composition</div>
          </div>
          <div className="boundary-crossing">
            <span>release event</span>
            <i />
            <strong>2 facts<br />263 tokens</strong>
          </div>
          <div className="boundary-zone boundary-zone--provider">
            <span className="boundary-zone__tag">AI PROVIDER</span>
            <div className="boundary-provider">
              <strong>Selected context packet</strong>
              <p>The provider’s data policy applies here.</p>
            </div>
          </div>
        </div>
      </section>

      <section className="privacy-sections shell">
        <article>
          <span className="privacy-index">02</span>
          <div>
            <p className="section-label">What is stored</p>
            <h2>Compact memory with evidence.</h2>
            <p>
              The MVP stores durable content, memory type, scope, source URI, importance,
              confidence, timestamps, permission grants, and disclosure logs in SQLite.
            </p>
            <ul>
              <li>Decisions, commitments, facts, preferences, procedures, and events</li>
              <li>Source references such as <code>linear://NIN-42</code></li>
              <li>Which client received which memory and why</li>
            </ul>
          </div>
        </article>
        <article>
          <span className="privacy-index">03</span>
          <div>
            <p className="section-label">What is rejected</p>
            <h2>Credentials are not memory.</h2>
            <p>
              Ninai rejects common private-key, bearer-token, GitHub-token, and API-key
              patterns. The hook selects durable outcome fields instead of persisting whole
              tool responses.
            </p>
            <div className="rejected-sample">
              <span>api_key=sk-••••••••</span>
              <strong>[REDACTED_SECRET]</strong>
            </div>
          </div>
        </article>
        <article>
          <span className="privacy-index">04</span>
          <div>
            <p className="section-label">Permission model</p>
            <h2>One client. Explicit scopes.</h2>
            <p>
              A grant applies to a named client and one scope. Access to project memory does
              not imply access to personal, health, or finance memory. Revocation takes effect
              on the next recall.
            </p>
            <div className="scope-map">
              <span className="is-granted">project · allow</span>
              <span className="is-granted">preference · allow</span>
              <span>personal · deny</span>
              <span>health · deny</span>
              <span>finance · deny</span>
            </div>
          </div>
        </article>
        <article>
          <span className="privacy-index">05</span>
          <div>
            <p className="section-label">Current limitations</p>
            <h2>An MVP, not a security certification.</h2>
            <p>
              The MVP implements the policy layer. It has not completed the
              controls required for high-risk production data.
            </p>
            <ul>
              <li>No SQLCipher or full-database encryption yet</li>
              <li>No signed and notarized desktop package</li>
              <li>No prompt-injection classifier or independent audit</li>
              <li>Hosted external acceptance, backup operations, and deletion verification remain incomplete</li>
            </ul>
          </div>
        </article>
      </section>

      <section className="privacy-cta">
        <div className="shell">
          <h2>Inspect before you trust.</h2>
          <p>Ninai is open for technical review. Security reports are welcome.</p>
          <div>
            <a className="button button--acid" href="https://github.com/HariDarshan2321/ninai">View source ↗</a>
            <a className="button button--dark-line" href="mailto:security@ninai.io">security@ninai.io</a>
          </div>
          <Link href="/install/">Continue to installation →</Link>
        </div>
      </section>
    </main>
  );
}
