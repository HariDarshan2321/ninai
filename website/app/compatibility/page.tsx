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
  ["Claude Code", "Local path available", "Local MCP and optional PostToolUse capture are implemented. Hosted round-trip testing is pending."],
  ["Codex CLI / IDE", "Hosted support in development", "Not yet release-tested against the remote Ninai service."],
  ["Claude web / Desktop / Cowork", "Not yet verified", "Availability and authentication depend on host MCP capabilities and account policy."],
  ["ChatGPT", "Not yet verified", "MCP/app access depends on the ChatGPT plan, workspace settings, and host review restrictions."],
  ["Anthropic API", "Planned", "A client application must explicitly call Ninai tools; Ninai cannot observe unrelated conversations."],
  ["OpenAI Responses API", "Planned", "A client application must explicitly connect and invoke Ninai."],
];

export default function CompatibilityPage() {
  return <main id="main-content"><section className="page-hero"><div className="shell page-hero__grid"><div><p className="section-label">Compatibility · current status</p><h1>Tested means tested.</h1></div><div className="page-hero__aside"><p>This matrix separates implemented local behavior from hosted targets. Ninai will not claim cross-provider support until the round-trip and revocation acceptance test passes.</p></div></div></section>
  <section className="compat-section shell"><div className="compat-table" role="table" aria-label="Ninai client compatibility"><div className="compat-row compat-row--head" role="row"><strong role="columnheader">Client</strong><strong role="columnheader">Status</strong><strong role="columnheader">What that means</strong></div>{clients.map(([client,status,note]) => <div className="compat-row" role="row" key={client}><strong role="cell">{client}</strong><span role="cell">{status}</span><p role="cell">{note}</p></div>)}</div><div className="notice"><strong>Important host boundary</strong><p>MCP is a tool connection, not a universal conversation listener. A host decides when tools are available and invoked. Ninai cannot silently read all ChatGPT or Claude conversations.</p></div><p className="install-next">Want the working path? <Link href="/local/">Use the local engine</Link>. Want hosted updates? <a href="mailto:hello@ninai.io?subject=Ninai%20hosted%20beta">Contact the founder</a>.</p></section></main>;
}
