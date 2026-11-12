import type { Metadata } from "next";
import Link from "next/link";

import styles from "./home.module.css";

export const metadata: Metadata = {
  title: "Ninai — private memory for your AI assistants",
  description:
    "Ninai lets supported AI assistants remember the same project while you control what each assistant may use.",
  alternates: { canonical: "/" },
};

export default function HomePage() {
  return (
    <main id="main-content" className={styles.page}>
      <section className={styles.hero} id="product">
        <div className={`shell ${styles.heroInner}`}>
          <div className={styles.heroCopy}>
            <p className={styles.kicker}><span /> Private memory for your AI assistants</p>
            <h1 className={styles.heroTitle}>Your assistants remember.<em>You stay in control.</em></h1>
            <p className={styles.heroLead}>
              Finish work in one supported assistant and continue in another without explaining
              the project again. Built today for people who use Claude Code and Codex on the same project.
            </p>
            <div className={styles.heroActions}>
              <Link className={styles.primaryAction} href="/install/">See setup steps <span aria-hidden="true">↗</span></Link>
              <Link className={styles.secondaryAction} href="#how-it-works">See how it works</Link>
            </div>
            <p className={styles.heroNote}>Mac source setup · Windows preview · you choose what each assistant can use</p>
          </div>
          <div className={styles.heroProduct}>
            <p className={styles.productCaption}>First success <span>Three clear steps</span></p>
            <ol className={styles.quickStart}>
              <li><span>1</span><div><strong>Install Ninai</strong><p>Choose the version for your computer.</p></div></li>
              <li><span>2</span><div><strong>Choose assistants</strong><p>Ninai shows the supported tools it found.</p></div></li>
              <li><span>3</span><div><strong>Test one memory</strong><p>Save a decision and recall it from another assistant.</p></div></li>
            </ol>
          </div>
        </div>
      </section>

      <section className={styles.returnSection} id="how-it-works">
        <div className="shell">
          <div className={styles.sectionHeading}>
            <p className={styles.eyebrow}>A simple example</p>
            <h2>The first assistant finishes. The next one knows the decision.</h2>
          </div>
          <div className={styles.returnFlow}>
            <article className={styles.sessionCard}>
              <div className={styles.cardMeta}><span>Session 01</span><span>Claude Code</span></div>
              <p className={styles.userPrompt}>Claude Code session ends.</p>
              <div className={styles.toolEvent}><span>Ninai saved</span><strong>The useful project decision.</strong><small>stored on this computer · source attached</small></div>
            </article>
            <div className={styles.returnBridge} aria-hidden="true"><div className={styles.returnMark}><img src="/assets/ninai-app-icon.svg" alt="" width="54" height="54" /></div><span>Only the allowed memory</span></div>
            <article className={`${styles.sessionCard} ${styles.sessionCardRecall}`}>
              <div className={styles.cardMeta}><span>Session 02</span><span>Codex</span></div>
              <p className={styles.userPrompt}>Codex opens in the same project.</p>
              <div className={styles.memoryReceipt}><span className={styles.receiptIndex}>01</span><div><strong>Keep every migration reversible.</strong><small>claude-code://project/decision</small></div></div>
              <p className={styles.receiptFooter}>1 memory · source included</p>
            </article>
          </div>
        </div>
      </section>

      <section className={styles.finalCta}>
        <div className={`shell ${styles.finalCtaInner}`}>
          <img src="/assets/ninai-app-icon.svg" alt="" width="62" height="62" />
          <h2>Continue the work.<em>Keep control of the memory.</em></h2>
          <div><Link className={styles.primaryAction} href="/install/">See installation options ↗</Link><Link className={styles.secondaryActionLight} href="/privacy/">How privacy works</Link></div>
        </div>
      </section>
    </main>
  );
}
