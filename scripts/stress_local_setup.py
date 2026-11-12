#!/usr/bin/env python3
"""Bounded concurrent local setup regression; disposable synthetic SQLite only.

Run with Ninai's installed Python interpreter. This exercises real database
connections, not model calls or authenticated editor applications. Timing is
local diagnostic evidence, not a production capacity benchmark.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import json
import math
from pathlib import Path
import sqlite3
import tempfile
from threading import Barrier
import time

from ninai.store import MemoryStore


def latency_summary(samples: list[float]) -> dict[str, float | int]:
    ordered = sorted(samples)
    return {
        "count": len(ordered),
        "p50_ms": round(ordered[math.ceil(len(ordered) * .50) - 1] * 1000, 3),
        "p95_ms": round(ordered[math.ceil(len(ordered) * .95) - 1] * 1000, 3),
        "max_ms": round(ordered[-1] * 1000, 3),
    }


def run_stress(*, workers: int, operations: int, timeout_seconds: float) -> dict[str, object]:
    """An operation is one bounded scenario; revocation contains multiple calls."""
    started = time.monotonic()
    deadline = started + timeout_seconds
    budget = 400

    def require(condition: bool, message: str) -> None:
        if not condition:
            raise AssertionError(message)

    def check_deadline() -> None:
        if time.monotonic() >= deadline:
            raise TimeoutError("Configured stress duration exceeded")

    with tempfile.TemporaryDirectory(prefix="ninai-local-stress-") as directory:
        path = Path(directory) / "synthetic.sqlite3"
        # Start from the pre-project schema, rather than testing only a fresh
        # current database. Each worker must survive the same real migration.
        with sqlite3.connect(path) as db:
            db.execute("""CREATE TABLE memories(id TEXT PRIMARY KEY,content TEXT NOT NULL,
                memory_type TEXT NOT NULL,scope TEXT NOT NULL,source_uri TEXT NOT NULL,
                importance REAL NOT NULL,confidence REAL NOT NULL,created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,access_count INTEGER NOT NULL DEFAULT 0,deleted_at TEXT)""")
            db.execute("INSERT INTO memories VALUES(?,?,?,?,?,?,?,?,?,?,?)", (
                "legacy-record", "Preserve this synthetic legacy decision", "decision",
                "project", "synthetic://stress/legacy", 1, 1,
                "2026-01-01T00:00:00+00:00", "2026-01-01T00:00:00+00:00", 0, None,
            ))
        startup_barrier = Barrier(workers)

        def open_legacy_database(_):
            startup_barrier.wait(timeout=timeout_seconds)
            check_deadline()
            tick = time.monotonic()
            store = MemoryStore(path)
            require(store.explain("legacy-record")["project_id"] is None, "Legacy record moved into a named project")
            return store, time.monotonic() - tick

        with ThreadPoolExecutor(max_workers=workers) as pool:
            opened = list(pool.map(open_legacy_database, range(workers)))
        stores = [item[0] for item in opened]
        owner = stores[0]
        projects = [owner.ensure_project(name=name, binding_key=f"synthetic://stress/{name}", cwd_or_repo="")["id"] for name in ("alpha", "beta")]
        for index, project in enumerate(projects):
            label = ("alpha", "beta")[index]
            owner.remember(f"STRESS_{label.upper()} Keep migrations reversible", project_id=project, source_uri=f"synthetic://stress/{label}/seed")
        for worker in range(workers):
            for client in (f"stress-worker-{worker}", f"stress-revoke-{worker}"):
                owner.grant_project(client, projects[worker % 2], "read")
            owner.grant_project(f"stress-worker-{worker}", projects[worker % 2], "write")
        work_barrier = Barrier(workers)

        def verify_packet(packet, project, label):
            require(0 <= packet["estimated_tokens"] <= budget, "Recall exceeded estimated token budget")
            require(bool(packet["facts"]), "Granted project recall unexpectedly empty")
            for fact in packet["facts"]:
                require(fact.get("project_id") == project, "Cross-project memory disclosed")
                require(fact["source_uri"].startswith(f"synthetic://stress/{label}/"), "Provenance lost or crossed projects")
                require(f"STRESS_{label.upper()}" in fact["content"], "Returned content belongs to a different project")

        def scenarios(worker):
            store = stores[worker]
            own_index = worker % 2
            own, other = projects[own_index], projects[1 - own_index]
            label = ("alpha", "beta")[own_index]
            other_label = ("beta", "alpha")[own_index]
            client, probe = f"stress-worker-{worker}", f"stress-revoke-{worker}"
            counts = Counter()
            timings = defaultdict(list)
            work_barrier.wait(timeout=timeout_seconds)
            for step, index in enumerate(range(worker, operations, workers)):
                check_deadline()
                tick = time.monotonic()
                kind = ("write", "recall", "cross_project_denied", "revoke_and_regrant", "cross_project_write_denied")[step % 5]
                source = f"synthetic://stress/{label}/worker-{worker}/operation-{index}"
                if kind == "write":
                    memory = store.remember(f"STRESS_{label.upper()} Decision {index}: keep changes reversible", project_id=own, client_id=client, source_uri=source)
                    require(memory.project_id == own and memory.source_uri == source, "Saved record lost project or source")
                elif kind == "recall":
                    verify_packet(store.recall(f"STRESS_{label.upper()}", client_id=client, project_id=own, purpose="concurrent recall", max_tokens=budget), own, label)
                elif kind == "cross_project_denied":
                    packet = store.recall(f"STRESS_{other_label.upper()}", client_id=client, project_id=other, purpose="concurrent isolation denial", max_tokens=budget)
                    require(packet["facts"] == [] and packet["scopes"] == [], "Unpermitted project returned memory")
                elif kind == "revoke_and_regrant":
                    verify_packet(store.recall(f"STRESS_{label.upper()}", client_id=probe, project_id=own, purpose="before revocation", max_tokens=budget), own, label)
                    # No request for this client is started before revoke returns.
                    # Other clients keep operating concurrently throughout.
                    store.revoke_project(probe, own, "read")
                    packet = store.recall(f"STRESS_{label.upper()}", client_id=probe, project_id=own, purpose="after completed revocation", max_tokens=budget)
                    require(packet["facts"] == [] and packet["scopes"] == [], "Request after completed revocation disclosed memory")
                    require(store.project_setup_status(own, probe)["revocation_verified"], "Real denied request failed to verify revocation")
                    store.grant_project(probe, own, "read")
                    require(not store.project_setup_status(own, probe)["revocation_verified"], "Regrant left stale revocation proof")
                else:
                    denied_source = source + "/forbidden"
                    try:
                        store.remember(f"STRESS_{other_label.upper()} forbidden write", project_id=other, client_id=client, source_uri=denied_source)
                    except PermissionError:
                        pass
                    else:
                        raise AssertionError("Unpermitted cross-project write succeeded")
                    require(store.get_by_source_uri(denied_source) is None, "Denied write persisted a memory")
                counts[kind] += 1
                timings[kind].append(time.monotonic() - tick)
            return counts, timings

        with ThreadPoolExecutor(max_workers=workers) as pool:
            results = list(pool.map(scenarios, range(workers)))
        counts = Counter()
        timings = defaultdict(list)
        for worker_counts, worker_timings in results:
            counts.update(worker_counts)
            for kind, values in worker_timings.items():
                timings[kind].extend(values)
        require(sum(counts.values()) == operations, "Workload did not complete")
        check_deadline()
        with closing(owner.connect()) as db:
            require(db.execute("PRAGMA quick_check").fetchone()[0] == "ok", "SQLite integrity check failed")
            require(not db.execute("PRAGMA foreign_key_check").fetchall(), "Foreign-key integrity check failed")
            memory_count = db.execute("SELECT count(*) FROM memories").fetchone()[0]
            log_count = db.execute("SELECT count(*) FROM access_logs").fetchone()[0]
        require(memory_count == 3 + counts["write"], "Concurrent writes lost, duplicated, or created unauthorized records")
        expected_logs = counts["recall"] + counts["cross_project_denied"] + 2 * counts["revoke_and_regrant"]
        require(log_count == expected_logs, "Disclosure audit lost or duplicated requests")
        return {
            "passed": True,
            "boundary": "Disposable local SQLite regression; no model calls, host authentication, or production capacity claim",
            "workers": workers, "scenario_operations": operations,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "database_errors": 0, "isolation_failures": 0,
            "database_errors_note": "No surfaced database errors; successfully recovered startup lock contention is not counted",
            "persisted_memories": memory_count, "disclosure_logs": log_count,
            "completed_scenarios": dict(counts),
            "local_scenario_latencies": {"legacy_startup": latency_summary([item[1] for item in opened]), **{kind: latency_summary(values) for kind, values in sorted(timings.items())}},
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--operations", type=int, default=1000, help="Total scenarios across all workers")
    parser.add_argument("--timeout-seconds", type=float, default=45)
    args = parser.parse_args()
    if not 1 <= args.workers <= 32:
        parser.error("workers must be between 1 and 32")
    if not args.workers * 5 <= args.operations <= 100000:
        parser.error("operations must be at least workers × 5 and at most 100000")
    if not 1 <= args.timeout_seconds <= 120:
        parser.error("timeout-seconds must be between 1 and 120")
    try:
        print(json.dumps(run_stress(workers=args.workers, operations=args.operations, timeout_seconds=args.timeout_seconds), indent=2))
        return 0
    except Exception as error:
        print(json.dumps({"passed": False, "error_type": type(error).__name__, "reason": str(error)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
