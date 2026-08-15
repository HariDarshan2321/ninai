import type { Metadata } from "next";
import Link from "next/link";

import { CopyCommand } from "@/components/copy-command";

export const metadata: Metadata = {
  title: "Install Ninai AI memory locally or use the hosted invitation beta",
  description:
    "Connect a supported cloud AI client to Ninai's hosted dashboard or install the open-source local memory engine on macOS.",
  alternates: { canonical: "/install/" },
  openGraph: {
    title: "Choose how to run Ninai",
    description: "Hosted invitation-beta status and the complete local engine installation path.",
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

const installCommand = `curl -fsSL https://raw.githubusercontent.com/HariDarshan2321/ninai/main/scripts/install-local | bash`;

const installClaudeCommand = `${installCommand} -s -- --client claude-code`;

const installCodexCommand = `${installCommand} -s -- --client codex`;
const installBothCommand = `${installCommand} -s -- --client both`;

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
            <h1>Install locally or start a hosted workspace.</h1>
          </div>
          <div className="page-hero__aside">
            <p>
              The local engine is available today. The hosted endpoint and OAuth login are
              live; create an account, connect an AI, and grant one project from the dashboard.
            </p>
            <div className="requirement-row">
              <span>Local</span><strong>macOS</strong>
              <span>Hosted</span><strong>Invitation beta</strong>
              <span>Cloud sync</span><strong>Never automatic</strong>
            </div>
          </div>
        </div>
      </section>

      <section className="install-choice shell" aria-label="Deployment choices">
        <article><span className="status-pill status-pill--ready">Available now</span><h2>Local macOS app</h2><p>Install the owner UI and keep the complete vault in SQLite on your Mac. No account is required.</p><a href="#local-install">Continue to local install ↓</a></article>
        <article><span className="status-pill">Invitation beta</span><h2>Hosted cloud</h2><p>Create an account, make one project, and connect a supported remote MCP client to the separate PostgreSQL vault.</p><Link href="/start/">Start hosted onboarding →</Link></article>
      </section>

      <section className="install-layout shell" id="hosted-beta">
        <aside className="install-toc">
          <p className="section-label">Hosted invitation beta</p>
          <a href="#hosted-account">Ninai account</a>
          <a href="#hosted-claude">Claude Code</a>
          <a href="#hosted-codex">Codex</a>
          <a href="#hosted-chat">ChatGPT / Claude.ai</a>
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
              <div className="inline-actions"><a href="https://ninai-cloud.onrender.com/control/login?screen_hint=signup">Create account ↗</a><a href="https://ninai-cloud.onrender.com/control/login">Sign in</a></div>
            </div>
          </section>
          <section className="install-step" id="hosted-claude">
            <div className="install-step__number">02</div>
            <div>
              <p className="install-step__label">Claude Code</p>
              <h2>Add Ninai, then authenticate in the browser.</h2>
              <p>Open <code>/mcp</code>, approve Ninai, and choose Authenticate. OAuth creates a connection in your workspace with no memory access. In the Ninai dashboard, open Connections and grant only the project and actions this client needs.</p>
              <CopyCommand>{hostedClaudeCommand}</CopyCommand>
            </div>
          </section>
          <section className="install-step" id="hosted-codex">
            <div className="install-step__number">03</div>
            <div>
              <p className="install-step__label">Codex</p>
              <h2>Add the same endpoint as a separate connection.</h2>
              <p>Complete browser login, open the connection in your Ninai dashboard, and grant the intended project. Restart Codex after saving the grant.</p>
              <CopyCommand>{hostedCodexCommand}</CopyCommand>
            </div>
          </section>
          <section className="install-step" id="hosted-chat">
            <div className="install-step__number">04</div>
            <div>
              <p className="install-step__label">ChatGPT and Claude.ai</p>
              <h2>Add Ninai as a remote MCP app when your plan supports custom connectors.</h2>
              <p>Use <code>https://ninai-cloud.onrender.com/mcp</code> as the server URL and complete Ninai OAuth. ChatGPT currently limits custom MCP apps to supported managed workspaces, and Claude availability depends on the selected Claude surface and plan. These hosts use the cloud vault—not the private database on your Mac.</p>
              <p>After the host scans Ninai&apos;s tools and you approve OAuth, the connection appears automatically in your dashboard. It starts with zero project grants; choose the project and allowed actions before the first recall.</p>
            </div>
          </section>
          <section className="install-step" id="hosted-verify">
            <div className="install-step__number">05</div>
            <div>
              <p className="install-step__label">First memory</p>
              <h2>Propose, approve, then recall one safe test.</h2>
              <p>After you save the project grant, paste this into the connected client. Open the dashboard Review queue and approve the proposal, then start a fresh session and run the recall prompt.</p>
              <CopyCommand>{hostedProposalPrompt}</CopyCommand>
              <CopyCommand>{hostedRecallPrompt}</CopyCommand>
            </div>
          </section>
          <div className="notice notice--good">
            <strong>Connected automatically, access denied by default</strong>
            <p>OAuth dynamic registration creates the client connection but never silently grants memory access. Sign in to the <a href="https://ninai-cloud.onrender.com/control">hosted control center</a> to choose projects and actions, then manage review, export, and revocation. See the <a href="https://github.com/HariDarshan2321/ninai/blob/main/docs/HOSTED-BETA.md">complete beta guide</a>.</p>
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
              <h2>Install and connect in one command.</h2>
              <p>
                Choose your client below. The installer checks for Python 3.11+, installs
                the engine and desktop app in <code> ~/.ninai-app</code>, grants only the
                project scope, and registers the local MCP server. It does not require a Ninai account.
              </p>
              <p><strong>Claude Code + Codex</strong></p>
              <CopyCommand>{installBothCommand}</CopyCommand>
              <details><summary>Connect only one client</summary><CopyCommand>{installClaudeCommand}</CopyCommand><CopyCommand>{installCodexCommand}</CopyCommand></details>
              <p><a className="button button--ink" href="/download/install-ninai-macos.sh" download>Download the macOS installer ↓</a></p>
              <p>After downloading, run <code>bash ~/Downloads/install-ninai-macos.sh --client both</code>. The installer merges lifecycle hooks without overwriting existing settings and asks before enabling local session archive.</p>
              <p>Review the <a href="https://github.com/HariDarshan2321/ninai/blob/main/scripts/install-local">installer source</a> before running a downloaded script. If Python is missing, install it with <code>brew install python@3.13</code> and rerun the same command.</p>
              <p>The one-command installer is the supported Mac download today. A double-click <code>Ninai.app</code> is packaged internally but will be published only after Developer ID signing and Apple notarization. Do not bypass Gatekeeper for an unsigned build.</p>
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
              <p className="install-step__label">Automatic handoff</p>
              <h2>End in Claude Code. Continue in Codex.</h2>
              <p>
                When you consent during installation, Ninai merges SessionStart, Stop, and
                SessionEnd hooks for Claude Code and Codex. The transcript remains in this Mac&apos;s
                vault; only a small, project-scoped historical excerpt is injected on the next start.
                Disable it with <code>~/.ninai-app/venv/bin/ninai capture disable</code>.
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
                <li><span>Included</span> Local Claude Code ↔ Codex lifecycle handoff and explicit MCP remember/recall.</li>
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
