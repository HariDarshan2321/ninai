"""Explicit, offline installation of the bundled Codex continuity skill.

Codex's documented user skill root is ~/.agents/skills:
https://developers.openai.com/codex/skills#where-to-save-skills

Only files bearing a valid Ninai ownership marker and their original content
hash may be updated. Each replacement is atomic. An interrupted two-file
commit fails closed on the next invocation rather than trusting changed files.
This is an owner convenience, not a boundary against another same-user process.
"""
from __future__ import annotations

import hashlib
from importlib.resources import files
import json
import os
from pathlib import Path
import re
import stat
import tempfile
from typing import Any

SKILL_NAME = "project-continuity"
SKILL_VERSION = "1"
MARKER_NAME = ".ninai-managed.json"
_OWNER = "ninai.project-continuity"


def _bundled_skill() -> bytes:
    return files("ninai").joinpath("integration_skills", SKILL_NAME, "SKILL.md").read_bytes()


def _check_path(path: Path, *, directory: bool = False) -> None:
    """Do not follow an existing symlink at any level, including broken links."""
    for item in reversed((path, *path.parents)):
        try:
            mode = item.lstat().st_mode
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(mode):
            raise ValueError(f"Refusing symlink path: {item}")
        if item != path or directory:
            if not stat.S_ISDIR(mode):
                raise ValueError(f"Expected a directory: {item}")
        elif not stat.S_ISREG(mode):
            raise ValueError(f"Expected a regular file: {item}")


def _digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _stage(path: Path, content: bytes) -> Path:
    with tempfile.NamedTemporaryFile(prefix=".ninai-skill-", dir=path.parent, delete=False) as staged:
        name = Path(staged.name)
        try:
            staged.write(content)
            staged.flush()
            os.fsync(staged.fileno())
        except BaseException:
            name.unlink(missing_ok=True)
            raise
    return name


def _owned_content(destination: Path) -> tuple[bytes, dict[str, Any]]:
    skill = destination / "SKILL.md"
    marker = destination / MARKER_NAME
    _check_path(skill)
    _check_path(marker)
    if not skill.is_file() or not marker.is_file():
        raise ValueError(f"Existing skill is not managed by Ninai; leaving it unchanged: {destination}")
    try:
        metadata = json.loads(marker.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError) as error:
        raise ValueError("Invalid Ninai ownership marker; leaving existing skill unchanged") from error
    if (not isinstance(metadata, dict) or metadata.get("owner") != _OWNER
            or metadata.get("schema") != 1 or not isinstance(metadata.get("version"), str)
            or not metadata["version"] or not isinstance(metadata.get("sha256"), str)
            or not re.fullmatch(r"[0-9a-f]{64}", metadata["sha256"])):
        raise ValueError("Invalid Ninai ownership marker; leaving existing skill unchanged")
    content = skill.read_bytes()
    if _digest(content) != metadata["sha256"]:
        raise ValueError("The Ninai skill was edited; leaving it unchanged. Move it aside before reinstalling.")
    return content, metadata


def install_continuity_skill(
    client: str = "codex", target_root: str | Path | None = None,
) -> dict[str, str]:
    """Install/update one bundled skill only when explicitly called.

    ``target_root`` overrides the skill-discovery root (not HOME), for isolated
    tests or an explicitly selected directory. No credentials, network, MCP
    configuration, vault access, or permission grants are involved.

    Returns ``status`` (installed/updated/unchanged), ``path``, ``version``,
    ``sha256`` and a ``message``. Unsupported clients and unsafe/existing edited
    paths raise ValueError; filesystem failures propagate as OSError.
    """
    if client != "codex":
        raise ValueError("Continuity skill installation currently supports Codex only.")
    root = Path(target_root) if target_root is not None else Path.home() / ".agents" / "skills"
    root = Path(os.path.abspath(root.expanduser()))
    destination = root / SKILL_NAME
    _check_path(destination, directory=True)
    content = _bundled_skill()
    digest = _digest(content)
    metadata = {"owner": _OWNER, "schema": 1, "version": SKILL_VERSION, "sha256": digest}
    old: tuple[bytes, dict[str, Any]] | None = None
    if destination.exists():
        old = _owned_content(destination)
        installed_version = old[1]["version"]
        if not re.fullmatch(r"[0-9]{1,12}", installed_version):
            raise ValueError("Unrecognized installed skill version; leaving it unchanged.")
        if int(installed_version) > int(SKILL_VERSION):
            raise ValueError("A newer Ninai skill is installed; refusing to downgrade it.")
        if old == (content, metadata):
            return {"status": "unchanged", "path": str(destination), "version": SKILL_VERSION,
                    "sha256": digest, "message": "Ninai continuity skill is already current. No access grants changed."}
    root.mkdir(parents=True, exist_ok=True)
    _check_path(root, directory=True)
    created = old is None
    if created:
        destination.mkdir()  # Refuse a concurrently created folder rather than adopting it.
    staged: list[Path] = []
    try:
        _check_path(destination, directory=True)
        skill_stage = _stage(destination / "SKILL.md", content)
        staged.append(skill_stage)
        marker_stage = _stage(destination / MARKER_NAME, (json.dumps(metadata, sort_keys=True) + "\n").encode())
        staged.append(marker_stage)
        # Recheck ownership immediately before replacing either owned file.
        if old is not None and _owned_content(destination) != old:
            raise ValueError("The Ninai skill changed during installation; leaving it unchanged.")
        _check_path(destination / "SKILL.md")
        _check_path(destination / MARKER_NAME)
        os.replace(skill_stage, destination / "SKILL.md")
        os.replace(marker_stage, destination / MARKER_NAME)
    finally:
        for path in staged:
            path.unlink(missing_ok=True)
        if created:
            try:
                destination.rmdir()  # Only removes an empty directory after a failed preparation.
            except OSError:
                pass
    return {"status": "installed" if created else "updated", "path": str(destination),
            "version": SKILL_VERSION, "sha256": digest,
            "message": "Ninai continuity skill installed. Restart Codex if it does not appear. No access grants changed."}
