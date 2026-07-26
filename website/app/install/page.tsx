import type { Metadata } from "next";
import Link from "next/link";

import { CopyCommand } from "@/components/copy-command";

export const metadata: Metadata = {
  title: "Install Ninai AI memory locally or use the hosted beta",
  description:
    "Join Ninai's operator-assisted hosted beta or install the available open-source local MCP memory engine.",
  alternates: { canonical: "/install/" },
  openGraph: {
    title: "Choose how to run Ninai",
    description: "Hosted beta status and the complete local engine installation path.",
    url: "/install/",
    images: [
      {
        url: "/assets/og-image.png",
        width: 1200,
        height: 630,
        alt: "Install the Ninai local-first AI memory MVP",
      },
    ],
  },
};

const installCommand = `git clone https://github.com/HariDarshan2321/ninai.git
cd ninai
./scripts/install-local`;

const appCommand = `~/.ninai-app/venv/bin/ninai-app`;

const grantCommand = `~/.ninai-app/venv/bin/ninai permission grant claude-code project
~/.ninai-app/venv/bin/ninai permission list claude-code`;

const registerCommand = `claude mcp add --transport stdio --scope user ninai-local -- \
  "$HOME/.ninai-app/venv/bin/ninai-mcp"`;

const registerCodexCommand = `codex mcp add ninai-local --env NINAI_CLIENT_ID=codex -- \
  "$HOME/.ninai-app/venv/bin/ninai-mcp"
~/.ninai-app/venv/bin/ninai permission grant codex project`;

const hostedClaudeCommand = `claude mcp add --transport http --scope user ninai-cloud \\
  https://ninai-cloud.onrender.com/mcp
claude`;

const hostedCodexCommand = `codex mcp add ninai-cloud --url https://ninai-cloud.onrender.com/mcp
codex mcp login ninai-cloud --scopes ninai:read,ninai:propose,ninai:remember
codex mcp list`;

const hostedProposalPrompt = `Use Ninai propose_memory to propose this project decision:
"All database migrations must remain reversible."
Use the project ID from my Ninai dashboard, source_uri "user://onboarding/decision-1",
and a new idempotency key. Return the proposal ID and source URI.`;

const hostedRecallPrompt = `Use Ninai recall to answer: What did we decide about database migrations?
Purpose: verify the approved onboarding memory in a fresh session.
Include the source URI. Expected source: user://onboarding/decision-1.`;

const localRememberPrompt = `Use Ninai to remember exactly this durable project decision:
"All database migrations must remain reversible."
Store it as a decision in project scope with source_uri "user://onboarding/decision-1".
Then report the stored memory ID and source URI.`;

const localRecallPrompt = `Use Ninai recall to answer: What did we decide about database migrations?
Purpose: verify memory in a fresh session.
Include the source URI.`;

export default function InstallPage() {
  return (
    <main id="main-content">
      <section className="page-hero page-hero--install">
        <div className="shell page-hero__grid">
          <div>
            <p className="section-label">Choose your mode</p>
            <h1>Run local now. Join the hosted beta by invitation.</h1>
          </div>
          <div className="page-hero__aside">
            <p>
              The local engine is available today. The hosted endpoint and OAuth login are
              live, while workspace and client grants remain operator-assisted during beta.
            </p>
            <div className="requirement-row">
              <span>Local</span><strong>Available</strong>
              <span>Hosted</span><strong>Invitation beta</strong>
              <span>Cloud sync</span><strong>Never automatic</strong>
            </div>
          </div>
        </div>
      </section>

      <section className="install-choice shell" aria-label="Deployment choices">
        <article><span className="status-pill status-pill--ready">Available now</span><h2>Local engine</h2><p>Keep the complete vault in SQLite on this machine. No account is required.</p><a href="#local-install">Continue to local install ↓</a></article>
        <article><span className="status-pill">Invitation beta</span><h2>Hosted Beta</h2><p>OAuth login is live for Claude Code and Codex. An operator still provisions each workspace, connection, and least-privilege grant.</p><a href="#hosted-beta">Configure a beta client ↓</a></article>
      </section>

      <section className="install-layout shell" id="hosted-beta">
        <aside className="install-toc">
          <p className="section-label">Hosted beta</p>
          <a href="#hosted-account">Ninai account</a>
          <a href="#hosted-claude">Claude Code</a>
          <a href="#hosted-codex">Codex</a>
          <a href="#hosted-verify">First memory</a>
          <a href="https://ninai-cloud.onrender.com/control">Control center ↗</a>
        </aside>
        <div className="install-content">
          <section className="install-step" id="hosted-account">
            <div className="install-step__number">01</div>
            <div>
              <p className="install-step__label">Ninai account</p>
              <h2>Sign in and create one workspace and project.</h2>
              <p>The hosted vault is separate from local mode. Open the control center, sign in with Auth0, create a workspace, then create the project boundary you want to share.</p>
              <p><a href="https://ninai-cloud.onrender.com/control">Open the hosted control center ↗</a></p>
            </div>
          </section>
          <section className="install-step" id="hosted-claude">
            <div className="install-step__number">02</div>
            <div>
              <p className="install-step__label">Claude Code</p>
              <h2>Add Ninai, then authenticate in the browser.</h2>
              <p>Open <code>/mcp</code>, approve Ninai, and choose Authenticate. Then email <a href="mailto:hello@ninai.io?subject=Ninai%20Claude%20beta%20connection">hello@ninai.io</a> from your sign-in address and say “Claude connected.” The beta operator binds the public client ID and grants your project. Never send a token, authorization code, or secret.</p>
              <CopyCommand>{hostedClaudeCommand}</CopyCommand>
            </div>
          </section>
          <section className="install-step" id="hosted-codex">
            <div className="install-step__number">03</div>
            <div>
              <p className="install-step__label">Codex</p>
              <h2>Add the same endpoint as a separate connection.</h2>
              <p>Complete browser login, then email <a href="mailto:hello@ninai.io?subject=Ninai%20Codex%20beta%20connection">hello@ninai.io</a> from the same address and say “Codex connected.” Restart Codex after the operator confirms the project grant.</p>
              <CopyCommand>{hostedCodexCommand}</CopyCommand>
            </div>
          </section>
          <section className="install-step" id="hosted-verify">
            <div className="install-step__number">04</div>
            <div>
              <p className="install-step__label">First memory</p>
              <h2>Propose, approve, then recall one safe test.</h2>
              <p>After the operator confirms your project grant, paste this into the connected client. Open the dashboard Review queue and approve the proposal, then start a fresh session and run the recall prompt.</p>
              <CopyCommand>{hostedProposalPrompt}</CopyCommand>
              <CopyCommand>{hostedRecallPrompt}</CopyCommand>
            </div>
          </section>
          <div className="notice notice--good">
            <strong>Operator-assisted while the beta is small</strong>
            <p>OAuth dynamic registration does not silently grant memory access. Sign in to the <a href="https://ninai-cloud.onrender.com/control">hosted control center</a> to manage projects, grants, review, export, and revocation. See the <a href="https://github.com/HariDarshan2321/ninai/blob/main/docs/HOSTED-BETA.md">complete beta guide</a>.</p>
          </div>
        </div>
      </section>

      <section className="install-layout shell" id="local-install">
        <aside className="install-toc">
          <p className="section-label">On this page</p>
          <a href="#engine">01 · Install engine</a>
          <a href="#desktop">02 · Open the app</a>
          <a href="#permissions">03 · Grant a scope</a>
          <a href="#register">04 · Connect an agent</a>
          <a href="#verify">05 · Verify</a>
          <a href="#capture">06 · Enable capture</a>
          <a href="#limits">07 · MVP boundaries</a>
        </aside>

        <div className="install-content">
          <section className="install-step" id="engine">
            <div className="install-step__number">01</div>
            <div>
              <p className="install-step__label">Install engine</p>
              <h2>Clone and install the local package.</h2>
              <p>
                Ninai requires Python 3.11 or newer. The installer automatically chooses
                Python 3.13, 3.12, or 3.11 and installs the engine and desktop app in
                <code> ~/.ninai-app</code>. On macOS, run <code>brew install python@3.13</code>
                first if no compatible version is installed.
              </p>
              <CopyCommand>{installCommand}</CopyCommand>
            </div>
          </section>

          <section className="install-step" id="desktop">
            <div className="install-step__number">02</div>
            <div>
              <p className="install-step__label">Open the local app</p>
              <h2>See the vault before connecting an agent.</h2>
              <p>The desktop app shows memories, sources, permissions, and every disclosure. It uses the same local SQLite vault as the MCP server and requires no account.</p>
              <CopyCommand>{appCommand}</CopyCommand>
            </div>
          </section>

          <section className="install-step" id="permissions">
            <div className="install-step__number">03</div>
            <div>
              <p className="install-step__label">Grant scopes</p>
              <h2>Start with the smallest useful boundary.</h2>
              <p>
                Recall is denied by default. Grant only the scopes Claude Code needs for
                the initial workflow; personal, health, and finance remain unavailable.
              </p>
              <CopyCommand>{grantCommand}</CopyCommand>
            </div>
          </section>

          <section className="install-step" id="register">
            <div className="install-step__number">04</div>
            <div>
              <p className="install-step__label">Register MCP</p>
              <h2>Add the local server to Claude Code or Codex.</h2>
              <p>Use the stable executable path below, then restart the client. In Claude Code, open <code>/mcp</code>; in Codex, run <code>codex mcp list</code>.</p>
              <CopyCommand>{registerCommand}</CopyCommand>
              <p>For Codex, use its own client identity and permission:</p>
              <CopyCommand>{registerCodexCommand}</CopyCommand>
            </div>
          </section>

          <section className="install-step" id="verify">
            <div className="install-step__number">05</div>
            <div>
              <p className="install-step__label">Verify the boundary</p>
              <h2>Remember, recall, revoke.</h2>
              <div className="verify-grid">
                <div>
                  <span>STORE</span>
                  <p>Ask Claude: “Remember that the Ninai dashboard must be ready before launch.”</p>
                </div>
                <div>
                  <span>RECALL</span>
                  <p>Start a fresh session: “What must I finish before launch?”</p>
                </div>
                <div>
                  <span>REVOKE</span>
                  <p><code>ninai permission revoke claude-code project</code>, then repeat the request.</p>
                </div>
              </div>
              <p>Paste the first prompt now, then open a fresh session and paste the second.</p>
              <CopyCommand>{localRememberPrompt}</CopyCommand>
              <CopyCommand>{localRecallPrompt}</CopyCommand>
              <div className="notice notice--good">
                <strong>Expected result</strong>
                <p>The first recall includes a source URI. The second returns no project facts.</p>
              </div>
            </div>
          </section>

          <section className="install-step" id="capture">
            <div className="install-step__number">06</div>
            <div>
              <p className="install-step__label">Optional automatic capture</p>
              <h2>Add capture only after explicit recall works.</h2>
              <p>
                Claude Code can capture compact durable outcomes from existing MCP tools through
                the included PostToolUse hook. Follow the repository instructions and merge the
                hook entry into an existing <code>.claude/settings.json</code>; do not overwrite
                your project settings.
              </p>
              <p><a href="https://github.com/HariDarshan2321/ninai#2-optional-capture-results-from-existing-mcp-tools">Open the optional hook guide ↗</a></p>
            </div>
          </section>

          <section className="install-step" id="limits">
            <div className="install-step__number">07</div>
            <div>
              <p className="install-step__label">MVP boundaries</p>
              <h2>Know what this build is—and is not.</h2>
              <ul className="limit-list">
                <li><span>Included</span> Local SQLite, FTS5, explicit scopes, provenance, access logs, soft deletion.</li>
                <li><span>Included</span> Claude Code PostToolUse capture and explicit MCP remember/recall.</li>
                <li><span>Not yet</span> SQLCipher, signed desktop releases, universal capture, or an independent audit.</li>
                <li><span>Not included</span> Automatic local-to-cloud sync, billing, Gmail OAuth, or mobile applications.</li>
              </ul>
              <p className="install-next">
                Questions? <a href="mailto:hello@ninai.io">hello@ninai.io</a> · Read the{" "}
                <Link href="/privacy/">privacy architecture</Link>.
              </p>
            </div>
          </section>
        </div>
      </section>
    </main>
  );
}
