import type { Metadata } from "next";
import Link from "next/link";

import { CopyCommand } from "@/components/copy-command";

export const metadata: Metadata = {
  title: "Install the local MCP memory MVP",
  description:
    "Install Ninai locally, grant Claude Code selected memory scopes, register the MCP server, and enable optional PostToolUse capture.",
  alternates: { canonical: "/install/" },
  openGraph: {
    title: "Install the Ninai local memory MVP",
    description: "Run a permissioned AI memory server locally in minutes.",
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

export default function InstallPage() {
  return (
    <main id="main-content">
      <section className="page-hero page-hero--install">
        <div className="shell page-hero__grid">
          <div>
            <p className="section-label">Install / MVP 0.1</p>
            <h1>Run Ninai on your machine.</h1>
          </div>
          <div className="page-hero__aside">
            <p>
              The current MVP is a Python MCP server backed by local SQLite. It is built
              for technical evaluation and the Claude Code integration path.
            </p>
            <div className="requirement-row">
              <span>Python</span><strong>3.11+</strong>
              <span>Account</span><strong>Not required</strong>
              <span>Storage</span><strong>Local SQLite</strong>
            </div>
          </div>
        </div>
      </section>

      <section className="install-layout shell">
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
