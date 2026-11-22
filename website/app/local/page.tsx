import Link from "next/link";

import { pageMetadata } from "../site-metadata";

export const metadata = pageMetadata({
  path: "/local/",
  title: "Local AI memory for Claude Code and Codex",
  description: "Save project decisions on your Mac and retrieve them in later Claude Code or Codex sessions. Choose read, save, and delete access for each assistant.",
});

export default function LocalPage() {
  return <main id="main-content">
    <section className="page-hero"><div className="shell page-hero__grid"><div><p className="section-label">Available on Mac</p><h1>Local project memory.</h1></div><div className="page-hero__aside"><p>Save decisions with their sources in a vault on your Mac. Claude Code and Codex can ask for the project memories you’ve allowed them to read.</p><div className="requirement-row"><span>Works with</span><strong>Claude Code and Codex</strong><span>Storage</span><strong>On your Mac</strong><span>Setup</span><strong>Source installer</strong></div></div></div></section>
    <section className="mode-section shell"><div className="section-intro"><h2>Use the same decision in a fresh session.</h2></div><div className="lifecycle-grid"><article><h3>Save what matters</h3><p>Keep a project rule, correction, or decision with a reference to where it came from.</p></article><article><h3>Recall it when needed</h3><p>Ask a connected assistant for the saved decision in a later session.</p></article><article><h3>Choose who can use it</h3><p>Set project permissions for each assistant and review what was shared. <Link href="/governance/">Explore governance</Link>.</p></article></div></section>
    <section className="beta-trust shell"><div><h2>Where your information goes</h2></div><div><p>The vault stays on your Mac. Your connected AI provider may receive the context you allow an assistant to retrieve, and its data policy applies. The vault has no app-level encryption. Signed packages and an independent security audit are pending.</p><Link href="/privacy/">Read the privacy details <span aria-hidden="true">↗</span></Link></div></section>
    <section className="beta-cta"><div className="shell"><h2>Try Ninai on your Mac</h2><Link className="button button--acid" href="/install/">See Mac setup <span aria-hidden="true">↗</span></Link></div></section>
  </main>;
}
