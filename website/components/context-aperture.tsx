"use client";

import type { CSSProperties } from "react";
import { useState } from "react";

import styles from "./context-aperture.module.css";

const hiddenMemories = [
  "Project scope",
  "Personal preference",
  "Meeting notes",
  "Private draft",
  "Finance",
  "Source history",
];

export function ContextAperture() {
  const [projectAllowed, setProjectAllowed] = useState(true);

  return (
    <div
      className={`${styles.frame} ${projectAllowed ? styles.isOpen : styles.isClosed}`}
      aria-label="Interactive Ninai context aperture"
    >
      <div className={styles.topbar}>
        <div className={styles.identity}>
          <img src="/assets/ninai-app-icon.svg" alt="" width="30" height="30" />
          <div>
            <strong>Local vault</strong>
            <span>37 durable memories</span>
          </div>
        </div>
        <span className={styles.localState}><i /> On this device</span>
      </div>

      <div className={styles.stage}>
        <div className={styles.vaultField} aria-hidden="true">
          {hiddenMemories.map((memory, index) => (
            <span key={memory} style={{ "--index": index } as CSSProperties}>
              {memory}
            </span>
          ))}
        </div>

        <div className={styles.returnPath} aria-hidden="true"><i /></div>

        <div className={styles.apertureShell}>
          <div className={styles.aperture}>
            <div className={styles.apertureCopy} aria-hidden={!projectAllowed}>
              <span className={styles.releaseLabel}>Claude Code can recall</span>
              <article className={styles.fact}>
                <span>01</span>
                <div>
                  <strong>Finish the permission dashboard.</strong>
                  <small>linear://NIN-42</small>
                </div>
              </article>
              <article className={styles.fact}>
                <span>02</span>
                <div>
                  <strong>Keep Linear connected where it is.</strong>
                  <small>decision://capture-architecture</small>
                </div>
              </article>
              <div className={styles.releaseCount}>
                <strong>2</strong>
                <span>of 37 memories released</span>
              </div>
            </div>
          </div>

          <div className={styles.closedCopy} aria-hidden={projectAllowed}>
            <strong>The aperture is closed.</strong>
            <span>Project memory stays on this device.</span>
          </div>
        </div>
      </div>

      <div className={styles.permissionBar}>
        <div>
          <span>Permission</span>
          <strong>Project memory</strong>
        </div>
        <div className={styles.permissionResult}>
          <span role="status" aria-live="polite">
            {projectAllowed ? "2 facts visible" : "Nothing released"}
          </span>
          <button
            type="button"
            role="switch"
            aria-checked={projectAllowed}
            aria-label={`${projectAllowed ? "Revoke" : "Grant"} project memory`}
            onClick={() => setProjectAllowed((allowed) => !allowed)}
          >
            <span />
          </button>
        </div>
      </div>
    </div>
  );
}
