from __future__ import annotations

import sys
from importlib.resources import files
from pathlib import Path

from ninai.desktop.api import DesktopApi

WINDOW_TITLE = "Ninai"


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
    webview.create_window(
        WINDOW_TITLE,
        url=str(_index_path()),
        js_api=api,
        width=1120,
        height=760,
        min_size=(880, 620),
    )
    webview.start()


if __name__ == "__main__":
    main()
