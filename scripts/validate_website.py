from __future__ import annotations

from pathlib import Path
from html.parser import HTMLParser
import re
from urllib.parse import unquote, urlsplit


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.targets: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        element_id = attributes.get("id")
        if element_id:
            self.ids.add(element_id)
        for attribute in ("href", "src"):
            target = attributes.get(attribute)
            if target:
                self.targets.append(target)

website = Path(__file__).resolve().parents[1] / "website"
root = website / "out"
required = [
    "index.html", "install/index.html", "research/index.html", "privacy/index.html",
    "404.html", "robots.txt", "sitemap.xml", "site.webmanifest", "llms.txt",
    ".well-known/security.txt", "assets/og-image.png", "assets/ninai-wordmark.svg",
    "CNAME",
]
for item in required:
    if not (root / item).exists():
        raise SystemExit(f"Missing exported file: {item}. Run `npm run build` in website/.")

titles: set[str] = set()
descriptions: set[str] = set()
indexable_pages = [
    root / "index.html",
    root / "install/index.html",
    root / "research/index.html",
    root / "privacy/index.html",
]
public_pages = [*indexable_pages, root / "404.html"]
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

for html in indexable_pages:
    text = html.read_text(encoding="utf-8")
    for marker in (
        "<title>",
        'name="description"',
        'rel="canonical"',
        'property="og:title"',
        'property="og:description"',
        'property="og:image"',
    ):
        if marker not in text:
            raise SystemExit(f"{html}: missing {marker}")
    if len(re.findall(r"<h1(?:\s|>)", text)) != 1:
        raise SystemExit(f"{html}: expected exactly one H1")

    title_match = re.search(r"<title>(.*?)</title>", text)
    description_match = re.search(r'<meta name="description" content="(.*?)"', text)
    if title_match is None or description_match is None:
        raise SystemExit(f"{html}: metadata could not be parsed")
    title = title_match.group(1)
    description = description_match.group(1)
    if title in titles:
        raise SystemExit(f"{html}: duplicate title: {title}")
    if description in descriptions:
        raise SystemExit(f"{html}: duplicate description")
    titles.add(title)
    descriptions.add(description)

not_found = (root / "404.html").read_text(encoding="utf-8")
if 'name="robots" content="noindex"' not in not_found:
    raise SystemExit("404.html: expected noindex")
if len(re.findall(r"<h1(?:\s|>)", not_found)) != 1:
    raise SystemExit("404.html: expected exactly one H1")
print("Website validation passed")
