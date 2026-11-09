#!/usr/bin/env python3
"""Opt-in real Claude/Codex handoff with synthetic, isolated local memory.

Run with the installed Ninai Python interpreter. Uses existing host login, but
never reads credentials or changes global host configuration. Model calls may
consume subscription/API usage. Temporary evidence is retained for inspection.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import uuid

from ninai.store import MemoryStore


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=int, default=150)
    args = parser.parse_args()
    root = Path(tempfile.mkdtemp(prefix="ninai-real-host-"))
    work = root / "work"
    work.mkdir()
    vault = root / "vault"
    store = MemoryStore(vault / "ninai.sqlite3")
    project = store.ensure_project(name="Synthetic host gate", binding_key=f"path:{work}", cwd_or_repo=str(work))
    project_id = str(project["id"])
    marker = f"NINAI_GATE_{uuid.uuid4().hex[:12].upper()}"
    hosts = {"claude-code": shutil.which("claude"), "codex": shutil.which("codex")}
    if not all(hosts.values()):
        print(json.dumps({"status": "blocked", "reason": "Install both Claude Code and Codex CLI"}))
        return 1
    for host in hosts:
        store.grant_project(host, project_id, "read")
        store.grant_project(host, project_id, "write")
    print(json.dumps({"evidence_dir": str(root), "python": sys.executable, "project_id": project_id, "marker": marker}), flush=True)

    def invoke(host: str, stage: str, prompt: str) -> None:
        environment = os.environ.copy()
        environment.pop("CLAUDECODE", None)
        environment["NINAI_DATA_DIR"] = str(vault)
        environment["NINAI_CLIENT_ID"] = host
        server = {"command": sys.executable, "args": ["-m", "ninai.server"], "env": {"NINAI_DATA_DIR": str(vault), "NINAI_CLIENT_ID": host}}
        if host == "claude-code":
            command = [str(hosts[host]), "-p", "--restricted", "--strict-mcp-config", "--setting-sources", "", "--settings", '{"disableAllHooks":true}', "--tools", "", "--allowedTools", "mcp__ninai_gate__*", "--no-session-persistence", "--output-format", "json", "--mcp-config", json.dumps({"mcpServers": {"ninai_gate": server}}), "--", prompt]
        else:
            command = [str(hosts[host]), "exec", "--ignore-user-config", "--ignore-rules", "--ephemeral", "--skip-git-repo-check", "--sandbox", "read-only", "--disable", "hooks", "--disable", "apps", "-c", 'approval_policy="never"', "--json"]
            for key, value in server.items():
                command.extend(["-c", f"mcp_servers.ninai_gate.{key}=" + ("{" + ",".join(f"{k}={json.dumps(v)}" for k, v in value.items()) + "}" if isinstance(value, dict) else json.dumps(value))])
            command.extend(["-c", 'mcp_servers.ninai_gate.default_tools_approval_mode="approve"'])
            command.append(prompt)
        instruction = "Only call the ninai_gate MCP tools requested. Do not use shell, files, network tools, other connectors, or inspect any other context. "
        command[-1] = instruction + command[-1]
        try:
            result = subprocess.run(command, cwd=work, env=environment, capture_output=True, text=True, timeout=args.timeout)
            (root / f"{stage}-{host}.stdout").write_text(result.stdout)
            (root / f"{stage}-{host}.stderr").write_text(result.stderr)
            if result.returncode:
                raise RuntimeError(f"{host} {stage} exited {result.returncode}; see isolated evidence")
        except subprocess.TimeoutExpired as error:
            raise RuntimeError(f"{host} {stage} timed out after {args.timeout}s") from error
        print(json.dumps({"host": host, "stage": stage, "process": "completed"}), flush=True)

    def parallel(stage: str, prompts: dict[str, str]) -> None:
        with ThreadPoolExecutor(max_workers=2) as pool:
            jobs = [pool.submit(invoke, host, stage, prompt) for host, prompt in prompts.items()]
            for job in jobs:
                job.result()

    try:
        parallel("write", {host: f'Call remember once with content "{marker} {host} selected reversible migrations", scope "project", project_id "{project_id}", source_uri "synthetic://host-gate/{marker}/{host}". Report the tool result.' for host in hosts})
        memories = {str(memory["source_uri"]): memory for memory in store.list_memories(limit=20)}
        for host in hosts:
            assert f"synthetic://host-gate/{marker}/{host}" in memories, f"{host} did not store memory"
        parallel("read", {host: f'Call recall with query "{marker}", purpose "synthetic peer handoff", project_id "{project_id}", max_tokens 600. Report the returned memory IDs and sources verbatim.' for host in hosts})
        logs = store.list_logs(limit=100)
        for host in hosts:
            assert any(log["client_id"] == host and len(log["memory_ids"]) == 2 for log in logs), f"{host} failed peer recall"
        store.revoke_project("codex", project_id)
        invoke("codex", "revoked", f'Call recall once with query "{marker}", purpose "verify immediate revocation", project_id "{project_id}". Report the tool result even if empty.')
        assert store.list_logs(limit=1)[0]["memory_ids"] == [], "Revoked host disclosed memory"
        invoke("claude-code", "continuity", f'Call recall once with query "{marker}", purpose "verify peer continuity", project_id "{project_id}". Report the tool result.')
        assert len(store.list_logs(limit=1)[0]["memory_ids"]) == 2, "Remaining host lost continuity"
        print(json.dumps({"status": "pass", "memories": len(memories), "disclosures": len(store.list_logs(limit=100)), "evidence_dir": str(root)}), flush=True)
        return 0
    except (RuntimeError, AssertionError) as error:
        print(json.dumps({"status": "fail", "reason": str(error), "evidence_dir": str(root)}), flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
