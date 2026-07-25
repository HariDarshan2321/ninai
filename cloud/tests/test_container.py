from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ContainerDeploymentTests(unittest.TestCase):
    def test_image_runs_migrations_before_service_as_non_root(self) -> None:
        dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
        entrypoint = (ROOT / "docker-entrypoint.sh").read_text(encoding="utf-8")

        self.assertIn("USER 10001:10001", dockerfile)
        self.assertIn("HEALTHCHECK", dockerfile)
        self.assertIn('ENTRYPOINT ["ninai-cloud-entrypoint"]', dockerfile)
        self.assertIn("python -m ninai_cloud.migrations", entrypoint)
        self.assertIn('exec "$@"', entrypoint)
        self.assertLess(
            entrypoint.index("python -m ninai_cloud.migrations"),
            entrypoint.index('exec "$@"'),
        )

    def test_migration_runner_serializes_replica_startup(self) -> None:
        migrations = (ROOT / "src/ninai_cloud/migrations.py").read_text(encoding="utf-8")
        self.assertIn("pg_advisory_xact_lock", migrations)


if __name__ == "__main__":
    unittest.main()
