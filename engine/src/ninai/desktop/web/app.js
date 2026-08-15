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
    public: "Shareable with anyone. Nothing private lives here.",
    work: "General working context — your role, team, and how you operate.",
    project: "A specific project's state, decisions, and open threads.",
    preference: "How you like things done — tools, defaults, working style.",
    personal: "Personal life details kept outside of work context.",
    finance: "Money matters — budgets, costs, and accounts.",
    health: "Health and wellbeing information."
  };

  function scopeDescription(scope) {
    return SCOPE_DESC[scope] || ("Context filed under the " + scope + " scope.");
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
    return h("span", { class: "badge badge--scope", title: "Scope: " + scope },
      h("span", { class: "badge__dot" }), scope);
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
    lastFocus: null
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
              sourceTag(s.source_uri), formatRelative(s.updated_at)
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

  /* ---- Today ------------------------------------------------------------ */

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

  async function loadToday() {
    var body = $("#today-body");
    clear(body);
    body.appendChild(loadingBlock());
    try {
      var data = await B.today();
      var commitments = data.commitments || [];
      var decisions = data.decisions || [];
      setCount("today", commitments.length + decisions.length);
      clear(body);
      if (!commitments.length && !decisions.length) {
        body.appendChild(stateBlock({
          title: "Nothing needs your attention yet",
          body: "As you work, commitments and decisions worth keeping will return here — each with a source you can trace."
        }));
        return;
      }
      var cols = h("div", { class: "today-cols" });
      cols.appendChild(todayGroup("Open commitments", commitments, "commitment"));
      cols.appendChild(todayGroup("Recent decisions", decisions, "decision"));
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
        title: filtering ? "No memories match" : "Your vault is empty",
        body: filtering
          ? "Try a different search term or clear the filters."
          : "Add one durable decision here. Then open Permissions and grant only the scope your AI needs."
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
      sel.appendChild(h("option", { value: v, selected: v === current }, v));
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
        h("div", { class: "form__field" }, h("label", { class: "form__label", for: "edit-scope" }, "Scope"), scopeSel)
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
      h("p", { class: "confirm__q", text: "Forget this memory? The record is removed from the vault and cannot be undone." })
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
    setTimeout(function () { drawer.hidden = true; scrim.hidden = true; }, 260);
    if (state.lastFocus && state.lastFocus.focus) state.lastFocus.focus();
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
      banner.appendChild(h("p", {}, "Live connectors (Gmail, Calendar) aren't available yet. These are the origins of memories already captured in the vault — grouped by where they came from."));
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
    if (label) label.textContent = grantedCount(card) + " / " + total + " scopes";
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

  function clientCard(clientId, perms) {
    var card = h("article", { class: "client-card" });
    var head = h("div", { class: "client-card__head" },
      markSvg("nav__glyph"),
      h("span", { class: "client-card__id", text: clientId }),
      h("span", { class: "client-card__granted" })
    );
    card.appendChild(head);
    state.meta.scopes.forEach(function (scope) {
      var allowed = !!perms[scope];
      card.appendChild(h("div", { class: "scope-row" },
        h("div", { class: "scope-row__text" },
          h("div", { class: "scope-row__name", text: scope }),
          h("div", { class: "scope-row__desc", text: scopeDescription(scope) })
        ),
        scopeSwitch(clientId, scope, allowed)
      ));
    });
    updateGrantedLabel(card);
    return card;
  }

  async function loadPermissions() {
    var body = $("#permissions-body");
    clear(body);
    body.appendChild(loadingBlock());
    try {
      var clients = await B.listClients();
      clients = Array.isArray(clients) ? clients.slice() : [];
      extraClients.forEach(function (c) { if (clients.indexOf(c) === -1) clients.push(c); });
      clients.sort();
      setCount("permissions", clients.length);

      var permsList = await Promise.all(clients.map(function (c) {
        return B.getPermissions(c).catch(function () { return {}; });
      }));

      clear(body);

      // add-client bar
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
      var bar = h("div", { class: "perm-addbar" },
        h("label", { for: "new-client" }, "Pre-authorize an assistant by id:"),
        input, addBtn
      );
      body.appendChild(bar);

      if (!clients.length) {
        body.appendChild(stateBlock({ title: "No clients yet", body: "Add a client id above to set what it may read." }));
        return;
      }
      var grid = h("div", { class: "client-grid" });
      clients.forEach(function (c, i) { grid.appendChild(clientCard(c, permsList[i] || {})); });
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
          title: "No packets released yet",
          body: "When an assistant requests context, the exact packet it received is recorded here — with the facts and scopes involved."
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

  function openModal() {
    state.lastFocus = document.activeElement;
    var modal = $("#add-modal");
    modal.hidden = false;
    requestAnimationFrame(function () { modal.classList.add("is-open"); });
    $("#add-error").classList.remove("is-shown");
    $("#add-content").focus();
  }

  function closeModal() {
    var modal = $("#add-modal");
    modal.classList.remove("is-open");
    setTimeout(function () { modal.hidden = true; }, 200);
    $("#add-form").reset();
    setFormDefaults();
    if (state.lastFocus && state.lastFocus.focus) state.lastFocus.focus();
  }

  function setFormDefaults() {
    if (!state.meta) return;
    var t = $("#add-type"); if (state.meta.memory_types.indexOf("fact") > -1) t.value = "fact";
    var s = $("#add-scope"); if (state.meta.scopes.indexOf("project") > -1) s.value = "project";
    var se = $("#add-sensitivity"); if (state.meta.sensitivities.indexOf("normal") > -1) se.value = "normal";
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
    var submitBtn = $("#add-submit");
    submitBtn.disabled = true;
    try {
      await B.addMemory(
        content,
        $("#add-type").value,
        $("#add-scope").value,
        $("#add-source").value.trim() || "app://manual",
        $("#add-sensitivity").value
      );
      closeModal();
      toast("Memory added to the vault.");
      if (state.screen === "memories") loadMemories();
      refreshCounts();
    } catch (err) {
      errBox.textContent = err.message || String(err);
      errBox.classList.add("is-shown");
    } finally {
      submitBtn.disabled = false;
    }
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
    B.today().then(function (d) {
      setCount("today", (d.commitments || []).length + (d.decisions || []).length);
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

  function fillFilter(sel, values) {
    values.forEach(function (v) { sel.appendChild(h("option", { value: v }, v)); });
  }

  function fillFormSelect(sel, values) {
    values.forEach(function (v) { sel.appendChild(h("option", { value: v }, v)); });
  }

  function applyMeta(meta) {
    state.meta = meta;
    $("#vault-path").textContent = meta.vault_path || "local";
    $("#vault-path").title = meta.vault_path || "";
    fillFilter($("#filter-scope"), meta.scopes);
    fillFilter($("#filter-type"), meta.memory_types);
    fillFormSelect($("#add-type"), meta.memory_types);
    fillFormSelect($("#add-scope"), meta.scopes);
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
    $("#add-close").addEventListener("click", closeModal);
    $("#add-cancel").addEventListener("click", closeModal);
    $("#add-form").addEventListener("submit", submitAdd);
    $("#add-modal").addEventListener("mousedown", function (e) { if (e.target === $("#add-modal")) closeModal(); });

    $("#drawer-close").addEventListener("click", closeDrawer);
    $("#drawer-scrim").addEventListener("click", closeDrawer);

    document.addEventListener("keydown", function (e) {
      if (e.key !== "Escape") return;
      if (!$("#add-modal").hidden) { closeModal(); }
      else if (!$("#drawer").hidden) { closeDrawer(); }
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
    inner.appendChild(h("p", { class: "state__title", text: "Can't reach the vault" }));
    inner.appendChild(h("p", { class: "state__body", text: (err && err.message) ? err.message : String(err) }));
    boot.appendChild(inner);
  }

  async function init() {
    wireEvents();
    try {
      await B.waitForBridge();
      var meta = await B.meta();
      applyMeta(meta);
      revealApp();
      navTo("today");
      refreshCounts();
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
