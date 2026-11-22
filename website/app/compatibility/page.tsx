import Link from "next/link";

import { pageMetadata } from "../site-metadata";

export const metadata = pageMetadata({
  path: "/compatibility/",
  title: "AI Assistant Compatibility on Mac",
  description: "Check which AI assistants work with Ninai on Mac, including verified local handoff from Claude Code to Codex, previews, and private hosted tests.",
});

const clients = [
  ["Claude Code", "Available on Mac", "The installer detects Claude Code, connects Ninai, and adds consent-based session handoff."],
  ["Codex CLI", "Available on Mac", "The installer detects Codex, connects Ninai, and adds consent-based session handoff."],
  ["Cursor / VS Code", "Agent testing pending", "Connection setup and repair are available. Authenticated editor-agent handoff has not been verified."],
  ["Gemini CLI", "Preview on Mac", "The installer can connect Gemini to the same local memory with separate access. Real-model acceptance is still in progress."],
  ["Other local AI tools", "Manual setup", "Compatible tools can connect through Ninai's local interface after the user allows access. Automatic session capture depends on the tool."],
  ["Claude.ai", "Host acceptance pending", "Public directory listing and a complete sign-in-to-recall test are pending. Availability depends on your account and plan."],
  ["ChatGPT", "Private hosted test", "Sign-in, recall, and access revocation passed in a private ChatGPT web test. Public directory availability and desktop support are pending."],
  ["Claude Desktop / Cowork", "Host acceptance pending", "Availability and authentication depend on the selected host surface, plan, and account policy."],
  ["Anthropic API", "Planned", "A client application must explicitly call Ninai tools; Ninai cannot observe unrelated conversations."],
  ["OpenAI Responses API", "Planned", "A client application must explicitly connect and invoke Ninai."],
];

export default function CompatibilityPage() {
  return <main id="main-content"><section className="page-hero"><div className="shell page-hero__grid"><div><h1>Assistant compatibility.</h1></div><div className="page-hero__aside"><p>Claude Code and Codex on Mac are the verified local setup. Hosted memory is a separate option for invited testing.</p></div></div></section>
  <section className="compat-section shell"><div className="compat-table" role="table" aria-label="Ninai client compatibility"><div className="compat-row compat-row--head" role="row"><strong role="columnheader">Client</strong><strong role="columnheader">Status</strong><strong role="columnheader">What that means</strong></div>{clients.map(([client,status,note]) => <div className="compat-row" role="row" key={client}><strong role="cell">{client}</strong><span role="cell">{status}</span><p role="cell">{note}</p></div>)}</div><div className="notice"><strong>Current boundary</strong><p>Local and hosted memory are separate. Connecting a tool does not grant it project access or make Ninai passively read browser chats.</p></div><p className="install-next">Want the working path? <Link href="/install/">See installation options</Link>.</p></section></main>;
}
