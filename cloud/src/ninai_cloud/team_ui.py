"""Browser controls for the opt-in team preview."""

TEAM_HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="robots" content="noindex,nofollow">
  <meta name="theme-color" content="#0b302b">
  <title>Ninai Team</title>
  <style>
    :root{color-scheme:light;--ink:#182421;--muted:#4b615a;--green:#0b302b;--paper:#f4efe5;--panel:#fffdf8;--line:#c6cfc5;--focus:#ae421f;font:16px/1.52 system-ui,sans-serif;color:var(--ink);background:var(--paper)}
    *{box-sizing:border-box}[hidden]{display:none!important}body{margin:0}a{color:var(--green)}
    a:focus-visible,button:focus-visible,input:focus-visible,select:focus-visible,textarea:focus-visible,summary:focus-visible{outline:3px solid var(--focus);outline-offset:3px}
    .skip{position:absolute;left:12px;top:12px;transform:translateY(-180%);z-index:3;background:var(--panel);padding:9px 14px}.skip:focus{transform:none}
    .top{background:var(--green);color:#fffdf8}.top>div{max-width:1160px;margin:auto;padding:15px clamp(16px,4vw,36px);display:flex;align-items:center;justify-content:space-between;gap:18px}.top a{color:inherit}.brand{font-weight:800;letter-spacing:-.04em;font-size:1.5rem;text-decoration:none}
    main{max-width:1160px;margin:auto;padding:0 clamp(16px,4vw,36px) 64px}.intro{padding:36px 0 22px}.intro p{margin:8px 0;max-width:68ch;color:var(--muted)}
    h1,h2,h3{line-height:1.15;letter-spacing:-.025em}h1{font-size:clamp(2.2rem,5vw,3.7rem);margin:0;font-weight:800}h2{font-size:1.45rem;margin:0 0 10px}h3{font-size:1.05rem;margin:0 0 8px}
    p{margin:0 0 12px}.muted,small{color:var(--muted)}.wrap{overflow-wrap:anywhere}code{font: .86em ui-monospace,monospace}
    .card{background:var(--panel);border:1px solid var(--line);border-radius:13px;padding:clamp(14px,3vw,24px);margin:0 0 14px;min-width:0}.card.accent{border-left:4px solid var(--green)}
    .layout{display:grid;grid-template-columns:11rem minmax(0,1fr);gap:20px;align-items:start}.layout nav{position:sticky;top:16px;padding:6px 0}.layout nav ul{margin:0;padding:0;list-style:none}.layout nav a{display:block;padding:8px 12px;border-radius:6px;font-weight:650}.layout nav a:hover{background:#e3eade}
    .row{display:flex;gap:12px;align-items:end;flex-wrap:wrap}.row>label{flex:1 1 225px}.row>button{flex:0 0 auto}.fields{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,215px),1fr));gap:12px}.field{display:grid;gap:5px;font-weight:650;min-width:0}
    input,textarea,select,button{font:inherit;min-height:44px}input,textarea,select{width:100%;min-width:0;padding:8px 10px;border:1px solid #879c91;border-radius:7px;background:#fff;color:var(--ink)}textarea{resize:vertical}
    button{border:1px solid var(--green);border-radius:7px;background:var(--green);color:#fff;padding:7px 13px;font-weight:700;cursor:pointer}button:hover{background:#1b4c43}button:disabled{opacity:.7;cursor:wait}.secondary{background:#fff;color:var(--green)}.secondary:hover{background:#e7ede3}
    form,fieldset{min-width:0}form>button{margin-top:10px}.row>button{margin-top:0}.group{margin-top:12px}.controls{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
    fieldset{border:1px solid var(--line);border-radius:7px;padding:8px 12px;margin:12px 0 0}legend{font-weight:650}.choices{display:flex;gap:14px;flex-wrap:wrap}.choice{display:flex;align-items:center;gap:5px;min-height:44px}.choice input{width:18px;min-height:0;height:18px;padding:0}
    details{border-top:1px solid var(--line);padding-top:12px;margin-top:12px}summary{cursor:pointer;min-height:34px;font-weight:700}details>form{margin-top:8px}
    .notice{padding:8px 11px;border-left:4px solid #326054;background:#edf1e7;margin:0 0 10px}.notice:empty{display:none}.error{background:#fbeddf;border-color:var(--focus);color:#6b2b1b}
    .list{display:grid;gap:8px;padding:0;list-style:none;margin:10px 0 0}.item{border:1px solid var(--line);border-radius:8px;padding:10px;overflow-wrap:anywhere}.item p:last-child{margin-bottom:0}.credential input{font-family:ui-monospace,monospace}
    .setup{max-width:780px;margin:0 auto 24px}.setup h2{margin-bottom:8px}.setup form{margin-top:14px}
    .setup-steps{display:flex;gap:16px;flex-wrap:wrap;padding:0;list-style:none;margin:0 0 18px;color:var(--muted)}
    .setup-steps [aria-current=step]{font-weight:750;color:var(--green);text-decoration:underline;text-underline-offset:6px}
    .brief-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,255px),1fr));gap:24px;margin-top:18px}
    pre{white-space:pre-wrap;overflow-wrap:anywhere}
    @media(max-width:720px){.layout{display:block}.layout nav{position:static;padding:0 0 12px}.layout nav ul{display:flex;flex-wrap:wrap;gap:4px}.layout nav a{padding:6px 8px}.intro{padding-top:24px}}
  </style>
</head>
<body>
<a class="skip" href="#main">Skip to main content</a>
<header class="top"><div><a class="brand" href="/control" aria-label="Ninai control center">Ninai</a><a href="/control">Control center</a></div></header>
<main id="main" tabindex="-1">
  <div class="intro"><h1>Ninai Team</h1><p>Share decisions and handoffs with the people and assistants on your project.</p></div>
  <p id="status" class="notice" role="status" aria-live="polite"></p>
  <p id="error" class="notice error" role="alert"></p>
  <section id="signin" class="card" aria-labelledby="sign-in-title" hidden>
    <h2 id="sign-in-title">Sign in to continue</h2>
    <a id="team-signin" href="/control/login?return=team">Sign in to Ninai</a>
  </section>
  <section id="team-join" class="card accent setup" aria-labelledby="join-title" hidden>
    <h2 id="join-title">Join your team</h2>
    <p>Use the Ninai account with the verified email your teammate invited.</p>
    <form id="join-team"><button>Accept invitation</button></form>
  </section>
  <section id="team-onboarding" class="card accent setup" aria-labelledby="setup-title" hidden>
    <h2 id="setup-title">Set up your team</h2>
    <ol class="setup-steps" aria-label="Setup progress">
      <li id="setup-step-team">Team</li><li id="setup-step-project">Project</li><li id="setup-step-invite">Teammates</li>
    </ol>
    <div id="setup-team">
      <p>Give your team a name to create a shared workspace.</p>
      <form id="setup-team-form" class="row">
        <label class="field">Team name<input name="name" required maxlength="100" autocomplete="organization"></label>
        <button>Create team</button>
      </form>
      <div class="controls group"><button type="button" id="setup-existing" class="secondary">Open my existing team</button></div>
    </div>
    <div id="setup-project" hidden>
      <p>Name the project your team is working on.</p>
      <form id="setup-project-form" class="row">
        <label class="field">Project name<input name="name" required maxlength="100"></label>
        <button>Create project</button>
      </form>
    </div>
    <div id="setup-invite" hidden>
      <p>Invite a teammate to the project you’ve selected.</p>
      <form id="setup-invite-form" class="row">
        <label class="field">Teammate email<input name="email" type="email" autocomplete="off" required maxlength="254"></label>
        <button>Create invite link</button>
      </form>
      <div id="setup-invite-result" class="group" hidden>
        <label class="field">Invite link<input id="setup-invite-link" readonly autocomplete="off" spellcheck="false"></label>
        <div class="controls group"><button type="button" id="setup-copy-invite" class="secondary">Copy invite link</button></div>
        <p class="muted group">Share this link with the invited teammate. It expires in 24 hours.</p>
      </div>
      <div class="controls group"><button type="button" class="secondary" id="setup-finish">Go to project brief</button></div>
    </div>
  </section>
  <section id="pilot-access" class="card" hidden>
    <h2>Team is invite-only</h2>
    <p>To join a project, open the invite link your teammate shared with you.</p>
  </section>
  <div id="dashboard" class="layout" hidden>
    <nav aria-label="Team workspace"><ul>
      <li><a href="#workspace">Workspace</a></li><li data-admin hidden><a href="#access">Access</a></li>
      <li data-project hidden><a href="#decisions">Decisions</a></li><li data-project hidden><a href="#assistants">Assistants</a></li>
      <li data-project hidden><a href="#context">Task context</a></li><li data-admin hidden><a href="#audit">Audit</a></li>
    </ul></nav>
    <div>
      <section class="card accent" id="workspace" aria-labelledby="workspace-title">
        <h2 id="workspace-title">Workspace</h2>
        <details id="workspace-settings"><summary>Workspace settings</summary>
        <form id="open-workspace" class="row group">
          <label class="field">Workspace ID<input name="workspace" required maxlength="36" autocomplete="off" autocapitalize="off" spellcheck="false"></label>
          <button>Open workspace</button>
        </form>
        <details><summary>Use an existing workspace or create your first workspace</summary>
          <div class="controls"><button type="button" id="find-workspace" class="secondary">Use my existing workspace</button></div>
          <form id="create-workspace" class="row group"><label class="field">Workspace name<input name="name" required maxlength="120"></label><button>Create workspace</button></form>
          <form id="enable" class="group"><p class="muted">A workspace owner can explicitly enable the team preview. Existing permissions stay separate.</p><button>Enable team preview</button></form>
        </details>
        <details><summary>Accept an invitation</summary>
          <p class="muted">Enter the workspace ID and the one-time invitation token shared with you.</p>
          <form id="accept" class="row"><label class="field">Invitation token<input name="token" required type="password" maxlength="128" autocomplete="off"></label><button>Accept invitation</button></form>
          <details><summary>My invitation details</summary><dl><dt>Identity issuer</dt><dd id="identity-issuer" class="wrap"></dd><dt>Identity subject</dt><dd id="identity-subject" class="wrap"></dd><dt>User ID</dt><dd id="identity-user" class="wrap"></dd></dl></details>
        </details>
        </details>
        <p class="group" id="workspace-selection" hidden></p>
      </section>

      <section class="card" id="access" aria-labelledby="access-title" data-admin hidden>
        <h2 id="access-title">Workspace access</h2>
        <div id="members"></div>
        <details><summary>Invite a member</summary>
          <form id="invite"><div class="fields">
            <label class="field">Recipient identity issuer<input name="issuer" type="url" required maxlength="255" autocomplete="off" autocapitalize="off" spellcheck="false"></label>
            <label class="field">Recipient identity subject<input name="subject" required maxlength="255" autocomplete="off" autocapitalize="off" spellcheck="false"></label>
            <label class="field">Workspace role<select name="role" data-owner-role><option value="member">Member</option><option value="admin">Administrator</option></select></label>
          </div><button>Create one-time invitation</button></form>
        </details>
        <details><summary>Change a workspace role or offboard a member</summary>
          <form id="member"><div class="fields">
            <label class="field">Member<select name="user" data-members required></select></label>
            <label class="field">New workspace role<select name="role" data-owner-role><option value="member">Member</option><option value="admin">Administrator</option><option value="remove">Offboard</option></select></label>
          </div><button>Apply workspace role</button></form>
        </details>
        <details><summary>Create a project or assign project access</summary>
          <form id="project" class="row">
            <label class="field">Project name<input name="name" required maxlength="100"></label>
            <label class="field">GitHub repository (optional)<input name="repository" placeholder="owner/repo" maxlength="240" autocomplete="off" spellcheck="false"></label>
            <button>Create project</button>
          </form>
          <form id="project-repository" class="row group">
            <label class="field">Project to connect<select name="project" data-projects-without-repo required></select></label>
            <label class="field">GitHub repository<input name="repository" required placeholder="owner/repo" maxlength="240" autocomplete="off" spellcheck="false"></label>
            <button>Connect existing project</button>
          </form>
          <form id="project-member" class="group"><div class="fields">
            <label class="field">Project<select name="project" data-all-projects required></select></label>
            <label class="field">Member<select name="user" data-members required></select></label>
            <label class="field">Project role<select name="role"><option value="member">Member</option><option value="maintainer">Maintainer</option><option value="remove">Remove direct access</option></select></label>
          </div><button>Apply project access</button></form>
        </details>
        <details><summary>Archive a project</summary>
          <form id="archive-project" class="row">
            <label class="field">Project to archive<select name="project" data-all-projects required></select></label>
            <button>Archive project</button>
          </form>
        </details>
        <details><summary>Manage groups</summary>
          <form id="group" class="row"><label class="field">Group name<input name="name" required maxlength="100"></label><button>Create group</button></form>
          <form id="group-edge" class="group"><div class="fields">
            <label class="field">Group<select name="group" data-groups required></select></label>
            <label class="field">Change type<select name="kind" id="group-kind"><option value="member">Member</option><option value="project">Project</option></select></label>
            <label class="field">Member or project<select name="subject" id="group-subject" required></select></label>
            <label class="field">Action<select name="active"><option value="true">Add</option><option value="false">Remove</option></select></label>
          </div><button>Apply group change</button></form>
        </details>
      </section>

      <section class="card" id="project-panel" aria-labelledby="project-title" hidden>
        <h2 id="project-title">Project</h2>
        <label class="field">Project with decision access<select id="active-project"></select></label>
        <p class="group muted" id="project-role"></p>
        <p id="project-repo" class="muted wrap"></p>
        <section id="project-brief" aria-labelledby="brief-title" hidden>
          <h3 id="brief-title" tabindex="-1">Project brief</h3>
          <div class="brief-grid">
            <div><h3>Recent handoffs</h3><div id="handoff-results" aria-live="polite"></div></div>
            <div><h3>Approved decisions</h3><div id="brief-decisions" aria-live="polite"></div></div>
          </div>
          <details><summary>Share a handoff</summary>
            <form id="browser-handoff" class="group"><div class="fields">
              <label class="field">Topic<input name="topic" required maxlength="80"></label>
              <label class="field">Status<select name="status"><option value="working">In progress</option>
                <option value="blocked">Blocked</option><option value="done">Done</option></select></label>
              <label class="field">Update<textarea name="summary" required maxlength="400" rows="2"></textarea></label>
              <label class="field">Next step (optional)<textarea name="next_step" maxlength="240" rows="2"></textarea></label>
            </div><button>Share with project</button></form>
          </details>
          <form id="project-handoffs" class="group"><button class="secondary">Refresh project brief</button></form>
        </section>
      </section>

      <section class="card" id="decisions" aria-labelledby="decisions-title" data-project hidden>
        <h2 id="decisions-title">Decisions</h2>
        <details open><summary>Propose a decision</summary>
          <form id="propose"><div class="fields">
            <label class="field">Topic<input name="topic" required maxlength="80"></label>
            <label class="field">Visibility<select name="visibility"><option value="team">Project members</option><option value="private">Private</option></select></label>
            <label class="field">Rule<textarea name="rule" required maxlength="500" rows="3"></textarea></label>
            <label class="field">Documented rationale (optional)<textarea name="rationale" maxlength="600" rows="3"></textarea></label>
            <label class="field">Repository paths, one per line<textarea name="paths" rows="2" aria-describedby="scope-help" placeholder="checkout:refunds"></textarea></label>
            <label class="field">Task phrases, one per line<textarea name="terms" rows="2" aria-describedby="scope-help"></textarea></label>
            <label class="field">GitHub PR, Linear issue or Notion page links<textarea name="links" required rows="2" aria-describedby="source-help"></textarea></label>
            <label class="field">Expires after hours (optional)<input name="expires_hours" type="number" min="1" max="8760"></label>
          </div><p id="scope-help" class="muted group">Enter at least one repository path or task phrase.</p><p id="source-help" class="muted">Enter one to four links, one per line. A link adds a reference that must be verified for each recipient.</p><button>Submit proposal</button></form>
        </details>
        <details><summary>Review proposals and manage versions</summary>
          <form id="proposals"><button class="secondary">Load review queue</button></form>
          <div id="proposal-results"></div>
          <form id="version-action" class="group"><div class="fields">
            <label class="field">Decision ID<input name="decision" required maxlength="36" autocomplete="off" spellcheck="false"></label>
            <label class="field">Version<input name="version" required type="number" min="1" value="1"></label>
            <label class="field">Lifecycle action<select name="action"><option value="approve">Approve</option><option value="retire">Retire</option><option value="revoke">Revoke</option></select></label>
            <label class="field">Replaced decision ID (approval only)<input name="replaces" maxlength="36" autocomplete="off" spellcheck="false"></label>
            <label class="field">Replaced version (approval only)<input name="replaces_version" type="number" min="1"></label>
          </div><button>Apply lifecycle action</button></form>
        </details>
        <details><summary>Change private reviewer access</summary>
          <form id="reviewer"><div class="fields">
            <label class="field">Private decision ID<input name="decision" required maxlength="36" autocomplete="off" spellcheck="false"></label>
            <label class="field">Reviewer user ID<input name="user" required maxlength="36" autocomplete="off" spellcheck="false"></label>
            <label class="field">Reviewer access<select name="active"><option value="true">Grant</option><option value="false">Remove</option></select></label>
          </div><button>Apply reviewer access</button></form>
        </details>
      </section>

      <section class="card" id="assistants" aria-labelledby="assistants-title" data-project hidden>
        <h2 id="assistants-title">Connect an assistant</h2>
        <details id="team-helper" class="group" data-revision="<!--TEAM_HELPER_REVISION-->" hidden>
          <summary>Install the Ninai Team helper</summary>
          <p>Run this once per machine for this release. It needs Git and <a href="https://docs.astral.sh/uv/getting-started/installation/" rel="noreferrer">uv</a>. It installs in your home directory.</p>
          <pre id="team-helper-command" class="wrap"></pre>
          <button type="button" id="copy-team-helper" class="secondary">Copy install command</button>
        </details>
        <form id="guided-assistant" class="row group">
          <label class="field">Coding assistant<select name="client"><option value="claude-code">Claude Code</option><option value="codex">Codex</option></select></label>
          <label class="choice"><input name="publish" type="checkbox"> Allow publishing handoffs</label>
          <button>Start connection</button>
        </form>
        <section id="assistant-setup" class="group" aria-labelledby="assistant-setup-title" hidden>
          <h3 id="assistant-setup-title">Finish in your coding assistant</h3>
          <p>With the Ninai Team helper installed, open Bash or Zsh in your checkout. Copy the setup, then enter your assistant token when prompted.</p>
          <pre id="assistant-command" class="wrap"></pre>
          <div class="controls group"><button id="copy-assistant-command" type="button" class="secondary">Copy setup</button></div>
          <details><summary>Load the brief automatically when a session starts</summary>
            <p>Merge this hook into your assistant’s project settings.</p>
            <p id="assistant-hook-location" class="muted"></p>
            <pre class="wrap">{"hooks":{"SessionStart":[{"matcher":"","hooks":[{"type":"command","command":"ninai-team-session-start"}]}]}}</pre>
          </details>
          <form id="check-assistant" class="group"><button class="secondary">Check connection</button></form>
        </section>
        <details><summary>Advanced assistant permissions</summary>
        <form id="binding"><div class="fields">
          <label class="field">Assistant client<select name="client"><option value="claude-code">Claude Code</option><option value="codex">Codex</option></select></label>
          <label class="field">Binding identity<select name="kind" id="binding-kind"><option value="human">My user</option><option value="service">Sponsored service</option></select></label>
        </div><fieldset><legend>Allowed actions</legend><div class="choices">
          <label class="choice"><input name="actions" type="checkbox" value="read"> Read context</label>
          <label class="choice"><input name="actions" type="checkbox" value="propose"> Propose decisions</label>
          <label class="choice"><input name="actions" type="checkbox" value="view-history"> View history</label>
          <label class="choice"><input name="actions" type="checkbox" value="read-handoffs"> Read team handoffs</label>
          <label class="choice"><input name="actions" type="checkbox" value="publish-handoff"> Publish team handoffs</label>
        </div></fieldset><button>Issue credential</button></form>
        </details>
        <details id="binding-controls"><summary>Rotate or revoke a binding</summary>
          <form id="manage-binding"><div class="fields">
            <label class="field">Binding ID<input name="binding" required maxlength="36" autocomplete="off" spellcheck="false"></label>
            <label class="field">Action<select name="action"><option value="rotate-binding">Rotate credential</option><option value="revoke-binding">Revoke binding</option></select></label>
          </div><button>Apply credential action</button></form>
        </details>
      </section>

      <section class="card" id="context" aria-labelledby="context-title" data-project hidden>
        <h2 id="context-title">Task context</h2>
        <form id="context-form"><div class="fields">
          <label class="field">Describe a coding task<textarea name="task" required rows="2" maxlength="1200"></textarea></label>
          <label class="field">Repository paths, one per line<textarea name="paths" rows="2" placeholder="checkout:refunds/write.py"></textarea></label>
          <label class="field">Request<select name="history_only"><option value="false">Current guidance</option><option value="true">Decision history</option></select></label>
          <label class="field">Maximum tokens (optional)<input name="max_tokens" type="number" min="1" max="4096"></label>
        </div><button>Check task context</button></form>
        <div id="context-results" class="group"></div>
      </section>

      <section class="card" id="audit" aria-labelledby="audit-title" data-admin hidden>
        <h2 id="audit-title">Workspace audit</h2>
        <form id="audit-form"><button class="secondary">Load visible events</button></form>
        <div id="audit-results"></div>
        <form id="project-export" data-project hidden><button class="secondary">Download authorized project export</button></form>
        <form id="project-audit-export" data-project hidden><button class="secondary">Download authorized project audit</button></form>
      </section>

      <section id="credential" class="card accent credential" aria-labelledby="credential-title" hidden>
        <h2 id="credential-title" tabindex="-1">One-time credential</h2>
        <p id="credential-details"></p>
        <label class="field">Token<input id="credential-value" readonly autocomplete="off" spellcheck="false"></label>
        <div class="controls group"><button type="button" id="copy-credential">Copy token</button><button type="button" id="hide-credential" class="secondary">Dismiss token</button></div>
      </section>
    </div>
  </div>
</main>
<script>
'use strict';
const select = (id) => document.getElementById(id);
const state = {workspace: '', project: '', overview: null, generation: 0, identity: '', invite: null,
  setupFinished: false, binding: ''};
const uuid = /^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/i;
const outcomeNotes = {
  packet: 'Current guidance', history: 'Decision history', empty: 'No relevant, verified guidance to show.',
  conflict: 'Resolve the conflicting guidance before editing.', abstain: 'Current guidance could not be verified.',
  denied: 'Team access is unavailable.'
};

function notice(message, error = false) {
  select('error').textContent = error ? message : '';
  select('status').textContent = error ? '' : message;
}

async function api(path, body) {
  const response = await fetch(path, {
    method: body === undefined ? 'GET' : 'POST', credentials: 'same-origin', cache: 'no-store',
    headers: body === undefined ? {} : {'Content-Type': 'application/json'},
    body: body === undefined ? undefined : JSON.stringify(body), signal: AbortSignal.timeout(15000)
  });
  if (!response.ok) {
    const messages = {
      400: 'Check the fields and try again.', 401: 'Your session has expired. Sign in from the control center.',
      403: 'Team access is unavailable.', 404: 'Team access is unavailable.',
      409: 'The state changed. Refresh the workspace and try again.', 429: 'Too many requests. Try again shortly.'
    };
    throw Error(messages[response.status] || 'Ninai could not complete the request. Try again.');
  }
  if (response.status === 204) {
    return {
      outcome: response.headers.get('X-Ninai-Outcome') || 'empty',
      signals: (response.headers.get('X-Ninai-Signals') || '').split(',').map(x => x.trim()).filter(Boolean)
    };
  }
  return response.json();
}

function append(parent, tag, value, style) {
  const node = document.createElement(tag);
  if (style) node.className = style;
  if (value !== undefined && value !== null) node.textContent = String(value);
  parent.append(node);
  return node;
}

function setOptions(target, options, placeholder) {
  const selected = target.value;
  target.replaceChildren(new Option(placeholder, ''));
  for (const item of options) target.add(new Option(item.label, item.value));
  if (options.some(item => item.value === selected)) target.value = selected;
}

function members(overview) {
  return (overview?.members || []).map(row => ({value: row.user_id, label: row.display_name || row.user_id}));
}

function projects(overview, accessOnly = false) {
  return (overview?.projects || []).filter(row => !accessOnly || row.access)
    .map(row => ({value: row.id, label: row.name}));
}

function updateGroupSubject() {
  const options = select('group-kind').value === 'member' ? members(state.overview) : projects(state.overview);
  setOptions(select('group-subject'), options, 'Choose a member or project');
}

function clearCredential(restoreFocus = false) {
  const origin = select('credential').origin;
  select('credential-value').value = '';
  select('credential-details').textContent = '';
  select('credential').hidden = true;
  select('credential').origin = null;
  if (restoreFocus && origin?.isConnected) origin.focus();
}

function showCredential(title, value, details, origin) {
  if (typeof value !== 'string' || !value) return;
  select('credential-title').textContent = title;
  select('credential-details').textContent = details;
  select('credential-value').value = value;
  select('credential').hidden = false;
  select('credential').origin = origin;
  select('credential-title').focus();
}

function selectProject(project) {
  if (state.project !== project) {
    state.generation += 1;
    clearCredential();
    for (const id of ['proposal-results', 'context-results', 'handoff-results', 'brief-decisions']) select(id).replaceChildren();
    for (const id of ['propose', 'version-action', 'reviewer', 'binding', 'manage-binding', 'context-form', 'browser-handoff']) select(id).reset();
    state.binding = '';
    select('assistant-setup').hidden = true;
    clearInviteLink();
  }
  state.project = project;
  const selection = state.overview?.projects?.find(row => row.id === project && row.access);
  for (const node of document.querySelectorAll('[data-project]')) node.hidden = !selection;
  const elevated = selection?.maintainer || ['owner', 'admin'].includes(state.overview?.role);
  select('project-export').hidden = !selection || !['owner', 'admin'].includes(state.overview?.role);
  select('project-audit-export').hidden = select('project-export').hidden;
  select('project-role').textContent = selection ? (elevated ? 'Decision review available.' : 'Project member access.') : 'Choose a project to continue.';
  select('project-repo').textContent = selection?.repository ? `Repository ${selection.repository} · Project ID ${project}` : '';
  select('project-brief').hidden = !selection;
  renderSetup();
}

function displayOverview(overview) {
  state.overview = overview;
  const role = overview?.role;
  const administrator = ['owner', 'admin'].includes(role);
  for (const node of document.querySelectorAll('[data-admin]')) node.hidden = !administrator;
  for (const node of document.querySelectorAll('[data-owner-role]')) node.querySelector('[value="admin"]').disabled = role !== 'owner';
  select('binding-kind').querySelector('[value="service"]').disabled = !administrator;
  select('workspace-selection').textContent = role ? `Workspace role: ${role}` : '';
  select('workspace-selection').hidden = !role;
  select('project-panel').hidden = !role;
  for (const node of document.querySelectorAll('[data-members]')) setOptions(node, members(overview), 'Choose a member');
  for (const node of document.querySelectorAll('[data-all-projects]')) setOptions(node, projects(overview), 'Choose a project');
  const unconnected = (overview?.projects || []).filter(row => !row.repository)
    .map(row => ({value: row.id, label: row.name}));
  setOptions(document.querySelector('[data-projects-without-repo]'), unconnected, 'Choose a project');
  for (const node of document.querySelectorAll('[data-groups]')) {
    setOptions(node, (overview?.groups || []).map(row => ({value: row.id, label: row.name})), 'Choose a group');
  }
  const list = select('members');
  list.replaceChildren();
  if (administrator) {
    const roster = append(list, 'ul', null, 'list');
    for (const row of overview.members || []) append(roster, 'li', `${row.display_name || row.user_id} · ${row.role}`, 'item');
  }
  updateGroupSubject();
  const accessible = projects(overview, true);
  const picker = select('active-project');
  setOptions(picker, accessible, accessible.length ? 'Choose a project' : 'No projects are assigned');
  if (accessible.length === 1 && !picker.value) picker.value = accessible[0].value;
  selectProject(picker.value);
}

function workspaceId() {
  const value = select('open-workspace').elements.workspace.value.trim().toLowerCase();
  if (!uuid.test(value)) throw Error('Enter the workspace ID first.');
  return value;
}

async function openWorkspace(workspace) {
  const previous = state.workspace === workspace ? select('active-project').value : '';
  state.workspace = workspace;
  select('open-workspace').elements.workspace.value = workspace;
  clearCredential();
  select('audit-results').replaceChildren();
  displayOverview(null);
  const request = ++state.generation;
  const result = await api(`/api/team/${workspace}/overview`);
  if (state.generation !== request) return;
  displayOverview(result);
  if (result.projects.some(project => project.id === previous && project.access)) {
    select('active-project').value = previous;
    selectProject(previous);
  }
  if (state.identity) writeStored('ninai-team-last:' + state.identity, workspace, true);
  notice('Workspace opened.');
  if (state.project) loadBrief();
}

function pathFor(workspace, project, action) {
  return `/api/team/${workspace}${project ? `/projects/${project}` : ''}/${action}`;
}

function lines(value) { return value.split('\n').map(line => line.trim()).filter(Boolean); }

function run(button, work) {
  return async () => {
    if (!button || button.disabled) return;
    button.disabled = true;
    button.closest('form')?.setAttribute('aria-busy', 'true');
    notice('');
    try { await work(); }
    catch (error) { notice(error.name === 'TimeoutError' ? 'The request timed out. Try again.' : (error.message || 'Ninai could not complete the request.'), true); }
    finally { button.disabled = false; button.closest('form')?.removeAttribute('aria-busy'); }
  };
}

function bind(id, handle) {
  const form = select(id);
  form.addEventListener('submit', event => {
    event.preventDefault();
    const button = event.submitter || form.querySelector('button');
    const data = new FormData(form);
    run(button, () => handle(data, button, form))();
  });
}

function workspaceAction(id, action, transform, complete) {
  bind(id, async (data, button, form) => {
    const workspace = workspaceId();
    if (!['enable', 'accept'].includes(action) && (state.workspace !== workspace || !state.overview)) {
      throw Error('Open the workspace first.');
    }
    const generation = state.generation;
    const result = await api(pathFor(workspace, '', action), transform(Object.fromEntries(data), form));
    if (generation !== state.generation || workspaceId() !== workspace) return;
    await complete(result, workspace, button);
  });
}

function projectAction(id, action, transform, complete) {
  bind(id, async (data, button) => {
    const {workspace, project, generation} = state;
    if (!project || workspaceId() !== workspace) throw Error('Open the workspace and choose a project first.');
    const values = Object.fromEntries(data);
    const target = typeof action === 'function' ? action(values) : action;
    const result = await api(pathFor(workspace, project, target), transform(values, data));
    if (generation === state.generation) await complete(result, button);
  });
}

function unchanged(values) { return values; }
function empty() { return {}; }
function updated(result, workspace) { return openWorkspace(workspace); }
function postNotice(text) { return () => notice(text); }

function sourceLinks(parent, sources) {
  const links = [];
  for (const source of sources || []) {
    try {
      const url = new URL(source.uri || source.url);
      if (url.protocol === 'https:' && !url.username && !url.password) links.push(url);
    } catch { /* A malformed reference is omitted. */ }
  }
  if (!links.length) return;
  const list = append(parent, 'ul', null, 'list');
  for (const link of links) {
    const entry = append(list, 'li');
    const anchor = append(entry, 'a', link.href, 'wrap');
    anchor.href = link.href;
    anchor.rel = 'noreferrer';
  }
}

function showProposals(result) {
  const target = select('proposal-results');
  target.replaceChildren();
  if (!result.items?.length) { append(target, 'p', 'No reviewable proposals.', 'muted group'); return; }
  const list = append(target, 'ul', null, 'list');
  for (const row of result.items) {
    const item = append(list, 'li', null, 'item');
    append(item, 'h3', row.topic);
    append(item, 'p', row.rule);
    append(item, 'p', row.rationale || 'Rationale undocumented.', 'muted');
    append(item, 'p', `${row.decision_id} · version ${row.version}`, 'muted');
    sourceLinks(item, row.sources);
    const button = append(item, 'button', 'Select version', 'secondary group');
    button.type = 'button';
    button.addEventListener('click', () => {
      const form = select('version-action');
      form.elements.decision.value = row.decision_id;
      form.elements.version.value = row.version;
      form.elements.action.focus();
    });
  }
}

function showContext(result) {
  const target = select('context-results');
  target.replaceChildren();
  append(target, 'h3', outcomeNotes[result.outcome] || 'Task context');
  const signals = result.signals || [];
  if (signals.includes('budget-exhausted')) append(target, 'p', 'Increase the token limit to see more context.', 'muted');
  if (signals.includes('evidence-unverified') && result.outcome !== 'abstain') append(target, 'p', 'Some guidance could not be verified.', 'muted');
  const versions = [...(result.current || []), ...(result.history || []), ...(result.conflicting || [])];
  if (versions.length) {
    const list = append(target, 'ul', null, 'list');
    for (const row of versions) {
      const item = append(list, 'li', null, 'item');
      append(item, 'p', row.rule);
      append(item, 'p', row.rationale_status === 'documented' ? row.rationale : 'Rationale undocumented.', 'muted');
      append(item, 'code', row.version_id);
      sourceLinks(item, row.sources);
    }
  }
  if (result.lineage?.length) {
    const lineage = append(target, 'ul', null, 'list');
    for (const edge of result.lineage) append(lineage, 'li', `${edge.current} replaces ${edge.replaces}`, 'item');
  }
  notice('Task context checked.');
}

function showAudit(result) {
  const target = select('audit-results');
  target.replaceChildren();
  if (!result.items?.length) { append(target, 'p', 'No visible workspace events.', 'muted group'); return; }
  const list = append(target, 'ul', null, 'list');
  for (const row of result.items) {
    const item = append(list, 'li', null, 'item');
    append(item, 'p', `${row.action} · ${row.outcome}`);
    append(item, 'p', `${row.recorded_at} · actor ${row.actor_user_id || 'unavailable'}`, 'muted');
    append(item, 'code', row.request_id);
  }
}

function downloadExport(result, filename, message) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(result, null, 2)], {type: 'application/json'}));
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  notice(message);
}

bind('open-workspace', () => openWorkspace(workspaceId()));
bind('create-workspace', async (data) => {
  const result = await api('/api/control/workspaces', {name: data.get('name')});
  select('open-workspace').elements.workspace.value = result.id;
  notice('Workspace ID ready. Enable the preview if you own this workspace.');
});
const findButton = select('find-workspace');
findButton.addEventListener('click', run(findButton, async () => {
  const result = await api('/api/control/overview');
  select('open-workspace').elements.workspace.value = result.workspace.id;
  notice('Workspace ID ready. Open the team workspace or enable the preview if you own it.');
}));
select('active-project').addEventListener('change', event => { selectProject(event.target.value); loadBrief(); });
select('group-kind').addEventListener('change', updateGroupSubject);
select('hide-credential').addEventListener('click', () => { clearCredential(true); notice('Token dismissed.'); });
select('copy-credential').addEventListener('click', run(select('copy-credential'), async () => {
  await navigator.clipboard.writeText(select('credential-value').value);
  notice('Token copied.');
}));
window.addEventListener('pagehide', () => { clearCredential(); clearInviteLink(); });

workspaceAction('enable', 'enable', empty, updated);
workspaceAction('accept', 'accept', (values, form) => { form.reset(); return values; }, updated);
workspaceAction('invite', 'invite', unchanged, (result, workspace, button) => {
  showCredential('Invitation token', result.invitation_token, `Share this one-time token and workspace ID ${workspace} with the intended recipient.`, button);
});
bind('member', async (data) => {
  const values = Object.fromEntries(data);
  const workspace = workspaceId();
  if (workspace !== state.workspace || !state.overview) throw Error('Open the workspace first.');
  if (values.role === 'remove' && !confirm('Offboard this member and revoke their workspace access?')) return;
  await api(pathFor(workspace, '', 'member'), values);
  if (workspace === state.workspace && workspace === workspaceId()) await openWorkspace(workspace);
});
workspaceAction('project-member', 'project-member', unchanged, updated);
workspaceAction('group', 'group', unchanged, updated);
workspaceAction('project', 'project', values => ({name: values.name, repository: values.repository.trim() || null}), updated);
workspaceAction('project-repository', 'connect-repository', unchanged, updated);
bind('archive-project', async (data) => {
  const workspace = workspaceId();
  if (state.workspace !== workspace || !state.overview) throw Error('Open the workspace first.');
  if (!confirm('Archive this project and revoke its assistant credentials?')) return;
  await api(pathFor(workspace, '', 'archive-project'), {project: data.get('project')});
  if (workspace === state.workspace && workspace === workspaceId()) await openWorkspace(workspace);
});
workspaceAction('group-edge', 'group-edge', values => ({...values, active: values.active === 'true'}), updated);
workspaceAction('audit-form', 'audit', empty, showAudit);

projectAction('binding', 'binding', (values, data) => ({client: values.client, kind: values.kind, actions: data.getAll('actions')}), (result, button) => {
  select('manage-binding').elements.binding.value = result.binding_id;
  showCredential('Assistant token', result.token, `Binding ${result.binding_id}. This token is shown once and expires ${result.expires_at}.`, button);
});
projectAction('manage-binding', values => values.action, values => ({binding: values.binding}), (result, button) => {
  clearCredential();
  if (result.token) {
    showCredential('Replacement assistant token', result.token, `Store the new token before dismissing this message. Expires ${result.expires_at}.`, button);
  } else notice('Binding access updated.');
});
projectAction('propose', 'propose', values => {
  const {topic, rule, rationale, visibility, paths, terms, links, expires_hours} = values;
  return {topic, rule, rationale: rationale.trim() || null, visibility, paths: lines(paths), terms: lines(terms),
          links: lines(links), expires_hours: expires_hours ? Number(expires_hours) : null};
}, (result) => {
  select('propose').reset();
  notice(`Proposal saved as version ${result.version}.`);
});
projectAction('proposals', 'proposals', empty, showProposals);
projectAction('version-action', values => values.action, values => {
  const body = {decision: values.decision, version: Number(values.version)};
  if (values.action === 'approve' && values.replaces) {
    body.replaces = values.replaces;
    body.replaces_version = Number(values.replaces_version);
  }
  return body;
}, () => { select('proposal-results').replaceChildren(); notice('Lifecycle action processed.'); });
projectAction('reviewer', 'reviewer', values => ({...values, active: values.active === 'true'}), postNotice('Reviewer access updated.'));
projectAction('context-form', 'context', values => {
  const body = {task: values.task, paths: lines(values.paths), history_only: values.history_only === 'true'};
  if (values.max_tokens) body.max_tokens = Number(values.max_tokens);
  return body;
}, showContext);
projectAction('project-export', 'export', empty, result => {
  downloadExport(result, 'ninai-project-export.json', 'Project export prepared.');
});
projectAction('project-audit-export', 'audit-export', empty, result => {
  downloadExport(result, 'ninai-project-audit.json', 'Project audit prepared.');
});

const pendingInviteKey = 'ninai-team-pending-invite';

function readStored(key, persistent = false) {
  try { return (persistent ? localStorage : sessionStorage).getItem(key); } catch { return null; }
}

function writeStored(key, value, persistent = false) {
  try {
    const storage = persistent ? localStorage : sessionStorage;
    if (value === null) storage.removeItem(key);
    else storage.setItem(key, value);
  } catch { /* The open page can still operate with tab storage disabled. */ }
}

function currentInvite() {
  const fragment = new URLSearchParams(location.hash.slice(1));
  const shared = fragment.get('invite');
  const match = /^([0-9a-f-]{36})\.([A-Za-z0-9_-]{43})$/i.exec(shared || '');
  if (match && uuid.test(match[1])) return {workspace: match[1], token: match[2]};
  if (fragment.has('invite')) return null;
  try {
    const saved = JSON.parse(readStored(pendingInviteKey));
    if (saved && saved.expires >= Date.now() && uuid.test(saved.workspace)
        && /^[A-Za-z0-9_-]{43}$/.test(saved.token)) return saved;
  } catch { /* Ignore malformed stored invitations. */ }
  writeStored(pendingInviteKey, null);
  return null;
}

function clearInviteLink() {
  select('setup-invite-link').value = '';
  select('setup-invite-result').hidden = true;
}

function renderSetup() {
  const setup = select('team-onboarding');
  const role = state.overview?.role;
  const visible = Boolean(state.identity && !state.invite && !state.setupFinished
    && (role ? ['owner', 'admin'].includes(role) : state.canCreateTeam));
  select('pilot-access').hidden = !(state.identity && !state.invite && !role && !state.canCreateTeam);
  setup.hidden = !visible;
  if (!visible) return;
  const step = !role ? 'team' : state.project ? 'invite' : 'project';
  for (const name of ['team', 'project', 'invite']) {
    const item = select('setup-step-' + name);
    if (name === step) item.setAttribute('aria-current', 'step');
    else item.removeAttribute('aria-current');
    select('setup-' + name).hidden = name !== step;
  }
}

function selectedProject(project) {
  const picker = select('active-project');
  if (project !== state.project && [...picker.options].some(option => option.value === project)) {
    picker.value = project;
    selectProject(project);
    loadBrief();
  }
}

function showHandoffs(result) {
  const target = select('handoff-results');
  target.replaceChildren();
  if (!result.items.length) {
    append(target, 'p', 'No recent handoffs.', 'muted');
    return;
  }
  const list = append(target, 'ul', null, 'list');
  for (const row of result.items) {
    const item = append(list, 'li', null, 'item');
    append(item, 'h3', row.topic);
    const status = {working: 'In progress', blocked: 'Blocked', done: 'Done'}[row.status];
    append(item, 'p', `${status} · ${row.author}`, 'muted');
    append(item, 'p', row.summary);
    if (row.next_step) append(item, 'p', row.next_step);
  }
}

function showBriefDecisions(result) {
  const target = select('brief-decisions');
  target.replaceChildren();
  if (!result.current?.length) {
    append(target, 'p', outcomeNotes[result.outcome] || 'No approved decisions yet.', 'muted');
    return;
  }
  const list = append(target, 'ul', null, 'list');
  for (const row of result.current) {
    const item = append(list, 'li', null, 'item');
    if (row.topic) append(item, 'h3', row.topic);
    append(item, 'p', row.rule);
    if (row.rationale) append(item, 'p', row.rationale, 'muted');
    sourceLinks(item, row.sources);
  }
}

async function loadBrief() {
  const {workspace, project, generation} = state;
  if (!workspace || !project) return;
  const requests = [
    ['handoff-results', showHandoffs, api(pathFor(workspace, project, 'handoffs'), {})],
    ['brief-decisions', showBriefDecisions, api(pathFor(workspace, project, 'context'), {
      task: 'Project orientation', project_overview: true, max_tokens: 2048
    })]
  ];
  await Promise.all(requests.map(async ([target, render, request]) => {
    try {
      const result = await request;
      if (state.generation === generation) render(result);
    } catch {
      if (state.generation === generation) {
        select(target).replaceChildren();
        append(select(target), 'p', 'This part of the brief is unavailable. Try refreshing.', 'muted');
      }
    }
  }));
}

function openBrief() {
  state.setupFinished = true;
  clearInviteLink();
  renderSetup();
  select('brief-title').focus();
}

bind('setup-team-form', async data => {
  const result = await api('/api/control/workspaces', {name: data.get('name')});
  await api(pathFor(result.id, '', 'enable'), {});
  await openWorkspace(result.id);
});
const existingTeam = select('setup-existing');
existingTeam.addEventListener('click', run(existingTeam, async () => {
  const result = await api('/api/control/overview');
  await api(pathFor(result.workspace.id, '', 'enable'), {});
  await openWorkspace(result.workspace.id);
}));
bind('setup-project-form', async data => {
  const workspace = state.workspace;
  const result = await api(pathFor(workspace, '', 'project'), {name: data.get('name'), assign_creator: true});
  if (state.workspace !== workspace) return;
  await openWorkspace(workspace);
  selectedProject(result.project_id);
});
bind('setup-invite-form', async data => {
  const {workspace, project, generation} = state;
  if (!workspace || !project) throw Error('Choose a project first.');
  const result = await api(pathFor(workspace, '', 'invite'), {email: data.get('email'), project});
  if (state.generation !== generation) return;
  const link = new URL('/control/team', location.origin);
  link.hash = 'invite=' + workspace + '.' + result.invitation_token;
  select('setup-invite-link').value = link.href;
  select('setup-invite-result').hidden = false;
  select('setup-invite-link').focus();
});
const copyInvite = select('setup-copy-invite');
copyInvite.addEventListener('click', run(copyInvite, async () => {
  await navigator.clipboard.writeText(select('setup-invite-link').value);
  notice('Invite link copied.');
}));
select('setup-finish').addEventListener('click', openBrief);
select('team-signin').addEventListener('click', () => {
  if (state.invite) writeStored(pendingInviteKey, JSON.stringify({...state.invite, expires: Date.now() + 600000}));
});
bind('join-team', async () => {
  const invite = state.invite;
  if (!invite) throw Error('Open your invitation link again.');
  const joined = await api(pathFor(invite.workspace, '', 'accept'), {token: invite.token, verify_email: true});
  state.invite = null;
  writeStored(pendingInviteKey, null);
  select('team-join').hidden = true;
  select('dashboard').hidden = false;
  await openWorkspace(invite.workspace);
  if (joined.project_id) selectedProject(joined.project_id);
  openBrief();
  notice('You joined the team.');
});
bind('project-handoffs', loadBrief);
bind('browser-handoff', async (data, button, form) => {
  const {workspace, project, generation} = state;
  if (!workspace || !project) throw Error('Choose a project first.');
  const draft = Object.fromEntries(data);
  // A repeated submission after a lost response reuses the same request key.
  const signature = JSON.stringify(draft);
  if (form.signature !== signature || !form.requestKey) {
    form.signature = signature;
    form.requestKey = crypto.randomUUID();
  }
  await api(pathFor(workspace, project, 'publish-handoff'), {
    ...draft, next_step: draft.next_step.trim() || null, request_key: form.requestKey
  });
  if (generation === state.generation) {
    form.reset();
    form.requestKey = null;
    notice('Handoff shared with your project.');
    await loadBrief();
  }
});
const teamHelper = select('team-helper');
const teamHelperRevision = teamHelper.dataset.revision;
const managedHelper = /^[0-9a-f]{40}$/.test(teamHelperRevision);
const teamHelperDirectory = '"$HOME/.local/share/ninai/team/' + teamHelperRevision + '"';
if (managedHelper) {
  const install = [
    'ninai_team_helper=' + teamHelperDirectory,
    'mkdir -p "$ninai_team_helper" &&',
    'git -C "$ninai_team_helper" init -q &&',
    'git -C "$ninai_team_helper" fetch -q --no-tags --depth=1 https://github.com/HariDarshan2321/ninai.git ' + teamHelperRevision + ' &&',
    'git -C "$ninai_team_helper" checkout -q --detach ' + teamHelperRevision + ' &&',
    'uv sync --locked --no-dev --project "$ninai_team_helper/cloud"'
  ];
  select('team-helper-command').textContent = install.join('\n');
  const copyInstall = select('copy-team-helper');
  copyInstall.addEventListener('click', run(copyInstall, async () => {
    await navigator.clipboard.writeText(select('team-helper-command').textContent);
    notice('Team helper install command copied.');
  }));
  teamHelper.hidden = false;
}
projectAction('guided-assistant', 'binding', (values, data) => ({
  client: values.client,
  actions: ['read', 'read-handoffs', ...(data.has('publish') ? ['publish-handoff'] : [])]
}), (result, button) => {
  state.binding = result.binding_id;
  select('manage-binding').elements.binding.value = result.binding_id;
  const client = select('guided-assistant').elements.client.value;
  select('assistant-hook-location').textContent = client === 'claude-code'
    ? '.claude/settings.local.json' : '.codex/hooks.json';
  const launch = client === 'claude-code'
    ? "claude --mcp-config '" + JSON.stringify({mcpServers:{'ninai-team':{command:'ninai-team-mcp'}}}) + "'"
    : 'codex -c \'mcp_servers.ninai_team.command="ninai-team-mcp"\' -c \'mcp_servers.ninai_team.env_vars=["NINAI_TEAM_ORIGIN","NINAI_TEAM_WORKSPACE","NINAI_TEAM_PROJECT","NINAI_TEAM_CHECKOUT","NINAI_TEAM_TOKEN"]\'';
  const lines = [
    '(',
    ...(managedHelper ? [
      'export PATH=' + teamHelperDirectory + '/cloud/.venv/bin:"$PATH"',
      'command -v ninai-team-mcp >/dev/null || { printf "%s\\n" "Install the Ninai Team helper first."; exit 1; }',
    ] : []),
    `export NINAI_TEAM_ORIGIN='${location.origin}'`,
    `export NINAI_TEAM_WORKSPACE='${state.workspace}'`,
    `export NINAI_TEAM_PROJECT='${state.project}'`,
    'export NINAI_TEAM_CHECKOUT="$(pwd -P)"',

    "printf 'Paste Ninai token and press Enter: '; read -r -s NINAI_TEAM_TOKEN && export NINAI_TEAM_TOKEN && " + launch,
    ')'
  ];
  select('assistant-command').textContent = lines.join('\n');
  select('assistant-setup').hidden = false;
  showCredential('Assistant token', result.token, 'Enter this token at the terminal prompt. Ninai shows it only once.', button);
});
const copyAssistant = select('copy-assistant-command');
copyAssistant.addEventListener('click', run(copyAssistant, async () => {
  await navigator.clipboard.writeText(select('assistant-command').textContent);
  notice('Assistant setup copied.');
}));
projectAction('check-assistant', 'check-binding', () => ({binding: state.binding}), result => {
  notice(result.connected ? 'Assistant connected to this project.' : 'Waiting for the first read from your assistant.');
});

function loadInvitation() {
  state.invite = currentInvite();
  if (location.hash.startsWith('#invite=')) history.replaceState(null, '', location.pathname);
  if (state.identity && state.invite) {
    state.generation += 1;
    clearCredential();
    clearInviteLink();
    select('dashboard').hidden = true;
    select('team-join').hidden = false;
    renderSetup();
  }
}
loadInvitation();
window.addEventListener('hashchange', () => {
  if (location.hash.startsWith('#invite=')) loadInvitation();
});
api('/api/team/identity').then(async identity => {
  state.identity = identity.user_id;
  state.canCreateTeam = identity.can_create_team === true;
  select('create-workspace').hidden = !state.canCreateTeam;
  select('enable').hidden = !state.canCreateTeam;
  select('identity-issuer').textContent = identity.issuer;
  select('identity-subject').textContent = identity.subject;
  select('identity-user').textContent = identity.user_id;
  select('invite').elements.issuer.value = identity.issuer || '';
  writeStored(pendingInviteKey, null);
  if (state.invite) {
    select('team-join').hidden = false;
    return;
  }
  select('dashboard').hidden = false;
  const previous = readStored('ninai-team-last:' + state.identity, true);
  if (previous && uuid.test(previous)) {
    state.setupFinished = true;
    try {
      await openWorkspace(previous);
      return;
    } catch {
      writeStored('ninai-team-last:' + state.identity, null, true);
      state.setupFinished = false;
    }
  }
  renderSetup();
}).catch(() => { select('signin').hidden = false; });
</script>
</body>
</html>"""
