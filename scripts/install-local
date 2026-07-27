#!/usr/bin/env bash
set -euo pipefail

repository="HariDarshan2321/ninai"
script_source="${BASH_SOURCE[0]:-}"
script_dir="$(cd "$(dirname "${script_source:-.}")" 2>/dev/null && pwd || true)"
repo_root="$(cd "${script_dir}/.." 2>/dev/null && pwd || true)"
install_dir="${NINAI_INSTALL_DIR:-${HOME}/.ninai-app}"
client="auto"

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

Usage: install-local [--client claude-code|codex|none]

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
  auto|claude-code|codex|none) ;;
  *) printf '%s\n' '--client must be claude-code, codex, or none.' >&2; exit 2 ;;
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
  package_source="${repo_root}/engine[desktop]"
else
  package_url="${NINAI_PACKAGE_URL:-https://github.com/${repository}/archive/refs/heads/main.tar.gz#subdirectory=engine}"
  package_source="ninai-memory[desktop] @ ${package_url}"
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
install_complete=1

if [[ "${client}" == "auto" ]]; then
  if command -v claude >/dev/null 2>&1; then
    client="claude-code"
  elif command -v codex >/dev/null 2>&1; then
    client="codex"
  else
    client="none"
  fi
fi

case "${client}" in
  claude-code)
    if ! command -v claude >/dev/null 2>&1; then
      printf '%s\n' 'Ninai installed, but Claude Code was not found. Install Claude Code and rerun with --client claude-code.' >&2
      exit 1
    fi
    "${install_dir}/venv/bin/ninai" permission grant claude-code project
    claude mcp remove ninai-local --scope user >/dev/null 2>&1 || true
    claude mcp add --transport stdio --scope user ninai-local -- "${install_dir}/venv/bin/ninai-mcp"
    ;;
  codex)
    if ! command -v codex >/dev/null 2>&1; then
      printf '%s\n' 'Ninai installed, but Codex was not found. Install Codex and rerun with --client codex.' >&2
      exit 1
    fi
    "${install_dir}/venv/bin/ninai" permission grant codex project
    codex mcp remove ninai-local >/dev/null 2>&1 || true
    codex mcp add ninai-local --env NINAI_CLIENT_ID=codex -- "${install_dir}/venv/bin/ninai-mcp"
    ;;
esac

printf '\nNinai is ready.\n'
printf 'Open the local app:\n  %s\n' "${install_dir}/venv/bin/ninai-app"
if [[ "${client}" == "none" ]]; then
  printf 'No supported AI client was detected. Rerun with --client after installing Claude Code or Codex.\n'
else
  printf 'Connected client: %s (project scope only)\n' "${client}"
fi
