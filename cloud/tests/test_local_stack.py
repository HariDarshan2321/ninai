from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]

class LocalHostedStackTests(unittest.TestCase):
    def test_compose_orders_migration_and_health_without_local_vault_mount(self) -> None:
        compose = (ROOT / "compose.yaml").read_text(encoding="utf-8")
        self.assertIn("service_completed_successfully", compose)
        self.assertIn('"ninai_cloud.migrations"', compose)
        self.assertIn("NINAI_AUTH_MODE: pat", compose)
        self.assertIn("NINAI_PUBLIC_RESOURCE_URL:-http://localhost:", compose)
        self.assertIn("/health", compose)
        active = "\n".join(line for line in compose.splitlines() if not line.lstrip().startswith("#"))
        self.assertNotIn(".ninai", active)

    def test_helper_exposes_lifecycle_checks_and_bootstrap(self) -> None:
        helper = (ROOT / "scripts" / "ninai-cloud-local").read_text(encoding="utf-8")
        for value in ("setup|start", "doctor)", "bootstrap)", "schema_migrations"):
            self.assertIn(value, helper)

if __name__ == "__main__":
    unittest.main()
