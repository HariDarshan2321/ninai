/* ==========================================================================
   Ninai bridge — thin wrapper over window.pywebview.api
   Every Python method returns {ok:true,data} or {ok:false,error}. This module
   unwraps the envelope, throwing on failure so callers can use try/catch.
   ========================================================================== */
(function () {
  "use strict";

  var READY_TIMEOUT = 12000;

  // Resolve once the Python bridge is attached. pywebview fires `pywebviewready`
  // on window, but it may already be present, and in some builds the event is
  // missed — so we also poll defensively.
  function waitForBridge() {
    return new Promise(function (resolve, reject) {
      if (window.pywebview && window.pywebview.api) {
        resolve();
        return;
      }
      var settled = false;
      function ready() {
        if (settled) return;
        settled = true;
        clearInterval(poll);
        resolve();
      }
      window.addEventListener("pywebviewready", ready, { once: true });
      var started = Date.now();
      var poll = setInterval(function () {
        if (window.pywebview && window.pywebview.api) {
          ready();
        } else if (Date.now() - started > READY_TIMEOUT) {
          clearInterval(poll);
          if (!settled) {
            settled = true;
            reject(new Error("Could not reach the Ninai vault (bridge unavailable)."));
          }
        }
      }, 60);
    });
  }

  async function call(method) {
    var args = Array.prototype.slice.call(arguments, 1);
    var api = window.pywebview && window.pywebview.api;
    if (!api || typeof api[method] !== "function") {
      throw new Error("Bridge method unavailable: " + method);
    }
    var res = await api[method].apply(api, args);
    if (!res || typeof res !== "object") {
      throw new Error("Malformed response from " + method);
    }
    if (!res.ok) {
      throw new Error(res.error || "Request failed");
    }
    return res.data;
  }

  window.NinaiBridge = {
    waitForBridge: waitForBridge,
    call: call,
    // Convenience typed wrappers around the contract.
    meta: function () { return call("meta"); },
    listMemories: function (limit) { return call("list_memories", limit == null ? 200 : limit); },
    search: function (query) { return call("search", query); },
    getMemory: function (id) { return call("get_memory", id); },
    addMemory: function (content, type, scope, source, sensitivity) {
      return call("add_memory", content, type, scope, source, sensitivity);
    },
    updateMemory: function (id, changes) { return call("update_memory", id, changes); },
    deleteMemory: function (id) { return call("delete_memory", id); },
    today: function () { return call("today"); },
    sources: function () { return call("sources"); },
    listClients: function () { return call("list_clients"); },
    getPermissions: function (clientId) { return call("get_permissions", clientId); },
    setPermission: function (clientId, scope, allowed) {
      return call("set_permission", clientId, scope, allowed);
    },
    listLogs: function (limit) { return call("list_logs", limit == null ? 100 : limit); },
    listSessions: function (limit) { return call("list_sessions", limit == null ? 100 : limit); },
    deleteSession: function (id) { return call("delete_session", id); },
    captureStatus: function () { return call("capture_status"); },
    setCaptureEnabled: function (enabled) { return call("set_capture_enabled", enabled); }
  };
})();
