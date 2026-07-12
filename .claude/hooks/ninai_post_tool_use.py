#!/usr/bin/env python3
"""Claude Code PostToolUse hook for Ninai.

Reads the official hook JSON from stdin and forwards it to the locally installed
Ninai CLI. Failures are deliberately non-blocking so memory capture never breaks
the user's primary tool workflow.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0

    executable = shutil.which("ninai")
    if executable is None:
        return 0

    try:
        subprocess.run(
            [executable, "capture-hook", "--quiet"],
            input=json.dumps(event),
            text=True,
            timeout=8,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.SubprocessError):
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
