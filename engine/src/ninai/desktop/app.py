from __future__ import annotations

import sys
from importlib.resources import files
from pathlib import Path

from ninai.desktop.api import DesktopApi

WINDOW_TITLE = "Ninai"

# Expose flat, explicit RPC names only; never pass the owner object to the
# webview recursive/dotted dispatcher. Private store and approval authority stay
# unreachable through native bridge payload names.
BRIDGE_METHODS = (
    'list_access_requests',
    'approve_access_request',
    'deny_access_request',
    'meta',
    'check_for_updates',
    'list_memories',
    'search',
    'get_memory',
    'add_memory',
    'update_memory',
    'delete_memory',
    'today',
    'sources',
    'list_projects',
    'setup_status',
    'create_project',
    'get_project_permissions',
    'set_project_permission',
    'get_capabilities',
    'set_capability',
    'list_clients',
    'assistant_statuses',
    'connect_assistant',
    'get_permissions',
    'set_permission',
    'list_logs',
    'list_sessions',
    'delete_session',
    'capture_status',
    'set_capture_enabled',
)



def _index_path() -> Path:
    index = Path(str(files("ninai.desktop").joinpath("web", "index.html")))
    if not index.exists():
        raise FileNotFoundError(f"Ninai web assets not found at {index}")
    return index


def _configure_macos_app() -> None:
    """Give an unbundled pywebview launch Ninai's Dock identity."""
    if sys.platform != "darwin":
        return
    try:
        from AppKit import NSApplication, NSImage
        from Foundation import NSProcessInfo

        icon_path = Path(str(files("ninai.desktop").joinpath("web", "ninai-app-icon.svg")))
        icon = NSImage.alloc().initWithContentsOfFile_(str(icon_path))
        app = NSApplication.sharedApplication()
        if icon is not None:
            app.setApplicationIconImage_(icon)
        process = NSProcessInfo.processInfo()
        if hasattr(process, "setProcessName_"):
            process.setProcessName_(WINDOW_TITLE)
    except Exception:
        # Branding must not prevent the local vault UI from opening.
        return


def main() -> None:
    """Launch the Ninai desktop window.

    Requires the optional desktop dependency: install with `pip install '.[desktop]'`.
    """
    try:
        import webview
    except ImportError:
        sys.stderr.write(
            "Ninai desktop requires pywebview.\n"
            "Install it with:  pip install 'ninai-memory[desktop]'\n"
        )
        raise SystemExit(1)

    api = DesktopApi()
    _configure_macos_app()
    sys.stdout.write("Opening Ninai…\n")
    sys.stdout.flush()
    window = webview.create_window(
        WINDOW_TITLE,
        url=str(_index_path()),
        js_api=None,
        width=1120,
        height=760,
        min_size=(880, 620),
    )
    window.expose(*(getattr(api, name) for name in BRIDGE_METHODS))
    webview.start()


if __name__ == "__main__":
    main()
