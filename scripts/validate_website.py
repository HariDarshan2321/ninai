from __future__ import annotations

from pathlib import Path
from html.parser import HTMLParser
import re
import json
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.targets: list[str] = []
        self.metadata: dict[str, list[str]] = {}
        self.structured_data: list[str] = []
        self.title = ""
        self.h1_count = 0
        self._in_head = False
        self._in_title = False
        self._in_json_ld = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        element_id = attributes.get("id")
        if element_id:
            self.ids.add(element_id)
        for attribute in ("href", "src"):
            target = attributes.get(attribute)
            if target:
                self.targets.append(target)
        if tag == "head":
            self._in_head = True
        if tag == "title" and self._in_head:
            self._in_title = True
        if tag == "script" and attributes.get("type") == "application/ld+json":
            self._in_json_ld = True
        if tag == "h1":
            self.h1_count += 1
        if not self._in_head:
            return
        if tag == "meta":
            name = attributes.get("name") or attributes.get("property")
            content = attributes.get("content")
            if name and content:
                self.metadata.setdefault(name, []).append(content)
        if tag == "link" and attributes.get("rel") == "canonical":
            canonical = attributes.get("href")
            if canonical:
                self.metadata.setdefault("canonical", []).append(canonical)
        if tag == "link" and attributes.get("rel") == "icon" and attributes.get("type") == "image/png":
            self.metadata.setdefault("favicon", []).append(attributes.get("href") or "")

    def handle_endtag(self, tag: str) -> None:
        if tag == "head":
            self._in_head = False
        if tag == "title":
            self._in_title = False
        if tag == "script":
            self._in_json_ld = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data
        if self._in_json_ld:
            self.structured_data.append(data)

website = Path(__file__).resolve().parents[1] / "website"
root = website / "out"
site_url = "https://ninai.io"
indexable_paths = ("/", "/install/", "/local/", "/governance/", "/compatibility/", "/privacy/", "/terms/", "/support/")
nonindex_paths = ("/start/", "/research/")
pages = {path: root / path.lstrip("/") / "index.html" for path in (*indexable_paths, *nonindex_paths)}
required = [
    "404.html", "robots.txt", "sitemap.xml", "site.webmanifest", "llms.txt",
    ".well-known/security.txt", "assets/og-image.png", "assets/ninai-icon.png", "assets/ninai-wordmark.svg", "CNAME",
]
for item in [*pages.values(), *(root / file for file in required)]:
    if not item.is_file():
        raise SystemExit(f"Missing exported file: {item.relative_to(root)}. Run `npm run build` in website/.")

titles: set[str] = set()
descriptions: set[str] = set()
public_pages = [*pages.values(), root / "404.html"]
parsed_pages: dict[Path, PageParser] = {}
for html in public_pages:
    parser = PageParser()
    parser.feed(html.read_text(encoding="utf-8"))
    parsed_pages[html] = parser


def resolve_internal_path(source: Path, path: str) -> Path:
    if path.startswith("/"):
        candidate = root / unquote(path.lstrip("/"))
    else:
        candidate = source.parent / unquote(path)
    if path.endswith("/") or candidate.is_dir():
        candidate /= "index.html"
    return candidate


for source, parser in list(parsed_pages.items()):
    for target in parser.targets:
        parsed = urlsplit(target)
        if parsed.scheme or parsed.netloc or target.startswith(("mailto:", "tel:", "data:")):
            continue
        target_page = source
        if parsed.path:
            target_page = resolve_internal_path(source, parsed.path)
            if not target_page.exists():
                raise SystemExit(f"{source}: broken internal target: {target}")
        if parsed.fragment:
            target_parser = parsed_pages.get(target_page)
            if target_parser is None and target_page.suffix == ".html":
                target_parser = PageParser()
                target_parser.feed(target_page.read_text(encoding="utf-8"))
                parsed_pages[target_page] = target_parser
            if target_parser is None or parsed.fragment not in target_parser.ids:
                raise SystemExit(f"{source}: missing anchor target: {target}")

for path, html in pages.items():
    parser = parsed_pages[html]
    title = parser.title
    if parser.h1_count != 1:
        raise SystemExit(f"{html}: expected exactly one H1")
    if not title.endswith(" - Ninai") or any(separator in title for separator in ("—", "–", " -- ")):
        raise SystemExit(f"{html}: expected a page title ending in ' - Ninai'")
    descriptions_in_head = parser.metadata.get("description", [])
    if len(descriptions_in_head) != 1:
        raise SystemExit(f"{html}: expected exactly one page description")
    description = descriptions_in_head[0]
    if title in titles:
        raise SystemExit(f"{html}: duplicate title: {title}")
    if description in descriptions:
        raise SystemExit(f"{html}: duplicate description")
    titles.add(title)
    descriptions.add(description)

    canonical = site_url + path
    social_image = f"{site_url}/assets/og-image.png"
    expected_metadata = {
        "canonical": canonical,
        "favicon": "/assets/ninai-icon.png",
        "og:url": canonical,
        "og:type": "website",
        "og:site_name": "Ninai",
        "og:title": title,
        "og:description": description,
        "og:image": social_image,
        "twitter:card": "summary_large_image",
        "twitter:title": title,
        "twitter:description": description,
        "twitter:image": social_image,
    }
    for name, value in expected_metadata.items():
        if parser.metadata.get(name) != [value]:
            raise SystemExit(f"{html}: expected one {name} with value {value!r}")
    robots = parser.metadata.get("robots", [])
    if path in nonindex_paths and robots != ["noindex, follow"]:
        raise SystemExit(f"{html}: expected noindex, follow")
    if path in indexable_paths and any(
        "noindex" in directive for directive in [*robots, *parser.metadata.get("googlebot", [])]
    ):
        raise SystemExit(f"{html}: indexable page contains noindex")
    if path != "/":
        for payload in parser.structured_data:
            data = json.loads(payload)
            if any(item.get("@type") == "WebSite" for item in data.get("@graph", [data])):
                raise SystemExit(f"{html}: WebSite structured data belongs on the homepage")

not_found = parsed_pages[root / "404.html"]
if "noindex" not in not_found.metadata.get("robots", []):
    raise SystemExit("404.html: expected noindex")
if not_found.h1_count != 1:
    raise SystemExit("404.html: expected exactly one H1")

sitemap = ElementTree.parse(root / "sitemap.xml")
sitemap_urls = [(node.text or "").strip() for node in sitemap.findall("{*}url/{*}loc")]
if sorted(sitemap_urls) != sorted(site_url + path for path in indexable_paths):
    raise SystemExit("sitemap.xml: URLs must list each indexable canonical page exactly once")
robots_lines = (root / "robots.txt").read_text(encoding="utf-8").splitlines()
if f"Sitemap: {site_url}/sitemap.xml" not in robots_lines:
    raise SystemExit("robots.txt: missing the canonical sitemap URL")

homepage = parsed_pages[pages["/"]]
if len(homepage.structured_data) != 1:
    raise SystemExit("index.html: expected one structured data graph")
graph = json.loads(homepage.structured_data[0])["@graph"]
entities = {item["@type"]: item for item in graph}
if set(entities) != {"Organization", "WebSite"} or len(graph) != len(entities):
    raise SystemExit("index.html: expected organization and website structured data")
if any(entity.get("name") != "Ninai" or entity.get("url") != f"{site_url}/" for entity in entities.values()):
    raise SystemExit("index.html: structured data does not match the canonical Ninai homepage")
if [entities["WebSite"].get("description")] != homepage.metadata["description"]:
    raise SystemExit("index.html: website and page descriptions must match")

public_install = (root / "install/index.html").read_text(encoding="utf-8")
for private_setup_marker in (
    "raw.githubusercontent.com",
    "/download/install-ninai-macos.sh",
    "--client both",
    "https://app.ninai.io/mcp",
):
    if private_setup_marker in public_install:
        raise SystemExit(f"Public install page exposes account-gated setup: {private_setup_marker}")
for gated_copy in ("official installer", "Create account for Mac setup", "Sign in for Mac setup", "screen_hint=signup"):
    if gated_copy not in public_install:
        raise SystemExit(f"Public install page is missing account gate copy: {gated_copy}")
for current_release_copy in ("Follow a real setup walkthrough", "With local setup, your memory stays on your computer"):
    if current_release_copy not in public_install:
        raise SystemExit(f"Public install page is missing current-release copy: {current_release_copy}")

for media in ("ninai-install-guide.mp4", "ninai-install-poster.jpg", "ninai-install-guide.vtt", "ninai-install-chapters.json"):
    if not (root / "assets" / media).is_file():
        raise SystemExit(f"Setup walkthrough asset missing: {media}")
chapters = json.loads((root / "assets/ninai-install-chapters.json").read_text())["chapters"]
if not chapters or any(chapter["end"] <= chapter["start"] for chapter in chapters):
    raise SystemExit("Setup walkthrough must have playable chapter timings")

global_css = (website / "app/globals.css").read_text(encoding="utf-8")
closed_panel = re.search(r"\.mobile-nav__panel\s*\{[^}]*display:\s*none;", global_css, re.S)
open_panel = re.search(r"\.mobile-nav\[open\]\s+\.mobile-nav__panel\s*\{[^}]*display:\s*grid;", global_css, re.S)
if closed_panel is None or open_panel is None:
    raise SystemExit("Mobile navigation panel must remain hidden until its details element is open")
print("Website validation passed")
