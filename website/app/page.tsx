import Link from "next/link";

import { HomeSearchMetadata } from "./home-search-metadata";
import { pageMetadata } from "./site-metadata";
import styles from "./home.module.css";

const description = "Keep project decisions on your Mac for Claude Code and Codex. Grant each assistant separate read, save, and delete permissions and see what Ninai shared.";

export const metadata = pageMetadata({
  path: "/",
  title: "Local AI Memory with Project Permissions",
  description,
});

export default function HomePage() {
  return (
    <main id="main-content" className={styles.page}>
      <HomeSearchMetadata description={description} />
      <section className={styles.hero} id="product">
        <div className={`shell ${styles.heroInner}`}>
          <div className={styles.heroCopy}>
            <p className={styles.kicker}><span aria-hidden="true" /> Local AI memory with project permissions</p>
            <h1 className={styles.heroTitle}>Project memory{" "}<em>you control.</em></h1>
            <p className={styles.heroLead}>
              Save project decisions and their sources on your Mac. Pick up the work in a later
              Claude Code or Codex session, with permissions you set for each assistant and project.
            </p>
            <div className={styles.heroActions}>
              <Link className={styles.primaryAction} href="/install/">Install on Mac <span aria-hidden="true">↗</span></Link>
              <Link className={styles.secondaryAction} href="#how-it-works">See how it works</Link>
            </div>
          </div>
          <div className={styles.heroProduct}>
            <p className={styles.productCaption} id="project-permissions">Permissions for each assistant and project</p>
            <ul className={styles.quickStart} aria-labelledby="project-permissions">
              <li><div><strong>Read</strong><p>Retrieve saved decisions and their sources.</p></div></li>
              <li><div><strong>Save</strong><p>Add a memory when you allow it.</p></div></li>
              <li><div><strong>Delete</strong><p>Remove a memory only with a separate grant.</p></div></li>
            </ul>
          </div>
        </div>
      </section>

      <section className={styles.returnSection} id="how-it-works">
        <div className="shell">
          <div className={styles.sectionHeading}>
            <h2>Pick up a decision in a new session.</h2>
            <p>Enable session handoff and grant access to the project. A later session can ask Ninai for the context it’s allowed to read.</p>
          </div>
          <div className={styles.returnFlow}>
            <article className={styles.sessionCard}>
              <div className={styles.cardMeta}><span>Save a decision</span><span>Claude Code</span></div>
              <p className={styles.userPrompt}>“Keep database migrations reversible.”</p>
              <div className={styles.toolEvent}><strong>Saved to this project</strong><small>Stored on your Mac with a source reference</small></div>
            </article>
            <div className={styles.returnBridge} aria-hidden="true"><div className={styles.returnMark}><img src="/assets/ninai-app-icon.svg" alt="" width="54" height="54" /></div><span>Only the allowed memory</span></div>
            <article className={`${styles.sessionCard} ${styles.sessionCardRecall}`}>
              <div className={styles.cardMeta}><span>Recall the decision</span><span>Codex</span></div>
              <p className={styles.userPrompt}>“What’s our rule for database migrations?”</p>
              <div className={styles.memoryReceipt}><div><strong>Keep database migrations reversible.</strong><small>Source: Claude Code session</small></div></div>
            </article>
          </div>
        </div>
      </section>

      <section className={styles.finalCta}>
        <div className={`shell ${styles.finalCtaInner}`}>
          <h2>Access starts off.</h2>
          <p>Approve what each assistant can do for a project, see what Ninai shared, and revoke future access.</p>
          <div><Link className={styles.primaryAction} href="/governance/">Explore governance <span aria-hidden="true">↗</span></Link></div>
        </div>
      </section>
    </main>
  );
}
