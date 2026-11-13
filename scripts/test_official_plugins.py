"""Regression checks for distribution boundaries, not hosted runtime acceptance."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from shutil import copytree
from zipfile import ZipFile

SPEC = importlib.util.spec_from_file_location('build_official_plugins', Path(__file__).with_name('build_official_plugins.py'))
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


class OfficialPluginPackagingTests(unittest.TestCase):
    def test_archives_are_reproducible_and_host_specific(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            builder.build(output)
            first = {p.name:p.read_bytes() for p in output.glob('*.zip')}
            builder.build(output)
            self.assertEqual(first, {p.name:p.read_bytes() for p in output.glob('*.zip')})
            for name, contents in first.items():
                with ZipFile(output/name) as archive:
                    names = archive.namelist()
                    self.assertIn('skills/project-continuity/SKILL.md', names)
                    self.assertIn('assets/ninai-app-icon.png', names)
                    if 'openai' in name:
                        self.assertIn('plugin.json', names)
                        self.assertIn('mcp.json', names)
                        self.assertNotIn('.claude-plugin/plugin.json', names)
                    else:
                        self.assertIn('.claude-plugin/plugin.json', names)
                        self.assertNotIn('plugin.json', names)
                        self.assertNotIn('mcp.json', names)
                        self.assertNotIn('.codex-plugin/plugin.json', names)

    def test_rejects_credentials_and_escaped_icon_paths(self):
        for mutation in ('credential', 'path'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as tmp:
                plugin = Path(tmp)/'ninai'
                copytree(builder.PLUGIN, plugin)
                path = plugin/'plugin.json'
                document = json.loads(path.read_text())
                if mutation == 'credential':
                    document['clientSecret'] = 'synthetic-test-value'
                else:
                    for relative in ('plugin.json','.codex-plugin/plugin.json'):
                        manifest_path = plugin/relative
                        manifest = json.loads(manifest_path.read_text())
                        interface = manifest['extensions']['com.openai']['interface'] if relative == 'plugin.json' else manifest['interface']
                        interface['logo'] = './../outside.svg'
                        manifest_path.write_text(json.dumps(manifest))
                    document = json.loads(path.read_text())
                path.write_text(json.dumps(document))
                with self.assertRaises(ValueError):
                    builder.validate(plugin)

    def test_rejects_symlink_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            plugin = Path(tmp)/'ninai'
            copytree(builder.PLUGIN, plugin)
            (plugin/'copied.md').symlink_to(plugin/'README.md')
            with self.assertRaisesRegex(ValueError,'Symlink'):
                builder.validate(plugin)


if __name__ == '__main__':
    unittest.main()
