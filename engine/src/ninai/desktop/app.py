from __future__ import annotations

import sys
from pathlib import Path

from .api import DesktopApi

WEB_DIR = Path(__file__).resolve().parent / "web"
WINDOW_TITLE = "Ninai"


def _index_path() -> Path:
    index = WEB_DIR / "index.html"
    if not index.exists():
        raise FileNotFoundError(f"Ninai web assets not found at {index}")
    return index


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
