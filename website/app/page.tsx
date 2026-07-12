import Link from "next/link";

import { ContextAperture } from "@/components/context-aperture";
import { CopyCommand } from "@/components/copy-command";

import styles from "./home.module.css";

const personas = [
  {
    name: "Builder",
    prompt: "“What did we decide about the auth flow?”",
    title: "Stop repeating technical decisions.",
    copy: "Architecture choices, project state, and completed tool outcomes return in a fresh coding session.",
    proof: "Existing GitHub and Linear MCP connections stay untouched.",
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
    question: "Where is memory stored?",
    answer:
      "The current MVP stores memory, provenance, permission grants, and disclosure logs in a local SQLite database on your machine.",
  },
  {
    question: "Is Ninai production encrypted?",
    answer:
      "Not yet. The MVP is honest about this boundary: it uses local SQLite and does not claim SQLCipher, an independent audit, or production security certification.",
  },
];

export default function HomePage() {
  return (
    <main id="main-content" className={styles.page}>
      <section className={styles.hero} id="product">
        <div className={`shell ${styles.heroInner}`}>
          <div className={styles.heroCopy}>
            <p className={styles.kicker}>
              <span /> Local-first memory for the AI tools you already use
            </p>
            <h1 className={styles.heroTitle}>
              Your AI should remember the work.
              <em>Not your whole life.</em>
            </h1>
            <p className={styles.heroLead}>
              Ninai saves the decisions, commitments, and project context that should
              survive a session—on your device. Each assistant recalls only what you allow.
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
              <li>One local install</li>
              <li>No duplicate connectors</li>
              <li>No account</li>
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
              Today, an AI can read your tools and still forget the outcome tomorrow.
              Ninai keeps the durable result, not the entire transcript.
            </p>
          </div>

          <div className={styles.returnFlow}>
            <article className={styles.sessionCard}>
              <div className={styles.cardMeta}>
                <span>Session 01</span>
                <span>Claude Code + Linear</span>
              </div>
              <p className={styles.userPrompt}>“Review NIN-42 and tell me what matters.”</p>
              <div className={styles.toolEvent}>
                <span>Linear returned</span>
                <strong>Permission dashboard required before launch</strong>
                <small>owner · deadline · status · source</small>
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
                <span>Fresh context</span>
              </div>
              <p className={styles.userPrompt}>“What must I finish before launch?”</p>
              <div className={styles.memoryReceipt}>
                <span className={styles.receiptIndex}>01</span>
                <div>
                  <strong>Finish the permission dashboard.</strong>
                  <small>linear://NIN-42 · confidence 0.97</small>
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
            <p className={styles.eyebrow}>One install</p>
            <h2>Keep your tools where they are.</h2>
            <p>
              Linear remains connected to Claude. GitHub remains connected to Claude.
              Ninai listens to completed host events, so you do not re-enter credentials
              or rebuild the setup you already trust.
            </p>
            <Link href="/install/">See the four-minute setup →</Link>
          </div>

          <div className={styles.setupDiagram} aria-label="Ninai capture architecture">
            <div className={styles.toolColumn}>
              <span className={styles.diagramLabel}>Already connected</span>
              <div><b>LI</b> Linear MCP</div>
              <div><b>GH</b> GitHub MCP</div>
              <div><b>••</b> Your tools</div>
            </div>
            <div className={styles.diagramArrow}><span>existing calls</span><i /></div>
            <div className={styles.hostColumn}>
              <span className={styles.diagramLabel}>AI host</span>
              <strong>Claude Code</strong>
              <small>PostToolUse event</small>
            </div>
            <div className={`${styles.diagramArrow} ${styles.diagramArrowSignal}`}>
              <span>local hook</span><i />
            </div>
            <div className={styles.ninaiColumn}>
              <span className={styles.diagramLabel}>Your machine</span>
              <img src="/assets/ninai-app-icon.svg" alt="" width="42" height="42" />
              <strong>Ninai</strong>
              <small>capture · policy · recall</small>
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
              Your complete memory remains on your machine. If Claude or another cloud AI
              uses a selected packet, that packet leaves the device and the provider’s
              policy applies.
            </p>
            <Link href="/privacy/">Inspect the privacy architecture →</Link>
          </div>

          <div className={styles.boundaryVisual}>
            <div className={styles.boundaryLocal}>
              <span>Your machine</span>
              <strong>Complete local vault</strong>
              <small>37 memories · permissions · sources · logs</small>
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
            <p className={styles.eyebrow}>Local MVP</p>
            <h2>Try the boundary yourself.</h2>
            <p>
              Install the Python engine, grant Claude Code one project scope, remember a
              fact, recall it, then revoke the scope. No account required.
            </p>
            <Link className={styles.primaryActionDark} href="/install/">
              Open the install guide <span aria-hidden="true">↗</span>
            </Link>
          </div>
          <CopyCommand>{`cd engine
python3 -m venv .venv
source .venv/bin/activate
pip install .

ninai permission grant claude-code project
claude mcp add ninai -- ninai-mcp`}</CopyCommand>
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
            <Link className={styles.primaryAction} href="/install/">Install Ninai ↗</Link>
            <a className={styles.secondaryActionLight} href="mailto:hello@ninai.io?subject=Ninai%20MVP">
              Talk to the founder
            </a>
          </div>
        </div>
      </section>
    </main>
  );
}
