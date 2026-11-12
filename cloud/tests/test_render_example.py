from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("validate_render_example", ROOT / "scripts" / "validate_render_example.py")
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)
EXAMPLE = json.loads((ROOT / "cloud" / "render.example.yaml").read_text())


class RenderExamplePolicyTest(unittest.TestCase):
    def test_optional_example_meets_local_safeguards(self):
        validator.validate_policy(EXAMPLE)
        self.assertFalse((ROOT / "render.yaml").exists(), "Do not make the optional billable example auto-applied")

    def test_unsafe_deployment_variants_are_rejected(self):
        variants = [
            ("free web service", lambda d: d["services"][0].update(plan="free")),
            ("free database", lambda d: d["databases"][0].update(plan="free")),
            ("process-only health", lambda d: d["services"][0].update(healthCheckPath="/health")),
            ("ungated deployment", lambda d: d["services"][0].update(autoDeployTrigger="commit")),
            ("public database", lambda d: d["databases"][0].update(ipAllowList=[{"source": "0.0.0.0/0"}])),
            ("cross-region database", lambda d: d["databases"][0].update(region="oregon")),
            ("local disk mount", lambda d: d["services"][0].update(disk={"name": "vault", "mountPath": "/local"})),
            ("extra billable resources", lambda d: d.update(projects=[{"name": "extra"}])),
            ("production name reuse", lambda d: d["services"][0].update(name="ninai-cloud")),
        ]
        for name, mutate in variants:
            document = deepcopy(EXAMPLE)
            mutate(document)
            with self.subTest(variant=name), self.assertRaises(ValueError):
                validator.validate_policy(document)

    def test_plaintext_credentials_and_auth_downgrades_are_rejected(self):
        variants = [
            ("DATABASE_URL", {"value": "postgresql://example.invalid/not-a-real-credential"}),
            ("NINAI_AUTH_MODE", {"value": "pat"}),
            ("NINAI_OAUTH_ALLOW_PAT", {"value": "true"}),
            ("NINAI_OAUTH_ISSUER", {"value": "https://example.invalid/"}),
            ("NINAI_OAUTH_ISSUER", {"sync": 0}),
        ]
        for key, replacement in variants:
            document = deepcopy(EXAMPLE)
            variables = document["services"][0]["envVars"]
            variables[:] = [{"key": key, **replacement} if item["key"] == key else item for item in variables]
            with self.subTest(key=key, replacement=replacement), self.assertRaises(ValueError):
                validator.validate_policy(document)


if __name__ == "__main__":
    unittest.main()
