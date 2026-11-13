#!/usr/bin/env python3
"""Launch a real frozen app over a synthetic prior-version vault; never user data.

This smoke checks data preservation and startup, not Gatekeeper or visual acceptance.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PRIOR = "8eb5224ce2c7023ad52ad42e7563c446c10e3b3f"


def snapshot(database: Path) -> dict:
    with sqlite3.connect(f"file:{database}?mode=ro", uri=True) as db:
        result = {}
        for table in ("memories", "permissions", "access_logs", "settings", "projects", "project_permissions"):
            result[table] = db.execute(f'SELECT * FROM "{table}" ORDER BY rowid').fetchall()
        return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("app", type=Path)
    args = parser.parse_args()
    executable = args.app.resolve() / "Contents/MacOS/Ninai"
    if sys.platform != "darwin" or not executable.is_file():
        parser.error("Run on macOS with a built Ninai.app")
    with tempfile.TemporaryDirectory(prefix="ninai-old-new-") as temporary:
        fixture = Path(temporary)
        archive = fixture / "prior.tar"
        with archive.open("wb") as stream:
            subprocess.run(["git", "archive", PRIOR, "engine/src"], cwd=ROOT, stdout=stream, check=True)
        with tarfile.open(archive) as tar:
            tar.extractall(fixture, filter="data")
        env = dict(os.environ, HOME=str(fixture / "home"), NINAI_DATA_DIR=str(fixture / "Private vault"), PYTHONPATH=str(fixture / "engine/src"))
        Path(env["HOME"]).mkdir()
        # Use prior source for the fixture, not the current MemoryStore.
        seed = """
from ninai.store import MemoryStore
s = MemoryStore()
s.remember('Installer smoke fixture survives upgrade', source_uri='fixture://mac/prior')
s.grant('codex', 'project')
p = s.ensure_project(name='Prior project', binding_key='fixture://mac/project', cwd_or_repo='/synthetic/prior')
s.grant_project('codex', p['id'])
s.remember('Project fixture survives upgrade', project_id=p['id'], source_uri='fixture://mac/project-memory')
s.set_capture_enabled(False)
s.recall('Installer smoke', client_id='codex', purpose='prior-version-fixture', max_tokens=500)
"""
        subprocess.run([sys.executable, "-c", seed], cwd=fixture, env=env, check=True)
        database = Path(env["NINAI_DATA_DIR"]) / "ninai.sqlite3"
        before = snapshot(database)
        assert before["memories"] and before["permissions"] and before["access_logs"] and before["projects"] and before["project_permissions"]
        env.pop("PYTHONPATH")
        with (fixture / "app.log").open("w+") as log:
            process = subprocess.Popen([str(executable)], cwd=fixture, env=env, stdout=log, stderr=log)
            try:
                try:
                    code = process.wait(timeout=12)
                    raise RuntimeError(f"Frozen app exited early ({code})")
                except subprocess.TimeoutExpired:
                    pass
                log.flush()
                log.seek(0)
                output = log.read()
                if "Opening Ninai" not in output:
                    raise RuntimeError(f"App did not reach native window startup: {output[-2000:]}")
                after = snapshot(database)
                for table, rows in before.items():
                    if after[table] != rows:
                        raise AssertionError(f"Prior fixture changed in {table}")
                print(json.dumps({"passed": True, "prior_commit": PRIOR, "app": str(args.app.resolve()), "checks": ["prior-source 0.1.0 vault", "native frozen app stayed running 12s", "memories/provenance", "permissions", "audit history", "capture setting", "projects"], "limits": "ad-hoc startup/data smoke; no signed trust, visual or assistant-host acceptance"}, indent=2))
            finally:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=8)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=5)


if __name__ == "__main__":
    main()
