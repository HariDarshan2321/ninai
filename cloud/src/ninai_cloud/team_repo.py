"""Canonical GitHub repository selectors shared by the Team client and service."""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path


_GITHUB_REPO = re.compile(
    r"(?:(?:https://github\.com/|ssh://git@github\.com/|git@github\.com:))?"
    r"([a-z0-9](?:[a-z0-9-]{0,37}[a-z0-9])?)/([a-z0-9_.-]{1,100})(?:/)?",
    re.ASCII | re.IGNORECASE,
)


def repository_key(value: str) -> str:
    match = _GITHUB_REPO.fullmatch(value.strip()) if isinstance(value, str) and len(value) <= 240 else None
    if match is None:
        raise ValueError("Enter a GitHub repository as owner/name or a GitHub clone URL.")
    owner, repo = (part.lower() for part in match.groups())
    repo = repo.removesuffix(".git")
    if repo in {"", ".", ".."}:
        raise ValueError("Invalid GitHub repository name.")
    return f"{owner}/{repo}"


def checkout_repository(cwd: str) -> str | None:
    """Read the local origin without contacting GitHub or accepting Git overrides."""
    if not isinstance(cwd, str) or not Path(cwd).is_absolute():
        return None
    try:
        result = subprocess.run(
            ["git", "-C", cwd, "config", "--local", "--get-all", "remote.origin.url"],
            env={key: value for key, value in os.environ.items() if not key.startswith("GIT_")},
            capture_output=True, text=True, timeout=2, check=False,
        )
        urls = result.stdout.splitlines()
        if result.returncode == 0 and len(urls) == 1:
            # The repository setting can use owner/name. The actual origin must
            # name GitHub explicitly, so a relative local remote never matches.
            if urls[0].startswith(("https://github.com/", "ssh://git@github.com/", "git@github.com:")):
                return repository_key(urls[0])
    except (OSError, subprocess.SubprocessError, ValueError):
        pass
    return None
