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

Usage: install-local [--client both|claude-code|codex|none] [--session-capture ask|on|off]

Environment:
  NINAI_INSTALL_DIR  Installation directory (default: ~/.ninai-app)
  NINAI_PYTHON       Python 3.11+ executable
  NINAI_PACKAGE_URL  Override the source archive used by the remote installer

Examples:
  ./scripts/install-local --client claude-code
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
  auto|both|claude-code|codex|none) ;;
  *) printf '%s\n' '--client must be both, claude-code, codex, or none.' >&2; exit 2 ;;
esac
case "${session_capture}" in
  ask|on|off) ;;
  *) printf '%s\n' '--session-capture must be ask, on, or off.' >&2; exit 2 ;;
esac

case "$(uname -s)" in
  Darwin) ;;
  *) printf '%s\n' 'This MVP installer currently supports macOS only.' >&2; exit 1 ;;
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
finish_install() {
  status=$?
  if [[ "${install_complete}" -ne 1 ]]; then
    rm -rf "${install_dir}"
    if [[ -n "${backup_dir}" && -d "${backup_dir}" ]]; then
      mv "${backup_dir}" "${install_dir}"
    fi
  elif [[ -n "${backup_dir}" && -d "${backup_dir}" ]]; then
    rm -rf "${backup_dir}"
  fi
  exit "${status}"
}
trap finish_install EXIT

if [[ -d "${install_dir}" ]]; then
  backup_dir="${install_dir}.previous.$$"
  mv "${install_dir}" "${backup_dir}"
fi

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
install_complete=1

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
from pathlib import Path

path = Path(os.environ["NINAI_HOOK_TARGET"])
try:
    data = json.loads(path.read_text()) if path.exists() else {}
except (OSError, json.JSONDecodeError) as exc:
    raise SystemExit(f"Cannot safely merge hooks into {path}: {exc}")
hooks = data.setdefault("hooks", {})
provider = os.environ["NINAI_HOOK_PROVIDER"]
executable = os.environ["NINAI_HOOK_COMMAND"]

def add(event, command, matcher=""):
    groups = hooks.setdefault(event, [])
    for group in groups:
        for item in group.get("hooks", []):
            if item.get("command") == command:
                return
    groups.append({"matcher": matcher, "hooks": [{"type": "command", "command": command, "timeout": 15}]})

lifecycle = f'{executable} session-hook --provider {provider}'
for event in ("SessionStart", "Stop", "SessionEnd"):
    add(event, lifecycle)
if os.environ["NINAI_INCLUDE_POST_TOOL"] == "yes":
    add("PostToolUse", f'{executable} capture-hook --quiet', "mcp__.*")
path.write_text(json.dumps(data, indent=2) + "\n")
PY
}

if [[ "${client}" == "auto" ]]; then
  if command -v claude >/dev/null 2>&1 && command -v codex >/dev/null 2>&1; then
    client="both"
  elif command -v claude >/dev/null 2>&1; then
    client="claude-code"
  elif command -v codex >/dev/null 2>&1; then
    client="codex"
  else
    client="none"
  fi
fi

connect_claude() {
    if ! command -v claude >/dev/null 2>&1; then
      printf '%s\n' 'Ninai installed, but Claude Code was not found. Install Claude Code and rerun with --client claude-code.' >&2
      exit 1
    fi
    "${install_dir}/venv/bin/ninai" permission grant claude-code project
    claude mcp remove ninai-local --scope user >/dev/null 2>&1 || true
    claude mcp remove ninai --scope user >/dev/null 2>&1 || true
    claude mcp remove ninai-cloud --scope user >/dev/null 2>&1 || true
    claude mcp add --transport stdio --scope user ninai-local -- "${install_dir}/venv/bin/ninai-mcp"
    merge_hooks "${HOME}/.claude/settings.json" "claude-code" "yes"
}

connect_codex() {
    if ! command -v codex >/dev/null 2>&1; then
      printf '%s\n' 'Ninai installed, but Codex was not found. Install Codex and rerun with --client codex.' >&2
      exit 1
    fi
    "${install_dir}/venv/bin/ninai" permission grant codex project
    codex mcp remove ninai-local >/dev/null 2>&1 || true
    codex mcp remove ninai-cloud >/dev/null 2>&1 || true
    codex mcp add ninai-local --env NINAI_CLIENT_ID=codex -- "${install_dir}/venv/bin/ninai-mcp"
    merge_hooks "${HOME}/.codex/hooks.json" "codex" "no"
}

case "${client}" in
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
esac

printf '\nNinai is ready.\n'
open "${app_bundle}" >/dev/null 2>&1 || true
printf '%s\n' 'The Ninai app is opening now.'
if [[ "${client}" == "none" ]]; then
  printf 'No supported AI client was detected. Rerun with --client after installing Claude Code or Codex.\n'
else
  printf 'Connected client: %s (project scope only)\n' "${client}"
fi
if [[ "${session_capture}" == "on" ]]; then
  printf '%s\n' 'Automatic local session capture: enabled'
else
  printf '%s\n' 'Automatic local session capture: disabled (enable it later in Ninai settings)'
fi
