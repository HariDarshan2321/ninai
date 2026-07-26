import type { Metadata } from "next";
import Link from "next/link";

import { CopyCommand } from "@/components/copy-command";

export const metadata: Metadata = {
  title: "Choose hosted beta or local installation",
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
cd ninai/engine
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install .`;

const grantCommand = `ninai permission grant claude-code project
ninai permission grant claude-code work
ninai permission list claude-code`;

const registerCommand = `claude mcp add ninai -- ninai-mcp`;

const hookCommand = `mkdir -p .claude/hooks
cp /path/to/ninai/.claude/hooks/ninai_post_tool_use.py .claude/hooks/
cp /path/to/ninai/.claude/settings.example.json .claude/settings.json
chmod +x .claude/hooks/ninai_post_tool_use.py`;

const hostedClaudeCommand = `claude mcp add --transport http --scope user ninai \\
  https://ninai-cloud.onrender.com/mcp
claude`;

const hostedCodexCommand = `codex mcp add ninai --url https://ninai-cloud.onrender.com/mcp
codex mcp login ninai --scopes ninai:read,ninai:propose,ninai:remember
codex mcp list`;

const hostedRecallPrompt = `Use the Ninai recall tool to answer: What project decisions should I carry into this session?
Purpose: resume the current project without repeating prior decisions.
Include the source URI for every fact. If Ninai returns nothing, say that clearly.`;

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
          <a href="#hosted-claude">Claude Code</a>
          <a href="#hosted-codex">Codex</a>
          <a href="#hosted-verify">First recall</a>
          <a href="https://ninai-cloud.onrender.com/control">Control center ↗</a>
        </aside>
        <div className="install-content">
          <section className="install-step" id="hosted-claude">
            <div className="install-step__number">01</div>
            <div>
              <p className="install-step__label">Claude Code</p>
              <h2>Add Ninai, then authenticate in the browser.</h2>
              <p>Open <code>/mcp</code>, approve Ninai, and choose Authenticate. Tell the beta operator when login finishes so they can bind the public OAuth client ID and grant your project. Never send them a token or secret.</p>
              <CopyCommand>{hostedClaudeCommand}</CopyCommand>
            </div>
          </section>
          <section className="install-step" id="hosted-codex">
            <div className="install-step__number">02</div>
            <div>
              <p className="install-step__label">Codex</p>
              <h2>Add the same endpoint as a separate connection.</h2>
              <p>Complete browser login, then wait for the operator to bind the Codex client and grant the requested project. Restart Codex and confirm the server reports OAuth.</p>
              <CopyCommand>{hostedCodexCommand}</CopyCommand>
            </div>
          </section>
          <section className="install-step" id="hosted-verify">
            <div className="install-step__number">03</div>
            <div>
              <p className="install-step__label">First recall</p>
              <h2>Give the agent a precise, testable request.</h2>
              <p>After the operator confirms your project grant, paste this into either client. A useful result includes at least one source URI.</p>
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
          <a href="#permissions">02 · Grant scopes</a>
          <a href="#register">03 · Register MCP</a>
          <a href="#capture">04 · Enable capture</a>
          <a href="#verify">05 · Verify</a>
          <a href="#limits">06 · MVP boundaries</a>
        </aside>

        <div className="install-content">
          <section className="install-step" id="engine">
            <div className="install-step__number">01</div>
            <div>
              <p className="install-step__label">Install engine</p>
              <h2>Clone and install the local package.</h2>
              <p>
                Ninai uses the Python standard library for its engine and the official MCP
                SDK for transport. The normal installation builds a local wheel.
              </p>
              <CopyCommand>{installCommand}</CopyCommand>
            </div>
          </section>

          <section className="install-step" id="permissions">
            <div className="install-step__number">02</div>
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
            <div className="install-step__number">03</div>
            <div>
              <p className="install-step__label">Register MCP</p>
              <h2>Add one local server to Claude Code.</h2>
              <p>Restart Claude Code afterward, open <code>/mcp</code>, and confirm Ninai is available.</p>
              <CopyCommand>{registerCommand}</CopyCommand>
            </div>
          </section>

          <section className="install-step" id="capture">
            <div className="install-step__number">04</div>
            <div>
              <p className="install-step__label">Optional automatic capture</p>
              <h2>Observe existing MCP activity through the host.</h2>
              <p>
                Copy the PostToolUse hook into a project where Claude already uses Linear,
                GitHub, or another MCP server. You do not reconnect those services to Ninai.
              </p>
              <CopyCommand>{hookCommand}</CopyCommand>
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

          <section className="install-step" id="limits">
            <div className="install-step__number">06</div>
            <div>
              <p className="install-step__label">MVP boundaries</p>
              <h2>Know what this build is—and is not.</h2>
              <ul className="limit-list">
                <li><span>Included</span> Local SQLite, FTS5, explicit scopes, provenance, access logs, soft deletion.</li>
                <li><span>Included</span> Claude Code PostToolUse capture and explicit MCP remember/recall.</li>
                <li><span>Not yet</span> SQLCipher, signed desktop releases, universal capture, or an independent audit.</li>
                <li><span>Not included</span> Cloud sync, accounts, billing, Gmail OAuth, or mobile applications.</li>
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
