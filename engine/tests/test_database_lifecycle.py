from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ninai.store import MemoryStore


class DatabaseLifecycleTest(unittest.TestCase):
    def test_another_connection_removing_sidecars_does_not_break_open(self):
        real_chmod = os.chmod
        def chmod(path, mode):
            if str(path).endswith(('-wal', '-shm')):
                raise FileNotFoundError('SQLite closed its final connection')
            return real_chmod(path, mode)
        with tempfile.TemporaryDirectory() as folder, patch('ninai.store.os.chmod', side_effect=chmod):
            store = MemoryStore(Path(folder) / 'memory.sqlite3')
            self.assertEqual(store.owner_memory_count(), 0)

    def test_genuine_permission_failures_are_not_silenced(self):
        real_chmod = os.chmod
        def chmod(path, mode):
            if str(path).endswith(('-wal', '-shm')):
                raise PermissionError('Cannot protect database sidecar')
            return real_chmod(path, mode)
        with tempfile.TemporaryDirectory() as folder, patch('ninai.store.os.chmod', side_effect=chmod):
            with self.assertRaises(PermissionError):
                MemoryStore(Path(folder) / 'memory.sqlite3')
