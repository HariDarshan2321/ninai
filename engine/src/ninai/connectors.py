"""Explicit local editor configuration. Never grants memory permissions."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import tempfile

CLIENTS = {"cursor": "Cursor", "vscode": "Visual Studio Code"}


def installed(client: str) -> bool:
    command = "cursor" if client == "cursor" else "code"
    windows_name = "Cursor/Cursor.exe" if client == "cursor" else "Microsoft VS Code/Code.exe"
    windows_paths = [Path(os.environ[root]) / "Programs" / windows_name
                     for root in ("LOCALAPPDATA",) if os.environ.get(root)]
    return bool(shutil.which(command) or any(p.is_file() for p in windows_paths) or any(
        (root / (CLIENTS[client] + ".app")).is_dir()
        for root in (Path("/Applications"), Path.home() / "Applications")
    ))


def config_path(client: str) -> Path:
    if client == "cursor":
        return Path.home() / ".cursor" / "mcp.json"
    if sys.platform == "darwin":
        return Path.home() / "Library/Application Support/Code/User/mcp.json"
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA", str(Path.home() / "AppData/Roaming"))) / "Code/User/mcp.json"
    return Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "Code/User/mcp.json"


def configuration(client: str, command: str) -> dict:
    env = {"NINAI_CLIENT_ID": client}
    if os.environ.get("NINAI_DATA_DIR"):
        env["NINAI_DATA_DIR"] = str(Path(os.environ["NINAI_DATA_DIR"]).resolve())
    entry = {"command": command, "env": env}
    if client == "vscode":
        entry["type"] = "stdio"
    return {"servers" if client == "vscode" else "mcpServers": {"ninai-local": entry}}


def _read(path: Path) -> dict:
    if path.is_symlink():
        raise ValueError("Configuration is a symlink. Use the editor to review and configure Ninai manually.")
    try:
        data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("Configuration could not be safely read as JSON. Comments or invalid JSON must be edited in the app; existing content was kept.") from exc
    if not isinstance(data, dict):
        raise ValueError("Configuration root must be an object; existing content was kept.")
    return data


def configure(client: str, command: str, *, target: Path | None = None, remove: bool = False) -> bool:
    path = target or config_path(client)
    data = _read(path)
    key = "servers" if client == "vscode" else "mcpServers"
    servers = data.setdefault(key, {})
    if not isinstance(servers, dict):
        raise ValueError(f"{key} must be an object; existing content was kept.")
    expected = configuration(client, command)[key]["ninai-local"]
    current = servers.get("ninai-local")
    owned = isinstance(current, dict) and current.get("command") == command and isinstance(current.get("env"), dict) and current["env"].get("NINAI_CLIENT_ID") == client
    if remove:
        # Do not remove another installation's entry, even if its name matches.
        if not owned:
            return False
        del servers["ninai-local"]
    else:
        if current == expected:
            return False
        if current is not None and not owned:
            raise ValueError("A different ninai-local entry already exists. Review it in the editor before replacing it.")
        servers["ninai-local"] = expected
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o600
    # Keep an exact recovery copy, without overwriting an earlier backup.
    backup = path.with_name(path.name + ".ninai-backup")
    if path.exists() and not backup.exists():
        fd = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(path.read_bytes())
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".ninai-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, indent=2)
            stream.write("\n")
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return True


def status(client: str) -> dict:
    found = installed(client)
    try:
        data = _read(config_path(client))
        entry = data.get("servers" if client == "vscode" else "mcpServers", {}).get("ninai-local", {})
        configured = bool(entry.get("command")) and entry.get("env", {}).get("NINAI_CLIENT_ID") == client
    except (ValueError, AttributeError):
        configured = False
    return {"installed": found, "configured": configured,
            "status": "configured" if found and configured else "needs_attention" if found else "not_installed",
            "message": "Configuration saved. Open the editor and verify Ninai tools before use." if found and configured else "Choose Connect to configure Ninai, then verify its tools in the editor." if found else "Install this editor first. Configuration can be copied for later setup."}


def main() -> None:
    parser = argparse.ArgumentParser(description="Configure a local editor. Memory access stays off until you grant it in Ninai.")
    parser.add_argument("client", choices=CLIENTS)
    parser.add_argument("--command", default=str(Path(sys.executable).with_name("ninai-mcp.exe" if os.name == "nt" else "ninai-mcp")))
    parser.add_argument("--config", type=Path, help="Explicit editor configuration file, for example a workspace .vscode/mcp.json")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--apply", action="store_true", help="Explicitly save the configuration")
    action.add_argument("--remove", action="store_true", help="Remove only this installation's entry")
    action.add_argument("--status", action="store_true")
    args = parser.parse_args()
    try:
        if args.status:
            print(json.dumps(status(args.client)))
        elif args.apply or args.remove:
            if not Path(args.command).is_absolute():
                raise ValueError("Use an absolute Ninai server executable path.")
            configure(args.client, args.command, target=args.config, remove=args.remove)
            print("Ninai configuration saved. Open the editor to verify tools. Memory access is managed separately in Ninai.")
        else:
            print(json.dumps(configuration(args.client, args.command), indent=2))
    except (OSError, ValueError) as exc:
        parser.exit(1, str(exc) + "\n")


if __name__ == "__main__":
    main()
