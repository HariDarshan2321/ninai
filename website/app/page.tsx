import type { Metadata } from "next";
import Link from "next/link";

import styles from "./home.module.css";

export const metadata: Metadata = {
  title: "Ninai AI memory for Claude Code and Codex",
  description:
    "Ninai is permissioned AI memory for Claude Code and Codex. Remember project decisions, recall them with sources, and revoke access at any time.",
  alternates: { canonical: "/" },
};

export default function HomePage() {
  return (
    <main id="main-content" className={styles.page}>
      <section className={styles.hero} id="product">
        <div className={`shell ${styles.heroInner}`}>
          <div className={styles.heroCopy}>
            <p className={styles.kicker}><span /> Local memory for Claude Code and Codex</p>
            <h1 className={styles.heroTitle}>Switch agents.<em>Keep the project.</em></h1>
            <p className={styles.heroLead}>
              Ninai keeps useful project decisions available when you move between Claude Code
              and Codex. The complete vault stays on your Mac.
            </p>
            <div className={styles.heroActions}>
              <Link className={styles.primaryAction} href="/install/">Get Ninai for Mac <span aria-hidden="true">↗</span></Link>
              <a className={styles.secondaryAction} href="https://app.ninai.io/control/login">Sign in</a>
            </div>
            <p className={styles.heroNote}>Mac MVP · local vault · you choose what each agent can read</p>
          </div>
          <div className={styles.heroProduct}>
            <p className={styles.productCaption}>Setup <span>About two minutes</span></p>
            <ol className={styles.quickStart}>
              <li><span>1</span><div><strong>Sign in</strong><p>Unlock the official Mac installer.</p></div></li>
              <li><span>2</span><div><strong>Run one command</strong><p>Ninai finds Claude Code and Codex.</p></div></li>
              <li><span>3</span><div><strong>Keep working</strong><p>Ninai opens with your local vault ready.</p></div></li>
            </ol>
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
              <p className={styles.userPrompt}>Claude Code session ends.</p>
              <div className={styles.toolEvent}><span>Ninai archived</span><strong>The scoped project outcome.</strong><small>automatic local handoff · source attached</small></div>
            </article>
            <div className={styles.returnBridge} aria-hidden="true"><div className={styles.returnMark}><img src="/assets/ninai-app-icon.svg" alt="" width="54" height="54" /></div><span>Only the durable outcome</span></div>
            <article className={`${styles.sessionCard} ${styles.sessionCardRecall}`}>
              <div className={styles.cardMeta}><span>Session 02</span><span>Codex</span></div>
              <p className={styles.userPrompt}>Codex opens in the same project.</p>
              <div className={styles.memoryReceipt}><span className={styles.receiptIndex}>01</span><div><strong>Keep every migration reversible.</strong><small>claude-code://project/decision</small></div></div>
              <p className={styles.receiptFooter}>1 fact · source included</p>
            </article>
          </div>
        </div>
      </section>

      <section className={styles.finalCta}>
        <div className={`shell ${styles.finalCtaInner}`}>
          <img src="/assets/ninai-app-icon.svg" alt="" width="62" height="62" />
          <h2>Ready in one install.<em>Private on your Mac.</em></h2>
          <div><Link className={styles.primaryAction} href="/install/">Set up Ninai ↗</Link><a className={styles.secondaryActionLight} href="https://app.ninai.io/control/login">Sign in</a></div>
        </div>
      </section>
    </main>
  );
}
