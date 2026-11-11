#!/usr/bin/env python3
"""Test fixture: product desktop assets and real API over loopback, synthetic vault only.

Not an application server. Never serves or accepts a user's existing vault.
Stop with Ctrl-C; the disposable vault is removed on exit.
"""
from __future__ import annotations

import json
import argparse
import mimetypes
import os
import secrets
import sys
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engine" / "src"))
from ninai.desktop.api import DesktopApi
from ninai.store import MemoryStore

WEB = ROOT / "engine" / "src" / "ninai" / "desktop" / "web"
METHODS = frozenset({
    "meta", "list_memories", "search", "get_memory", "add_memory", "update_memory",
    "delete_memory", "today", "sources", "list_projects", "create_project",
    "get_project_permissions", "set_project_permission", "get_capabilities", "set_capability",
    "list_clients", "assistant_statuses", "get_permissions", "set_permission", "list_logs",
    "list_sessions", "delete_session", "capture_status", "set_capture_enabled",
    "setup_status",
})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=58040)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("port must be between 1024 and 65535")
    with tempfile.TemporaryDirectory(prefix="ninai-desktop-acceptance-") as fixture:
        os.environ["NINAI_DATA_DIR"] = fixture
        api = DesktopApi(MemoryStore(Path(fixture) / "ninai.sqlite3"))
        token = secrets.token_urlsafe(32)
        origin = f"http://127.0.0.1:{args.port}"
        bridge = """<script>
        window.pywebview={api:{}};
        METHODS.forEach(function(method){window.pywebview.api[method]=async function(){
          var response=await fetch('/__test_bridge__',{method:'POST',
            headers:{'Content-Type':'application/json','X-Ninai-Test-Token':TOKEN},
            body:JSON.stringify({method:method,args:Array.from(arguments)})});
          if(!response.ok)throw new Error('Test bridge request failed: '+response.status);
          return response.json();
        };});
        </script>""".replace("METHODS", json.dumps(sorted(METHODS))).replace("TOKEN", json.dumps(token))

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def reply(self, status, body, content_type="application/json"):
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()
                self.wfile.write(body)

            def host_allowed(self):
                return self.headers.get("Host") == f"127.0.0.1:{args.port}"

            def do_GET(self):
                if not self.host_allowed():
                    self.reply(403, b'{}')
                    return
                path = urlsplit(self.path).path
                name = "index.html" if path == "/" else path.removeprefix("/")
                if name not in {p.name for p in WEB.iterdir() if p.is_file()}:
                    self.reply(404, b'{}')
                    return
                target = WEB / name
                body = target.read_bytes()
                if name == "index.html":
                    body = body.replace(b'<script src="api.js">', bridge.encode() + b'<script src="api.js">')
                self.reply(200, body, mimetypes.guess_type(name)[0] or "application/octet-stream")

            def do_POST(self):
                if (not self.host_allowed() or self.path != "/__test_bridge__"
                    or self.headers.get("Origin") != origin
                    or not secrets.compare_digest(self.headers.get("X-Ninai-Test-Token", ""), token)):
                    self.reply(403, b'{}')
                    return
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    if not 0 < length <= 65536:
                        self.reply(413, b'{}')
                        return
                    request = json.loads(self.rfile.read(length))
                    if request.get("method") not in METHODS or not isinstance(request.get("args"), list):
                        self.reply(400, b'{}')
                        return
                    result = getattr(api, request["method"])(*request["args"])
                    self.reply(200, json.dumps(result).encode())
                except (ValueError, TypeError, KeyError):
                    self.reply(400, b'{"ok":false,"error":"Invalid test bridge request"}')

        server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
        print(origin + "/", flush=True)
        print(f"Synthetic database: {api.store.path}", flush=True)
        print("Disposable synthetic desktop API fixture; Ctrl-C stops it.", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()


if __name__ == "__main__":
    main()
