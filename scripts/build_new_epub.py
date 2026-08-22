"""Build per-part EPUBs from chapter markdown."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import io
import json
import re
import subprocess
import sys
import urllib.parse
import urllib.request
import uuid
import zipfile
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

try:
    from PIL import Image
except Exception:  # Pillow is optional unless images need conversion.
    Image = None



# PATHS
SCRIPT_DIR = Path(__file__).parent.resolve()
REPO_ROOT = SCRIPT_DIR.parent
CHAPTERS_ROOT = REPO_ROOT / "chapters"
IMAGES_ROOT = REPO_ROOT / "images"
CSS_PATH = SCRIPT_DIR / "epub.css"
FONTS_DIR = REPO_ROOT / "website" / "static" / "fonts"

OUTPUT_DIR = SCRIPT_DIR / "epub"
TWITTER_IMG_DIR = OUTPUT_DIR / "twitter_images"
TWEET_CACHE_PATH = TWITTER_IMG_DIR / "cache.json"

EPUB_SOURCE_URL = "https://ireum.pages.dev"

UA = "GSGW-Reader-EPUB/2.0"



# PART & VARIANT DEFINITIONS
PART_DEFS: dict[str, list[dict[str, Any]]] = {
    "gsgw": [
        {"id": "part1", "label": "Part 1", "range": "Chapters 0–208", "max_index": 208},
        {"id": "part2", "label": "Part 2", "range": "Chapters 209–371", "min_index": 209, "max_index": 371},
        {"id": "part3", "label": "Part 3", "range": "Chapter 372 – Current", "min_index": 372},
    ],
    "debut": [
        {"id": "part1", "label": "Part 1", "range": "Chapters 1–147", "max_index": 146},
        {"id": "part2", "label": "Part 2", "range": "Chapters 148–364", "min_index": 147, "max_index": 363},
        {"id": "part3", "label": "Part 3", "range": "Chapters 365–451", "min_index": 364, "max_index": 450},
        {"id": "part4", "label": "Part 4", "range": "Chapters 452–644", "min_index": 451},
    ],
}

VARIANTS: dict[str, list[dict[str, str]]] = {
    "gsgw": [
        {"id": "plaintext", "label": "PlainText"},
    ],
    "debut": [
        {"id": "plaintext", "label": "PlainText"},
    ],
}

BOOK_SHORT_NAME: dict[str, str] = {
    "gsgw": "Ghost.Story",
    "debut": "Debut.or.Die",
}

BOOK_COVER_DIR: dict[str, str] = {
    "gsgw": "gsgw",
    "debut": "dod",
}



# DATA CLASSES
@dataclass
class EpubAsset:
    source_path: Path
    href: str
    media_type: str


@dataclass
class Chapter:
    path: Path
    metadata: dict[str, Any]
    content: str
    title: str
    index: int
    slug: str


@dataclass
class EpubItem:
    item_id: str
    href: str
    title: str
    body: str


@dataclass
class RenderContext:
    book_id: str
    chapter_path: Path
    assets: dict[Path, EpubAsset]
    asset_names: set[str]
    tweet_cache: dict[str, Any]
    fetch_twitter: bool



# FRONTMATTER PARSING
def normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    text = normalize_newlines(text)
    if not text.startswith("---\n"):
        return {}, text

    match = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.DOTALL)
    if not match:
        return {}, text

    return parse_simple_yaml(match.group(1)), match.group(2)


def split_key_value(line: str) -> tuple[str, str] | None:
    if ":" not in line:
        return None
    key, value = line.split(":", 1)
    return key.strip(), value.strip()


def parse_scalar(value: str) -> Any:
    value = value.strip()
    if value == "":
        return ""
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if value in {"null", "Null", "~"}:
        return None

    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        value = value[1:-1]
        return (
            value.replace(r"\"", '"')
            .replace(r"\'", "'")
            .replace(r"\\", "\\")
        )

    if re.fullmatch(r"-?\d+", value):
        try:
            return int(value)
        except ValueError:
            pass

    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [parse_scalar(part.strip()) for part in inner.split(",")]

    return value


def parse_indented_block(lines: list[str], start: int) -> tuple[Any, int]:
    items: list[Any] = []
    mapping: dict[str, Any] = {}
    i = start

    while i < len(lines):
        raw = lines[i]
        if not raw.strip() or raw.lstrip().startswith("#"):
            i += 1
            continue
        if raw == raw.lstrip():
            break

        stripped = raw.strip()
        if stripped.startswith("- "):
            item_text = stripped[2:].strip()
            key_value = split_key_value(item_text)
            if key_value:
                key, value = key_value
                item: dict[str, Any] = {key: parse_scalar(value)}
                i += 1
                while i < len(lines):
                    next_raw = lines[i]
                    if not next_raw.strip() or next_raw.lstrip().startswith("#"):
                        i += 1
                        continue
                    next_stripped = next_raw.strip()
                    if next_raw == next_raw.lstrip() or next_stripped.startswith("- "):
                        break
                    nested = split_key_value(next_stripped)
                    if nested:
                        nested_key, nested_value = nested
                        item[nested_key] = parse_scalar(nested_value)
                    i += 1
                items.append(item)
                continue

            items.append(parse_scalar(item_text))
            i += 1
            continue

        key_value = split_key_value(stripped)
        if key_value:
            key, value = key_value
            mapping[key] = parse_scalar(value)
        i += 1

    return (items if items else mapping), i


def parse_simple_yaml(raw: str) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    lines = raw.splitlines()
    i = 0

    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        if line != line.lstrip():
            i += 1
            continue

        key_value = split_key_value(line)
        if not key_value:
            i += 1
            continue

        key, value = key_value
        if value:
            metadata[key] = parse_scalar(value)
            i += 1
            continue

        block, next_i = parse_indented_block(lines, i + 1)
        metadata[key] = block
        i = next_i

    return metadata


def load_markdown(path: Path) -> tuple[dict[str, Any], str]:
    return split_frontmatter(path.read_text(encoding="utf-8-sig"))



# METADATA HELPERS
def metadata_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, dict):
        if "text" in value:
            return metadata_text(value["text"], default)
        for item in value.values():
            text = metadata_text(item, "")
            if text:
                return text
        return default
    if isinstance(value, list):
        for item in value:
            text = metadata_text(item, "")
            if text:
                return text
        return default
    return str(value)


def sort_value(metadata: dict[str, Any], fallback: int) -> int:
    value = metadata.get("index", metadata.get("slug", fallback))
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def strip_markup(text: str) -> str:
    text = re.sub(r"^#+\s*", "", text.strip())
    text = re.sub(r"!\[([\s\S]*?)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"([*_~`])", "", text)
    text = re.sub(r"#><(.*?)><#", r"\1", text)
    text = re.sub(r"#([rbygpo])(.+?)\1#", r"\2", text)
    text = re.sub(r";([rbygpo])(.+?)\1;", r"\2", text)
    text = re.sub(r"[@%#~^<>]+", "", text)
    return html.unescape(text).strip()


def first_heading(content: str) -> str | None:
    for line in normalize_newlines(content).splitlines():
        match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if match:
            return strip_markup(match.group(2))
    return None


def sanitize_filename(name: str, fallback: str = "book") -> str:
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "-", name)
    name = re.sub(r"\s+", " ", name).strip(" .")
    return name or fallback


def safe_id(value: str, fallback: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_-]+", "_", value).strip("_")
    return value or fallback


def valid_identifier(value: str, book_title: str) -> str:
    """Return a valid dc:identifier for the OPF/NCX.

    urn:uuid values must be well-formed UUIDs; anything else falls back to a
    deterministic UUID derived from the book title.
    """
    value = (value or "").strip()
    if not value:
        return f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, book_title)}"
    if value.lower().startswith("urn:uuid:"):
        try:
            uuid.UUID(value[len("urn:uuid:"):])
            return value
        except ValueError:
            pass
    return f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, book_title)}"


def escape_text(value: Any) -> str:
    return html.escape(str(value), quote=False)


def escape_attr(value: Any) -> str:
    return html.escape(str(value), quote=True)



# ASSET MACHINERY
def media_type_for(path: Path) -> str:
    suffix = path.suffix.lower()
    return {
        ".css": "text/css",
        ".gif": "image/gif",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".svg": "image/svg+xml",
        ".webp": "image/webp",
        ".xhtml": "application/xhtml+xml",
        ".ncx": "application/x-dtbncx+xml",
    }.get(suffix, "application/octet-stream")


def convert_to_png(source_path: Path, output_dir: Path) -> Path | None:
    """Convert an image to PNG (a core EPUB media type). Returns the PNG path, or None on failure."""
    if Image is None:
        return None
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{source_path.stem}.png"
        with Image.open(source_path) as img:
            img.save(output_path, "PNG", optimize=True)
        return output_path if output_path.exists() and output_path.stat().st_size > 0 else None
    except Exception:
        return None


def unique_asset_name(source_path: Path, preferred: str, used: set[str]) -> str:
    preferred = sanitize_filename(preferred.replace(" ", "_"), "asset")
    stem = Path(preferred).stem or "asset"
    suffix = Path(preferred).suffix or source_path.suffix
    candidate = f"{stem}{suffix}"
    if candidate not in used:
        used.add(candidate)
        return candidate

    digest = hashlib.sha1(str(source_path).encode("utf-8")).hexdigest()[:8]
    candidate = f"{stem}_{digest}{suffix}"
    counter = 2
    while candidate in used:
        candidate = f"{stem}_{digest}_{counter}{suffix}"
        counter += 1
    used.add(candidate)
    return candidate


def register_asset(ctx: RenderContext, source_path: Path, preferred: str | None = None) -> EpubAsset:
    source_path = source_path.resolve()
    existing = ctx.assets.get(source_path)
    if existing:
        return existing

    name = unique_asset_name(source_path, preferred or source_path.name, ctx.asset_names)
    asset = EpubAsset(
        source_path=source_path,
        href=f"Images/{name}",
        media_type=media_type_for(source_path),
    )
    ctx.assets[source_path] = asset
    return asset


def resolve_local_image(src: str, ctx: RenderContext) -> Path | None:
    clean_src = urllib.parse.unquote(src.split("#", 1)[0].split("?", 1)[0])
    src_path = Path(clean_src.replace("/", "\\"))

    candidates = []
    if src_path.is_absolute():
        candidates.append(src_path)
    else:
        img_dir = BOOK_COVER_DIR.get(ctx.book_id, ctx.book_id)
        candidates.extend(
            [
                ctx.chapter_path.parent / src_path,
                IMAGES_ROOT / img_dir / "illustrations" / src_path,
                IMAGES_ROOT / img_dir / src_path,
                IMAGES_ROOT / ctx.book_id / "illustrations" / src_path,
                IMAGES_ROOT / ctx.book_id / src_path,
                IMAGES_ROOT / src_path,
                OUTPUT_DIR / src_path,
            ]
        )

    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate
    return None



# PRECOMPILED REGEX
IMG_TAG_RE = re.compile(r"<img [^>]+>")
SRC_RE = re.compile(r'src="([^"]+)"')
IMG_TITLE_SIZE_RE = re.compile(r'\btitle="(\d+(?:\.\d+)?(?:px|%))"', re.IGNORECASE)

SHAKE_RE = re.compile(r"%%(.*?)%%", re.DOTALL)
SHAKE_CHAR_RE = re.compile(r"%~(.*?)~%", re.DOTALL)
WAVE_RE = re.compile(r"%\^(.*?)\^%", re.DOTALL)

DISTORT_RE = re.compile(r"@@([^@]+)@@", re.DOTALL)
SUBTLEDISTORT_RE = re.compile(r"@_@(.+?)@_@", re.DOTALL)
GROW_RE = re.compile(r"#\^#(.+?)#\^#", re.DOTALL)
SHRINK_RE = re.compile(r"#v#(.+?)#v#", re.DOTALL)

SMOKE_RE = re.compile(r"\$s(.+?)s\$", re.DOTALL)
AURORA_RE = re.compile(r"\$a(.+?)a\$", re.DOTALL)
GOLD_RE = re.compile(r"\$g(.+?)g\$", re.DOTALL)
SPARKLE_RE = re.compile(r"\$\*(.+?)\*\$", re.DOTALL)
MOON_RE = re.compile(r"\$\((.+?)\)\$", re.DOTALL)
SILVER_RE = re.compile(r"\$ag(.+?)ag\$", re.DOTALL)
OUTLINE_WHITE_RE = re.compile(r"\$wo(.+?)wo\$", re.DOTALL)
OUTLINE_BLACK_RE = re.compile(r"\$bo(.+?)bo\$", re.DOTALL)
HEX_COLOR_RE = re.compile(r"#hx\(([^)]+)\)(.*?)hx#", re.DOTALL)
HEX_OUTLINE_RE = re.compile(r"\$hxo\(([^)]+)\)(.*?)hxo#", re.DOTALL)
HEX_AURORA_RE = re.compile(r"\$hxa\(([^)]+)\)\(([^)]+)\)\(([^)]+)\)(.*?)hxa\$", re.DOTALL)
HEX_AURORA_STATIC_RE = re.compile(r"\$hxas\(([^)]+)\)\(([^)]+)\)\(([^)]+)\)(.*?)hxas\$", re.DOTALL)
HEX_AURORA_UP_RE = re.compile(r"\$hxau\(([^)]+)\)\(([^)]+)\)\(([^)]+)\)(.*?)hxau\$", re.DOTALL)
HEX_AURORA_UP_STATIC_RE = re.compile(r"\$hxaus\(([^)]+)\)\(([^)]+)\)\(([^)]+)\)(.*?)hxaus\$", re.DOTALL)

SCROLL_LEFT_RE = re.compile(r"\|<(.+?)<\|", re.DOTALL)
SCROLL_RIGHT_RE = re.compile(r"\|>(.+?)>\|", re.DOTALL)
TRANSITION_TEXT_RE = re.compile(r"\|t\s*(?:\(([^)]*)\))?\s*(.*?)\s*t\|", re.DOTALL)

FOOTNOTE_RE = re.compile(r"\[(\d+)\]\{([^}]+)\}", re.DOTALL)

TRIPLE_STRIKE_RE = re.compile(r"<ts>([\s\S]*?)</ts>", re.DOTALL)

TWITTER_URL_RE = re.compile(
    r'https?://(?:x|twitter)\.com/(\w+)/status/(\d+)(?:/photo/(\d+))?[^\s<>"\']*'
)

VISIBLE_HR_RE = re.compile(r"^~~~(?=\s*$)", re.MULTILINE)
INVISIBLE_HR_RE = re.compile(r"^~\^~(?=\s*$)", re.MULTILINE)

WIKI_WINDOW_RE = re.compile(r"\+[-+]+\n(.*?)\n[-+]+\+", re.DOTALL)
BLACK_WINDOW_RE = re.compile(r"\+[=]+\n(.*?)\n[=]+\+", re.DOTALL)
SYSTEM_WINDOW_RE = re.compile(r"\+[~]+\n(.*?)\n[~]+\+", re.DOTALL)
PLAIN_WINDOW_RE = re.compile(r"\+\$\n(.*?)\n\$\+", re.DOTALL)
BARE_WINDOW_RE = re.compile(r"\+\.\n(.*?)\n\.\+", re.DOTALL)

RECORD_WINDOW_RE = re.compile(r"&[-]+\n(.*?)\n[-]+&", re.DOTALL)
FOLLOWUP_WINDOW_RE = re.compile(r"\+\$\n(.*?)\n-\$", re.DOTALL)
AMPERSAND_WINDOW_RE = re.compile(r"&\$\n(.*?)\n\$&", re.DOTALL)

NOTE_WINDOW_RE = re.compile(r"![-]+\n(.*?)\n[-]+!", re.DOTALL)
STICKY_WINDOW_RE = re.compile(r"!\$\n(.*?)\n\$!", re.DOTALL)
PAPER_BOAT_WINDOW_RE = re.compile(r"!pb\n(.*?)\npb!", re.DOTALL)
BRAUN_WINDOW_RE = re.compile(r"!\[\n(.*?)\n\]!", re.DOTALL)
BRAUN_TV_TEXT_RE = re.compile(r"\$[Bb][Rr][Tt]\n(.*?)\n[Bb][Rr][Tt]\$", re.DOTALL)
BRAUN_DOLL_TEXT_RE = re.compile(r"\$[Bb][Rr][Dd]\n(.*?)\n[Bb][Rr][Dd]\$", re.DOTALL)
PADDING_WINDOW_RE = re.compile(r"\$p\n(.*?)\np\$", re.DOTALL)

DEBUT_WINDOW_RE = re.compile(r"★-\n(.*?)\n-★", re.DOTALL)
DEBUT_ALERT_RE = re.compile(r"★!\n(.*?)\n!★", re.DOTALL)
DEBUT_ACHIEVE_RE = re.compile(r"★=\n(.*?)\n=★", re.DOTALL)
SMS_WINDOW_RE = re.compile(r"★:\n([\s\S]*?)\n:★", re.DOTALL)
COMMENT_WINDOW_RE = re.compile(r"★\$\n([\s\S]*?)\n\$★", re.DOTALL)


SIMPLE_REPLACEMENTS = [
    (TRANSITION_TEXT_RE, lambda m: transition_replacer(m)),

    (re.compile(r"(?<!\\)_(.*?)(?<!\\)_", re.DOTALL), r"[\1]{.underline}"),


    (re.compile(r"@ll@(.*?)@ll@", re.DOTALL), r'<span class="mono mono-left">\1</span>'),
    (re.compile(r"@cc@(.*?)@cc@", re.DOTALL), r'<span class="mono mono-center">\1</span>'),
    (re.compile(r"@rr@(.*?)@rr@", re.DOTALL), r'<span class="mono mono-right">\1</span>'),

    (re.compile(r"@l@(.*?)@l@", re.DOTALL), r'<span class="align-left">\1</span>'),
    (re.compile(r"@c@(.*?)@c@", re.DOTALL), r'<span class="align-center">\1</span>'),
    (re.compile(r"@r@(.*?)@r@", re.DOTALL), r'<span class="align-right">\1</span>'),

    (re.compile(r"#r(.*?)r#", re.DOTALL), r'<span class="text-red">\1</span>'),
    (re.compile(r"#b(.*?)b#", re.DOTALL), r'<span class="text-blue">\1</span>'),
    (re.compile(r"#y(.*?)y#", re.DOTALL), r'<span class="text-yellow">\1</span>'),
    (re.compile(r"#p(.*?)p#", re.DOTALL), r'<span class="text-magenta">\1</span>'),
    (re.compile(r"#g(.*?)g#", re.DOTALL), r'<span class="text-green">\1</span>'),
    (re.compile(r"#o(.*?)o#", re.DOTALL), r'<span class="text-orange">\1</span>'),
    (re.compile(r"#lp(.*?)lp#", re.DOTALL), r'<span class="text-light-purple">\1</span>'),
    (re.compile(r"#cy(.*?)cy#", re.DOTALL), r'<span class="text-cyan">\1</span>'),
    (re.compile(r"#d(.*?)d#", re.DOTALL), r'<span class="text-base-content">\1</span>'),
    (re.compile(r"#f#(.*?)#f#", re.DOTALL), r'<span class="text-faded">\1</span>'),
    (re.compile(r"(?<!\\)\-#\s*(.+?)\s*#-(?!\\)", re.DOTALL), r'<span class="text-sub">\1</span>'),
    (re.compile(r"#f>#(.*?)#f>#", re.DOTALL), r'<span class="text-fade-right">\1</span>'),
    (re.compile(r"#f<#(.*?)#f<#", re.DOTALL), r'<span class="text-fade-left">\1</span>'),

    (re.compile(r"#\*(.*?)\*#", re.DOTALL), r'<span class="text-large">\1</span>'),
    (re.compile(r"#><(.*?)><#", re.DOTALL), r'<span class="text-large-centered">\1</span>'),

    (re.compile(r";r(.*?)r;", re.DOTALL), r'<span class="hl-red">\1</span>'),
    (re.compile(r";b(.*?)b;", re.DOTALL), r'<span class="hl-blue">\1</span>'),
    (re.compile(r";y(.*?)y;", re.DOTALL), r'<span class="hl-yellow">\1</span>'),
    (re.compile(r";p(.*?)p;", re.DOTALL), r'<span class="hl-magenta">\1</span>'),
    (re.compile(r";g(.*?)g;", re.DOTALL), r'<span class="hl-green">\1</span>'),
    (re.compile(r";o(.*?)o;", re.DOTALL), r'<span class="hl-orange">\1</span>'),

    (re.compile(r"\$c(.*?)c\$", re.DOTALL), r'<span class="contaminated">\1</span>'),
    (re.compile(r"\$Eb(.*?)Eb\$", re.DOTALL), r'<span class="eb-garamond">\1</span>'),
    (re.compile(r"\$lat(.*?)lat\$", re.DOTALL), r'<span class="lato">\1</span>'),
    (re.compile(r"\$fox(.*?)fox\$", re.DOTALL), r'<span class="fox">\1</span>'),
    (re.compile(r"\$h(?!x)(.*?)h\$", re.DOTALL), r'<span class="paulo-bittencourt">\1</span>'),
    (re.compile(r"\$nbg(.*?)nbg\$", re.DOTALL), r'<span class="nanum-barun-gothic">\1</span>'),
    (re.compile(r"\$tf(.*?)tf\$", re.DOTALL), r'<span class="chungju-kimsaeng">\1</span>'),
    (re.compile(r"\$vcr(.*?)vcr\$", re.DOTALL), r'<span class="vcr-osd-mono">\1</span>'),
    (re.compile(r"\$Bh(.*?)Bh\$", re.DOTALL), r'<span class="braun-handwriting">\1</span>'),
    (re.compile(r"\$wo(.*?)wo\$", re.DOTALL), r'<span class="outline-white">\1</span>'),
    (re.compile(r"\$bo(.*?)bo\$", re.DOTALL), r'<span class="outline-black">\1</span>'),
]



# HELPERS
def escape_markdown_except_bold(text):

    html_placeholders = {}
    def save_html(m):
        key = f"\x00HTML{len(html_placeholders)}\x00"
        html_placeholders[key] = m.group(0)
        return key
    text = re.sub(r'<[a-zA-Z][^>]*>.*?</[a-zA-Z][^>]*>', save_html, text, flags=re.DOTALL)
    text = re.sub(r'<[a-zA-Z][^>]*/>', save_html, text)

    text = re.sub(r'(?<!\\)\[', r'\\[', text)
    text = re.sub(r'(?<!\\)\]', r'\\]', text)

    text = re.sub(r'(?<!\\)\(', r'\\(', text)
    text = re.sub(r'(?<!\\)\)', r'\\)', text)

    text = re.sub(r'(?<!\\)_', r'\\_', text)

    text = re.sub(r'(?m)^(?<!\\):(?=\s)', r'\\:', text)
    text = re.sub(r'(?m)^(?<!\\)#(?=\s)', r'\\#', text)
    text = re.sub(r'(?m)^(?<!\\)>(?=\s)', r'\\>', text)

    for key, val in html_placeholders.items():
        text = text.replace(key, val)

    return text



# TWITTER URL PROCESSING

def load_tweet_cache() -> dict[str, Any]:
    if not TWEET_CACHE_PATH.exists():
        return {}
    try:
        return json.loads(TWEET_CACHE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_tweet_cache(cache: dict[str, Any]) -> None:
    TWITTER_IMG_DIR.mkdir(parents=True, exist_ok=True)
    TWEET_CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def request_json(url: str) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def request_bytes(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=40) as response:
        return response.read()


def fetch_twitter_webp(username: str, tweet_id: str, photo_index: int) -> tuple[Path | None, str | None]:
    cache_key = f"{tweet_id}_{photo_index}"
    webp_path = TWITTER_IMG_DIR / f"{cache_key}.webp"
    if webp_path.exists():
        return webp_path, None

    if Image is None:
        print(f"      Pillow is unavailable; cannot convert tweet {tweet_id} to WebP")
        return None, None

    api_url = f"https://api.fxtwitter.com/{username}/status/{tweet_id}"
    data = request_json(api_url)
    tweet = data.get("tweet") or {}
    screen_name = ((tweet.get("user") or {}).get("screen_name")) or username
    photos = ((tweet.get("media") or {}).get("photos") or [])
    idx = photo_index - 1
    if idx < 0 or idx >= len(photos):
        print(f"      Tweet {tweet_id} has no photo #{photo_index}")
        return None, None

    photo_url = photos[idx].get("url")
    if not photo_url:
        print(f"      Tweet {tweet_id} photo #{photo_index} has no URL")
        return None, None

    image_bytes = request_bytes(photo_url)
    image = Image.open(io.BytesIO(image_bytes))
    TWITTER_IMG_DIR.mkdir(parents=True, exist_ok=True)
    image.save(webp_path, "WEBP", quality=88, method=6)
    return webp_path, screen_name


def image_block_html(src: str, alt: str = "") -> str:
    alt_attr = escape_attr(strip_markup(alt))
    img = f'<img src="{escape_attr(src)}" alt="{alt_attr}" />'
    if alt_attr:
        return f'<div class="image-block">{img}<div class="thumbcaption">{alt_attr}</div></div>'
    return f'<div class="image-block">{img}</div>'


def twitter_image_html(match: re.Match, ctx: RenderContext) -> str:
    username = match.group(1)
    tweet_id = match.group(2)
    photo_index = int(match.group(3) or 1)
    return _twitter_image_html_impl(username, tweet_id, photo_index, ctx)


def _twitter_image_html_impl(username: str, tweet_id: str, photo_index: int, ctx: RenderContext) -> str:
    cache_key = f"{tweet_id}_{photo_index}"
    webp_path = TWITTER_IMG_DIR / f"{cache_key}.webp"

    cached_entry = ctx.tweet_cache.get(cache_key)
    screen_name = None

    if cached_entry:
        screen_name = cached_entry.get("screen_name")

    if not webp_path.exists() and ctx.fetch_twitter:
        try:
            print(f"      Fetching tweet image {tweet_id}/{photo_index}")
            webp_path, api_screen_name = fetch_twitter_webp(username, tweet_id, photo_index)
            screen_name = api_screen_name or screen_name
            if webp_path:
                ctx.tweet_cache[cache_key] = {
                    "username": username,
                    "screen_name": screen_name or username,
                    "tweet_id": tweet_id,
                    "photo": photo_index,
                    "path": str(webp_path),
                }
                save_tweet_cache(ctx.tweet_cache)
        except Exception as exc:
            print(f"      Warning: failed to fetch tweet {tweet_id}: {exc}")

    if webp_path.exists():
        png_path = convert_to_png(webp_path, TWITTER_IMG_DIR / "png") or webp_path
        asset = register_asset(ctx, png_path, f"twitter_{cache_key}.png" if png_path.suffix.lower() == ".png" else f"twitter_{cache_key}{png_path.suffix}")
        display_name = screen_name or username
        alt = f"Illustration by @{display_name} on X"
        alt_attr = escape_attr(alt)
        img = f'<img src="{escape_attr(f"../{asset.href}")}" alt="{alt_attr}" />'
        return f'<div class="image-block">{img}<div class="thumbcaption">{alt_attr}</div></div>'

    url = f"https://x.com/{username}/status/{tweet_id}"
    return f'<p><a href="{escape_attr(url)}">{escape_text(url)}</a></p>'


def process_twitter_urls(content):
    def replacer(match):
        username = match.group(1)
        tweet_id = match.group(2)
        photo_idx = match.group(3)
        attrs = f'data-user="{username}" data-tweet-id="{tweet_id}"'
        if photo_idx:
            attrs += f' data-photo="{photo_idx}"'
        return (
            f'<div class="twitter-embed" {attrs}>'
            f'<div class="twitter-embed-loading">Loading…</div>'
            f'</div>'
        )
    return TWITTER_URL_RE.sub(replacer, content)


TWITTER_EMBED_RE = re.compile(
    r'<div class="twitter-embed"[^>]*>\s*<div class="twitter-embed-loading">.*?</div>\s*</div>',
    re.DOTALL,
)


def process_twitter_embeds(html_content: str, ctx: RenderContext) -> str:
    """EPUB-only step: the website hydrates twitter-embed divs client-side;
    an EPUB has no JS, so fetch the tweet image via fxtwitter API and embed it."""

    def repl(match: re.Match) -> str:
        user_m = re.search(r'data-user="([^"]*)"', match.group(0))
        id_m = re.search(r'data-tweet-id="(\d+)"', match.group(0))
        photo_m = re.search(r'data-photo="(\d+)"', match.group(0))
        if not user_m or not id_m:
            return ""
        username = user_m.group(1)
        tweet_id = id_m.group(1)
        photo_index = int(photo_m.group(1)) if photo_m else 1
        return _twitter_image_html_impl(username, tweet_id, photo_index, ctx)

    return TWITTER_EMBED_RE.sub(repl, html_content)



# EFFECT REPLACERS
def shake_char_replacer(match):

    text = match.group(1)

    out = []

    for i, c in enumerate(text):

        if c == " ":
            out.append(" ")
            continue

        out.append(
            f'<span class="shake" '
            f'style="animation-delay:-{(i * 0.05) % 0.5:.2f}s">{c}</span>'
        )

    return "".join(out)


def wave_char_replacer(match):

    text = match.group(1)

    out = []

    length = len(text)

    for i, c in enumerate(text):

        if c == " ":
            out.append(" ")
            continue

        delay = ((length - 1 - i) * 0.05) % 0.5

        out.append(
            f'<span class="wave-up" '
            f'style="animation-delay:-{delay:.2f}s">{c}</span>'
        )

    return "".join(out)


def distorted_replacer(match):

    inner = match.group(1)

    inner = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", inner)

    parts = re.split(r"(<[^>]+>)", inner)

    chars = []

    idx = 0

    for part in parts:

        if part.startswith("<") and part.endswith(">"):
            chars.append(part)
            continue

        for c in part:

            if c == " ":
                chars.append(" ")
                continue

            chars.append(
                f'<span class="char">{c}</span>'
            )

            idx += 1

    return (
        f'<span class="glitch-text">'
        f'{"".join(chars)}'
        f'</span>'
    )


def subtle_replacer(match):

    inner = match.group(1)

    inner = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", inner)

    inner = re.sub(r"\$\$(.+?)\$\$", r'<span class="handwritten">\1</span>', inner)
    inner = re.sub(r"\$lat(.+?)lat\$", r'<span class="lato">\1</span>', inner)
    inner = re.sub(r"\$fox(.+?)fox\$", r'<span class="fox">\1</span>', inner)
    inner = re.sub(r"\$Eb(.+?)Eb\$", r'<span class="eb-garamond">\1</span>', inner)
    inner = re.sub(r"\$c(.+?)c\$", r'<span class="contaminated">\1</span>', inner)
    inner = re.sub(r"\$wo(.+?)wo\$", r'<span class="outline-white">\1</span>', inner)
    inner = re.sub(r"\$bo(.+?)bo\$", r'<span class="outline-black">\1</span>', inner)
    inner = re.sub(r"\$h(?!x)(.+?)h\$", r'<span class="paulo-bittencourt">\1</span>', inner)
    inner = re.sub(r"\$nbg(.+?)nbg\$", r'<span class="nanum-barun-gothic">\1</span>', inner)
    inner = re.sub(r"\$tf(.+?)tf\$", r'<span class="chungju-kimsaeng">\1</span>', inner)
    inner = re.sub(r"\$vcr(.+?)vcr\$", r'<span class="vcr-osd-mono">\1</span>', inner)
    inner = re.sub(r"\$Bh(.+?)Bh\$", r'<span class="braun-handwriting">\1</span>', inner)

    parts = re.split(r"(<[^>]+>)", inner)

    chars = []

    idx = 0

    for part in parts:

        if part.startswith("<") and part.endswith(">"):
            chars.append(part)
            continue

        for c in part:

            if c == " ":
                chars.append(" ")
                continue

            chars.append(
                f'<span class="char">{c}</span>'
            )

            idx += 1

    return (
        f'<span class="glitch-subtle">'
        f'{"".join(chars)}'
        f'</span>'
    )


def smoke_replacer(match):

    inner = match.group(1)

    inner = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", inner)

    return f'<span class="smoke-text">{inner}</span>'


def aurora_replacer(match):

    inner = match.group(1)

    inner = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", inner)

    return f'<span class="aurora-text">{inner}</span>'


def hex_aurora_replacer(match):

    inner = match.group(4)

    inner = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", inner)

    return (
        f'<span class="hex-aurora" '
        f'style="--ha-c1:{match.group(1)};--ha-c2:{match.group(2)};--ha-c3:{match.group(3)}">'
        f'{inner}</span>'
    )


def hex_aurora_static_replacer(match):

    inner = match.group(4)

    inner = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", inner)

    return (
        f'<span class="hex-aurora-static" '
        f'style="--ha-c1:{match.group(1)};--ha-c2:{match.group(2)};--ha-c3:{match.group(3)}">'
        f'{inner}</span>'
    )


def hex_aurora_up_replacer(match):

    inner = match.group(4)

    inner = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", inner)

    return (
        f'<span class="hex-aurora-up" '
        f'style="--ha-c1:{match.group(1)};--ha-c2:{match.group(2)};--ha-c3:{match.group(3)}">'
        f'{inner}</span>'
    )


def hex_aurora_up_static_replacer(match):

    inner = match.group(4)

    inner = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", inner)

    return (
        f'<span class="hex-aurora-up-static" '
        f'style="--ha-c1:{match.group(1)};--ha-c2:{match.group(2)};--ha-c3:{match.group(3)}">'
        f'{inner}</span>'
    )


def silver_replacer(match):

    inner = match.group(1)

    inner = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", inner)

    return f'<span class="silver-text">{inner}</span>'


def grow_replacer(match):

    inner = match.group(1)

    length = len(inner)

    chars = []

    for i, c in enumerate(inner):

        if c == " ":
            chars.append(" ")
            continue

        scale = 1 + (i / max(length - 1, 1)) * 0.6

        chars.append(
            f'<span class="grow-char" '
            f'style="font-size:{scale:.2f}em">{c}</span>'
        )

    return f'<span class="text-grow">{"".join(chars)}</span>'


def shrink_replacer(match):

    inner = match.group(1)

    length = len(inner)

    chars = []

    for i, c in enumerate(inner):

        if c == " ":
            chars.append(" ")
            continue

        scale = 1.4 - (i / max(length - 1, 1)) * 0.4

        chars.append(
            f'<span class="grow-char" '
            f'style="font-size:{scale:.2f}em">{c}</span>'
        )

    return f'<span class="text-grow">{"".join(chars)}</span>'



# WINDOW REPLACERS
def make_window(class_name, inner, extra_class=None):

    inner = fix_underline(inner)
    inner = escape_markdown_except_bold(inner)
    inner = re.sub(r"\*\*\*(.+?)\*\*\*", r"<strong><em>\1</em></strong>", inner, flags=re.DOTALL)
    inner = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", inner, flags=re.DOTALL)

    cls = class_name

    if extra_class:
        cls += f" {extra_class}"

    dotted = " ".join(f".{c.lstrip('.')}" for c in cls.split())

    return f'\n::: {{{dotted}}}\n{inner}\n:::\n'


def braun_text_replacer(class_name):
    def replacer(match):
        inner = re.sub(r"\n+", "\n\n", match.group(1))
        return f"\n{make_window(class_name, inner)}\n"
    return replacer


def wiki_window_replacer(match):

    inner = match.group(1)

    if inner.lstrip().startswith("\\"):
        idx = inner.find("\\")
        inner = inner[:idx] + inner[idx + 1:]
        return make_window("wiki-window", inner, "no-meta")

    return make_window("wiki-window", inner)


def system_window_replacer(match):

    inner = match.group(1)

    if inner.lstrip().startswith("\\"):
        idx = inner.find("\\")
        inner = inner[:idx] + inner[idx + 1:]
        return make_window("system-window", inner, "no-fl-dividers")

    return make_window("system-window", inner)


def record_window_replacer(match):

    inner = match.group(1)

    if inner.lstrip().startswith("\\"):
        idx = inner.find("\\")
        inner = inner[:idx] + inner[idx + 1:]
        return make_window("record-window", inner, "no-meta")

    return make_window("record-window", inner)


def note_window_replacer(match):

    inner = match.group(1)

    if inner.lstrip().startswith("\\"):
        idx = inner.find("\\")
        inner = inner[:idx] + inner[idx + 1:]
        return make_window("note-window", inner, "no-meta")

    return make_window("note-window", inner)


def debut_subs_replacer(text):
    """Convert }text} and {text{ sub markers (with optional [!] alert prefix)
    into their debut-achievement / alert-sub spans. Used across all debut
    star windows so clickable option entries render everywhere."""
    def sub_left(match):
        inner = match.group(1).strip()
        if inner.startswith("[!]"):
            return f'<span class="alert-sub alert-sub-left">{inner[3:].strip()}</span>'
        return f'<span class="debut-achievement-sub debut-achievement-sub-left">{inner}</span>'

    def sub_right(match):
        inner = match.group(1).strip()
        if inner.startswith("[!]"):
            return f'<span class="alert-sub alert-sub-right">{inner[3:].strip()}</span>'
        return f'<span class="debut-achievement-sub debut-achievement-sub-right">{inner}</span>'

    text = re.sub(r"\}([^\n}]+)\}", sub_left, text)
    text = re.sub(r"\{([^\n{]+)\{", sub_right, text)
    return text


def debut_window_replacer(match):
    inner = match.group(1)
    lines = inner.split("\n")
    title = lines[0].strip()
    if title.startswith("\\"):
        title = ""
        lines[0] = lines[0][1:] if lines[0].startswith("\\") else lines[0]
        lines[0] = lines[0].strip()
    body_lines = []
    for line in (lines[1:] if title else lines):
        if line.startswith("\\"):
            body_lines.append(line[1:])
        else:
            m = re.match(r"^\s*\[(.+?)\]\s*$", line)
            if m:
                body_lines.append(f'<div class="debut-window-label">{m.group(1)}</div>')
            else:
                body_lines.append(line)
    body = "\n".join(body_lines).strip()
    title_html = f'<div class="debut-window-title">{title}</div>\n\n' if title else ""
    return make_window("debut-window", debut_subs_replacer(title_html + body))


def debut_alert_replacer(match):
    inner = match.group(1)
    if inner.lstrip().startswith("<p align="):
        inner = re.sub(r'^\s*<p\s+align="center">\s*', '', inner)
        return make_window("debut-alert debut-alert-center", debut_subs_replacer(inner))
    return make_window("debut-alert", debut_subs_replacer(inner))


def debut_achieve_replacer(match):
    inner = match.group(1)
    lines = inner.split("\n")
    title = lines[0].strip()
    if title.startswith("\\"):
        title = ""
        lines[0] = lines[0][1:] if lines[0].startswith("\\") else lines[0]
        lines[0] = lines[0].strip()
    body = "\n".join(lines[1:] if title else lines).strip()
    body = re.sub(
        r"\[\n([\s\S]*?)\n\]",
        lambda m: '<div class="debut-achievement-list">\n' +
            "\n".join(
                f'<div class="debut-achievement-list-item">{l.strip()}</div>'
                for l in m.group(1).strip().split("\n") if l.strip()
            ).replace(
                '</div>\n<div class="debut-achievement-list-item">',
                '</div>\n<div class="debut-achievement-list-divider"></div>\n<div class="debut-achievement-list-item">'
            ) +
            '\n</div>',
        body,
    )
    body = re.sub(
        r"^\s*\[(.+?)\]\s*$",
        lambda m: f'<div class="debut-achievement-list">\n<div class="debut-achievement-list-item">{m.group(1).strip()}</div>\n</div>',
        body,
        flags=re.MULTILINE,
    )

    title_html = f'<div class="debut-achievement-title">{title}</div>\n\n' if title else ""
    return make_window("debut-achievement", debut_subs_replacer(title_html + body))


def safe_html(text):
    """Escape HTML special characters but preserve existing HTML tags."""
    parts = re.split(r'(<[^>]*>)', text)
    result = []
    for i, part in enumerate(parts):
        if i % 2 == 1:
            result.append(part)
        else:
            result.append(html.escape(part))
    return ''.join(result)



# FOOTNOTES
# The same custom-tag replacements the main pipeline applies to
# chapter text, kept here so footnote content gets identical
# formatting when it is rendered into the tooltip and the bottom card.
FOOTNOTE_TAG_REPLACEMENTS = [
    (re.compile(r"\$\$(.*?)\$\$", re.DOTALL), r'<span class="handwritten">\1</span>'),
    (re.compile(r"\$s(.+?)s\$", re.DOTALL), lambda m: smoke_replacer(m)),
    (re.compile(r"\$a(.+?)a\$", re.DOTALL), lambda m: aurora_replacer(m)),
    (re.compile(r"\$g(.+?)g\$", re.DOTALL), r'<span class="gold-text">\1</span>'),
    (re.compile(r"\$\*(.+?)\*\$", re.DOTALL), r'<span class="sparkle-text">\1</span>'),
    (re.compile(r"\$\((.+?)\)\$", re.DOTALL), r'<span class="moon-text">\1</span>'),
    (re.compile(r"\$ag(.+?)ag\$", re.DOTALL), lambda m: silver_replacer(m)),
    (re.compile(r"\$wo(.+?)wo\$", re.DOTALL), r'<span class="outline-white">\1</span>'),
    (re.compile(r"\$bo(.+?)bo\$", re.DOTALL), r'<span class="outline-black">\1</span>'),
    (re.compile(r"\$lat(.+?)lat\$", re.DOTALL), r'<span class="lato">\1</span>'),
    (re.compile(r"\$fox(.+?)fox\$", re.DOTALL), r'<span class="fox">\1</span>'),
    (re.compile(r"#hx\(([^)]+)\)(.*?)hx#", re.DOTALL),
     lambda m: f'<span style="color:{m.group(1)}">{m.group(2)}</span>'),
    (re.compile(r"\$hxo\(([^)]+)\)(.*?)hxo#", re.DOTALL),
     lambda m: f'<span class="hex-outline" style="--hxo-color:{m.group(1)}">{m.group(2)}</span>'),
    (re.compile(r"\$hxa\(([^)]+)\)\(([^)]+)\)\(([^)]+)\)(.*?)hxa\$", re.DOTALL),
     lambda m: hex_aurora_replacer(m)),
    (re.compile(r"\$hxas\(([^)]+)\)\(([^)]+)\)\(([^)]+)\)(.*?)hxas\$", re.DOTALL),
     lambda m: hex_aurora_static_replacer(m)),
    (re.compile(r"\$hxau\(([^)]+)\)\(([^)]+)\)\(([^)]+)\)(.*?)hxau\$", re.DOTALL),
     lambda m: hex_aurora_up_replacer(m)),
    (re.compile(r"\$hxaus\(([^)]+)\)\(([^)]+)\)\(([^)]+)\)(.*?)hxaus\$", re.DOTALL),
     lambda m: hex_aurora_up_static_replacer(m)),
    (re.compile(r"\|<(.+?)<\|", re.DOTALL), lambda m: scroll_replacer(m, "left")),
    (re.compile(r"\|>(.+?)>\|", re.DOTALL), lambda m: scroll_replacer(m, "right")),
]


def render_footnote_text(text):
    """Render footnote content with the same formatting as chapter text."""
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)

    link_placeholders = {}

    def save_markdown_link(m):
        key = f"\x00FN-L{len(link_placeholders)}\x00"
        link_placeholders[key] = f'<a href="{m.group(2).strip()}">{m.group(1).strip()}</a>'
        return key

    def save_bare_url(m):
        key = f"\x00FN-L{len(link_placeholders)}\x00"
        url = m.group(1)
        link_placeholders[key] = f'<a href="{url}">{url}</a>'
        return key

    text = re.sub(r"(?<!!)\[([^\]]+)\]\(([^)]+)\)", save_markdown_link, text)
    text = re.sub(r"(?<![\"'>])(https?://[^\s<>\"')]+)", save_bare_url, text)

    for pattern, repl in SIMPLE_REPLACEMENTS:
        text = pattern.sub(repl, text)
    for pattern, repl in FOOTNOTE_TAG_REPLACEMENTS:
        text = pattern.sub(repl, text)
    text = fix_underline(text)
    text = text.replace('\n\n', '<br><br>')
    text = text.replace('\n', '<br>')

    for key, val in link_placeholders.items():
        text = text.replace(key, val)
    return text


def fix_underline(text):
    """Convert [text]{.underline} to <span class="underline">text</span>.
    Uses bracket-depth counting to correctly handle nested brackets."""
    while True:
        marker = "{.underline}"
        idx = text.find(marker)
        if idx == -1:
            break
        close_bracket = idx - 1
        if close_bracket < 0 or text[close_bracket] != "]":
            break
        depth = 1
        pos = close_bracket - 1
        while pos >= 0 and depth > 0:
            ch = text[pos]
            if ch == "]":
                depth += 1
            elif ch == "[":
                depth -= 1
            pos -= 1
        if depth != 0:
            break
        open_bracket = pos + 1
        inner = text[open_bracket + 1 : close_bracket]
        text = (
            text[:open_bracket]
            + '<span class="underline">'
            + inner
            + "</span>"
            + text[idx + len(marker) :]
        )
    return text


def sms_window_replacer(match):
    inner = match.group(1)
    lines = inner.split("\n")
    speaker_colors = {
        'PMD': '#FFF8D9', 'SAH': '#FFF0E1', 'BSJ': '#EDF5FF',
        'LSJ': '#F2ECFF', 'KRB': '#FDE8F1', 'CE': '#FFE5E5',
        'RCW': '#EAF8F2'
    }
    html_parts = []
    for raw in lines:
        trimmed = raw.strip()
        if not trimmed:
            continue
        dash_left = re.match(r"^[-–—]\s*(.+)", trimmed)
        dash_right = re.match(r"(.+)\s*[-–—]$", trimmed)
        if dash_left:
            content = dash_left.group(1)
            sp = re.match(r"^(PMD|SAH|BSJ|LSJ|KRB|CE|RCW):\s*", content)
            color = speaker_colors[sp.group(1)] if sp else None
            display = fix_underline(safe_html(content[sp.end():] if sp else content))
            style = f' style="background:{color};color:#222"' if color else ''
            html_parts.append(f'<div class="sms-bubble sms-left"{style}>{display}</div>')
        elif dash_right:
            content = dash_right.group(1)
            sp = re.match(r"^(PMD|SAH|BSJ|LSJ|KRB|CE|RCW):\s*", content)
            color = speaker_colors[sp.group(1)] if sp else None
            display = fix_underline(safe_html(content[sp.end():] if sp else content))
            style = f' style="background:{color};color:#222"' if color else ''
            html_parts.append(f'<div class="sms-bubble sms-right"{style}>{display}</div>')
        else:
            html_parts.append(f'<div class="sms-bubble sms-center">{fix_underline(safe_html(trimmed))}</div>')
    return make_window("sms-window", "\n\n".join(html_parts))


def comment_window_replacer(match):
    inner = match.group(1)
    lines = inner.split("\n")
    title = ""
    desc = ""
    items = []
    in_comments = False

    for raw in lines:
        line = raw.strip()
        if line.startswith("["):
            title = fix_underline(safe_html(line.strip()))
        elif line.startswith(":"):
            desc = fix_underline(safe_html(line.replace(":", "", 1).strip()))
        elif line.startswith("-") or line.startswith("\u2013") or line.startswith("\u2014"):
            in_comments = True
            content = re.sub(r"^[\u2014\u2013-]", "", line).strip()
            items.append((fix_underline(safe_html(content)), 0))
        elif line.startswith("\u2937") or line.startswith("\u2514") or line.startswith("\u221F"):
            in_comments = True
            depth = 0
            content = line
            while content.startswith("\u2937") or content.startswith("\u2514") or content.startswith("\u221F"):
                depth += 1
                content = re.sub(r"^[\u2937\u2514\u221F]", "", content).lstrip()
            if depth > 3:
                depth = 3
            items.append((fix_underline(safe_html(content.strip())), depth))
        elif line and not in_comments:
            desc += ("" if not desc else "</p>\n<p>") + fix_underline(safe_html(line))

    html_parts = []
    if title or desc:
        html_parts.append('<div class="comment-post-header">')
        if title:
            html_parts.append(f'<div class="comment-post-title">{title}</div>')
        if desc:
            html_parts.append(f'<div class="comment-post-desc"><p>{desc}</p></div>')
        html_parts.append('</div>')
    if items:
        html_parts.append('<div class="comment-section">')
        for text, depth in items:
            if depth == 0:
                html_parts.append(f'<div class="comment">{text}</div>')
            else:
                html_parts.append(
                    f'<div class="comment-reply depth-{depth}">'
                    f'<span class="reply-icon">\u2937</span>'
                    f'<span class="reply-body">{text}</span></div>'
                )
        html_parts.append('</div>')
    return make_window("alert-window", "\n\n".join(html_parts))



# MAIN CONVERTER
def scroll_replacer(match, direction):
    inner = match.group(1)
    inner = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", inner)
    cls = "scroll-left" if direction == "left" else "scroll-right"
    return (
        f'<span class="scroll-wrap {cls}">'
        f'<span class="scroll-sizer"><span class="scroll-text">{inner}</span></span>'
        f'<span class="scroll-track">'
        f'<span class="scroll-text">{inner}</span>'
        f'<span class="scroll-text">{inner}</span>'
        f'</span></span>'
    )


def transition_replacer(match):
    duration = match.group(1)
    parts = [p.strip() for p in match.group(2).split(">")]
    if len(parts) > 6:
        return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", parts[0])
    dur_style = ""
    if duration and re.fullmatch(r"\d+(\.\d+)?(ms|s)", duration):
        dur_style = f"--tt-slot:{duration};"
    items = "".join(
        '<span class="transition-item" style="--tt-i:%d">%s</span>' % (
            i,
            re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", p),
        )
        for i, p in enumerate(parts)
    )
    return (
        '<span class="transition-text" data-count="%d" style="%s--tt-count:%d">%s</span>'
        % (len(parts), dur_style, len(parts), items)
    )


def convert_chapter(content, ctx):
    """Format a chapter with the exact build_web.py pipeline, then run pandoc.

    Returns (html_body, footnotes_html).
    """

    content = process_twitter_urls(content)

    tw_placeholders = {}
    def protect_twitter(text):
        def save(m):
            key = f"\x00TW{len(tw_placeholders)}\x00"
            tw_placeholders[key] = m.group(0)
            return key
        return re.sub(
            r'<div class="twitter-embed"[^>]*>.*?</div>\s*</div>',
            save,
            text,
            flags=re.DOTALL
        )
    content = protect_twitter(content)

    content = TRANSITION_TEXT_RE.sub(transition_replacer, content)

    footnotes = {}
    fn_placeholders = {}

    def footnote_ref_replacer(m):
        num = int(m.group(1))
        text = m.group(2)
        tip_html = render_footnote_text(text)
        key = f"\x00FN{len(fn_placeholders)}\x00"
        footnotes[num] = tip_html
        fn_placeholders[key] = (
            f'<a href="#fn-{num}" class="fn-ref" id="fn-ref-{num}">'
            f'[{num}]</a>'
        )
        return key

    content = FOOTNOTE_RE.sub(footnote_ref_replacer, content)

    content = SHAKE_RE.sub(r'<span class="shake">\1</span>', content)

    content = SHAKE_CHAR_RE.sub(shake_char_replacer, content)

    content = WAVE_RE.sub(wave_char_replacer, content)

    content = VISIBLE_HR_RE.sub('<hr class="visible-hr">', content)
    content = INVISIBLE_HR_RE.sub('<hr class="invisible-hr">', content)

    content = SUBTLEDISTORT_RE.sub(subtle_replacer, content)

    content = GROW_RE.sub(grow_replacer, content)

    content = SHRINK_RE.sub(shrink_replacer, content)

    img_placeholders = {}
    def protect_patterns(text):
        def save(key_store):
            def save_inner(m):
                key = f"\x00IMG{len(key_store)}\x00"
                key_store[key] = m.group(0)
                return key
            return save_inner
        text = re.sub(r'!\[.*?\]\(.*?\)', save(img_placeholders), text)
        return text
    content = protect_patterns(content)

    for pattern, repl in SIMPLE_REPLACEMENTS:
        content = pattern.sub(repl, content)

    content = TRIPLE_STRIKE_RE.sub(r'<span class="triple-strike">\1</span>', content)

    content = re.sub(r"\$\$(.*?)\$\$", r'<span class="handwritten">\1</span>', content, flags=re.DOTALL)

    content = SMOKE_RE.sub(smoke_replacer, content)

    content = AURORA_RE.sub(aurora_replacer, content)

    content = GOLD_RE.sub(r'<span class="gold-text">\1</span>', content)

    content = SPARKLE_RE.sub(r'<span class="sparkle-text">\1</span>', content)

    content = MOON_RE.sub(r'<span class="moon-text">\1</span>', content)

    content = SILVER_RE.sub(silver_replacer, content)

    content = OUTLINE_WHITE_RE.sub(r'<span class="outline-white">\1</span>', content)
    content = OUTLINE_BLACK_RE.sub(r'<span class="outline-black">\1</span>', content)

    content = HEX_COLOR_RE.sub(lambda m: f'<span style="color:{m.group(1)}">{m.group(2)}</span>', content)

    content = HEX_OUTLINE_RE.sub(
        lambda m: f'<span class="hex-outline" style="--hxo-color:{m.group(1)}">{m.group(2)}</span>',
        content
    )

    content = HEX_AURORA_RE.sub(hex_aurora_replacer, content)

    content = HEX_AURORA_STATIC_RE.sub(hex_aurora_static_replacer, content)

    content = HEX_AURORA_UP_RE.sub(hex_aurora_up_replacer, content)

    content = HEX_AURORA_UP_STATIC_RE.sub(hex_aurora_up_static_replacer, content)

    content = SCROLL_LEFT_RE.sub(lambda m: scroll_replacer(m, "left"), content)
    content = SCROLL_RIGHT_RE.sub(lambda m: scroll_replacer(m, "right"), content)

    for key, val in img_placeholders.items():
        content = content.replace(key, val)
    for key, val in tw_placeholders.items():
        content = content.replace(key, val)

    content = DISTORT_RE.sub(distorted_replacer, content)

    content = WIKI_WINDOW_RE.sub(wiki_window_replacer, content)

    content = BLACK_WINDOW_RE.sub(
        lambda m: make_window("black-window", m.group(1)),
        content
    )

    content = SYSTEM_WINDOW_RE.sub(system_window_replacer, content)

    content = PLAIN_WINDOW_RE.sub(
        lambda m: make_window("plain-window", m.group(1)),
        content
    )

    content = BARE_WINDOW_RE.sub(
        lambda m: make_window("bare-window", m.group(1)),
        content
    )

    content = RECORD_WINDOW_RE.sub(record_window_replacer, content)

    content = FOLLOWUP_WINDOW_RE.sub(
        lambda m: make_window("plain-window", m.group(1)),
        content
    )

    content = AMPERSAND_WINDOW_RE.sub(
        lambda m: make_window("followup-window", m.group(1)),
        content
    )

    content = NOTE_WINDOW_RE.sub(note_window_replacer, content)

    content = STICKY_WINDOW_RE.sub(
        lambda m: make_window("sticky-window", m.group(1)),
        content
    )

    content = PAPER_BOAT_WINDOW_RE.sub(
        lambda m: make_window("paper-boat", m.group(1)),
        content
    )

    content = BRAUN_WINDOW_RE.sub(
        lambda m: make_window("braun-screen", m.group(1)),
        content
    )

    content = BRAUN_TV_TEXT_RE.sub(braun_text_replacer("braun-tv-text"), content)
    content = BRAUN_DOLL_TEXT_RE.sub(braun_text_replacer("braun-doll-text"), content)
    content = PADDING_WINDOW_RE.sub(braun_text_replacer("padding-window"), content)

    content = DEBUT_ALERT_RE.sub(debut_alert_replacer, content)
    content = DEBUT_WINDOW_RE.sub(debut_window_replacer, content)
    content = DEBUT_ACHIEVE_RE.sub(debut_achieve_replacer, content)

    content = SMS_WINDOW_RE.sub(sms_window_replacer, content)
    content = COMMENT_WINDOW_RE.sub(comment_window_replacer, content)

    for key, val in fn_placeholders.items():
        content = content.replace(key, val)

    footnotes_html = ""
    if footnotes:
        lines = []
        for num in sorted(footnotes):
            lines.append(f'<li value="{num}" id="fn-{num}">{footnotes[num]} <a href="#fn-ref-{num}" class="fn-back" aria-label="Back to reference {num} in text">↩</a></li>')
        footnotes_html = '<div class="footnotes-section">\n<hr class="footnotes-divider" />\n<p class="footnotes-title">Footnotes</p>\n<ol>\n' + '\n'.join(lines) + '\n</ol>\n</div>\n'

    try:
        proc = subprocess.run(
            ["pandoc", "--from", "markdown-definition_lists+smart-tex_math_dollars-subscript-superscript-citations-pipe_tables-grid_tables", "--to", "html", "--quiet"],
            input=content.encode("utf-8"),
            capture_output=True,
            timeout=120
        )
        if proc.returncode != 0:
            err = proc.stderr.decode().strip()
            print(f"Pandoc error: {err}")
            return f"<p>Error converting content: {err}</p>", footnotes_html
        html_out = proc.stdout.decode("utf-8")
    except subprocess.TimeoutExpired:
        print("Pandoc timed out on a chapter — skipping")
        return "<p>Chapter skipped due to conversion timeout.</p>", footnotes_html
    except OSError as exc:
        print(f"Pandoc failed to run: {exc}")
        return f"<p>Error converting content: {exc}</p>", footnotes_html

    html_out = process_html_images(html_out, ctx)
    html_out = process_twitter_embeds(html_out, ctx)

    return html_out, footnotes_html



# IMAGE PROCESSING
def process_html_images(html_content: str, ctx: RenderContext) -> str:

    def replacer(match):
        full_tag = match.group(0)

        src_match = SRC_RE.search(full_tag)

        if not src_match:
            return full_tag

        original_src = src_match.group(1)

        if original_src.startswith("../Images/") or re.match(r"https?://", original_src, re.IGNORECASE):
            return full_tag

        image_path = resolve_local_image(original_src, ctx)

        if not image_path:
            print(f"      Warning: image not found for {ctx.chapter_path.name}: {original_src}")
            return full_tag

        if image_path.suffix.lower() == ".webp":
            png_path = convert_to_png(image_path, OUTPUT_DIR / "converted_images")
            if png_path:
                image_path = png_path

        asset = register_asset(ctx, image_path)

        new_tag = full_tag.replace(src_match.group(0), f'src="../{escape_attr(asset.href)}"')

        title_size = IMG_TITLE_SIZE_RE.search(new_tag)
        if title_size:
            width = title_size.group(1)
            new_tag = IMG_TITLE_SIZE_RE.sub("", new_tag)
            new_tag = new_tag.replace("<img", f'<img style="width:{width}"', 1)

        return new_tag

    return IMG_TAG_RE.sub(replacer, html_content)



# EPUB PACKAGING
XHTML_VOID_ELEMENTS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}


class _XhtmlTreeBuilder(HTMLParser):
    """Tolerant HTML→XHTML re-serializer.

    Chapter sources contain raw HTML (<br>, <u>, ...) that pandoc passes
    through verbatim, and the formatting pipeline can emit interleaved tags
    that pandoc re-nests incorrectly (e.g. emphasis markers inside
    per-character effect spans). Browsers heal that on the website, but EPUB
    XHTML must be well-formed XML, so bodies are re-serialized with balanced
    tags, self-closed void elements and escaped text.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self.open_stack: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in XHTML_VOID_ELEMENTS:
            self.out.append(self._format_tag(tag, attrs, self_closing=True))
            return
        self.out.append(self._format_tag(tag, attrs, self_closing=False))
        self.open_stack.append(tag)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.out.append(self._format_tag(tag.lower(), attrs, self_closing=True))

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in XHTML_VOID_ELEMENTS:
            return
        if tag in self.open_stack:
            while self.open_stack:
                open_tag = self.open_stack.pop()
                self.out.append(f"</{open_tag}>")
                if open_tag == tag:
                    break

    def handle_data(self, data: str) -> None:
        self.out.append(html.escape(data, quote=False))

    def handle_comment(self, data: str) -> None:
        self.out.append(f"<!--{data}-->")

    @staticmethod
    def _format_tag(
        tag: str,
        attrs: list[tuple[str, str | None]],
        self_closing: bool,
    ) -> str:
        parts = [tag]
        for name, value in attrs:
            name = name.lower()
            if value is None:
                parts.append(f'{name}="{name}"')
            else:
                parts.append(f'{name}="{html.escape(value, quote=True)}"')
        closing = " />" if self_closing else ">"
        return "<" + " ".join(parts) + closing

    def result(self) -> str:
        while self.open_stack:
            self.out.append(f"</{self.open_stack.pop()}>")
        return "".join(self.out)


def to_xhtml(body: str) -> str:
    builder = _XhtmlTreeBuilder()
    builder.feed(body)
    builder.close()
    return builder.result()


def xhtml_page(title: str, body: str) -> str:
    body = to_xhtml(body)
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<!DOCTYPE html>\n'
        '<html xmlns="http://www.w3.org/1999/xhtml">'
        f"<head><title>{escape_text(title)}</title>"
        '<link href="../Styles/stylesheet.css" type="text/css" rel="stylesheet" />'
        f"</head><body>{body}</body></html>\n"
    )


def nav_xhtml(book_title: str, items: list[EpubItem]) -> str:
    links = "\n".join(
        f'<li><a href="{escape_attr(item.href)}">{escape_text(item.title)}</a></li>'
        for item in items
    )
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<!DOCTYPE html>\n'
        '<html xmlns="http://www.w3.org/1999/xhtml" '
        'xmlns:epub="http://www.idpf.org/2007/ops">'
        f"<head><title>{escape_text(book_title)} Table of Contents</title>"
        '<link href="Styles/stylesheet.css" type="text/css" rel="stylesheet" />'
        "</head><body>"
        '<nav epub:type="toc" id="toc"><h1>Table of Contents</h1>'
        f"<ol>{links}</ol></nav></body></html>\n"
    )


def content_opf(
    book_title: str,
    metadata: dict[str, Any],
    items: list[EpubItem],
    assets: list[EpubAsset],
    modified: str,
    cover_asset: EpubAsset | None = None,
    cover_item: EpubItem | None = None,
) -> str:
    language = metadata_text(metadata.get("language"), "en")
    creator = metadata_text(metadata.get("creator"), "unknown")
    contributor = metadata_text(metadata.get("contributor"), "")
    publisher = metadata_text(metadata.get("publisher"), "GSGW-Reader")
    description = metadata_text(metadata.get("description"), "")
    rights = metadata_text(metadata.get("rights"), "")
    identifier = metadata_text(metadata.get("identifier"), "")
    identifier = valid_identifier(identifier, book_title)

    manifest_items = [
        '<item href="Styles/stylesheet.css" id="stylesheet" media-type="text/css"/>',
        '<item href="toc.ncx" id="ncx" media-type="application/x-dtbncx+xml"/>',
        '<item href="nav.xhtml" id="nav" media-type="application/xhtml+xml" properties="nav"/>',
    ]
    if cover_item:
        manifest_items.append(
            f'<item href="{escape_attr(cover_item.href)}" id="{cover_item.item_id}" '
            'media-type="application/xhtml+xml"/>'
        )
    for item in items:
        manifest_items.append(
            f'<item href="{escape_attr(item.href)}" id="{item.item_id}" '
            'media-type="application/xhtml+xml"/>'
        )
    for idx, asset in enumerate(assets):
        if cover_asset and asset.source_path == cover_asset.source_path:
            manifest_items.append(
                f'<item href="{escape_attr(asset.href)}" id="cover-image" '
                f'media-type="{escape_attr(asset.media_type)}" properties="cover-image"/>'
            )
        else:
            manifest_items.append(
                f'<item href="{escape_attr(asset.href)}" id="image{idx:04d}" '
                f'media-type="{escape_attr(asset.media_type)}"/>'
            )

    FONT_FILES = [
        ("Fonts/ComicNeue-Regular.woff2", "font-comic-neue-regular", "font/woff2"),
        ("Fonts/ComicNeue-Bold.woff2", "font-comic-neue-bold", "font/woff2"),
        ("Fonts/Caveat-Variable.woff2", "font-caveat", "font/woff2"),
        ("Fonts/Lato-Regular.woff2", "font-lato-regular", "font/woff2"),
        ("Fonts/Lato-Bold.woff2", "font-lato-bold", "font/woff2"),
        ("Fonts/Lato-Italic.woff2", "font-lato-italic", "font/woff2"),
        ("Fonts/Lato-BoldItalic.woff2", "font-lato-bold-italic", "font/woff2"),
        ("Fonts/GowunBatang-Regular.woff2", "font-gowun-batang-regular", "font/woff2"),
        ("Fonts/GowunBatang-Bold.woff2", "font-gowun-batang-bold", "font/woff2"),
        ("Fonts/PauloBittencourt-Regular.ttf", "font-paulo-bittencourt-regular", "font/sfnt"),
        ("Fonts/PauloBittencourt-Bold.ttf", "font-paulo-bittencourt-bold", "font/sfnt"),
        ("Fonts/NanumBarunGothic.woff2", "font-nanum-barun-gothic", "font/woff2"),
        ("Fonts/NanumBarunGothicBold.woff2", "font-nanum-barun-gothic-bold", "font/woff2"),
        ("Fonts/ChungjuKimSaeng.ttf", "font-chungju-kimsaeng", "font/sfnt"),
        ("Fonts/VCR_OSD_MONO_1.001.ttf", "font-vcr-osd-mono", "font/sfnt"),
        ("Fonts/GabiaMaeumgyeol.woff2", "font-gabia-maeumgyeol", "font/woff2"),
    ]
    for href, fid, media in FONT_FILES:
        manifest_items.append(
            f'<item href="{escape_attr(href)}" id="{fid}" media-type="{media}"/>'
        )

    spine_items = []
    if cover_item:
        spine_items.append(f'<itemref idref="{cover_item.item_id}"/>')
    spine_items.extend(f'<itemref idref="{item.item_id}"/>' for item in items)
    spine = "\n".join(spine_items)

    meta_lines = [
        f'<dc:title>{escape_text(book_title)}</dc:title>',
        f'<dc:language>{escape_text(language)}</dc:language>',
        f'<dc:identifier id="BookId">{escape_text(identifier)}</dc:identifier>',
        f'<dc:creator>{escape_text(creator)}</dc:creator>',
        f'<dc:publisher>{escape_text(publisher)}</dc:publisher>',
        f'<dc:date>{escape_text(dt.date.today().isoformat())}</dc:date>',
        f'<meta property="dcterms:modified">{escape_text(modified)}</meta>',
        f'<dc:source>{escape_text(EPUB_SOURCE_URL)}</dc:source>',
    ]
    if cover_asset:
        meta_lines.append('<meta name="cover" content="cover-image"/>')
    if contributor:
        meta_lines.append(f'<dc:contributor>{escape_text(contributor)}</dc:contributor>')
    if description:
        meta_lines.append(f'<dc:description>{escape_text(description)}</dc:description>')
    if rights:
        meta_lines.append(f'<dc:rights>{escape_text(rights)}</dc:rights>')

    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<package xmlns="http://www.idpf.org/2007/opf" version="3.0" '
        'unique-identifier="BookId">'
        '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">'
        + "".join(meta_lines)
        + "</metadata><manifest>"
        + "".join(manifest_items)
        + f'</manifest><spine toc="ncx">{spine}</spine></package>\n'
    )


def toc_ncx(book_title: str, identifier: str, items: list[EpubItem]) -> str:
    nav_points = []
    for order, item in enumerate(items, start=1):
        nav_points.append(
            f'<navPoint id="navPoint-{order}" playOrder="{order}">'
            f"<navLabel><text>{escape_text(item.title)}</text></navLabel>"
            f'<content src="{escape_attr(item.href)}"/>'
            "</navPoint>"
        )

    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">'
        "<head>"
        f'<meta name="dtb:uid" content="{escape_attr(identifier)}"/>'
        '<meta name="dtb:depth" content="1"/>'
        '<meta name="dtb:totalPageCount" content="0"/>'
        '<meta name="dtb:maxPageNumber" content="0"/>'
        "</head>"
        f"<docTitle><text>{escape_text(book_title)}</text></docTitle>"
        "<navMap>"
        + "".join(nav_points)
        + "</navMap></ncx>\n"
    )


def container_xml() -> str:
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
        "<rootfiles>"
        '<rootfile full-path="OEBPS/content.opf" '
        'media-type="application/oebps-package+xml"/>'
        "</rootfiles></container>\n"
    )


def write_epub(
    epub_path: Path,
    book_title: str,
    metadata: dict[str, Any],
    items: list[EpubItem],
    assets: dict[Path, EpubAsset],
    cover_item: EpubItem | None = None,
    cover_asset: EpubAsset | None = None,
) -> None:
    css = CSS_PATH.read_text(encoding="utf-8")
    modified = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    identifier = metadata_text(metadata.get("identifier"), "")
    identifier = valid_identifier(identifier, book_title)
    asset_list = sorted(assets.values(), key=lambda asset: asset.href)

    epub_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(epub_path, "w") as zf:
        mimetype = zipfile.ZipInfo("mimetype")
        mimetype.compress_type = zipfile.ZIP_STORED
        zf.writestr(mimetype, "application/epub+zip")

        def write_text(name: str, data: str) -> None:
            zf.writestr(name, data.encode("utf-8"), compress_type=zipfile.ZIP_DEFLATED)

        write_text("META-INF/container.xml", container_xml())
        write_text("OEBPS/Styles/stylesheet.css", css)
        write_text("OEBPS/content.opf", content_opf(book_title, metadata, items, asset_list, modified, cover_asset, cover_item))
        write_text("OEBPS/toc.ncx", toc_ncx(book_title, identifier, items))
        write_text("OEBPS/nav.xhtml", nav_xhtml(book_title, items))

        if cover_item:
            write_text(f"OEBPS/{cover_item.href}", xhtml_page(cover_item.title, cover_item.body))

        for item in items:
            write_text(f"OEBPS/{item.href}", xhtml_page(item.title, item.body))

        for asset in asset_list:
            zf.write(asset.source_path, f"OEBPS/{asset.href}", compress_type=zipfile.ZIP_DEFLATED)

        _write_epub_fonts(zf)


def _write_epub_fonts(zf: zipfile.ZipFile) -> None:
    font_names = [
        "ComicNeue-Regular.woff2", "ComicNeue-Bold.woff2",
        "Caveat-Variable.woff2",
        "Lato-Regular.woff2", "Lato-Bold.woff2", "Lato-Italic.woff2", "Lato-BoldItalic.woff2",
        "GowunBatang-Regular.woff2", "GowunBatang-Bold.woff2",
        "PauloBittencourt-Regular.ttf", "PauloBittencourt-Bold.ttf",
        "NanumBarunGothic.woff2", "NanumBarunGothicBold.woff2",
        "ChungjuKimSaeng.ttf",
        "VCR_OSD_MONO_1.001.ttf",
        "GabiaMaeumgyeol.woff2",
    ]
    for font_name in font_names:
        src = FONTS_DIR / font_name
        if src.exists():
            zf.write(src, f"OEBPS/Fonts/{font_name}", compress_type=zipfile.ZIP_DEFLATED)



# CHAPTER LOADING
def find_chapter_dirs(book_id: str) -> list[Path]:
    root = CHAPTERS_ROOT / book_id
    if book_id == "gsgw":
        return [root / "fantl", root / "unfinishedtl", root / "MTL"]
    if book_id == "debut":
        return [root / "DebutFormatted", root / "DebutPlainTxt"]
    return []


def load_all_chapters(chapter_dirs: list[Path], limit: int | None = None) -> list[Chapter]:
    chapters: list[Chapter] = []
    total_files = 0
    for dir_path in chapter_dirs:
        chapter_files = sorted(path for path in dir_path.glob("*.md") if path.name != "metadata.md")
        remaining = None
        if limit is not None:
            remaining = limit - total_files
            if remaining <= 0:
                break
            chapter_files = chapter_files[:remaining]
        for fallback, path in enumerate(chapter_files):
            metadata, content = load_markdown(path)
            title = first_heading(content) or metadata_text(metadata.get("title"), path.stem)
            slug = metadata_text(metadata.get("slug"), path.stem)
            chapters.append(
                Chapter(
                    path=path, metadata=metadata, content=content,
                    title=title, index=sort_value(metadata, fallback), slug=slug,
                )
            )
            total_files += 1
    chapters.sort(key=lambda c: (c.index, c.path.name))
    return chapters


def chapter_in_part(chapter: Chapter, part_def: dict[str, Any]) -> bool:
    if "category" in part_def:
        return chapter.metadata.get("category") == part_def["category"]
    if "max_index" in part_def and chapter.index > part_def["max_index"]:
        return False
    if "min_index" in part_def and chapter.index < part_def["min_index"]:
        return False
    return True


def chapter_output_name(position: int, chapter: Chapter) -> str:
    title = safe_id(chapter.title.replace(".", ""), f"chapter_{position}")
    return f"{position:04d}_{title}.xhtml"



# BUILD
def build_book(args: argparse.Namespace) -> list[Path]:
    book_id = args.book
    chapter_dirs = find_chapter_dirs(book_id)
    if not chapter_dirs:
        print(f"No chapter directories found for book '{book_id}'")
        return []

    metadata_path = chapter_dirs[0] / "metadata.md"
    if not metadata_path.exists():
        print(f"No metadata.md found in {chapter_dirs[0]}")
        return []

    master_meta, master_content = load_markdown(metadata_path)
    book_title = metadata_text(master_meta.get("title"), book_id)
    part_defs = PART_DEFS.get(book_id, [])
    variants = VARIANTS.get(book_id, [])

    if not part_defs:
        print(f"No part definitions for book '{book_id}'")
        return []

    chapters = load_all_chapters(chapter_dirs, args.limit)
    if not chapters:
        print("No chapters found")
        return []

    print(f"Loaded {len(chapters)} chapters for {book_title}")

    today = dt.date.today()
    pretty_date = f"{today:%B} {today.day}, {today:%Y}"
    master_content = master_content.replace("{{DATE}}", pretty_date)

    built: list[Path] = []
    cover_asset_base: EpubAsset | None = None
    cover_item_base: EpubItem | None = None
    cover_image_path_base = IMAGES_ROOT / BOOK_COVER_DIR.get(book_id, book_id) / "cover.webp"

    if cover_image_path_base.exists():
        cover_src = convert_to_png(cover_image_path_base, OUTPUT_DIR / "cover_images") or cover_image_path_base
        cover_name = unique_asset_name(
            cover_src,
            "cover.png" if cover_src.suffix.lower() == ".png" else cover_src.name,
            set(),
        )
        cover_asset_base = EpubAsset(
            source_path=cover_src,
            href=f"Images/{cover_name}",
            media_type=media_type_for(cover_src),
        )
        cover_body = (
            '<div class="cover-page">'
            f'<img src="../{escape_attr(cover_asset_base.href)}" alt="Cover" class="cover-image" />'
            "</div>"
        )
        cover_item_base = EpubItem(
            item_id="cover",
            href="Text/cover.xhtml",
            title="Cover",
            body=cover_body,
        )
        print(f"  Cover: {cover_asset_base.href}")

    if args.variant:
        variants = [v for v in variants if v["id"] == args.variant]
    if args.part:
        part_defs = [p for p in part_defs if p["id"] == args.part]
    if args.chapter is not None:
        if args.chapter < 1 or args.chapter > len(chapters):
            print(f"Chapter {args.chapter} out of range (1-{len(chapters)})")
            return []
        chapters = [chapters[args.chapter - 1]]
        print(f"  Building chapter {args.chapter}: {chapters[0].title}")

    tweet_cache = load_tweet_cache()
    fetch_twitter = not args.no_fetch_twitter

    for variant in variants:
        variant_label = variant["label"]
        print(f"\nBuilding {variant_label} variant...")

        for part_def in part_defs:
            part_chapters = [c for c in chapters if chapter_in_part(c, part_def)]
            if not part_chapters:
                print(f"  {part_def['label']}: no chapters, skipping")
                continue

            print(f"  {part_def['label']} ({part_def['range']}): {len(part_chapters)} chapters")

            full_name = sanitize_filename(book_title)
            output_name = f"{full_name} - {part_def['label']} [{variant_label}]"
            output_name = re.sub(r'[ ,]', '.', output_name).replace('[', '').replace(']', '')
            output_name = re.sub(r'\.+', '.', output_name) + '.epub'
            epub_path = OUTPUT_DIR / output_name

            assets: dict[Path, EpubAsset] = {}
            asset_names: set[str] = set()
            cover_asset = None
            cover_item = None

            if cover_asset_base:
                cover_asset = cover_asset_base
                asset_names.add(Path(cover_asset.href).name)
                assets[cover_asset.source_path] = cover_asset
                cover_item = cover_item_base

            info_ctx = RenderContext(book_id, metadata_path, assets, asset_names, tweet_cache, fetch_twitter)
            info_body, info_footnotes = convert_chapter(master_content, info_ctx)
            if info_footnotes:
                info_body += "\n" + info_footnotes

            items: list[EpubItem] = [
                EpubItem(
                    item_id="xhtml0000",
                    href="Text/0000_Information.xhtml",
                    title="Information",
                    body=info_body,
                )
            ]

            for position, chapter in enumerate(part_chapters, start=1):
                print(f"    [{position}/{len(part_chapters)}] {chapter.title}")
                ctx = RenderContext(book_id, chapter.path, assets, asset_names, tweet_cache, fetch_twitter)
                body, footnotes_html = convert_chapter(chapter.content, ctx)
                if footnotes_html:
                    body += "\n" + footnotes_html
                items.append(
                    EpubItem(
                        item_id=f"xhtml{position:04d}",
                        href=f"Text/{chapter_output_name(position, chapter)}",
                        title=chapter.title,
                        body=body,
                    )
                )

            write_epub(epub_path, book_title, master_meta, items, assets, cover_item, cover_asset)

            print(f"    Done -> {epub_path}")
            built.append(epub_path)

    save_tweet_cache(tweet_cache)
    return built


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build per-part EPUBs from chapter markdown using the build_web.py formatting pipeline.")
    parser.add_argument("--book", default="gsgw", help="Book folder under chapters/ to build.")
    parser.add_argument("--limit", type=int, help="Build only the first N chapters total, useful for testing.")
    parser.add_argument("--variant", help="Build only this variant (e.g. plaintext, windows).")
    parser.add_argument("--part", help="Build only this part (e.g. part1, part2).")
    parser.add_argument("--chapter", type=int, help="Build only this chapter number (1-based index within the book).")
    parser.add_argument("--no-fetch-twitter", action="store_true", help="Use cached Twitter WebPs only; leave missing tweet images as links.")
    return parser.parse_args()


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = parse_args()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    built = build_book(args)

    if not built:
        print("No EPUBs built.")
        return

    print("\nBuilt EPUBs:")
    for path in built:
        print(f"  {path}")


if __name__ == "__main__":
    main()
