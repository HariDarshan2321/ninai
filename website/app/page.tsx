import type { Metadata } from "next";
import Link from "next/link";

import { ContextAperture } from "@/components/context-aperture";

import styles from "./home.module.css";

export const metadata: Metadata = {
  title: "Ninai AI memory for Claude Code and Codex",
  description:
    "Ninai is permissioned AI memory for Claude Code and Codex. Remember project decisions, recall them with sources, and revoke access at any time.",
  alternates: { canonical: "/" },
};

const outcomes = [
  {
    name: "Remember once",
    prompt: "“Keep migrations reversible.”",
    title: "Stop re-explaining decisions.",
    copy: "Save the durable result of the work—not the whole transcript.",
    proof: "Every memory keeps its source.",
  },
  {
    name: "Switch agents",
    prompt: "“What did Claude decide?”",
    title: "Start the next session informed.",
    copy: "Claude and Codex recall the same permitted project context.",
    proof: "Packets stay small and scoped.",
  },
  {
    name: "Stay in control",
    prompt: "“What was disclosed?”",
    title: "Review, audit, and revoke.",
    copy: "Grant one project, inspect every recall, and cut off access immediately.",
    proof: "Permission is checked before retrieval.",
  },
];

export default function HomePage() {
  return (
    <main id="main-content" className={styles.page}>
      <section className={styles.hero} id="product">
        <div className={`shell ${styles.heroInner}`}>
          <div className={styles.heroCopy}>
            <p className={styles.kicker}><span /> Permissioned shared memory for Claude and Codex</p>
            <h1 className={styles.heroTitle}>Your agents should remember the project.<em>Not your whole life.</em></h1>
            <p className={styles.heroLead}>
              Ninai is permissioned shared memory for Claude Code and Codex. Remember project
              decisions once, recall them with sources, and revoke access at any time.
            </p>
            <div className={styles.heroActions}>
              <Link className={styles.primaryAction} href="/install/#local-install">Install locally <span aria-hidden="true">↗</span></Link>
              <Link className={styles.secondaryAction} href="/start/">Create hosted account</Link>
            </div>
            <ul className={styles.proofList} aria-label="MVP properties">
              <li>Local cross-agent gate passed</li><li>Source-backed recall</li><li>Immediate revocation</li>
            </ul>
          </div>
          <div className={styles.heroProduct}>
            <p className={styles.productCaption}>The permission boundary <span>Try the switch</span></p>
            <ContextAperture />
          </div>
        </div>
      </section>

      <section className={styles.returnSection} id="how-it-works">
        <div className="shell">
          <div className={styles.sectionHeading}>
            <p className={styles.eyebrow}>One useful outcome</p>
            <h2>A session ends. The decision stays.</h2>
          </div>
          <div className={styles.returnFlow}>
            <article className={styles.sessionCard}>
              <div className={styles.cardMeta}><span>Session 01</span><span>Claude Code</span></div>
              <p className={styles.userPrompt}>“Remember why migrations stay reversible.”</p>
              <div className={styles.toolEvent}><span>Ninai stored</span><strong>Migrations must remain reversible.</strong><small>project scope · source attached</small></div>
            </article>
            <div className={styles.returnBridge} aria-hidden="true"><div className={styles.returnMark}><img src="/assets/ninai-app-icon.svg" alt="" width="54" height="54" /></div><span>Only the durable outcome</span></div>
            <article className={`${styles.sessionCard} ${styles.sessionCardRecall}`}>
              <div className={styles.cardMeta}><span>Session 02</span><span>Codex</span></div>
              <p className={styles.userPrompt}>“What did we decide about migrations?”</p>
              <div className={styles.memoryReceipt}><span className={styles.receiptIndex}>01</span><div><strong>Keep every migration reversible.</strong><small>claude-code://project/decision</small></div></div>
              <p className={styles.receiptFooter}>1 fact · source included</p>
            </article>
          </div>
        </div>
      </section>

      <section className={styles.personaSection}>
        <div className="shell">
          <div className={styles.sectionHeading}><p className={styles.eyebrow}>What you get</p><h2>Continuity without context sprawl.</h2></div>
          <div className={styles.personaGrid}>
            {outcomes.map((item, index) => (
              <article className={styles.personaCard} key={item.name}>
                <div className={styles.personaTopline}><span>0{index + 1}</span><strong>{item.name}</strong></div>
                <p className={styles.personaPrompt}>{item.prompt}</p><h3>{item.title}</h3><p>{item.copy}</p><small>{item.proof}</small>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className={styles.setupSection}>
        <div className={`shell ${styles.setupLayout}`}>
          <div className={styles.setupCopy}>
            <p className={styles.eyebrow}>Choose your vault</p><h2>Invitation beta or local.</h2>
            <p>Try the hosted invitation beta with supported OAuth clients, or keep an open-source SQLite vault entirely on your machine. Local memory is never uploaded automatically.</p>
            <Link href="/install/">Open the setup guide →</Link>
          </div>
          <div className={styles.setupDiagram} aria-label="Ninai product flow">
            <div className={styles.toolColumn}><span className={styles.diagramLabel}>Agents</span><div><b>CL</b> Claude Code</div><div><b>OX</b> Codex</div></div>
            <div className={styles.diagramArrow}><span>scoped MCP</span><i /></div>
            <div className={styles.hostColumn}><span className={styles.diagramLabel}>Ninai</span><strong>Remember · recall</strong><small>source · review · revoke</small></div>
            <div className={`${styles.diagramArrow} ${styles.diagramArrowSignal}`}><span>your choice</span><i /></div>
            <div className={styles.ninaiColumn}><span className={styles.diagramLabel}>Vault</span><img src="/assets/ninai-app-icon.svg" alt="" width="42" height="42" /><strong>Hosted or local</strong></div>
          </div>
        </div>
      </section>

      <section className={styles.finalCta}>
        <div className={`shell ${styles.finalCtaInner}`}>
          <img src="/assets/ninai-app-icon.svg" alt="" width="62" height="62" />
          <h2>Remember the work.<em>Keep the rest yours.</em></h2>
          <div><Link className={styles.primaryAction} href="/install/">Set up Ninai ↗</Link><a className={styles.secondaryActionLight} href="https://ninai-cloud.onrender.com/control">Open dashboard</a></div>
        </div>
      </section>
    </main>
  );
}
