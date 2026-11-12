from __future__ import annotations

from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from ninai.store import MemoryStore


class ConnectionStartupTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.store = MemoryStore(Path(self.directory.name) / "synthetic.sqlite3")

    def tearDown(self):
        self.directory.cleanup()

    def test_initial_wal_lock_can_recover_without_reopening_the_database(self):
        connection = MagicMock()
        attempts = 0

        def execute(sql):
            nonlocal attempts
            if sql == "PRAGMA journal_mode=WAL":
                attempts += 1
                if attempts < 3:
                    error = sqlite3.OperationalError("database is locked")
                    error.sqlite_errorcode = sqlite3.SQLITE_BUSY
                    raise error

        connection.execute.side_effect = execute
        with (
            patch("ninai.store.sqlite3.connect", return_value=connection) as connect,
            patch("ninai.store.time.monotonic", side_effect=[0, 0, .1, .2, .3, .4]),
            patch("ninai.store.time.sleep"),
        ):
            self.assertIs(self.store.connect(), connection)
        connect.assert_called_once()
        self.assertEqual(attempts, 3)
        connection.close.assert_not_called()
        statements = [call.args[0] for call in connection.execute.call_args_list]
        self.assertEqual(statements[0], "PRAGMA busy_timeout=5000")
        self.assertIn("PRAGMA busy_timeout=4800", statements)
        self.assertIn("PRAGMA busy_timeout=4600", statements)

    def test_persistent_wal_lock_expires_and_closes_failed_connection(self):
        connection = MagicMock()
        error = sqlite3.OperationalError("database is locked")
        error.sqlite_errorcode = sqlite3.SQLITE_BUSY

        def execute(sql):
            if sql == "PRAGMA journal_mode=WAL":
                raise error

        connection.execute.side_effect = execute
        with (
            patch("ninai.store.sqlite3.connect", return_value=connection),
            patch("ninai.store.time.monotonic", side_effect=[10, 10, 15.1]),
            patch("ninai.store.time.sleep") as sleep,
        ):
            with self.assertRaises(sqlite3.OperationalError):
                self.store.connect()
        sleep.assert_not_called()
        connection.close.assert_called_once()

    def test_io_and_corruption_errors_are_not_retried_as_contention(self):
        for error in (sqlite3.OperationalError("disk I/O error"), sqlite3.DatabaseError("database disk image is malformed")):
            connection = MagicMock()

            def execute(sql, problem=error):
                if sql == "PRAGMA journal_mode=WAL":
                    raise problem

            connection.execute.side_effect = execute
            with (
                self.subTest(error=str(error)),
                patch("ninai.store.sqlite3.connect", return_value=connection),
                patch("ninai.store.time.sleep") as sleep,
            ):
                with self.assertRaises(type(error)):
                    self.store.connect()
            sleep.assert_not_called()
            connection.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
