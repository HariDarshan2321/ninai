#!/usr/bin/env python3
"""Non-blocking lifecycle adapter shared by Claude Code and Codex."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", required=True, choices=("claude-code", "codex"))
    args = parser.parse_args()
    try:
        event = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        return 0
    configured = os.getenv("NINAI_EXECUTABLE", "").strip()
    installed = Path.home() / ".ninai-app" / "venv" / "bin" / "ninai"
    executable = configured or shutil.which("ninai") or (str(installed) if installed.is_file() else "")
    if not executable:
        return 0
    try:
        result = subprocess.run(
            [executable, "session-hook", "--provider", args.provider],
            input=json.dumps(event), text=True, timeout=12, check=False,
            capture_output=True,
        )
        if result.returncode == 0 and result.stdout.strip():
            sys.stdout.write(result.stdout)
    except (OSError, subprocess.SubprocessError):
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
