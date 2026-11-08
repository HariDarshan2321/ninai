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
  ["Gemini CLI", "Preview on Mac", "The installer can connect Gemini to the same local memory with separate access. Real-model acceptance is still in progress."],
  ["Other local AI tools", "Manual setup", "Compatible tools can connect through Ninai's local interface after the user allows access. Automatic session capture depends on the tool."],
  ["Claude.ai", "Coming later", "Remote browser-chat integration is not available today."],
  ["ChatGPT", "Coming later", "Remote workspace integration is not available today."],
  ["Claude Desktop / Cowork", "Host acceptance pending", "Availability and authentication depend on the selected host surface, plan, and account policy."],
  ["Anthropic API", "Planned", "A client application must explicitly call Ninai tools; Ninai cannot observe unrelated conversations."],
  ["OpenAI Responses API", "Planned", "A client application must explicitly connect and invoke Ninai."],
];

export default function CompatibilityPage() {
  return <main id="main-content"><section className="page-hero"><div className="shell page-hero__grid"><div><p className="section-label">Compatibility · current status</p><h1>Tested means tested.</h1></div><div className="page-hero__aside"><p>The current release supports Claude Code and Codex on Mac. Hosted connections are coming later.</p></div></div></section>
  <section className="compat-section shell"><div className="compat-table" role="table" aria-label="Ninai client compatibility"><div className="compat-row compat-row--head" role="row"><strong role="columnheader">Client</strong><strong role="columnheader">Status</strong><strong role="columnheader">What that means</strong></div>{clients.map(([client,status,note]) => <div className="compat-row" role="row" key={client}><strong role="cell">{client}</strong><span role="cell">{status}</span><p role="cell">{note}</p></div>)}</div><div className="notice"><strong>Current boundary</strong><p>Ninai connects supported tools installed on the same Mac. It does not passively read browser chats.</p></div><p className="install-next">Want the working path? <Link href="/install/">See installation options</Link>.</p></section></main>;
}
