/* ==========================================================================
   Ninai desktop — application logic
   Vanilla JS, no build step. Renders five screens over the Python bridge:
   Today, Memories, Sources, Sessions, Permissions, Activity.
   ========================================================================== */
(function () {
  "use strict";

  var B = window.NinaiBridge;

  /* ---- tiny DOM helpers ------------------------------------------------- */

  function $(sel, root) { return (root || document).querySelector(sel); }
  function $$(sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); }

  // Create an element. attrs: {class, text, title, onclick, dataId, ...}
  function h(tag, attrs) {
    var node = document.createElement(tag);
    if (attrs) {
      Object.keys(attrs).forEach(function (k) {
        var v = attrs[k];
        if (v == null || v === false) return;
        if (k === "class") node.className = v;
        else if (k === "text") node.textContent = v;
        else if (k === "html") node.innerHTML = v;
        else if (k.slice(0, 2) === "on" && typeof v === "function") {
          node.addEventListener(k.slice(2), v);
        } else if (k === "dataId") node.setAttribute("data-id", v);
        else node.setAttribute(k, v === true ? "" : v);
      });
    }
    for (var i = 2; i < arguments.length; i++) {
      appendChild(node, arguments[i]);
    }
    return node;
  }

  function appendChild(node, kid) {
    if (kid == null || kid === false) return;
    if (Array.isArray(kid)) {
      kid.forEach(function (k) { appendChild(node, k); });
    } else if (kid.nodeType) {
      node.appendChild(kid);
    } else {
      node.appendChild(document.createTextNode(String(kid)));
    }
  }

  function clear(node) { while (node.firstChild) node.removeChild(node.firstChild); }

  /* ---- static reference data ------------------------------------------- */

  var SCOPE_DESC = {
    public: "Information you choose to share. Assistants still need permission.",
    work: "General working context — your role, team, and how you operate.",
    project: "Older or unassigned memories share this permission. Named projects use separate access controls.",
    preference: "How you like things done — tools, defaults, working style.",
    personal: "Personal life details kept outside of work context.",
    finance: "Money matters — budgets, costs, and accounts.",
    health: "Health and wellbeing information."
  };

  var SCOPE_LABEL = {
    public: "Public information",
    work: "General work memories",
    project: "Unassigned project memories",
    preference: "Working preferences",
    personal: "Personal memories",
    finance: "Financial memories",
    health: "Health memories"
  };

  function scopeDescription(scope) {
    return SCOPE_DESC[scope] || ("Memories in " + humanize(scope) + ".");
  }

  /* ---- formatting ------------------------------------------------------- */

  function parseDate(value) {
    if (!value) return null;
    var s = String(value);
    var d = new Date(s);
    if (isNaN(d.getTime()) && s.indexOf(" ") > -1 && s.indexOf("T") === -1) {
      d = new Date(s.replace(" ", "T"));
    }
    return isNaN(d.getTime()) ? null : d;
  }

  function formatAbsolute(value) {
    var d = parseDate(value);
    if (!d) return String(value || "—");
    try {
      return d.toLocaleString(undefined, {
        year: "numeric", month: "short", day: "numeric",
        hour: "2-digit", minute: "2-digit"
      });
    } catch (e) {
      return d.toISOString();
    }
  }

  function formatRelative(value) {
    var d = parseDate(value);
    if (!d) return "";
    var secs = Math.round((Date.now() - d.getTime()) / 1000);
    if (secs < 45) return "just now";
    if (secs < 90) return "a minute ago";
    var mins = Math.round(secs / 60);
    if (mins < 60) return mins + " min ago";
    var hrs = Math.round(mins / 60);
    if (hrs < 24) return hrs + (hrs === 1 ? " hour ago" : " hours ago");
    var days = Math.round(hrs / 24);
    if (days < 30) return days + (days === 1 ? " day ago" : " days ago");
    return formatAbsolute(value);
  }

  function numberFmt(n) {
    var v = Number(n);
    if (isNaN(v)) return String(n);
    return v.toLocaleString();
  }

  /* ---- shared UI pieces ------------------------------------------------- */

  var RETURN_MARK =
    '<g transform="translate(3.2,3.2) scale(0.9)" fill="currentColor">' +
    '<path d="M18.07 45.75 L17.28 44.97 L16.61 44.10 L16.02 43.16 L15.50 42.17 L15.05 41.14 L14.67 40.08 L14.37 38.99 L14.14 37.88 L13.99 36.75 L13.92 35.61 L13.92 34.46 L14.01 33.31 L14.17 32.17 L14.41 31.04 L14.73 29.93 L15.12 28.83 L15.58 27.77 L16.12 26.74 L16.72 25.74 L17.39 24.79 L18.13 23.89 L18.92 23.04 L19.77 22.24 L20.67 21.50 L21.62 20.83 L22.61 20.22 L23.64 19.68 L24.70 19.21 L25.79 18.82 L26.90 18.50 L28.03 18.26 L29.16 18.10 L30.31 18.02 L31.45 18.01 L32.59 18.08 L33.71 18.23 L34.82 18.45 L35.90 18.75 L36.96 19.12 L37.99 19.56 L38.97 20.06 L39.92 20.63 L40.81 21.26 L41.66 21.94 L42.45 22.68 L43.19 23.47 L43.86 24.29 L44.47 25.16 L45.01 26.06 L45.49 26.99 L45.90 27.94 L46.23 28.90 L46.50 29.88 L46.69 30.87 L46.81 31.86 L46.87 32.84 L46.85 33.81 L46.76 34.77 L46.61 35.71 L46.40 36.63 L46.12 37.52 L45.78 38.37 L45.39 39.18 L44.95 39.96 L44.46 40.69 L43.92 41.37 L43.35 42.00 L42.74 42.58 L42.09 43.10 L41.43 43.57 L40.74 43.97 L40.03 44.31 L39.31 44.60 L38.58 44.82 L37.86 44.98 L37.13 45.07 L36.41 45.10 L35.71 45.06 L35.01 44.94 L34.33 44.69 L34.33 44.69 L34.80 44.30 L35.26 43.97 L35.70 43.64 L36.13 43.29 L36.53 42.94 L36.90 42.57 L37.26 42.18 L37.59 41.78 L37.89 41.37 L38.17 40.95 L38.43 40.52 L38.66 40.08 L38.86 39.63 L39.04 39.17 L39.20 38.71 L39.32 38.24 L39.43 37.77 L39.50 37.29 L39.56 36.81 L39.58 36.33 L39.58 35.85 L39.56 35.37 L39.51 34.89 L39.44 34.42 L39.34 33.95 L39.21 33.48 L39.06 33.02 L38.89 32.57 L38.69 32.12 L38.47 31.68 L38.22 31.25 L37.94 30.83 L37.65 30.43 L37.33 30.03 L36.98 29.65 L36.61 29.29 L36.22 28.94 L35.81 28.61 L35.37 28.30 L34.91 28.01 L34.43 27.75 L33.92 27.50 L33.40 27.29 L32.86 27.10 L32.30 26.94 L31.72 26.80 L31.13 26.71 L30.52 26.64 L29.90 26.61 L29.26 26.61 L28.62 26.66 L27.97 26.74 L27.32 26.86 L26.66 27.03 L26.01 27.24 L25.35 27.49 L24.70 27.78 L24.06 28.13 L23.42 28.51 L22.81 28.94 L22.20 29.42 L21.62 29.95 L21.06 30.52 L20.53 31.13 L20.03 31.79 L19.56 32.49 L19.13 33.24 L18.74 34.02 L18.39 34.84 L18.09 35.70 L17.84 36.59 L17.64 37.51 L17.49 38.46 L17.40 39.44 L17.38 40.44 L17.41 41.46 L17.50 42.49 L17.65 43.55 L17.86 44.62 L18.07 45.75 Z"/>' +
    '<circle cx="32" cy="36" r="5.2"/></g>';

  function markSvg(cls) {
    var wrap = h("span", { class: cls, "aria-hidden": "true" });
    var svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", "0 0 64 64");
    svg.innerHTML = RETURN_MARK;
    wrap.appendChild(svg);
    return wrap;
  }

  function stateBlock(opts) {
    var block = h("div", { class: "state" + (opts.error ? " state--error" : "") });
    block.appendChild(markSvg("state__mark"));
    block.appendChild(h("p", { class: "state__title", text: opts.title }));
    if (opts.body) block.appendChild(h("p", { class: "state__body", text: opts.body }));
    if (opts.action) block.appendChild(opts.action);
    return block;
  }

  function loadingBlock() {
    return h("div", { class: "state" }, h("div", { class: "spinner", role: "status", "aria-label": "Loading" }));
  }

  function scopeBadge(scope) {
    var label = memoryAreaLabel(scope);
    return h("span", { class: "badge badge--scope", title: "Memory area: " + label },
      h("span", { class: "badge__dot" }), label);
  }

  function memoryAreaLabel(scope) {
    return scope === "project" ? "Project memories" : (SCOPE_LABEL[scope] || humanize(scope));
  }

  function typeBadge(type) {
    return h("span", { class: "badge badge--type", title: "Type: " + type }, type);
  }

  function sensitivityBadge(sens) {
    var value = sens || "normal";
    var note = (state.meta && state.meta.sensitivity_note) || "";
    return h("span", {
      class: "badge badge--sensitivity is-" + value,
      title: "Sensitivity: " + value + (note ? "\n\n" + note : "")
    }, value);
  }

  function sourceTag(uri) {
    var value = uri || "app://manual";
    var isWeb = /^https?:\/\//i.test(value);
    if (isWeb) {
      return h("a", { class: "source-tag", href: value, target: "_blank", rel: "noreferrer noopener", title: value }, value);
    }
    return h("span", { class: "source-tag", title: value }, value);
  }

  function confidenceEl(conf) {
    var v = Math.max(0, Math.min(1, Number(conf)));
    if (isNaN(v)) v = 0;
    return h("span", { class: "confidence", title: "Confidence " + v.toFixed(2) },
      h("span", { class: "confidence__track" }, h("span", { class: "confidence__fill", style: "width:" + (v * 100).toFixed(0) + "%" })),
      "conf " + v.toFixed(2));
  }

  /* ---- toasts ----------------------------------------------------------- */

  function toast(message, kind) {
    var wrap = $("#toasts");
    var el = h("div", { class: "toast" + (kind === "error" ? " toast--error" : ""), role: "status" }, message);
    wrap.appendChild(el);
    setTimeout(function () {
      el.classList.add("is-leaving");
      setTimeout(function () { if (el.parentNode) el.parentNode.removeChild(el); }, 220);
    }, kind === "error" ? 5200 : 3400);
  }

  /* ---- application state ------------------------------------------------ */

  var state = {
    meta: null,
    screen: "today",
    memories: [],
    filters: { query: "", scope: "", type: "" },
    lastFocus: null,
    modalGeneration: 0,
    addFromGuide: false,
    assistantStatuses: null,
    guide: { open: true, step: 0, project: "", client: "" }
  };

  var extraClients = []; // client ids added this session but not yet persisted

  function setCount(name, n) {
    var el = $('[data-count="' + name + '"]');
    if (!el) return;
    if (n == null) { el.hidden = true; return; }
    el.hidden = false;
    el.textContent = n > 999 ? "999+" : String(n);
  }

  /* ---- navigation ------------------------------------------------------- */

  var LOADERS = {
    today: loadToday,
    memories: loadMemories,
    sources: loadSources,
    sessions: loadSessions,
    permissions: loadPermissions,
    activity: loadActivity
  };

  async function loadSessions() {
    var body = $("#sessions-body");
    clear(body);
    body.appendChild(loadingBlock());
    try {
      var result = await Promise.all([B.listSessions(100), B.captureStatus()]);
      var sessions = result[0], capture = result[1];
      clear(body);
      var consent = h("section", { class: "today-group" },
        h("div", { class: "today-group__head" }, h("h2", { text: "Automatic archive" })),
        h("p", { class: "state__body", text: capture.enabled ? "Enabled — connected Claude Code and Codex sessions are stored locally." : "Disabled — no lifecycle transcript is archived." }),
        h("button", { class: "btn btn--primary", type: "button", text: capture.enabled ? "Disable archive" : "Enable archive", onclick: async function () { await B.setCaptureEnabled(!capture.enabled); loadSessions(); } })
      );
      body.appendChild(consent);
      if (!sessions.length) body.appendChild(stateBlock({ title: "No archived sessions", body: "Enable capture, then finish a Claude Code or Codex session." }));
      else {
        var list = h("div", { class: "today-list" });
        sessions.forEach(function (s) {
          list.appendChild(h("article", { class: "today-item" },
            h("p", { class: "today-item__content", text: s.title }),
            h("div", { class: "today-item__meta" },
              h("span", { class: "badge badge--type", text: s.provider }),
              h("span", { class: "badge badge--scope", text: s.project_name }),
              h("span", { class: "badge", text: s.capture_status }),
              sourceTag(s.source_uri), formatRelative(s.updated_at),
              h("button", { class: "btn btn--danger", type: "button", text: "Delete archive", onclick: async function () {
                if (!window.confirm("Delete this archived session from Ninai on this device?")) return;
                await B.deleteSession(s.id); toast("Session archive deleted."); loadSessions();
              } })
            )
          ));
        });
        body.appendChild(list);
      }
      setCount("sessions", sessions.length);
    } catch (err) {
      clear(body); body.appendChild(stateBlock({ title: "Could not load sessions", body: err.message, error: true }));
    }
  }

  function navTo(name) {
    if (!LOADERS[name]) return;
    state.screen = name;
    $$(".nav__item").forEach(function (btn) {
      var active = btn.getAttribute("data-screen") === name;
      if (active) btn.setAttribute("aria-current", "page");
      else btn.removeAttribute("aria-current");
    });
    $$(".screen").forEach(function (sec) {
      sec.classList.toggle("is-active", sec.id === "screen-" + name);
    });
    var active = $("#screen-" + name);
    if (active) active.focus({ preventScroll: true });
    LOADERS[name]();
  }

  /* ---- Home ------------------------------------------------------------- */

  function setupRequest(guide, status, revocation) {
    var block = h("div");
    if (!guide.project || !guide.client || !status.memory_saved) {
      block.appendChild(h("p", { text: "Choose a project and assistant above, and save a decision first." }));
      return block;
    }
    var prompt = 'Use Ninai recall for project_id "' + guide.project + '" with purpose "' + (revocation ? "verify revoked access" : "first setup handoff") + '" and query "" (an empty query for recent project memories). Make a fresh tool call even if you remember a previous answer. ' + (revocation ? 'Report whether Ninai returns any memories.' : 'Show a returned decision and its source, or say that none were returned.') + ' Use Ninai only; do not guess.';
    var request = h("textarea", { id: "setup-request", readonly: true, rows: "4", text: prompt, onclick: function () { this.select(); } });
    block.appendChild(h("label", { for: "setup-request", text: "Request to send to your assistant" }));
    block.appendChild(request);
    block.appendChild(h("button", { type: "button", class: "btn btn--ghost", text: "Copy request", onclick: async function () {
      try {
        if (!navigator.clipboard || !navigator.clipboard.writeText) throw new Error("Clipboard unavailable");
        await navigator.clipboard.writeText(prompt);
        toast("Request copied. Paste it into your chosen assistant.");
      } catch (_) {
        request.focus(); request.select();
        toast("Request selected. Use your keyboard’s Copy command.");
      }
    } }));
    block.appendChild(h("p", { class: "setup-guide__hint", text: "If the assistant cannot find Ninai, check its connection in Assistants and restart the assistant." }));
    return block;
  }

  async function setupGuide() {
    var guide = state.guide;
    var section = h("section", { class: "first-run setup-guide", "aria-labelledby": "setup-title" });
    section.appendChild(h("div", { class: "setup-guide__head" },
      h("div", {}, h("p", { class: "screen__eyebrow", text: "Setup guide" }), h("h2", { id: "setup-title", text: "Your first private handoff" })),
      h("button", { type: "button", class: "btn btn--ghost btn--sm", text: guide.open ? "Collapse guide" : "Continue setup", onclick: function () { guide.open = !guide.open; loadToday(); } })
    ));
    if (!guide.open) return section;
    var records = await Promise.all([B.listProjects(), B.listClients()]);
    var projects = records[0] || [], clients = records[1] || [];
    if (!projects.some(function (p) { return p.id === guide.project; })) guide.project = "";
    if (clients.indexOf(guide.client) < 0) guide.client = "";
    section.appendChild(h("p", { class: "setup-guide__intro", text: "Save one decision, choose who can read it, and test it in your assistant. Progress is checked against saved memories, permissions, and sharing history." }));
    var projectSelect = h("select", { id: "setup-project", onchange: function () { guide.project = this.value; loadToday(); } }, h("option", { value: "", text: "Choose a project" }));
    projects.forEach(function (p) { projectSelect.appendChild(h("option", { value: p.id, text: p.name })); });
    projectSelect.value = guide.project;
    var clientSelect = h("select", { id: "setup-assistant", onchange: function () { guide.client = this.value; loadToday(); } }, h("option", { value: "", text: "Choose an assistant" }));
    clients.forEach(function (id) {
      var connection = (state.assistantStatuses || []).filter(function (s) { return s.id === id; })[0];
      var label = { "claude-code": "Claude Code", codex: "Codex", gemini: "Gemini CLI", cursor: "Cursor", vscode: "VS Code" }[id] || id;
      var statusLabel = connection ? ({ configured: "Configured", connected: "Connected", needs_attention: "Needs attention", not_installed: "Not installed" }[connection.status] || "Not checked") : "Not checked";
      clientSelect.appendChild(h("option", { value: id, text: label + " — " + statusLabel }));
    });
    clientSelect.value = guide.client;
    section.appendChild(h("div", { class: "setup-guide__choices" },
      h("div", {}, h("label", { for: "setup-project", text: "Your project" }), projectSelect),
      h("div", {}, h("label", { for: "setup-assistant", text: "Assistant to test" }), clientSelect)
    ));
    var selectedConnection = (state.assistantStatuses || []).filter(function (s) { return s.id === guide.client; })[0];
    if (selectedConnection) section.appendChild(h("p", { class: "setup-guide__hint", text: selectedConnection.message }));
    section.appendChild(h("button", { type: "button", class: "btn btn--ghost btn--sm", text: "Check assistant connections", onclick: async function () {
      this.disabled = true; this.textContent = "Checking connections…";
      try { state.assistantStatuses = await B.assistantStatuses(); if (state.screen === "today") loadToday(); }
      catch (err) { toast(err.message || String(err), "error"); this.disabled = false; this.textContent = "Check assistant connections"; }
    } }));
    var status = await B.getSetupStatus(guide.project || null, guide.client || null);
    var complete = [!!status.memory_saved, !!status.read_allowed, !!status.recall_verified, !!status.revocation_verified];
    var names = ["Save a decision", "Choose access", "Test recall", "Test revocation"];
    var chapters = h("ol", { class: "setup-guide__chapters", "aria-label": "Setup chapters" });
    names.forEach(function (name, i) {
      chapters.appendChild(h("li", {}, h("button", { type: "button", "aria-current": guide.step === i ? "step" : null, class: "setup-guide__chapter" + (complete[i] ? " is-complete" : ""), text: (complete[i] ? "✓ " : (i + 1) + ". ") + name, onclick: function () { guide.step = i; loadToday(); } })));
    });
    section.appendChild(chapters);
    var content = h("div", { class: "setup-guide__content", "aria-live": "polite" });
    content.appendChild(h("p", { class: "setup-guide__status", text: complete[guide.step] ? "Verified in Ninai" : "Waiting for this step" }));
    content.appendChild(h("h3", { text: names[guide.step] }));
    if (guide.step === 0) {
      content.appendChild(h("p", { text: "Add a short decision under a named project, or create a project in the Add memory window. New projects start with assistant access off. Existing project permissions apply to any decision you add." }));
      content.appendChild(h("button", { class: "btn btn--primary", type: "button", text: "Add a project decision", onclick: function () { openModal(guide.project, true); $("#add-type").value = "decision"; } }));
    } else if (guide.step === 1) {
      content.appendChild(h("p", { text: "Open your chosen assistant’s card. Under your project, enable Read. Save and Delete are separate choices; leave them off unless you need them. Follow the card’s instructions if its connection needs attention, then return here." }));
      content.appendChild(h("button", { class: "btn btn--primary", type: "button", text: "Review connected assistants", onclick: function () { navTo("permissions"); } }));
    } else if (guide.step === 2) {
      content.appendChild(h("p", { text: "Open the assistant you selected and send the request below. Return here and check progress. A configured connection alone does not verify recall: Ninai needs a real request that returns this project’s memory." }));
      content.appendChild(setupRequest(guide, status, false));
      content.appendChild(h("button", { class: "btn btn--ghost", type: "button", text: "Inspect sharing history", onclick: function () { navTo("activity"); } }));
    } else {
      content.appendChild(h("p", { text: "After a successful recall, turn Read off for this project in Assistants. Ask the same assistant to call Ninai again. Already shared text cannot be taken back; this test checks that the next request receives no project memories." }));
      content.appendChild(h("button", { class: "btn btn--primary", type: "button", text: "Choose project access", onclick: function () { navTo("permissions"); } }));
      content.appendChild(setupRequest(guide, status, true));
      content.appendChild(h("p", { class: "setup-guide__hint", text: "You can turn Read back on later. The guide never changes your permissions." }));
    }
    section.appendChild(content);
    var check = h("button", { class: "btn btn--primary", type: "button", text: "Check progress", onclick: function () { loadToday(); } });
    section.appendChild(h("div", { class: "setup-guide__footer" }, check,
      h("button", { class: "btn btn--ghost", type: "button", disabled: guide.step === 0, text: "Back", onclick: function () { guide.step -= 1; loadToday(); } }),
      h("button", { class: "btn btn--ghost", type: "button", disabled: guide.step === 3, text: "Next chapter", onclick: function () { guide.step += 1; loadToday(); } })
    ));
    return section;
  }

  function todayItem(mem, kind) {
    return h("article", { class: "today-item" + (kind === "decision" ? " today-item--decision" : "") },
      h("p", { class: "today-item__content", text: mem.content }),
      h("div", { class: "today-item__meta" },
        scopeBadge(mem.scope),
        sourceTag(mem.source_uri)
      )
    );
  }

  function todayGroup(title, items, kind) {
    var group = h("section", { class: "today-group" });
    group.appendChild(h("div", { class: "today-group__head" },
      h("h2", { text: title }),
      h("span", { class: "today-group__count", text: String(items.length) })
    ));
    if (!items.length) {
      group.appendChild(h("p", { class: "state__body", style: "padding:10px 2px;color:var(--text-faint)", text: "None yet." }));
    } else {
      var list = h("div", { class: "today-list" });
      items.forEach(function (m) { list.appendChild(todayItem(m, kind)); });
      group.appendChild(list);
    }
    return group;
  }

  function recentSessionsGroup(sessions, captureEnabled) {
    var group = h("section", { class: "today-group" });
    group.appendChild(h("div", { class: "today-group__head" },
      h("h2", { text: "Recent agent sessions" }),
      h("span", { class: "today-group__count", text: String(sessions.length) })
    ));
    if (!sessions.length) {
      group.appendChild(h("p", { class: "state__body", style: "padding:10px 2px;color:var(--text-faint)", text: captureEnabled ? "Start Claude Code or Codex in a project to see captured activity here." : "Session capture is off. You can still save decisions and share them with your chosen assistant." }));
    } else {
      var list = h("div", { class: "today-list" });
      sessions.forEach(function (session) {
        list.appendChild(h("article", { class: "today-item" },
          h("p", { class: "today-item__content", text: session.title }),
          h("div", { class: "today-item__meta" },
            h("span", { class: "badge badge--type", text: session.provider }),
            h("span", { class: "badge badge--scope", text: session.project_name }),
            h("span", { class: "badge", text: session.capture_status }),
            formatRelative(session.updated_at)
          )
        ));
      });
      group.appendChild(list);
    }
    return group;
  }

  async function loadToday() {
    var body = $("#today-body");
    clear(body);
    body.appendChild(loadingBlock());
    try {
      var result = await Promise.all([B.today(), B.listSessions(5), B.captureStatus()]);
      var data = result[0];
      var sessions = result[1] || [];
      var memories = data.recent_memories || [];
      setCount("today", memories.length + sessions.length);
      var guide;
      try { guide = await setupGuide(); }
      catch (_) {
        guide = stateBlock({ title: "Setup progress is unavailable", body: "Your memories are still below. Try loading the setup guide again." });
        guide.appendChild(h("button", { type: "button", class: "btn btn--ghost", text: "Retry setup guide", onclick: loadToday }));
      }
      clear(body);
      body.appendChild(guide);
      if (!memories.length && !sessions.length) {
        body.appendChild(stateBlock({
          title: "Your private memory is ready",
          body: "Start with one decision in the setup guide above."
        }));
        return;
      }
      var cols = h("div", { class: "today-cols" });
      cols.appendChild(todayGroup("Recent memories", memories, "memory"));
      cols.appendChild(recentSessionsGroup(sessions, !!(result[2] && result[2].enabled)));
      body.appendChild(cols);
    } catch (err) {
      showError(body, err);
    }
  }

  /* ---- Memories --------------------------------------------------------- */

  function memRow(mem) {
    var row = h("button", {
      type: "button",
      class: "mem-row",
      dataId: mem.id,
      "aria-label": "Open memory: " + mem.content
    });
    row.appendChild(h("p", { class: "mem-row__content", text: mem.content }));
    row.appendChild(h("div", { class: "mem-row__meta" },
      sourceTag(mem.source_uri),
      confidenceEl(mem.confidence)
    ));
    row.appendChild(h("div", { class: "mem-row__badges" },
      typeBadge(mem.memory_type),
      scopeBadge(mem.scope),
      sensitivityBadge(mem.sensitivity)
    ));
    row.addEventListener("click", function () { openDrawer(mem.id, row); });
    return row;
  }

  function applyFilters(list) {
    return list.filter(function (m) {
      if (state.filters.scope && m.scope !== state.filters.scope) return false;
      if (state.filters.type && m.memory_type !== state.filters.type) return false;
      return true;
    });
  }

  function renderMemList() {
    var body = $("#mem-body");
    clear(body);
    var filtered = applyFilters(state.memories);
    var countEl = $("#mem-count");
    countEl.textContent = filtered.length + (filtered.length === 1 ? " memory" : " memories");
    if (!state.filters.query) setCount("memories", state.memories.length);

    if (!filtered.length) {
      var filtering = state.filters.query || state.filters.scope || state.filters.type;
      body.appendChild(stateBlock({
        title: filtering ? "No memories match" : "No saved memories yet",
        body: filtering
          ? "Try a different search term or clear the filters."
          : "Add one useful decision here. Then open Connected assistants and choose who may use it."
      }));
      return;
    }
    var list = h("div", { class: "mem-list" });
    filtered.forEach(function (m) { list.appendChild(memRow(m)); });
    body.appendChild(list);
  }

  async function loadMemories() {
    var body = $("#mem-body");
    clear(body);
    body.appendChild(loadingBlock());
    try {
      var list = await B.search(state.filters.query || "");
      state.memories = Array.isArray(list) ? list : [];
      renderMemList();
    } catch (err) {
      showError(body, err);
    }
  }

  var searchTimer = null;
  function onSearchInput(e) {
    state.filters.query = e.target.value.trim();
    clearTimeout(searchTimer);
    searchTimer = setTimeout(loadMemories, 220);
  }

  /* ---- Memory detail drawer -------------------------------------------- */

  function provRow(key, valNode, mono) {
    return h("div", { class: "prov__row" },
      h("span", { class: "prov__key", text: key }),
      valNode.nodeType ? h("span", { class: "prov__val" + (mono ? " is-mono" : "") }, valNode)
                       : h("span", { class: "prov__val" + (mono ? " is-mono" : ""), text: String(valNode) })
    );
  }

  function renderDrawerView(mem) {
    var body = $("#drawer-body");
    var actions = $("#drawer-actions");
    clear(body);
    clear(actions);

    body.appendChild(h("p", { class: "drawer__content", text: mem.content }));
    body.appendChild(h("div", { class: "drawer__badges" },
      typeBadge(mem.memory_type),
      scopeBadge(mem.scope),
      sensitivityBadge(mem.sensitivity)
    ));

    var prov = h("div", { class: "prov" });
    prov.appendChild(provRow("Importance", Number(mem.importance).toFixed(2)));
    prov.appendChild(provRow("Confidence", Number(mem.confidence).toFixed(2)));
    prov.appendChild(provRow("Source", sourceTag(mem.source_uri), true));
    prov.appendChild(provRow("Created", formatAbsolute(mem.created_at)));
    prov.appendChild(provRow("Updated", formatAbsolute(mem.updated_at)));
    prov.appendChild(provRow("Read count", numberFmt(mem.access_count)));
    prov.appendChild(provRow("ID", mem.id, true));
    body.appendChild(prov);

    actions.appendChild(h("button", {
      type: "button", class: "btn btn--ghost", onclick: function () { renderDrawerEdit(mem); }
    }, "Edit"));
    actions.appendChild(h("button", {
      type: "button", class: "btn btn--danger", onclick: function () { renderDrawerConfirm(mem); }
    }, "Delete"));
  }

  function editSelect(id, name, values, current) {
    var sel = h("select", { class: "form__control", id: id, name: name });
    values.forEach(function (v) {
      sel.appendChild(h("option", { value: v, selected: v === current }, name === "scope" ? memoryAreaLabel(v) : humanize(v)));
    });
    return sel;
  }

  function renderDrawerEdit(mem) {
    var body = $("#drawer-body");
    var actions = $("#drawer-actions");
    clear(body);
    clear(actions);

    var errBox = h("div", { class: "form__error", role: "alert" });
    var content = h("textarea", { class: "form__control", id: "edit-content" }, mem.content);
    var typeSel = editSelect("edit-type", "memory_type", state.meta.memory_types, mem.memory_type);
    var scopeSel = editSelect("edit-scope", "scope", state.meta.scopes, mem.scope);
    var sensSel = editSelect("edit-sens", "sensitivity", state.meta.sensitivities, mem.sensitivity || "normal");
    var importance = h("input", { class: "form__control", id: "edit-importance", type: "number", min: "0", max: "1", step: "0.05", value: Number(mem.importance).toFixed(2) });
    var confidence = h("input", { class: "form__control", id: "edit-confidence", type: "number", min: "0", max: "1", step: "0.05", value: Number(mem.confidence).toFixed(2) });

    var form = h("form", { class: "form", novalidate: true },
      errBox,
      h("div", { class: "form__field" }, h("label", { class: "form__label", for: "edit-content" }, "Content"), content),
      h("div", { class: "form__row" },
        h("div", { class: "form__field" }, h("label", { class: "form__label", for: "edit-type" }, "Type"), typeSel),
        h("div", { class: "form__field" }, h("label", { class: "form__label", for: "edit-scope" }, "Memory area"), scopeSel)
      ),
      h("div", { class: "form__row" },
        h("div", { class: "form__field" }, h("label", { class: "form__label", for: "edit-sens" }, "Sensitivity"), sensSel),
        h("div", { class: "form__field" },
          h("label", { class: "form__label", for: "edit-importance" }, "Importance"), importance)
      ),
      h("div", { class: "form__field" }, h("label", { class: "form__label", for: "edit-confidence" }, "Confidence"), confidence)
    );
    body.appendChild(form);

    function showErr(msg) { errBox.textContent = msg; errBox.classList.add("is-shown"); }

    async function save() {
      errBox.classList.remove("is-shown");
      var text = content.value.trim();
      if (!text) { showErr("Content cannot be empty."); content.focus(); return; }
      var changes = {
        content: text,
        memory_type: typeSel.value,
        scope: scopeSel.value,
        sensitivity: sensSel.value,
        importance: Number(importance.value),
        confidence: Number(confidence.value)
      };
      saveBtn.disabled = true;
      try {
        var updated = await B.updateMemory(mem.id, changes);
        renderDrawerView(updated);
        toast("Memory updated.");
        loadMemories();
        refreshCounts();
      } catch (err) {
        showErr(err.message || String(err));
        saveBtn.disabled = false;
      }
    }

    form.addEventListener("submit", function (e) { e.preventDefault(); save(); });

    actions.appendChild(h("button", { type: "button", class: "btn btn--ghost", onclick: function () { renderDrawerView(mem); } }, "Cancel"));
    var saveBtn = h("button", { type: "button", class: "btn btn--primary", onclick: save }, "Save changes");
    actions.appendChild(saveBtn);
    content.focus();
  }

  function renderDrawerConfirm(mem) {
    var actions = $("#drawer-actions");
    clear(actions);
    var strip = h("div", { class: "confirm" },
      h("p", { class: "confirm__q", text: "Delete this saved memory? You cannot restore it in the app. Assistants may still have copies they already received." })
    );
    var row = h("div", { class: "confirm__actions" });
    row.appendChild(h("button", { type: "button", class: "btn btn--ghost", onclick: function () { renderDrawerView(mem); } }, "Keep"));
    var delBtn = h("button", { type: "button", class: "btn btn--danger" }, "Forget it");
    delBtn.addEventListener("click", async function () {
      delBtn.disabled = true;
      try {
        var res = await B.deleteMemory(mem.id);
        closeDrawer();
        if (res && res.forgotten) toast("Memory forgotten.");
        else toast("Memory was already gone.");
        loadMemories();
        refreshCounts();
      } catch (err) {
        toast(err.message || String(err), "error");
        delBtn.disabled = false;
      }
    });
    row.appendChild(delBtn);
    strip.appendChild(row);
    actions.appendChild(strip);
  }

  async function openDrawer(id, trigger) {
    state.lastFocus = trigger || document.activeElement;
    $$(".mem-row").forEach(function (r) { r.classList.toggle("is-selected", r.getAttribute("data-id") === id); });
    var drawer = $("#drawer");
    var scrim = $("#drawer-scrim");
    drawer.hidden = false;
    drawer.inert = false;
    clearTimeout(drawerCloseTimer);
    syncDialogBackground();
    scrim.hidden = false;
    requestAnimationFrame(function () { drawer.classList.add("is-open"); scrim.classList.add("is-open"); });

    var body = $("#drawer-body");
    var actions = $("#drawer-actions");
    clear(body); clear(actions);
    body.appendChild(loadingBlock());
    $("#drawer-close").focus();
    try {
      var mem = await B.getMemory(id);
      renderDrawerView(mem);
    } catch (err) {
      clear(body);
      showError(body, err);
    }
  }

  function closeDrawer() {
    var drawer = $("#drawer");
    var scrim = $("#drawer-scrim");
    drawer.classList.remove("is-open");
    scrim.classList.remove("is-open");
    $$(".mem-row").forEach(function (r) { r.classList.remove("is-selected"); });
    drawer.inert = true;
    drawerCloseTimer = setTimeout(function () { drawer.hidden = true; scrim.hidden = true; }, 260);
    syncDialogBackground();
    restoreDialogFocus();
  }

  /* ---- Sources ---------------------------------------------------------- */

  function sourceCard(src) {
    return h("article", { class: "source-card" },
      h("div", { class: "source-card__scheme", text: src.scheme }),
      h("div", { class: "source-card__count" }, numberFmt(src.count), h("small", {}, src.count === 1 ? "memory" : "memories")),
      h("div", { class: "source-card__seen" }, "Last seen " + (src.last_seen ? formatRelative(src.last_seen) : "—"))
    );
  }

  async function loadSources() {
    var body = $("#sources-body");
    clear(body);
    body.appendChild(loadingBlock());
    try {
      var list = await B.sources();
      list = Array.isArray(list) ? list : [];
      setCount("sources", list.length);
      clear(body);

      var banner = h("div", { class: "banner" });
      banner.appendChild(markSvg("banner__mark"));
      banner.appendChild(h("p", {}, "This page groups memories by where Ninai received them. Only sources already present on this computer appear here."));
      body.appendChild(banner);

      if (!list.length) {
        body.appendChild(stateBlock({
          title: "No sources yet",
          body: "Once memories are captured, the schemes they arrived through appear here."
        }));
        return;
      }
      var grid = h("div", { class: "source-grid" });
      list.forEach(function (s) { grid.appendChild(sourceCard(s)); });
      body.appendChild(grid);
    } catch (err) {
      showError(body, err);
    }
  }

  /* ---- Permissions ------------------------------------------------------ */

  function grantedCount(card) {
    return $$('.switch[aria-checked="true"]', card).length;
  }

  function updateGrantedLabel(card) {
    var total = $$(".switch", card).length;
    var label = $(".client-card__granted", card);
    if (label) label.textContent = grantedCount(card) + " of " + total + " other areas readable";
  }

  function scopeSwitch(clientId, scope, allowed) {
    var sw = h("button", {
      type: "button",
      class: "switch",
      role: "switch",
      "aria-checked": allowed ? "true" : "false",
      "aria-label": (allowed ? "Revoke" : "Grant") + " " + scope + " for " + clientId
    }, h("span", { class: "switch__knob", "aria-hidden": "true" }));

    sw.addEventListener("click", async function () {
      if (sw.getAttribute("data-busy") === "true") return;
      var next = sw.getAttribute("aria-checked") !== "true";
      sw.setAttribute("data-busy", "true");
      try {
        await B.setPermission(clientId, scope, next);
        sw.setAttribute("aria-checked", next ? "true" : "false");
        sw.setAttribute("aria-label", (next ? "Revoke" : "Grant") + " " + scope + " for " + clientId);
        updateGrantedLabel(sw.closest(".client-card"));
        toast((next ? "Granted " : "Revoked ") + scope + " for " + clientId + ".");
      } catch (err) {
        toast(err.message || String(err), "error");
      } finally {
        sw.removeAttribute("data-busy");
      }
    });
    return sw;
  }

  function permissionToggle(clientId, name, action, allowed, save) {
    var input = h("input", { type: "checkbox", "aria-label": action + " " + name + " for " + clientId });
    input.checked = !!allowed;
    input.addEventListener("change", async function () {
      var next = input.checked;
      input.disabled = true;
      try { await save(next); toast("Permission updated. Applies to future requests."); }
      catch (err) { input.checked = !next; toast(err.message || String(err), "error"); }
      finally { input.disabled = false; }
    });
    return h("label", { class: "permission-action" }, input, action);
  }

  function clientCard(clientId, perms, assistantStatus, projects, projectPermissions, capabilities) {
    var card = h("article", { class: "client-card" });
    var stateName = assistantStatus ? assistantStatus.status : "custom";
    var stateLabel = assistantStatus
      ? ({ connected: "Connected", configured: "Configured", needs_attention: "Needs attention", not_installed: "Not installed" }[stateName] || "Check status")
      : "Custom";
    var head = h("div", { class: "client-card__head" },
      markSvg("nav__glyph"),
      h("span", { class: "client-card__id", text: assistantStatus ? assistantStatus.name : clientId }),
      h("span", { class: "connection-state is-" + stateName, text: stateLabel }),
      h("span", { class: "client-card__granted" })
    );
    card.appendChild(head);
    if (assistantStatus) {
      card.appendChild(h("p", { class: "client-card__status-copy", text: assistantStatus.message }));
      if ((clientId === "cursor" || clientId === "vscode") && assistantStatus.installed) {
        var connectButton = h("button", { type: "button", class: "btn btn--ghost btn--sm", text: "Configure " + assistantStatus.name });
        connectButton.addEventListener("click", async function () {
          connectButton.disabled = true;
          try {
            await B.connectAssistant(clientId);
            toast("Configuration saved. Open the editor to verify Ninai tools. Memory access remains your choice.");
            await loadPermissions();
          } catch (err) { toast(err.message || String(err), "error"); }
          finally { connectButton.disabled = false; }
        });
        card.appendChild(h("div", { class: "connection-refresh" }, connectButton));
      }
    }
    card.appendChild(h("h3", { class: "permission-section-title", text: "Named projects" }));
    if (!projects.length) card.appendChild(h("p", { class: "client-card__status-copy", text: "Create a project when adding a memory to control its access separately." }));
    projects.forEach(function (project) {
      var grant = projectPermissions.filter(function (g) { return g.project_id === project.id; })[0] || {};
      var actions = h("div", { class: "permission-actions" });
      [["Read", "read"], ["Save", "write"], ["Delete", "delete"]].forEach(function (item) {
        actions.appendChild(permissionToggle(clientId, project.name, item[0], grant["can_" + item[1]], function (allowed) {
          return B.setProjectPermission(clientId, project.id, item[1], allowed);
        }));
      });
      card.appendChild(h("div", { class: "project-permission" }, h("strong", { text: project.name }), actions));
    });
    var otherAreas = h("details", { class: "perm-advanced" }, h("summary", {}, "Read other memory areas"));
    otherAreas.open = state.meta.scopes.some(function (scope) { return !!perms[scope]; });
    otherAreas.appendChild(h("p", { class: "client-card__status-copy", text: "Optional: share memories outside named projects. You can complete the setup guide using only your chosen project." }));
    state.meta.scopes.forEach(function (scope) {
      var allowed = !!perms[scope];
      otherAreas.appendChild(h("div", { class: "scope-row" },
        h("div", { class: "scope-row__text" },
          h("div", { class: "scope-row__name", text: SCOPE_LABEL[scope] || scope }),
          h("div", { class: "scope-row__desc", text: scopeDescription(scope) })
        ),
        scopeSwitch(clientId, scope, allowed)
      ));
    });
    card.appendChild(otherAreas);
    var advanced = h("details", { class: "perm-advanced" }, h("summary", {}, "Advanced: save and delete permissions"));
    advanced.appendChild(h("p", { class: "client-card__status-copy", text: "These permissions apply to the memory areas below, including unassigned project memories. Named projects use their own switches above." }));
    state.meta.scopes.forEach(function (scope) {
      var area = capabilities[scope] || {};
      var actions = h("div", { class: "permission-actions" });
      [["Save", "write"], ["Delete", "delete"]].forEach(function (item) {
        actions.appendChild(permissionToggle(clientId, SCOPE_LABEL[scope] || scope, item[0], area[item[1]], function (allowed) {
          return B.setCapability(clientId, scope, item[1], allowed);
        }));
      });
      advanced.appendChild(h("div", { class: "project-permission" }, h("span", { text: SCOPE_LABEL[scope] || scope }), actions));
    });
    card.appendChild(advanced);
    updateGrantedLabel(card);
    return card;
  }

  async function loadPermissions() {
    var body = $("#permissions-body");
    clear(body);
    body.appendChild(loadingBlock());
    try {
      var result = await Promise.all([B.listClients(), B.assistantStatuses(), B.listProjects()]);
      var clients = result[0];
      var statuses = Array.isArray(result[1]) ? result[1] : [];
      var statusById = {};
      statuses.forEach(function (item) { statusById[item.id] = item; });
      clients = Array.isArray(clients) ? clients.slice() : [];
      extraClients.forEach(function (c) { if (clients.indexOf(c) === -1) clients.push(c); });
      clients.sort();
      setCount("permissions", clients.length);

      var projects = Array.isArray(result[2]) ? result[2] : [];
      var permsList = await Promise.all(clients.map(function (c) {
        return Promise.all([B.getPermissions(c), B.getProjectPermissions(c), B.getCapabilities(c)]);
      }));

      clear(body);

      // advanced add-client bar
      var input = h("input", { type: "text", id: "new-client", placeholder: "e.g. claude-code", autocomplete: "off", spellcheck: "false", "aria-label": "New client id" });
      var addBtn = h("button", { type: "button", class: "btn btn--ghost btn--sm" }, "Add client");
      function addClient() {
        var id = input.value.trim();
        if (!id) { input.focus(); return; }
        if (clients.indexOf(id) === -1 && extraClients.indexOf(id) === -1) extraClients.push(id);
        input.value = "";
        loadPermissions();
      }
      addBtn.addEventListener("click", addClient);
      input.addEventListener("keydown", function (e) { if (e.key === "Enter") { e.preventDefault(); addClient(); } });
      var intro = h("section", { class: "permission-help" },
        h("h2", { text: "You stay in control" }),
        h("p", { text: "Choose what each assistant may read, save, or delete. Named projects have separate permissions, all off by default. Changes apply to future requests; they cannot remove copies an assistant already received." })
      );
      body.appendChild(intro);
      var bar = h("details", { class: "perm-advanced" },
        h("summary", {}, "Advanced: add another assistant"),
        h("div", { class: "perm-addbar" },
          h("label", { for: "new-client" }, "Assistant technical id"),
          input, addBtn
        )
      );
      body.appendChild(bar);

      var refresh = h("button", {
        type: "button", class: "btn btn--ghost btn--sm", text: "Check connections again",
        onclick: loadPermissions
      });
      body.appendChild(h("div", { class: "connection-refresh" }, refresh));

      if (!clients.length) {
        body.appendChild(stateBlock({ title: "No clients yet", body: "Add a client id above to set what it may read." }));
        return;
      }
      var grid = h("div", { class: "client-grid" });
      clients.forEach(function (c, i) { grid.appendChild(clientCard(c, permsList[i][0] || {}, statusById[c], projects, permsList[i][1] || [], permsList[i][2] || {})); });
      body.appendChild(grid);
    } catch (err) {
      showError(body, err);
    }
  }

  /* ---- Activity --------------------------------------------------------- */

  function logRow(log) {
    var row = h("div", { class: "log-row" });
    var ids = Array.isArray(log.memory_ids) ? log.memory_ids : [];
    var scopes = Array.isArray(log.scopes) ? log.scopes : [];

    var top = h("div", { class: "log-row__top" },
      h("span", { class: "log-row__time", title: formatAbsolute(log.created_at), text: formatRelative(log.created_at) }),
      h("span", { class: "log-row__client", text: log.client_id || "unknown" }),
      log.purpose ? h("span", { class: "log-row__purpose", text: log.purpose }) : null,
      h("span", { class: "log-row__tokens", text: numberFmt(log.estimated_tokens || 0) + " tokens" })
    );
    row.appendChild(top);

    if (scopes.length) {
      var scopeWrap = h("div", { class: "log-row__scopes" });
      scopes.forEach(function (s) { scopeWrap.appendChild(scopeBadge(s)); });
      row.appendChild(scopeWrap);
    }

    if (log.query) {
      row.appendChild(h("div", { class: "log-row__query" }, "“" + log.query + "”"));
    }

    var facts = h("div", { class: "log-facts" });
    if (!ids.length) {
      facts.appendChild(h("span", { class: "confidence", style: "font-size:0.72rem", text: "No facts released" }));
    } else {
      var idsBox = h("div", { class: "log-facts__ids" });
      ids.forEach(function (id) { idsBox.appendChild(h("code", { text: id })); });
      var toggle = h("button", {
        type: "button", class: "log-facts__toggle", "aria-expanded": "false"
      }, h("span", { class: "chev", "aria-hidden": "true" }, "›"), (ids.length + (ids.length === 1 ? " fact released" : " facts released")));
      toggle.addEventListener("click", function () {
        var open = toggle.getAttribute("aria-expanded") === "true";
        toggle.setAttribute("aria-expanded", open ? "false" : "true");
        idsBox.classList.toggle("is-open", !open);
      });
      facts.appendChild(toggle);
      facts.appendChild(idsBox);
    }
    row.appendChild(facts);
    return row;
  }

  async function loadActivity() {
    var body = $("#activity-body");
    clear(body);
    body.appendChild(loadingBlock());
    try {
      var logs = await B.listLogs(100);
      logs = Array.isArray(logs) ? logs.slice() : [];
      logs.sort(function (a, b) {
        return String(b.created_at || "").localeCompare(String(a.created_at || ""));
      });
      setCount("activity", logs.length);
      clear(body);
      if (!logs.length) {
        body.appendChild(stateBlock({
          title: "No sharing requests yet",
          body: "When an assistant requests memory, this history records the request, memory areas and IDs shared, and estimated token count."
        }));
        return;
      }
      var list = h("div", { class: "log-list" });
      logs.forEach(function (l) { list.appendChild(logRow(l)); });
      body.appendChild(list);
    } catch (err) {
      showError(body, err);
    }
  }

  /* ---- add-memory modal ------------------------------------------------- */

  var modalCloseTimer = null, drawerCloseTimer = null;

  function activeDialog() {
    return [$("#add-modal"), $("#drawer")].filter(function (node) { return !node.hidden && !node.inert; })[0] || null;
  }

  function syncDialogBackground() { $("#app").inert = !!activeDialog(); }

  function restoreDialogFocus() {
    if (state.lastFocus && state.lastFocus.isConnected && state.lastFocus.focus) state.lastFocus.focus();
    else $("#screen-" + state.screen).focus({ preventScroll: true });
  }

  function openModal(selectedProject, requireProject) {
    state.modalGeneration += 1;
    state.addFromGuide = requireProject === true;
    state.lastFocus = document.activeElement;
    var modal = $("#add-modal");
    clearTimeout(modalCloseTimer);
    modal.hidden = false;
    modal.inert = false;
    syncDialogBackground();
    $("#add-submit").disabled = false;
    $("#add-submit").textContent = "Save memory";
    $("#add-scope").disabled = state.addFromGuide;
    $("#add-scope option[value='project']").textContent = state.addFromGuide ? "Project memories" : SCOPE_LABEL.project;
    if (state.addFromGuide) $("#add-scope").value = "project";
    requestAnimationFrame(function () { modal.classList.add("is-open"); });
    $("#add-error").classList.remove("is-shown");
    $("#add-content").focus();
    loadProjectOptions(typeof selectedProject === "string" ? selectedProject : null).catch(function (err) { toast(err.message || String(err), "error"); });
  }

  function closeModal() {
    state.modalGeneration += 1;
    state.addFromGuide = false;
    var modal = $("#add-modal");
    modal.classList.remove("is-open");
    modal.inert = true;
    modalCloseTimer = setTimeout(function () { modal.hidden = true; }, 200);
    $("#add-form").reset();
    $("#add-advanced").open = false;
    $("#new-project-details").open = false;
    $("#add-scope").disabled = false;
    $("#add-scope option[value='project']").textContent = SCOPE_LABEL.project;
    $("#add-project").removeAttribute("aria-invalid");
    setFormDefaults();
    syncDialogBackground();
    restoreDialogFocus();
  }

  function setFormDefaults() {
    if (!state.meta) return;
    var t = $("#add-type"); if (state.meta.memory_types.indexOf("fact") > -1) t.value = "fact";
    var s = $("#add-scope"); if (state.meta.scopes.indexOf("project") > -1) s.value = "project";
    var se = $("#add-sensitivity"); if (state.meta.sensitivities.indexOf("normal") > -1) se.value = "normal";
    $("#add-project-field").hidden = s.value !== "project";
  }

  async function submitAdd(e) {
    e.preventDefault();
    var errBox = $("#add-error");
    errBox.classList.remove("is-shown");
    var content = $("#add-content").value.trim();
    if (!content) {
      errBox.textContent = "Content cannot be empty.";
      errBox.classList.add("is-shown");
      $("#add-content").focus();
      return;
    }
    if (state.addFromGuide && !$("#add-project").value) {
      errBox.textContent = "Choose or create a named project so the setup guide can check your decision.";
      errBox.classList.add("is-shown");
      $("#add-project").setAttribute("aria-invalid", "true");
      $("#add-project").focus();
      return;
    }
    var generation = state.modalGeneration;
    var savedProject = $("#add-scope").value === "project" ? $("#add-project").value : "";
    var submitBtn = $("#add-submit");
    submitBtn.disabled = true;
    submitBtn.textContent = "Saving…";
    try {
      await B.addMemory(
        content,
        $("#add-type").value,
        $("#add-scope").value,
        $("#add-source").value.trim() || "app://manual",
        $("#add-sensitivity").value,
        $("#add-scope").value === "project" ? ($("#add-project").value || null) : null
      );
      if (generation === state.modalGeneration) {
        if (savedProject) state.guide.project = savedProject;
        closeModal();
      }
      toast("Memory saved.");
      if (state.screen === "memories") loadMemories();
      if (state.screen === "today") loadToday();
      refreshCounts();
    } catch (err) {
      if (generation === state.modalGeneration) {
        errBox.textContent = err.message || String(err);
        errBox.classList.add("is-shown");
      } else toast("The earlier memory could not be saved. Your current draft is unchanged.", "error");
    } finally {
      if (generation === state.modalGeneration) {
        submitBtn.disabled = false;
        submitBtn.textContent = "Save memory";
      }
    }
  }

  async function loadProjectOptions(selectedId) {
    var generation = state.modalGeneration;
    var projects = await B.listProjects();
    if (generation !== state.modalGeneration || $("#add-modal").hidden || $("#add-modal").inert) return;
    var select = $("#add-project");
    var selected = selectedId || select.value;
    clear(select);
    select.appendChild(h("option", { value: "", text: state.addFromGuide ? "Choose a project to continue" : "Unassigned project memories" }));
    projects.forEach(function (p) { select.appendChild(h("option", { value: p.id, text: p.name })); });
    select.value = selected;
    if (select.selectedIndex < 0) select.value = "";
    select.required = state.addFromGuide;
    select.removeAttribute("aria-invalid");
    if (state.addFromGuide && !projects.length) $("#new-project-details").open = true;
    $("#add-project-field").hidden = $("#add-scope").value !== "project";
  }

  /* ---- errors & counts -------------------------------------------------- */

  function showError(container, err) {
    clear(container);
    container.appendChild(stateBlock({
      error: true,
      title: "Something went wrong",
      body: (err && err.message) ? err.message : String(err)
    }));
  }

  function refreshCounts() {
    Promise.all([B.today(), B.listSessions(5)]).then(function (result) {
      setCount("today", (result[0].recent_memories || []).length + (result[1] || []).length);
    }).catch(function () {});
    B.listMemories(1000).then(function (l) { setCount("memories", (l || []).length); }).catch(function () {});
    B.sources().then(function (l) { setCount("sources", (l || []).length); }).catch(function () {});
    B.listClients().then(function (l) {
      var n = (l || []).length;
      extraClients.forEach(function (c) { if ((l || []).indexOf(c) === -1) n++; });
      setCount("permissions", n);
    }).catch(function () {});
    B.listLogs(100).then(function (l) { setCount("activity", (l || []).length); }).catch(function () {});
  }

  /* ---- populate selects from meta -------------------------------------- */

  function fillFilter(sel, values, label) {
    values.forEach(function (v) { sel.appendChild(h("option", { value: v }, label ? label(v) : humanize(v))); });
  }

  function humanize(value) {
    return String(value).replace(/[_-]+/g, " ").replace(/\b\w/g, function (c) { return c.toUpperCase(); });
  }

  function fillFormSelect(sel, values, labels) {
    values.forEach(function (v) {
      sel.appendChild(h("option", { value: v }, (labels && labels[v]) || humanize(v)));
    });
  }

  function applyMeta(meta) {
    state.meta = meta;
    $("#vault-path").textContent = meta.vault_path || "local";
    $("#vault-path").title = meta.vault_path || "";
    fillFilter($("#filter-scope"), meta.scopes, memoryAreaLabel);
    fillFilter($("#filter-type"), meta.memory_types);
    fillFormSelect($("#add-type"), meta.memory_types);
    fillFormSelect($("#add-scope"), meta.scopes, SCOPE_LABEL);
    fillFormSelect($("#add-sensitivity"), meta.sensitivities);
    setFormDefaults();
  }

  /* ---- wiring ----------------------------------------------------------- */

  function wireEvents() {
    $$(".nav__item").forEach(function (btn) {
      btn.addEventListener("click", function () { navTo(btn.getAttribute("data-screen")); });
    });

    $("#mem-search").addEventListener("input", onSearchInput);
    $("#filter-scope").addEventListener("change", function (e) { state.filters.scope = e.target.value; renderMemList(); });
    $("#filter-type").addEventListener("change", function (e) { state.filters.type = e.target.value; renderMemList(); });

    $("#add-memory-btn").addEventListener("click", openModal);
    $("#open-setup-guide").addEventListener("click", function () { state.guide.open = true; navTo("today"); });
    $("#add-close").addEventListener("click", closeModal);
    $("#add-cancel").addEventListener("click", closeModal);
    $("#add-form").addEventListener("submit", submitAdd);
    $("#add-modal").addEventListener("mousedown", function (e) { if (e.target === $("#add-modal")) closeModal(); });

    $("#drawer-close").addEventListener("click", closeDrawer);
    $("#drawer-scrim").addEventListener("click", closeDrawer);

    document.addEventListener("keydown", function (e) {
      var dialog = activeDialog();
      if (!dialog) return;
      if (e.key === "Escape") {
        e.preventDefault();
        if (dialog.id === "add-modal") closeModal(); else closeDrawer();
      } else if (e.key === "Tab") {
        var controls = $$("button:not([disabled]),input:not([disabled]),textarea:not([disabled]),select:not([disabled]),a[href],summary,[tabindex]:not([tabindex='-1'])", dialog).filter(function (node) { return node.getClientRects().length > 0; });
        var first = controls[0], last = controls[controls.length - 1];
        if (!first) { e.preventDefault(); return; }
        if (e.shiftKey && (document.activeElement === first || !dialog.contains(document.activeElement))) { e.preventDefault(); last.focus(); }
        else if (!e.shiftKey && (document.activeElement === last || !dialog.contains(document.activeElement))) { e.preventDefault(); first.focus(); }
      }
    });
  }

  /* ---- boot ------------------------------------------------------------- */

  function revealApp() {
    $("#boot").classList.add("is-hidden");
    $("#app").hidden = false;
    setTimeout(function () { $("#boot").style.display = "none"; }, 320);
  }

  function bootFailed(err) {
    var boot = $("#boot");
    clear(boot);
    var inner = h("div", { class: "boot__inner" });
    inner.appendChild(markSvg("boot__mark"));
    inner.appendChild(h("p", { class: "state__title", text: "Can't open your saved memories" }));
    inner.appendChild(h("p", { class: "state__body", text: (err && err.message) ? err.message : String(err) }));
    boot.appendChild(inner);
  }

  async function init() {
    wireEvents();
    $("#add-scope").addEventListener("change", function () { $("#add-project-field").hidden = this.value !== "project"; });
    $("#create-project").addEventListener("click", async function () {
      var button = this;
      var generation = state.modalGeneration;
      var name = $("#new-project-name").value.trim();
      if (!name) { $("#new-project-name").focus(); return; }
      button.disabled = true;
      try {
        var project = await B.createProject(name);
        if (generation === state.modalGeneration) {
          await loadProjectOptions(project.id);
          $("#new-project-name").value = "";
        }
        toast("Project created. Assistant access starts off.");
      } catch (err) { toast(err.message || String(err), "error"); }
      finally { button.disabled = false; }
    });
    try {
      await B.waitForBridge();
      var meta = await B.meta();
      applyMeta(meta);
      revealApp();
      navTo("today");
      refreshCounts();
      B.assistantStatuses().then(function (statuses) {
        state.assistantStatuses = statuses;
        if (state.screen === "today" && $("#add-modal").hidden) loadToday();
      }).catch(function () {});
    } catch (err) {
      bootFailed(err);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
