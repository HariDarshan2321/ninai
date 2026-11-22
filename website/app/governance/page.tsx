import Link from "next/link";

import { pageMetadata } from "../site-metadata";
import styles from "./governance.module.css";

export const metadata = pageMetadata({
  path: "/governance/",
  title: "AI Assistant Governance and Project Permissions",
  description: "See how Ninai governs local AI memory. Approve separate Read, Save, and Delete permissions by project for Claude Code and Codex, follow sources, and revoke access.",
});

const actions = [
  { name: "Read", description: "Retrieve saved memories and their source references." },
  { name: "Save", description: "Add new memories to the project." },
  { name: "Delete", description: "Remove saved project memories." },
];

export default function GovernancePage() {
  return (
    <main id="main-content" tabIndex={-1} className={styles.page}>
      <section className="page-hero">
        <div className={`shell ${styles.hero}`}>
          <div>
            <p className="section-label">Governance for local AI memory</p>
            <h1>Give each assistant the access it needs.</h1>
            <p className={styles.intro}>Choose which project memories Claude Code and Codex can read, save, or delete on your Mac. Connecting an assistant starts with its project permissions off.</p>
          </div>
          <div className={styles.panel}>
            <h2>Three separate permissions</h2>
            <dl className={styles.actions}>
              {actions.map(({ name, description }) => (
                <div key={name}><dt>{name}</dt><dd>{description}</dd></div>
              ))}
            </dl>
            <p>Granting one permission leaves the others as they were.</p>
          </div>
        </div>
      </section>

      <section className={`shell ${styles.workflow}`} aria-labelledby="review-title">
        <div className={styles.sectionIntro}>
          <h2 id="review-title">You approve access. You can take it back.</h2>
          <p>These controls apply to each assistant’s access to a named project through Ninai.</p>
        </div>
        <div className={styles.workflowCards}>
          <article>
            <h3>Review the request</h3>
            <p>An assistant can ask for specific permissions on a project. You see the assistant, project, requested actions, and reason in the Mac app.</p>
          </article>
          <article>
            <h3>Approve the exact change</h3>
            <p>The app asks macOS to verify you before increasing access. If you cancel or verification fails, permissions stay as they are.</p>
          </article>
          <article>
            <h3>See what was shared</h3>
            <p>Saved memories retain their sources. Sharing history shows what Ninai returned and which assistant requested it. Turn off permissions to stop future access.</p>
          </article>
        </div>
      </section>

      <section className={styles.boundary} aria-labelledby="boundary-title">
        <div className={`shell ${styles.boundaryInner}`}>
          <div>
            <h2 id="boundary-title">Where these controls apply</h2>
            <p>Project permissions govern access through Ninai. Software with file access under your Mac account can still reach the local vault. An assistant or its provider may keep context it already received.</p>
          </div>
          <div className={styles.resources}>
            <a href="https://github.com/HariDarshan2321/ninai/blob/main/docs/LOCAL-PROJECT-PERMISSIONS.md">Read the project permissions specification <span aria-hidden="true">↗</span></a>
            <Link href="/privacy/">See how Ninai handles your data <span aria-hidden="true">↗</span></Link>
          </div>
        </div>
      </section>

      <section className={`shell ${styles.install}`} aria-labelledby="governance-install">
        <div>
          <h2 id="governance-install">Try it on a sample project</h2>
          <p>Give an assistant Read access and leave Save off. Ask it to retrieve a saved decision, then revoke Read and try again.</p>
        </div>
        <Link className="button button--acid" href="/install/">Install on Mac <span aria-hidden="true">↗</span></Link>
      </section>
    </main>
  );
}
