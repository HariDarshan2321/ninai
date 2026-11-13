"""The webview bridge must expose only defensive desktop API methods."""
from __future__ import annotations

import ast
import importlib.util
import inspect
import io
import json
import logging
from pathlib import Path
import sys
import tempfile
import traceback
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from ninai.desktop import app
from ninai.desktop.api import DesktopApi
from ninai.governance import OwnerVerificationAuthority
from ninai.store import MemoryStore


class DesktopBridgeBoundaryTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.store = MemoryStore(Path(temporary.name) / "vault.sqlite3")
        self.api = DesktopApi(self.store, owner_verifier=lambda _: False)

    def launch_fake_window(self):
        window = SimpleNamespace(_functions={}, evaluate_js=Mock())

        def create_window(*args, **kwargs):
            window._js_api = kwargs["js_api"]
            return window

        def expose(*methods):
            window._functions.update({method.__name__: method for method in methods})

        window.expose = Mock(side_effect=expose)
        webview = SimpleNamespace(create_window=Mock(side_effect=create_window), start=Mock())
        with patch.dict(sys.modules, {"webview": webview}), \
                patch.object(app, "DesktopApi", return_value=self.api), \
                patch.object(app, "_configure_macos_app"), \
                patch("sys.stdout", new=io.StringIO()):
            app.main()
        return window, webview

    def test_launch_exposes_only_explicit_flat_methods_without_owner_object(self):
        window, webview = self.launch_fake_window()
        self.assertIsNone(webview.create_window.call_args.kwargs["js_api"])
        self.assertIsNone(window._js_api)
        self.assertEqual(len(app.BRIDGE_METHODS), len(set(app.BRIDGE_METHODS)))
        self.assertEqual(set(window._functions), set(app.BRIDGE_METHODS))
        for name, method in window._functions.items():
            with self.subTest(method=name):
                self.assertNotIn(".", name)
                self.assertFalse(name.startswith("_"))
                self.assertIs(method.__self__, self.api)
        window.expose.assert_called_once()
        webview.start.assert_called_once_with()

    def pywebview_source(self):
        spec = importlib.util.find_spec("webview")
        if spec is None or not spec.submodule_search_locations:
            self.skipTest("Optional pywebview dependency is not installed")
        return Path(next(iter(spec.submodule_search_locations))) / "util.py"

    def test_public_bridge_has_no_raw_owner_objects_or_nested_api(self):
        # pywebview recursively exposes public object attributes, not just the
        # methods declared on DesktopApi. A public store bypasses verification.
        for name in dir(self.api):
            if name.startswith("_"):
                continue
            value = getattr(self.api, name)
            with self.subTest(attribute=name):
                self.assertNotIsInstance(value, (MemoryStore, OwnerVerificationAuthority))
                self.assertTrue(inspect.ismethod(value), "Only desktop wrapper methods may be public")
                self.assertIs(value.__self__, self.api)
                self.assertEqual(inspect.signature(value).return_annotation, "dict[str, Any]")

    def test_installed_pywebview_exports_only_desktop_wrappers(self):
        # Exercise the installed framework's actual exporter when the optional
        # desktop dependency exists. Extract its nested pure helpers without
        # starting a GUI or duplicating the framework's traversal algorithm.
        source = self.pywebview_source()
        module = ast.parse(source.read_text(encoding="utf-8"))
        inject = next(node for node in module.body
                      if isinstance(node, ast.FunctionDef) and node.name == "inject_pywebview")
        helpers = [node for node in inject.body
                   if isinstance(node, ast.FunctionDef) and node.name in {"get_args", "get_functions"}]
        self.assertEqual({node.name for node in helpers}, {"get_args", "get_functions"},
                         "pywebview exporter changed; review its bridge exposure behavior")
        namespace = {"inspect": inspect, "exposed_objects": [], "logger": logging.getLogger(__name__)}
        exec(compile(ast.Module(body=helpers, type_ignores=[]), str(source), "exec"), namespace)
        exported = namespace["get_functions"](self.api)
        wrappers = {name for name, value in inspect.getmembers(self.api, inspect.ismethod)
                    if not name.startswith("_")}
        self.assertEqual(set(exported), wrappers)
        self.assertFalse(any("." in name for name in exported))

    def test_installed_dispatcher_cannot_resolve_raw_owner_or_private_paths(self):
        source = self.pywebview_source()
        module = ast.parse(source.read_text(encoding="utf-8"))
        dispatcher = next(node for node in module.body
                          if isinstance(node, ast.FunctionDef) and node.name == "js_bridge_call")

        class ImmediateThread:
            def __init__(self, target):
                self.target = target

            def start(self):
                self.target()

        logger = Mock()
        namespace = {"json": json, "traceback": traceback, "Thread": ImmediateThread, "logger": logger}
        exec(compile(ast.Module(body=[dispatcher], type_ignores=[]), str(source), "exec"), namespace)
        dispatch = namespace["js_bridge_call"]
        window, _ = self.launch_fake_window()
        project = self.store.ensure_project(name="Alpha", binding_key="alpha", cwd_or_repo="")
        for name in ("store.grant_project", "_store.grant_project",
                     "_approval_authority.verify", "set_project_permission.__self__._store.grant_project"):
            with self.subTest(path=name):
                window.evaluate_js.reset_mock()
                dispatch(window, name, ["codex", project["id"], "delete"], "test")
                window.evaluate_js.assert_not_called()
                self.assertEqual(self.store.project_permissions("codex"), [])
        self.assertEqual(logger.error.call_count, 4)
        # Flat bound methods receive the actual supplied arguments unchanged;
        # verification failure still blocks the legitimate approval wrapper.
        dispatch(window, "set_project_permission", ["codex", project["id"], "delete", True], "test")
        window.evaluate_js.assert_called_once()
        response = window.evaluate_js.call_args.args[0]
        self.assertIn("Owner verification was not completed", response)
        self.assertNotIn("isError", response)
        self.assertEqual(self.store.project_permissions("codex"), [])


if __name__ == "__main__":
    unittest.main()
