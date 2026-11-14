"""Set package version in a generated PyInstaller spec before it is signed."""
from __future__ import annotations

import argparse
import ast
from pathlib import Path
import re

from ninai import __version__


def set_bundle_version(path: Path, version: str) -> None:
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("A numeric three-part macOS bundle version is required")
    tree = ast.parse(path.read_text())
    bundles = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
               and isinstance(node.func, ast.Name) and node.func.id == "BUNDLE"]
    if len(bundles) != 1:
        raise ValueError("Expected exactly one generated macOS BUNDLE")
    bundle = bundles[0]
    keywords = {keyword.arg: keyword for keyword in bundle.keywords}
    if "version" in keywords:
        keywords["version"].value = ast.Constant(version)
    else:
        bundle.keywords.append(ast.keyword(arg="version", value=ast.Constant(version)))
    plist = keywords.get("info_plist")
    if plist is None:
        plist = ast.keyword(arg="info_plist", value=ast.Dict(keys=[], values=[]))
        bundle.keywords.append(plist)
    if not isinstance(plist.value, ast.Dict):
        raise ValueError("Expected literal generated bundle metadata")
    for name in ("CFBundleVersion", "CFBundleShortVersionString"):
        for index, key in enumerate(plist.value.keys):
            if isinstance(key, ast.Constant) and key.value == name:
                plist.value.values[index] = ast.Constant(version)
                break
        else:
            plist.value.keys.append(ast.Constant(name))
            plist.value.values.append(ast.Constant(version))
    ast.fix_missing_locations(tree)
    path.write_text(ast.unparse(tree) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", type=Path)
    set_bundle_version(parser.parse_args().spec, __version__)
