import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Client compatibility and test status",
  description: "See which AI clients Ninai has tested, which integrations are in development, and which host-controlled restrictions apply.",
  alternates: { canonical: "/compatibility/" },
  robots: { index: false, follow: true },
  openGraph: { title: "Ninai client compatibility", description: "Tested support, development status, and host restrictions—without guesswork.", url: "/compatibility/", images: [{ url: "/assets/og-image.png", width: 1200, height: 630, alt: "Ninai client compatibility" }] },
};

const clients = [
  ["Claude Code", "Available on Mac", "The installer detects Claude Code, connects Ninai, and adds consent-based session handoff."],
  ["Codex CLI / IDE", "Available on Mac", "The installer detects Codex, connects Ninai, and adds consent-based session handoff."],
  ["Claude.ai", "Cloud coming later", "Remote browser-chat integration is not part of the local MVP."],
  ["ChatGPT", "Cloud coming later", "Remote workspace integration is not part of the local MVP."],
  ["Claude Desktop / Cowork", "Host acceptance pending", "Availability and authentication depend on the selected host surface, plan, and account policy."],
  ["Anthropic API", "Planned", "A client application must explicitly call Ninai tools; Ninai cannot observe unrelated conversations."],
  ["OpenAI Responses API", "Planned", "A client application must explicitly connect and invoke Ninai."],
];

export default function CompatibilityPage() {
  return <main id="main-content"><section className="page-hero"><div className="shell page-hero__grid"><div><p className="section-label">Compatibility · current status</p><h1>Tested means tested.</h1></div><div className="page-hero__aside"><p>The MVP supports local Claude Code and Codex on Mac. Cloud-hosted connections are coming later.</p></div></div></section>
  <section className="compat-section shell"><div className="compat-table" role="table" aria-label="Ninai client compatibility"><div className="compat-row compat-row--head" role="row"><strong role="columnheader">Client</strong><strong role="columnheader">Status</strong><strong role="columnheader">What that means</strong></div>{clients.map(([client,status,note]) => <div className="compat-row" role="row" key={client}><strong role="cell">{client}</strong><span role="cell">{status}</span><p role="cell">{note}</p></div>)}</div><div className="notice"><strong>MVP boundary</strong><p>Ninai connects supported tools installed on the same Mac. It does not passively read browser chats.</p></div><p className="install-next">Want the working path? <Link href="/install/">Get Ninai for Mac</Link>.</p></section></main>;
}
