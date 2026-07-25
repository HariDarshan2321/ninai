from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "verify_postgres_restore", ROOT / "scripts/verify_postgres_restore.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class _Result:
    def __init__(self, rows):
        self.rows = rows

    def fetchall(self):
        return self.rows

    def fetchone(self):
        return self.rows[0]


class _Connection:
    def __init__(self, *, missing_table: str | None = None):
        self.missing_table = missing_table
        self.queries: list[str] = []

    def execute(self, query, params=None):
        self.queries.append(query)
        if query == "SET TRANSACTION READ ONLY":
            return _Result([])
        if query == "SELECT to_regclass(%s)":
            table = params[0].removeprefix("public.")
            return _Result([(None if table == self.missing_table else params[0],)])
        if query.startswith("SELECT version"):
            return _Result([(path.stem,) for path in MODULE.migration_files()])
        if query.startswith("SELECT count(*)"):
            return _Result([(3,)])
        raise AssertionError(f"unexpected query: {query}")


class RestoreVerifierTests(unittest.TestCase):
    def test_valid_restore_is_checked_read_only(self) -> None:
        connection = _Connection()
        report = MODULE.inspect_restore(connection)

        self.assertEqual(report["status"], "ok")
        self.assertEqual(connection.queries[0], "SET TRANSACTION READ ONLY")
        self.assertFalse(any(query.lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE")) for query in connection.queries))

    def test_missing_table_fails_report(self) -> None:
        report = MODULE.inspect_restore(_Connection(missing_table="memories"))
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["missing_tables"], ["memories"])

    def test_missing_migration_table_is_reported_without_querying_it(self) -> None:
        connection = _Connection(missing_table="schema_migrations")
        report = MODULE.inspect_restore(connection)
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["missing_tables"], ["schema_migrations"])
        self.assertFalse(any(query.startswith("SELECT version") for query in connection.queries))


if __name__ == "__main__":
    unittest.main()
