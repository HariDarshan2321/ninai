from __future__ import annotations

import unittest
from importlib.resources import files
from pathlib import Path


class InstallerAssetTest(unittest.TestCase):
    def test_packaged_installer_matches_canonical_script(self) -> None:
        root = Path(__file__).resolve().parents[2]
        canonical = (root / "scripts" / "install-local").read_bytes()
        packaged = files("ninai_cloud.assets").joinpath("install-ninai-macos.sh").read_bytes()
        self.assertEqual(
            packaged,
            canonical,
            "cloud installer asset drifted; sync it from scripts/install-local",
        )


if __name__ == "__main__":
    unittest.main()
