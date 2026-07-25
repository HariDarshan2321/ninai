import type { Metadata } from "next";
import Link from "next/link";

import { ContextAperture } from "@/components/context-aperture";
import { CopyCommand } from "@/components/copy-command";

import styles from "./home.module.css";

export const metadata: Metadata = {
  title: "Shared AI memory, with clear boundaries",
  description: "Ninai gives supported OpenAI and Anthropic clients one permissioned, source-backed memory, with a local engine available today.",
  alternates: { canonical: "/" },
};

const personas = [
  {
    name: "Builder",
    prompt: "“What did we decide about the auth flow?”",
    title: "Stop repeating technical decisions.",
    copy: "Architecture choices, project state, and completed tool outcomes return in a fresh coding session.",
    proof: "Claude Code and Codex passed the real-host local memory gate.",
  },
  {
    name: "Operator",
    prompt: "“Who is waiting on me this week?”",
    title: "Keep commitments in view.",
    copy: "Deadlines, owners, follow-ups, and decisions survive the context switches that normally erase them.",
    proof: "Every returned outcome keeps its original source.",
  },
  {
    name: "Steward",
    prompt: "“What did Claude actually receive?”",
    title: "See and control the boundary.",
    copy: "Inspect the exact packet, grant only useful scopes, and revoke future access without deleting the memory.",
    proof: "Permission is evaluated before retrieval begins.",
  },
];

const faqs = [
  {
    question: "Do I reconnect Linear, GitHub, or other MCP tools?",
    answer:
      "No. The Claude Code integration observes completed tool activity through a PostToolUse hook. Your existing MCP configuration stays where it is.",
  },
  {
    question: "Does Ninai send my complete memory vault to an AI?",
    answer:
      "No. Ninai filters by the requesting client’s granted scopes first, then releases a compact packet containing only selected facts and their sources.",
  },
  {
    question: "Where can memory be stored?",
    answer:
      "Local mode stores the vault in SQLite on your machine. The hosted beta uses a separate PostgreSQL workspace and never uploads the local vault automatically.",
  },
  {
    question: "Is Ninai production encrypted?",
    answer:
      "Not yet. Local SQLite is not SQLCipher-encrypted, and the hosted beta does not claim an independent audit or production security certification.",
  },
];

export default function HomePage() {
  return (
    <main id="main-content" className={styles.page}>
      <section className={styles.hero} id="product">
        <div className={`shell ${styles.heroInner}`}>
          <div className={styles.heroCopy}>
            <p className={styles.kicker}>
              <span /> One permissioned memory for OpenAI and Claude
            </p>
            <h1 className={styles.heroTitle}>
              Your AI should remember the work.
              <em>Not your whole life.</em>
            </h1>
            <p className={styles.heroLead}>
              Keep decisions, constraints, and project state when you switch AI tools.
              Every recalled memory keeps its source, scope, and permission boundary.
            </p>
            <div className={styles.heroActions}>
              <Link className={styles.primaryAction} href="/install/">
                Install Ninai <span aria-hidden="true">↗</span>
              </Link>
              <a
                className={styles.secondaryAction}
                href="https://github.com/HariDarshan2321/ninai"
              >
                View the source
              </a>
            </div>
            <ul className={styles.proofList} aria-label="MVP properties">
              <li>Local engine available</li>
              <li>Hosted beta in development</li>
              <li>Tested before claimed</li>
            </ul>
          </div>

          <div className={styles.heroProduct}>
            <p className={styles.productCaption}>
              The context aperture <span>Try the permission switch</span>
            </p>
            <ContextAperture />
          </div>
        </div>
      </section>

      <section className={styles.returnSection} id="how-it-works">
        <div className="shell">
          <div className={styles.sectionHeading}>
            <p className={styles.eyebrow}>What Ninai changes</p>
            <h2>A session ends. The useful part shouldn’t.</h2>
            <p>
              Useful work can disappear in the next session or provider. Ninai keeps the
              durable result, not the entire transcript.
            </p>
          </div>

          <div className={styles.returnFlow}>
            <article className={styles.sessionCard}>
              <div className={styles.cardMeta}>
                <span>Session 01</span>
                <span>Claude Code + Ninai</span>
              </div>
              <p className={styles.userPrompt}>“Remember why migrations stay reversible.”</p>
              <div className={styles.toolEvent}>
                <span>Claude stored</span>
                <strong>Migrations must remain reversible.</strong>
                <small>project scope · source attached · approved</small>
              </div>
            </article>

            <div className={styles.returnBridge} aria-hidden="true">
              <div className={styles.returnMark}>
                <img src="/assets/ninai-app-icon.svg" alt="" width="54" height="54" />
              </div>
              <span>Only the durable outcome returns</span>
            </div>

            <article className={`${styles.sessionCard} ${styles.sessionCardRecall}`}>
              <div className={styles.cardMeta}>
                <span>Session 02</span>
                <span>Codex · fresh context</span>
              </div>
              <p className={styles.userPrompt}>“What did we decide about migrations?”</p>
              <div className={styles.memoryReceipt}>
                <span className={styles.receiptIndex}>01</span>
                <div>
                  <strong>Keep every migration reversible.</strong>
                  <small>claude-code://project/decision · project scope</small>
                </div>
              </div>
              <p className={styles.receiptFooter}>1 useful fact · source included</p>
            </article>
          </div>
        </div>
      </section>

      <section className={styles.setupSection}>
        <div className={`shell ${styles.setupLayout}`}>
          <div className={styles.setupCopy}>
            <p className={styles.eyebrow}>Two clear modes</p>
            <h2>Choose where the vault lives.</h2>
            <p>
              Run the open-source SQLite engine entirely on your machine today. The hosted
              PostgreSQL beta is a separate, explicit workspace for cross-provider access;
              it never silently syncs the local vault.
            </p>
            <Link href="/install/">Compare both installation paths →</Link>
          </div>

          <div className={styles.setupDiagram} aria-label="Ninai capture architecture">
            <div className={styles.toolColumn}>
              <span className={styles.diagramLabel}>AI clients</span>
              <div><b>CL</b> Claude Code</div>
              <div><b>OX</b> Codex</div>
              <div><b>••</b> Tested clients</div>
            </div>
            <div className={styles.diagramArrow}><span>permissioned calls</span><i /></div>
            <div className={styles.hostColumn}>
              <span className={styles.diagramLabel}>Ninai boundary</span>
              <strong>Scopes + provenance</strong>
              <small>review · recall · revoke</small>
            </div>
            <div className={`${styles.diagramArrow} ${styles.diagramArrowSignal}`}>
              <span>explicit mode</span><i />
            </div>
            <div className={styles.ninaiColumn}>
              <span className={styles.diagramLabel}>Your chosen vault</span>
              <img src="/assets/ninai-app-icon.svg" alt="" width="42" height="42" />
              <strong>Ninai</strong>
              <small>local SQLite · hosted PostgreSQL</small>
            </div>
          </div>
        </div>
      </section>

      <section className={styles.personaSection}>
        <div className="shell">
          <div className={styles.sectionHeading}>
            <p className={styles.eyebrow}>Who it is for</p>
            <h2>Different work. The same missing continuity.</h2>
            <p>
              Ninai starts with people who rely on AI for real decisions and cannot afford
              to rebuild the story in every new session.
            </p>
          </div>

          <div className={styles.personaGrid}>
            {personas.map((persona, index) => (
              <article className={styles.personaCard} key={persona.name}>
                <div className={styles.personaTopline}>
                  <span>0{index + 1}</span>
                  <strong>{persona.name}</strong>
                </div>
                <p className={styles.personaPrompt}>{persona.prompt}</p>
                <h3>{persona.title}</h3>
                <p>{persona.copy}</p>
                <small>{persona.proof}</small>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className={styles.methodSection}>
        <div className={`shell ${styles.methodLayout}`}>
          <div className={styles.methodCopy}>
            <p className={styles.eyebrow}>PACT retrieval</p>
            <h2>Small by design.</h2>
            <p>
              More context is not automatically better context. Ninai first narrows memory
              by permission, then returns the smallest evidence packet that can still help.
            </p>
            <ol className={styles.methodSteps}>
              <li><span>01</span><div><strong>Permit</strong><p>Resolve the client’s explicit scopes.</p></div></li>
              <li><span>02</span><div><strong>Select</strong><p>Rank only permitted, current evidence.</p></div></li>
              <li><span>03</span><div><strong>Return</strong><p>Fit useful facts and sources into the budget.</p></div></li>
            </ol>
            <Link href="/research/">Read the research direction →</Link>
          </div>

          <div className={styles.packetCard}>
            <div className={styles.packetTopline}>
              <span>Context packet</span>
              <span>263 tokens</span>
            </div>
            <div className={styles.packetQuestion}>
              <span>Purpose</span>
              <strong>Prepare today’s Ninai work</strong>
            </div>
            <div className={styles.packetFact}>
              <span>A</span>
              <div>
                <strong>Finish the permission dashboard.</strong>
                <small>linear://NIN-42</small>
              </div>
            </div>
            <div className={styles.packetFact}>
              <span>B</span>
              <div>
                <strong>Keep existing MCP connections in place.</strong>
                <small>decision://capture-architecture</small>
              </div>
            </div>
            <div className={styles.packetMetric}>
              <strong>2</strong>
              <span>facts returned</span>
              <i />
              <strong>35</strong>
              <span>memories stayed private</span>
            </div>
          </div>
        </div>
      </section>

      <section className={styles.trustSection}>
        <div className={`shell ${styles.trustLayout}`}>
          <div className={styles.trustCopy}>
            <p className={styles.eyebrow}>The honest boundary</p>
            <h2>The vault stays. The packet travels.</h2>
            <p>
              In local mode the complete vault remains on your machine. Hosted mode uses a
              separate opt-in workspace. In either mode, a selected packet sent to an AI is
              then governed by that provider’s policy.
            </p>
            <Link href="/privacy/">Inspect the privacy architecture →</Link>
          </div>

          <div className={styles.boundaryVisual}>
            <div className={styles.boundaryLocal}>
              <span>Chosen storage</span>
              <strong>Local or hosted vault</strong>
              <small>memories · permissions · sources · logs</small>
            </div>
            <div className={styles.boundaryGate}>
              <span>permission</span>
              <i />
              <strong>2 facts</strong>
            </div>
            <div className={styles.boundaryCloud}>
              <span>Selected AI</span>
              <strong>Compact packet</strong>
              <small>Provider policy applies after release</small>
            </div>
          </div>
        </div>
      </section>

      <section className={styles.installSection}>
        <div className={`shell ${styles.installLayout}`}>
          <div className={styles.installCopy}>
            <p className={styles.eyebrow}>Available now</p>
            <h2>Try the boundary yourself.</h2>
            <p>
              Install the Python engine, grant Codex or Claude Code a project scope,
              remember a decision, recall it, then revoke the scope. No account required.
            </p>
            <Link className={styles.primaryActionDark} href="/install/">
              Open the install guide <span aria-hidden="true">↗</span>
            </Link>
          </div>
          <CopyCommand>{`cd engine
python3 -m venv .venv
source .venv/bin/activate
pip install .

ninai permission grant codex project
codex mcp add ninai-local --env NINAI_CLIENT_ID=codex -- $(pwd)/.venv/bin/ninai-mcp`}</CopyCommand>
        </div>
      </section>

      <section className={styles.faqSection}>
        <div className={`shell ${styles.faqLayout}`}>
          <div>
            <p className={styles.eyebrow}>Questions</p>
            <h2>Clear before clever.</h2>
          </div>
          <div className={styles.faqList}>
            {faqs.map((faq, index) => (
              <details key={faq.question} open={index === 0}>
                <summary>{faq.question}<span aria-hidden="true">+</span></summary>
                <p>{faq.answer}</p>
              </details>
            ))}
          </div>
        </div>
      </section>

      <section className={styles.finalCta}>
        <div className={`shell ${styles.finalCtaInner}`}>
          <img src="/assets/ninai-app-icon.svg" alt="" width="62" height="62" />
          <h2>Remember the work.<em>Keep the rest yours.</em></h2>
          <div>
            <Link className={styles.primaryAction} href="/install/">Choose a Ninai mode ↗</Link>
            <a className={styles.secondaryActionLight} href="mailto:hello@ninai.io?subject=Ninai%20MVP">
              Talk to the founder
            </a>
          </div>
        </div>
      </section>
    </main>
  );
}
