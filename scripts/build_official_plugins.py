#!/usr/bin/env python3
"""Validate Ninai package policy and build reproducible host-specific ZIPs.

This local check is not an official directory scan, approval, or runtime test.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
from pathlib import Path
from urllib.parse import urlsplit
from xml.etree import ElementTree
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / 'plugins' / 'ninai'


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def local_file(plugin: Path, value: str) -> Path:
    require(value.startswith('./'), f'Path must start with ./: {value}')
    path = plugin / value
    require(path.resolve().is_relative_to(plugin.resolve()), f'Path escapes plugin: {value}')
    require(path.is_file() and not path.is_symlink(), f'Missing regular file: {value}')
    return path


def luminance(color: str) -> float:
    values = [int(color[i:i+2], 16)/255 for i in (1, 3, 5)]
    values = [v/12.92 if v <= .04045 else ((v+.055)/1.055)**2.4 for v in values]
    return sum(v*w for v, w in zip(values, (.2126, .7152, .0722)))


def contrast(a: str, b: str) -> float:
    x, y = sorted((luminance(a), luminance(b)))
    return (y+.05)/(x+.05)


def validate(plugin: Path = PLUGIN) -> tuple[dict, list[Path]]:
    portable = read_json(plugin/'plugin.json')
    codex = read_json(plugin/'.codex-plugin/plugin.json')
    claude = read_json(plugin/'.claude-plugin/plugin.json')
    for manifest in (portable, codex, claude):
        require(manifest['name'] == 'ninai', 'Stable identity must remain ninai')
        require(re.fullmatch(r'\d+\.\d+\.\d+', manifest['version']) is not None, 'Invalid version')
        require(manifest['version'] == portable['version'], 'Versions differ')
        require(manifest['license'] == 'MIT', 'License mismatch')
    extension = portable['extensions']['com.openai']
    interface = extension['interface']
    require(interface == codex['interface'], 'Codex presentation diverges')
    for key, maximum in [('displayName',30),('shortDescription',30),('longDescription',4000),('developerName',80)]:
        require(isinstance(interface[key],str) and 0 < len(interface[key]) <= maximum, f'Invalid {key}')
    require(interface['category'] == 'Productivity', 'Unexpected category')
    require(len(interface['capabilities']) <= 20, 'Too many capabilities')
    require(all(isinstance(x,str) and 0 < len(x) <= 120 for x in interface['capabilities']), 'Invalid capability')
    for key in ('websiteURL','supportURL','privacyPolicyURL','termsOfServiceURL'):
        url = urlsplit(interface[key])
        require(url.scheme == 'https' and url.hostname == 'ninai.io' and not url.username and not url.fragment, f'Invalid {key}')
        require(len(interface[key]) <= 1024, f'{key} too long')
    prompts = interface['defaultPrompt']
    require(0 < len(prompts) <= 3 and len(set(prompts)) == len(prompts), 'Invalid starter prompts')
    require(all(0 < len(x) <= 128 and '@' not in x for x in prompts), 'Invalid starter prompt')
    for key in ('logo','composerIcon'):
        path = local_file(plugin, interface[key])
        require(path.stat().st_size <= 5*1024*1024, 'Icon exceeds limit')
        svg = ElementTree.parse(path).getroot()
        bounds = [float(x) for x in svg.attrib['viewBox'].split()]
        require(bounds[2] == bounds[3] and bounds[2] >= 48, 'Icon must be square and at least 48 units')
    require(contrast(interface['brandColor'], '#FFFFFF') >= 2, 'Light brand contrast too low')
    require(contrast(interface['brandColorDark'], '#212121') >= 2, 'Dark brand contrast too low')
    for name in ('ninai-app-icon.svg','ninai-wordmark.svg','ninai-wordmark-reversed.svg'):
        require((plugin/'assets'/name).read_bytes() == (ROOT/'website/public/assets'/name).read_bytes(), f'Website brand differs: {name}')
    png = local_file(plugin, claude['icon']).read_bytes()
    require(png[:8] == b'\x89PNG\r\n\x1a\n', 'Claude icon must be PNG')
    width, height = struct.unpack('>II', png[16:24])
    require(width == height and 512 <= width <= 2048 and len(png) < 2*1024*1024, 'Invalid Claude listing icon dimensions/size')
    require(claude['privacyPolicyUrl'] == interface['privacyPolicyURL'], 'Claude privacy URL differs')
    require(len((plugin/'README.md').read_text().split()) >= 40, 'README too short')
    require((plugin/'LICENSE').read_bytes() == (ROOT/'LICENSE').read_bytes(), 'LICENSE differs')
    for file, transport in [('mcp.json','streamable-http'),('.mcp.json','http')]:
        config = read_json(plugin/file)
        require(set(config['mcpServers']) == {'ninai'}, 'Exactly one MCP required')
        server = config['mcpServers']['ninai']
        require(server['type'] == transport and server['url'] == 'https://app.ninai.io/mcp', 'MCP routing differs')
        require(not server.get('headers') and 'command' not in server, 'Public package must not embed headers or execute local server')
    auth = read_json(plugin/'mcp.json')['mcpServers']['ninai']['extensions']['com.openai']['auth']
    require(auth == {'type':'oauth','client':{'mode':'dcr'}}, 'Expected discovery-based OAuth DCR')
    review = extension['review']['test_cases']
    for kind, count in [('positive',5),('negative',3)]:
        require(len(review[kind]) == count, f'Expected {count} {kind} review cases')
        for case in review[kind]:
            require(all(case.get(x) for x in ('description','prompt','expected_behavior')), 'Incomplete review case')
            if kind == 'positive':
                require(bool(case.get('tools_triggered')), 'Missing expected tools')
    forbidden = {'clientSecret','client_secret','test_credentials','reviewer_instructions','headers','apps','hooks'}
    def check_keys(obj: object) -> None:
        if isinstance(obj,dict):
            require(not forbidden.intersection(obj), f'Forbidden public manifest field: {forbidden.intersection(obj)}')
            for value in obj.values(): check_keys(value)
        elif isinstance(obj,list):
            for value in obj: check_keys(value)
    for file in plugin.rglob('*.json'): check_keys(read_json(file))
    files = []
    for path in sorted(plugin.rglob('*')):
        require(not path.is_symlink(), f'Symlink not distributable: {path}')
        require(path.name not in {'.DS_Store','Thumbs.db','desktop.ini','__MACOSX','.env'}, f'Forbidden artifact: {path}')
        if path.is_file():
            require(path.suffix in {'.json','.md','.svg','.png'} or path.name == 'LICENSE', f'Unexpected package file: {path}')
            require(path.stat().st_size < 256*1024, f'Package file too large: {path}')
            files.append(path)
    require(len(files) <= 512, 'Too many package files')
    return portable, files


def build(output: Path) -> None:
    manifest, files = validate()
    output.mkdir(parents=True, exist_ok=True)
    for host in ('openai','claude'):
        archive = output/f'ninai-{host}-{manifest["version"]}.zip'
        selected = [p for p in files if not (host == 'openai' and '.claude-plugin' in p.parts) and not (host == 'claude' and ('.codex-plugin' in p.parts or p.name in {'plugin.json','mcp.json'} and p.parent == PLUGIN))]
        with ZipFile(archive,'w',compression=ZIP_DEFLATED) as bundle:
            for path in selected:
                info = ZipInfo(path.relative_to(PLUGIN).as_posix(), date_time=(2026,1,1,0,0,0))
                info.compress_type = ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                bundle.writestr(info,path.read_bytes())
        with ZipFile(archive) as bundle:
            require(bundle.testzip() is None, 'ZIP corruption')
            require(len(bundle.namelist()) == len(selected), 'ZIP entry count differs')
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        archive.with_suffix('.zip.sha256').write_text(f'{digest}  {archive.name}\n')
        print(f'{archive}: {len(selected)} files; sha256 {digest}')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'dist'/'plugins')
    parser.add_argument('--check',action='store_true',help='Validate source without building ZIPs')
    args = parser.parse_args()
    try:
        if args.check:
            manifest, files = validate()
            print(f'Package policy passed: {manifest["version"]}, {len(files)} source files. Portal scans and runtime acceptance remain pending.')
        else:
            build(args.output)
    except (ValueError, KeyError, OSError, ElementTree.ParseError) as error:
        parser.exit(1, f'Package validation failed: {error}\n')


if __name__ == '__main__':
    main()
