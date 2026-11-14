import ast
from pathlib import Path
import tempfile
import unittest

from ninai.desktop.bundle_spec import set_bundle_version


class BundleMetadataTest(unittest.TestCase):
    def test_versions_are_set_before_signing_without_changing_other_settings(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "Ninai.spec"
            path.write_text("exe = EXE(codesign_identity='owner identity')\napp = BUNDLE(exe, version='0.0.0', info_plist={'NSHighResolutionCapable': True})\n")
            set_bundle_version(path, "0.1.2")
            tree = ast.parse(path.read_text())
            bundle = tree.body[1].value
            values = {item.arg: ast.literal_eval(item.value) for item in bundle.keywords}
            self.assertEqual(values['version'], '0.1.2')
            self.assertEqual(values['info_plist'], {'NSHighResolutionCapable': True, 'CFBundleVersion': '0.1.2', 'CFBundleShortVersionString': '0.1.2'})
            self.assertIn("codesign_identity='owner identity'", path.read_text())

    def test_missing_bundle_is_rejected_without_rewriting_spec(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "Ninai.spec"
            original = "exe = EXE()\n"
            path.write_text(original)
            with self.assertRaises(ValueError):
                set_bundle_version(path, '0.1.2')
            self.assertEqual(path.read_text(), original)
