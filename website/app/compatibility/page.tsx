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
  ["Claude Code", "Local path available", "Local MCP and consent-based lifecycle capture are implemented. The hosted OAuth CLI acceptance round trip is still pending."],
  ["Codex CLI / IDE", "Self-hosted path verified", "A real-host self-hosted round trip passed. The hosted OAuth acceptance round trip is still pending."],
  ["Claude.ai", "Hosted OAuth read verified", "OAuth, tool discovery, and a production read-tool call passed. The full hosted write, provenance, and revocation gate is still pending."],
  ["ChatGPT", "Hosted OAuth read verified", "Developer-mode install, OAuth, tool invocation, and a production read-tool call passed. The full hosted write, provenance, and revocation gate is still pending."],
  ["Claude Desktop / Cowork", "Host acceptance pending", "Availability and authentication depend on the selected host surface, plan, and account policy."],
  ["Anthropic API", "Planned", "A client application must explicitly call Ninai tools; Ninai cannot observe unrelated conversations."],
  ["OpenAI Responses API", "Planned", "A client application must explicitly connect and invoke Ninai."],
];

export default function CompatibilityPage() {
  return <main id="main-content"><section className="page-hero"><div className="shell page-hero__grid"><div><p className="section-label">Compatibility · current status</p><h1>Tested means tested.</h1></div><div className="page-hero__aside"><p>This matrix separates verified read-path evidence from the remaining full acceptance gate. Hosted mode remains an invitation beta until write, recall, provenance, and revocation pass together on the release deployment.</p></div></div></section>
  <section className="compat-section shell"><div className="compat-table" role="table" aria-label="Ninai client compatibility"><div className="compat-row compat-row--head" role="row"><strong role="columnheader">Client</strong><strong role="columnheader">Status</strong><strong role="columnheader">What that means</strong></div>{clients.map(([client,status,note]) => <div className="compat-row" role="row" key={client}><strong role="cell">{client}</strong><span role="cell">{status}</span><p role="cell">{note}</p></div>)}</div><div className="notice"><strong>Invitation-beta boundary</strong><p>Claude.ai and ChatGPT have each completed OAuth and a hosted read-tool call. That does not yet prove the full write, recall, provenance, and revocation release gate. MCP is a tool connection, not a universal conversation listener.</p></div><p className="install-next">Want the working path? <Link href="/local/">Use the local engine</Link>. Want invitation-beta access? <a href="mailto:hello@ninai.io?subject=Ninai%20hosted%20invitation%20beta">Contact the founder</a>.</p></section></main>;
}
