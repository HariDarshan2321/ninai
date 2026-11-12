#!/usr/bin/env bash
set -euo pipefail

repository="HariDarshan2321/ninai"
script_source="${BASH_SOURCE[0]:-}"
script_dir="$(cd "$(dirname "${script_source:-.}")" 2>/dev/null && pwd || true)"
repo_root="$(cd "${script_dir}/.." 2>/dev/null && pwd || true)"
install_dir="${NINAI_INSTALL_DIR:-${HOME}/.ninai-app}"
client="auto"
session_capture="ask"

case "${install_dir}" in
  /*) ;;
  *) printf '%s\n' 'NINAI_INSTALL_DIR must be an absolute path.' >&2; exit 2 ;;
esac
if [[ "${install_dir}" == "/" || "${install_dir}" == "${HOME}" ]]; then
  printf '%s\n' 'Refusing to use a system root or home directory as NINAI_INSTALL_DIR.' >&2
  exit 2
fi

usage() {
  cat <<'EOF'
Install Ninai's local engine and optional MCP client connection.

Usage: install-local [--client all|both|claude-code|codex|gemini|cursor|vscode|none] [--session-capture ask|on|off]

Environment:
  NINAI_INSTALL_DIR  Installation directory (default: ~/.ninai-app)
  NINAI_PYTHON       Python 3.11+ executable
  NINAI_PACKAGE_URL  Override the source archive used by the remote installer

Examples:
  ./scripts/install-local --client claude-code
  ./scripts/install-local --client gemini
  curl -fsSL https://raw.githubusercontent.com/HariDarshan2321/ninai/main/scripts/install-local | bash -s -- --client codex
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --client)
      [[ $# -ge 2 ]] || { printf '%s\n' 'Missing value after --client.' >&2; exit 2; }
      client="$2"
      shift 2
      ;;
    --session-capture)
      [[ $# -ge 2 ]] || { printf '%s\n' 'Missing value after --session-capture.' >&2; exit 2; }
      session_capture="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'Unknown option: %s\n\n' "$1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

case "${client}" in
  auto|all|both|claude-code|codex|gemini|cursor|vscode|none) ;;
  *) printf '%s\n' '--client must be all, both, claude-code, codex, gemini, cursor, vscode, or none.' >&2; exit 2 ;;
esac
case "${session_capture}" in
  ask|on|off) ;;
  *) printf '%s\n' '--session-capture must be ask, on, or off.' >&2; exit 2 ;;
esac

case "$(uname -s)" in
  Darwin) ;;
  *) printf '%s\n' 'This installer supports macOS only. Windows has a separate preview installer.' >&2; exit 1 ;;
esac

python_cmd="${NINAI_PYTHON:-}"
if [[ -z "${python_cmd}" ]]; then
  for candidate in python3.13 python3.12 python3.11 python3; do
    if command -v "${candidate}" >/dev/null 2>&1 && "${candidate}" -c 'import sys; raise SystemExit(sys.version_info < (3, 11))'; then
      python_cmd="${candidate}"
      break
    fi
  done
fi

if [[ -z "${python_cmd}" ]] || ! command -v "${python_cmd}" >/dev/null 2>&1 || ! "${python_cmd}" -c 'import sys; raise SystemExit(sys.version_info < (3, 11))'; then
  printf '%s\n' \
    'Ninai requires Python 3.11 or newer.' \
    'Install it with: brew install python@3.13' \
    'Then rerun this installer. You can also set NINAI_PYTHON.' >&2
  exit 1
fi

# An update may replace only an existing Ninai installation. Keep the data
# directory separate from the replaceable application, including symlink paths.
if [[ -L "${install_dir}" || ( -e "${install_dir}" && ! -x "${install_dir}/venv/bin/ninai" ) ]]; then
  printf '%s\n' 'The installation path already exists and is not a Ninai installation. Choose a new NINAI_INSTALL_DIR; existing files were kept.' >&2
  exit 2
fi
NINAI_INSTALL_DIR="${install_dir}" "${python_cmd}" - <<'PY'
import os
from pathlib import Path

application = Path(os.environ["NINAI_INSTALL_DIR"]).resolve()
if os.environ.get("NINAI_DATA_DIR") and not Path(os.environ["NINAI_DATA_DIR"]).is_absolute():
    raise SystemExit("Use an absolute NINAI_DATA_DIR so every assistant uses the same memory directory. Existing files were kept.")
data = Path(os.environ.get("NINAI_DATA_DIR", str(Path.home() / ".ninai"))).resolve()
if application == data or application in data.parents or data in application.parents:
    raise SystemExit("Choose separate installation and memory directories. Updates must never replace saved memories. Existing files were kept.")
PY

if [[ -f "${repo_root}/engine/pyproject.toml" ]]; then
  package_source="${repo_root}/engine[macos-build]"
else
  package_url="${NINAI_PACKAGE_URL:-https://github.com/${repository}/archive/refs/heads/main.tar.gz#subdirectory=engine}"
  package_source="ninai-memory[macos-build] @ ${package_url}"
fi

# Preserve the previous installation until the replacement passes diagnostics.
# Python virtual environments contain absolute paths, so the new environment
# must be created at its final location rather than built elsewhere and moved.
install_parent="$(dirname "${install_dir}")"
mkdir -p "${install_parent}"
backup_dir=""
install_complete=0
installation_started=0
config_backup_dir=""
config_paths=()
config_backups=()

snapshot_config() {
  local target="$1" index saved=""
  for ((index=0; index<${#config_paths[@]}; index++)); do
    [[ "${config_paths[index]}" != "${target}" ]] || return 0
  done
  if [[ -L "${target}" || ( -e "${target}" && ! -f "${target}" ) ]]; then
    printf 'Cannot safely update assistant settings at %s. Review this path before retrying.\n' "${target}" >&2
    return 1
  fi
  if [[ -z "${config_backup_dir}" ]]; then
    config_backup_dir=$(mktemp -d "${install_parent}/.ninai-settings-backup.XXXXXX")
    chmod 700 "${config_backup_dir}"
  fi
  index=${#config_paths[@]}
  if [[ -f "${target}" ]]; then
    cp -p "${target}" "${config_backup_dir}/${index}"
    saved="${config_backup_dir}/${index}"
  fi
  config_paths+=("${target}")
  config_backups+=("${saved}")
}

restore_configs() {
  local index target saved failed=0
  for ((index=0; index<${#config_paths[@]}; index++)); do
    target="${config_paths[index]}"
    saved="${config_backups[index]}"
    if [[ -n "${saved}" ]]; then
      if ! cp -p "${saved}" "${target}.ninai-restore.$$" || ! mv -f "${target}.ninai-restore.$$" "${target}"; then
        printf 'Could not restore %s; recovery copy is retained at %s.\n' "${target}" "${saved}" >&2
        failed=1
      fi
    elif ! rm -f "${target}"; then
      printf 'Could not remove incomplete assistant settings at %s.\n' "${target}" >&2
      failed=1
    fi
  done
  return "${failed}"
}

finish_install() {
  status=$?
  if [[ "${install_complete}" -ne 1 ]]; then
    restored=1
    if restore_configs; then
      [[ -z "${config_backup_dir}" ]] || rm -rf "${config_backup_dir}"
    else
      restored=0
    fi
    if [[ "${installation_started}" -eq 1 ]]; then rm -rf "${install_dir}"; fi
    if [[ -n "${backup_dir}" && -d "${backup_dir}" ]]; then
      mv "${backup_dir}" "${install_dir}"
    fi
    if [[ "${restored}" -eq 1 ]]; then
      printf '%s\n' 'Setup did not finish. Previous app and assistant settings were restored where a backup existed. Saved memories were not removed. Fix the error above and rerun the installer.' >&2
    else
      printf '%s\n' 'Setup did not finish. The previous app was restored where a backup existed, but some assistant settings need recovery from the paths printed above. Saved memories were not removed.' >&2
    fi
  else
    [[ -z "${backup_dir}" || ! -d "${backup_dir}" ]] || rm -rf "${backup_dir}"
    [[ -z "${config_backup_dir}" ]] || rm -rf "${config_backup_dir}"
  fi
  exit "${status}"
}
trap finish_install EXIT

if [[ -d "${install_dir}" ]]; then
  backup_dir="${install_dir}.previous.$$"
  mv "${install_dir}" "${backup_dir}"
fi
installation_started=1

printf '%s\n' 'Installing Ninai local mode…'
"${python_cmd}" -m venv "${install_dir}/venv"
"${install_dir}/venv/bin/python" -m pip --disable-pip-version-check install --upgrade pip
"${install_dir}/venv/bin/python" -m pip --disable-pip-version-check install "${package_source}"
"${install_dir}/venv/bin/ninai" doctor

app_bundle="${install_dir}/Ninai.app"
iconset="${install_dir}/Ninai.iconset"
app_build="${install_dir}/.app-build"
icon_source=$("${install_dir}/venv/bin/python" -c 'from importlib.resources import files; print(files("ninai.desktop").joinpath("web", "ninai-app-icon.svg"))')
app_entry=$("${install_dir}/venv/bin/python" -c 'import ninai.desktop.app as app; print(app.__file__)')
mkdir -p "${iconset}" "${app_build}/work" "${app_build}/spec"
for size in 16 32 128 256 512; do
  sips -s format png -z "${size}" "${size}" "${icon_source}" \
    --out "${iconset}/icon_${size}x${size}.png" >/dev/null
  double=$((size * 2))
  sips -s format png -z "${double}" "${double}" "${icon_source}" \
    --out "${iconset}/icon_${size}x${size}@2x.png" >/dev/null
done
icon_file="${app_build}/Ninai.icns"
iconutil -c icns "${iconset}" -o "${icon_file}"
rm -rf "${iconset}"
"${install_dir}/venv/bin/pyinstaller" \
  --noconfirm --clean --windowed --name Ninai \
  --osx-bundle-identifier io.ninai.app \
  --icon "${icon_file}" --collect-data ninai \
  --distpath "${install_dir}" --workpath "${app_build}/work" \
  --specpath "${app_build}/spec" "${app_entry}"
xattr -cr "${app_bundle}"
codesign --force --deep --sign - "${app_bundle}" >/dev/null
rm -rf "${app_build}" "${install_dir}/Ninai"

if [[ "${session_capture}" == "ask" ]]; then
  if [[ -r /dev/tty ]]; then
    printf '%s\n' \
      'Ninai can automatically archive connected Claude Code/Codex sessions in your local vault.' \
      'The archive stays on this Mac and can be disabled later in Ninai settings.'
    printf 'Enable automatic session capture? [Y/n] '
    IFS= read -r answer </dev/tty || answer="n"
    case "${answer}" in
      n|N|no|NO) session_capture="off" ;;
      *) session_capture="on" ;;
    esac
  else
    session_capture="off"
  fi
fi
if [[ "${session_capture}" == "on" ]]; then
  "${install_dir}/venv/bin/ninai" capture enable >/dev/null
else
  "${install_dir}/venv/bin/ninai" capture disable >/dev/null
fi

merge_hooks() {
  target="$1"
  provider="$2"
  include_post_tool="$3"
  mkdir -p "$(dirname "${target}")"
  NINAI_HOOK_TARGET="${target}" NINAI_HOOK_PROVIDER="${provider}" \
  NINAI_HOOK_COMMAND="${install_dir}/venv/bin/ninai" NINAI_INCLUDE_POST_TOOL="${include_post_tool}" \
    "${python_cmd}" - <<'PY'
import json
import os
import shlex
import stat
import tempfile
from pathlib import Path

path = Path(os.environ["NINAI_HOOK_TARGET"])
if path.is_symlink():
    raise SystemExit(f"Cannot safely merge hooks into symlink {path}")
try:
    data = json.loads(path.read_text()) if path.exists() else {}
except (OSError, json.JSONDecodeError) as exc:
    raise SystemExit(f"Cannot safely merge hooks into {path}: {exc}")
if not isinstance(data, dict):
    raise SystemExit(f"Cannot safely merge hooks into {path}: root must be an object")
hooks = data.setdefault("hooks", {})
if not isinstance(hooks, dict):
    raise SystemExit(f"Cannot safely merge hooks into {path}: hooks must be an object")
provider = os.environ["NINAI_HOOK_PROVIDER"]
executable = os.environ["NINAI_HOOK_COMMAND"]

def owned(command):
    try:
        words = shlex.split(command)
    except (ValueError, TypeError):
        return False
    if words[:1] == ["env"]:
        words = words[1:]
        while words and "=" in words[0] and not words[0].startswith("-"):
            words = words[1:]
    return len(words) >= 2 and words[0] == executable and words[1] in {"session-hook", "capture-hook"}

for event in ("SessionStart", "Stop", "SessionEnd", "PostToolUse"):
    groups = hooks.get(event, [])
    if not isinstance(groups, list) or any(not isinstance(group, dict) or not isinstance(group.get("hooks", []), list) or any(not isinstance(item, dict) for item in group.get("hooks", [])) for group in groups):
        raise SystemExit(f"Cannot safely merge hooks into {path}: invalid {event} hooks")
    kept = []
    for group in groups:
        items = [item for item in group.get("hooks", []) if not (isinstance(item, dict) and owned(item.get("command", "")))]
        if items or not group.get("hooks"):
            kept.append({**group, "hooks": items})
    if event in hooks:
        hooks[event] = kept

environment = ["env", "NINAI_DATA_DIR=" + os.environ["NINAI_DATA_DIR"]] if os.environ.get("NINAI_DATA_DIR") else []

def command(*arguments):
    return shlex.join(environment + [executable, *arguments])

def add(event, command, matcher=""):
    groups = hooks.setdefault(event, [])
    for group in groups:
        for item in group.get("hooks", []):
            if item.get("command") == command:
                return
    groups.append({"matcher": matcher, "hooks": [{"type": "command", "command": command, "timeout": 15}]})

lifecycle = command("session-hook", "--provider", provider)
for event in ("SessionStart", "Stop", "SessionEnd"):
    add(event, lifecycle)
if os.environ["NINAI_INCLUDE_POST_TOOL"] == "yes":
    add("PostToolUse", command("capture-hook", "--quiet"), "mcp__.*")
mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o600
fd, temporary = tempfile.mkstemp(prefix=path.name + ".ninai-", dir=path.parent)
try:
    with os.fdopen(fd, "w") as stream:
        stream.write(json.dumps(data, indent=2) + "\n")
    os.chmod(temporary, mode)
    os.replace(temporary, path)
finally:
    if os.path.exists(temporary):
        os.unlink(temporary)
PY
}

connect_claude() {
    if ! command -v claude >/dev/null 2>&1; then
      printf '%s\n' 'Claude Code was not found. Install Claude Code and rerun with --client claude-code.' >&2
      exit 1
    fi
    local config_dir="${CLAUDE_CONFIG_DIR:-${HOME}/.claude}"
    local user_config="${HOME}/.claude.json"
    if [[ -n "${CLAUDE_CONFIG_DIR:-}" ]]; then user_config="${config_dir}/.claude.json"; fi
    snapshot_config "${user_config}"
    snapshot_config "${config_dir}/settings.json"
    claude mcp remove ninai-local --scope user >/dev/null 2>&1 || true
    claude_env=(--env NINAI_CLIENT_ID=claude-code)
    if [[ -n "${NINAI_DATA_DIR:-}" ]]; then claude_env+=(--env "NINAI_DATA_DIR=${NINAI_DATA_DIR}"); fi
    claude mcp add --transport stdio --scope user ninai-local "${claude_env[@]}" -- "${install_dir}/venv/bin/ninai-mcp"
    merge_hooks "${config_dir}/settings.json" "claude-code" "yes"
}

connect_codex() {
    if ! command -v codex >/dev/null 2>&1; then
      printf '%s\n' 'Codex was not found. Install Codex and rerun with --client codex.' >&2
      exit 1
    fi
    local config_dir="${CODEX_HOME:-${HOME}/.codex}"
    snapshot_config "${config_dir}/config.toml"
    snapshot_config "${config_dir}/hooks.json"
    codex mcp remove ninai-local >/dev/null 2>&1 || true
    codex_env=(--env NINAI_CLIENT_ID=codex)
    if [[ -n "${NINAI_DATA_DIR:-}" ]]; then codex_env+=(--env "NINAI_DATA_DIR=${NINAI_DATA_DIR}"); fi
    codex mcp add ninai-local "${codex_env[@]}" -- "${install_dir}/venv/bin/ninai-mcp"
    merge_hooks "${config_dir}/hooks.json" "codex" "no"
}

connect_gemini() {
    if ! command -v gemini >/dev/null 2>&1; then
      printf '%s\n' 'Ninai installed, but Gemini CLI was not found. Install Gemini CLI and rerun with --client gemini.' >&2
      exit 1
    fi
    settings_path="${HOME}/.gemini/settings.json"
    snapshot_config "${settings_path}"
    mkdir -p "$(dirname "${settings_path}")"
    NINAI_GEMINI_SETTINGS="${settings_path}" NINAI_MCP_COMMAND="${install_dir}/venv/bin/ninai-mcp" \
      "${python_cmd}" - <<'PY'
import json
import os
import stat
from pathlib import Path

path = Path(os.environ["NINAI_GEMINI_SETTINGS"])
try:
    data = json.loads(path.read_text()) if path.exists() else {}
except (OSError, json.JSONDecodeError) as exc:
    raise SystemExit(f"Cannot safely merge Ninai into {path}: {exc}")
if not isinstance(data, dict):
    raise SystemExit(f"Cannot safely merge Ninai into {path}: root must be an object")
servers = data.setdefault("mcpServers", {})
if not isinstance(servers, dict):
    raise SystemExit(f"Cannot safely merge Ninai into {path}: mcpServers must be an object")
servers["ninai-local"] = {
    "command": os.environ["NINAI_MCP_COMMAND"],
    "env": {"NINAI_CLIENT_ID": "gemini"},
    "trust": False,
    "description": "Permissioned local Ninai memory",
}
if os.environ.get("NINAI_DATA_DIR"):
    servers["ninai-local"]["env"]["NINAI_DATA_DIR"] = os.environ["NINAI_DATA_DIR"]
mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o600
temporary = path.with_name(path.name + ".ninai-install.tmp")
temporary.write_text(json.dumps(data, indent=2) + "\n")
os.chmod(temporary, mode)
os.replace(temporary, path)
PY
}

connect_editor() {
    if ! "${install_dir}/venv/bin/python" -c 'from ninai.connectors import installed; import sys; sys.exit(not installed(sys.argv[1]))' "$1"; then
      printf '%s was not found. Copy this configuration after installing it:\n' "$1"
      "${install_dir}/venv/bin/ninai-connect" "$1" --command "${install_dir}/venv/bin/ninai-mcp"
      return
    fi
    local config_file
    config_file=$("${install_dir}/venv/bin/python" -c 'from ninai.connectors import config_path; import sys; print(config_path(sys.argv[1]))' "$1")
    snapshot_config "${config_file}"
    snapshot_config "${config_file}.ninai-backup"
    "${install_dir}/venv/bin/ninai-connect" "$1" --command "${install_dir}/venv/bin/ninai-mcp" --apply
}

case "${client}" in
  auto)
    detected_clients=()
    if command -v claude >/dev/null 2>&1; then connect_claude; detected_clients+=("claude-code"); fi
    if command -v codex >/dev/null 2>&1; then connect_codex; detected_clients+=("codex"); fi
    if command -v gemini >/dev/null 2>&1; then connect_gemini; detected_clients+=("gemini"); fi
    for editor in cursor vscode; do
      if "${install_dir}/venv/bin/python" -c 'from ninai.connectors import installed; import sys; sys.exit(not installed(sys.argv[1]))' "${editor}"; then
        connect_editor "${editor}"
        detected_clients+=("${editor} (verify in editor)")
      fi
    done
    if [[ ${#detected_clients[@]} -eq 0 ]]; then client="none"; else client="${detected_clients[*]}"; fi
    ;;
  all)
    connect_claude
    connect_codex
    connect_gemini
    connect_editor cursor
    connect_editor vscode
    ;;
  both)
    connect_claude
    connect_codex
    ;;
  claude-code)
    connect_claude
    ;;
  codex)
    connect_codex
    ;;
  gemini)
    connect_gemini
    ;;
  cursor|vscode)
    connect_editor "${client}"
    ;;
esac

install_complete=1
printf '\nNinai is ready.\n'
open "${app_bundle}" >/dev/null 2>&1 || true
printf '%s\n' 'The Ninai app is opening now.'
if [[ "${client}" == "none" ]]; then
  printf 'No assistant connection was configured. Choose an assistant in Ninai, or rerun the installer with --client.\n'
else
  printf 'Configured assistants: %s. Verify tools in each assistant, then choose memory access in Ninai. New access stays off until you grant it.\n' "${client}"
fi
if [[ "${session_capture}" == "on" ]]; then
  printf '%s\n' 'Automatic local session capture: enabled'
else
  printf '%s\n' 'Automatic local session capture: disabled (enable it later in Ninai settings)'
fi
