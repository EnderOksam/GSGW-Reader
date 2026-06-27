from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import json
import posixpath
import re
import sys
import urllib.parse
import urllib.request
import uuid
import zipfile
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any

try:
    from PIL import Image
except Exception:  # Pillow is optional unless Twitter images need conversion.
    Image = None


SCRIPT_DIR = Path(__file__).parent.resolve()
REPO_ROOT = SCRIPT_DIR.parent
CHAPTERS_ROOT = REPO_ROOT / "chapters"
IMAGES_ROOT = REPO_ROOT / "images"
CSS_PATH = SCRIPT_DIR / "epub.css"

OUTPUT_DIR = SCRIPT_DIR / "epub"
TWITTER_IMG_DIR = OUTPUT_DIR / "twitter_images"
TWEET_CACHE_PATH = TWITTER_IMG_DIR / "cache.json"

EPUB_SOURCE_URL = "https://ireum.pages.dev"

UA = "GSGW-Reader-EPUB/2.0"

TWITTER_RE = re.compile(
    r"https?://(?:x|twitter)\.com/([A-Za-z0-9_]+)/status/(\d+)"
    r"(?:/photo/(\d+))?(?:\?[^\s<>\"')]+)?",
    re.IGNORECASE,
)

IMAGE_RE = re.compile(r"!\[([\s\S]*?)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
LINK_RE = re.compile(r"(?<!!)\[([^\]]+)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")


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


class RenderContext:
    def __init__(
        self,
        book_id: str,
        chapter_path: Path,
        assets: dict[Path, EpubAsset],
        asset_names: set[str],
        tweet_cache: dict[str, Any],
        fetch_twitter: bool,
    ) -> None:
        self.book_id = book_id
        self.chapter_path = chapter_path
        self.assets = assets
        self.asset_names = asset_names
        self.tweet_cache = tweet_cache
        self.fetch_twitter = fetch_twitter


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
    image = Image.open(BytesIO(image_bytes))
    TWITTER_IMG_DIR.mkdir(parents=True, exist_ok=True)
    image.save(webp_path, "WEBP", quality=88, method=6)
    return webp_path, screen_name


def twitter_image_html(match: re.Match[str], ctx: RenderContext) -> str:
    username = match.group(1)
    tweet_id = match.group(2)
    photo_index = int(match.group(3) or 1)
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
        asset = register_asset(ctx, webp_path, webp_path.name)
        display_name = screen_name or username
        alt = f"Illustration from @{display_name} on X"
        return image_block_html(f"../{asset.href}", alt)

    url = match.group(0)
    return f'<p><a href="{escape_attr(url)}">{escape_text(url)}</a></p>'


def resolve_local_image(src: str, ctx: RenderContext) -> Path | None:
    clean_src = urllib.parse.unquote(src.split("#", 1)[0].split("?", 1)[0])
    src_path = Path(clean_src.replace("/", "\\"))

    candidates = []
    if src_path.is_absolute():
        candidates.append(src_path)
    else:
        candidates.extend(
            [
                ctx.chapter_path.parent / src_path,
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


def escape_text(value: Any) -> str:
    return html.escape(str(value), quote=False)


def escape_attr(value: Any) -> str:
    return html.escape(str(value), quote=True)


def image_block_html(src: str, alt: str = "") -> str:
    alt_attr = escape_attr(strip_markup(alt))
    img = f'<img src="{escape_attr(src)}" alt="{alt_attr}" />'
    if alt_attr:
        return f'<div class="image-block">{img}<div class="thumbcaption">{alt_attr}</div></div>'
    return f'<div class="image-block">{img}</div>'


def markdown_image_html(alt: str, src: str, ctx: RenderContext) -> str:
    src = src.strip()
    twitter_match = TWITTER_RE.fullmatch(src)
    if twitter_match:
        return twitter_image_html(twitter_match, ctx)

    if re.match(r"https?://", src, re.IGNORECASE):
        return image_block_html(src, alt)

    image_path = resolve_local_image(src, ctx)
    if not image_path:
        print(f"      Warning: image not found for {ctx.chapter_path.name}: {src}")
        return f'<p>{escape_text(alt or src)}</p>'

    asset = register_asset(ctx, image_path)
    return image_block_html(f"../{asset.href}", alt)


def stash_html(store: dict[str, str], value: str) -> str:
    key = f"\x00HTML{len(store)}\x00"
    store[key] = value
    return key


def protect_escapes(text: str, store: dict[str, str]) -> str:
    out: list[str] = []
    i = 0
    escapable = "\\`*_{}[]()#+-.!<>~"

    while i < len(text):
        if text[i] == "\\" and i + 1 < len(text) and text[i + 1] in escapable:
            out.append(stash_html(store, escape_text(text[i + 1])))
            i += 2
            continue
        out.append(text[i])
        i += 1

    return "".join(out)


def wrap_inline(
    text: str,
    pattern: str,
    wrapper: str,
    store: dict[str, str],
    ctx: RenderContext,
    flags: int = re.DOTALL,
) -> str:
    regex = re.compile(pattern, flags)

    def repl(match: re.Match[str]) -> str:
        inner = render_inline(match.group(1), ctx)
        return stash_html(store, wrapper.format(inner=inner))

    return regex.sub(repl, text)


def char_span_html(text: str, class_name: str, ctx: RenderContext) -> str:
    rendered = render_inline(text, ctx)
    return f'<span class="{class_name}">{rendered}</span>'


def render_inline(text: str, ctx: RenderContext) -> str:
    text = normalize_newlines(text)
    text = re.sub(r" {2,}\n", "\n<br />\n", text)
    text = text.replace("\n", " ")

    store: dict[str, str] = {}
    text = protect_escapes(text, store)

    def code_repl(match: re.Match[str]) -> str:
        return stash_html(store, f"<code>{escape_text(match.group(1))}</code>")

    text = re.sub(r"`([^`]+)`", code_repl, text)

    def image_repl(match: re.Match[str]) -> str:
        return stash_html(store, markdown_image_html(match.group(1), match.group(2), ctx))

    text = IMAGE_RE.sub(image_repl, text)

    def link_repl(match: re.Match[str]) -> str:
        label = render_inline(match.group(1), ctx)
        url = escape_attr(match.group(2))
        return stash_html(store, f'<a href="{url}">{label}</a>')

    text = LINK_RE.sub(link_repl, text)

    custom_wrappers = [
        (r"@@(.+?)@@", '<span class="glitch-text">{inner}</span>'),
        (r"@_@(.+?)@_@", '<span class="glitch-subtle">{inner}</span>'),
        (r"\$s(.+?)s\$", '<span class="smoke-text">{inner}</span>'),
        (r"@ll@(.+?)@ll@", '<span class="mono mono-left">{inner}</span>'),
        (r"@rr@(.+?)@rr@", '<span class="mono mono-right">{inner}</span>'),
        (r"@l@(.+?)@l@", '<span class="align-left">{inner}</span>'),
        (r"@r@(.+?)@r@", '<span class="align-right">{inner}</span>'),
        (r"@rs@(.+?)@rs@", '<span class="align-right window-small">{inner}</span>'),
        (r"#><(.+?)><#", '<span class="text-large-centered">{inner}</span>'),
        (r"#\*(.+?)\*#", '<span class="text-large">{inner}</span>'),
        (r"#f>#(.+?)#f>#", '<span class="text-fade-right">{inner}</span>'),
        (r"#f<#(.+?)#f<#", '<span class="text-fade-left">{inner}</span>'),
        (r"#f#(.+?)#f#", '<span class="text-faded">{inner}</span>'),
        (r"(?<!\\)\-#\s*(.+?)\s*#-(?!\\)", '<span class="text-sub">{inner}</span>'),
        (r"#r(.+?)r#", '<span class="text-red">{inner}</span>'),
        (r"#b(.+?)b#", '<span class="text-blue">{inner}</span>'),
        (r"#y(.+?)y#", '<span class="text-yellow">{inner}</span>'),
        (r"#p(.+?)p#", '<span class="text-magenta">{inner}</span>'),
        (r"#g(.+?)g#", '<span class="text-green">{inner}</span>'),
        (r"#o(.+?)o#", '<span class="text-orange">{inner}</span>'),
        (r";r(.+?)r;", '<span class="hl-red">{inner}</span>'),
        (r";b(.+?)b;", '<span class="hl-blue">{inner}</span>'),
        (r";y(.+?)y;", '<span class="hl-yellow">{inner}</span>'),
        (r";p(.+?)p;", '<span class="hl-magenta">{inner}</span>'),
        (r";g(.+?)g;", '<span class="hl-green">{inner}</span>'),
        (r";o(.+?)o;", '<span class="hl-orange">{inner}</span>'),
        (r"%%(.+?)%%", '<span class="shake">{inner}</span>'),
        (r"%~(.+?)~%", '<span class="shake">{inner}</span>'),
        (r"%\^(.+?)\^%", '<span class="wave-up">{inner}</span>'),
        (r"#\^#(.+?)#\^#", '<span class="text-grow">{inner}</span>'),
        (r"#v#(.+?)#v#", '<span class="text-grow">{inner}</span>'),
        (r"\$\$(.+?)\$\$", '<span class="handwritten">{inner}</span>'),
        (r"\$c(.+?)c\$", '<span class="contaminated">{inner}</span>'),
        (r"\$a(.+?)a\$", '<span class="aurora-text">{inner}</span>'),
        (r"\$g(.+?)g\$", '<span class="gold-text">{inner}</span>'),
        (r"\$\*(.+?)\*\$", '<span class="sparkle-text">{inner}</span>'),
        (r"\$\((.+?)\)\$", '<span class="moon-text">{inner}</span>'),
    ]

    for pattern, wrapper in custom_wrappers:
        text = wrap_inline(text, pattern, wrapper, store, ctx)

    markdown_wrappers = [
        (r"~~(.+?)~~", "<del>{inner}</del>"),
        (r"(?<!\*)\*\*\*(.+?)\*\*\*(?!\*)", "<strong><em>{inner}</em></strong>"),
        (r"(?<!\*)\*\*(.+?)\*\*(?!\*)", "<strong>{inner}</strong>"),
        (r"(?<!\*)\*(.+?)\*(?!\*)", "<em>{inner}</em>"),
        (r"_(.+?)_", '<span class="underline">{inner}</span>'),
    ]

    for pattern, wrapper in markdown_wrappers:
        text = wrap_inline(text, pattern, wrapper, store, ctx)

    escaped = escape_text(text)
    resolved: dict[str, str] = {}

    def resolve_placeholder(key: str, seen: set[str]) -> str:
        if key in resolved:
            return resolved[key]
        value = store[key]
        for nested_key in store:
            if nested_key not in value:
                continue
            if nested_key in seen:
                value = value.replace(nested_key, "")
            else:
                value = value.replace(
                    nested_key,
                    resolve_placeholder(nested_key, seen | {nested_key}),
                )
        resolved[key] = value
        return value

    for key in sorted(store, key=len, reverse=True):
        if key in escaped:
            escaped = escaped.replace(key, resolve_placeholder(key, {key}))
    return escaped


def is_hr_line(line: str) -> bool:
    stripped = line.strip()
    return stripped in {"~~~", "---", "***", "* * *"}


WINDOW_PATTERNS = [
    ("wiki-window", re.compile(r"^\+-+$"), re.compile(r"^-+\+$")),
    ("record-window", re.compile(r"^&-+$"), re.compile(r"^-+&$")),
    ("black-window", re.compile(r"^\+=$"), re.compile(r"^=\+$")),
    ("system-window", re.compile(r"^\+~$"), re.compile(r"^~\+$")),
    ("plain-window", re.compile(r"^\+\$$"), re.compile(r"^\$\+$")),
    ("followup-window", re.compile(r"^&\$$"), re.compile(r"^\$&$")),
    ("note-window", re.compile(r"^!-+$"), re.compile(r"^-+!$")),
    ("sticky-window", re.compile(r"^!\$$"), re.compile(r"^\$!$")),
    ("braun-screen", re.compile(r"^!\[$"), re.compile(r"^\]!$")),
]


def window_spec(line: str) -> tuple[str, re.Pattern[str]] | None:
    stripped = line.strip()
    for class_name, start_re, end_re in WINDOW_PATTERNS:
        if start_re.match(stripped):
            return class_name, end_re
    return None


def strip_leading_escape(inner: str) -> str:
    match = re.search(r"\S", inner)
    if match and inner[match.start()] == "\\":
        return inner[: match.start()] + inner[match.start() + 1 :]
    return inner


def is_block_start(line: str) -> bool:
    return bool(
        window_spec(line)
        or is_hr_line(line)
        or re.match(r"^\^\^\s*$", line)
        or re.match(r"^#{1,6}\s+", line)
        or re.match(r"^(```|~~~[A-Za-z0-9_-]+)", line.strip())
        or re.match(r"^>\s?", line)
        or re.match(r"^([-+*]|\d+\.)\s+\S", line)
    )


def render_list(lines: list[str], start: int, ctx: RenderContext) -> tuple[str, int]:
    first = lines[start]
    ordered = bool(re.match(r"^\d+\.\s+\S", first))
    tag = "ol" if ordered else "ul"
    items: list[str] = []
    i = start

    while i < len(lines):
        line = lines[i]
        match = re.match(r"^(?:[-+*]|\d+\.)\s+(.+)$", line)
        if not match:
            break
        items.append(f"<li>{render_inline(match.group(1), ctx)}</li>")
        i += 1

    return f"<{tag}>" + "".join(items) + f"</{tag}>", i


def render_standalone_image_paragraph(text: str, ctx: RenderContext) -> str | None:
    stripped = text.strip()
    twitter_match = TWITTER_RE.fullmatch(stripped)
    if twitter_match:
        return twitter_image_html(twitter_match, ctx)

    matches = list(IMAGE_RE.finditer(stripped))
    if not matches:
        return None

    cursor = 0
    parts: list[str] = []
    for match in matches:
        if stripped[cursor : match.start()].strip():
            return None
        parts.append(markdown_image_html(match.group(1), match.group(2), ctx))
        cursor = match.end()

    if stripped[cursor:].strip():
        return None
    return "\n".join(parts)


def render_blocks(text: str, ctx: RenderContext) -> str:
    lines = normalize_newlines(text).splitlines()
    out: list[str] = []
    i = 0

    while i < len(lines):
        line = lines[i]

        if not line.strip():
            i += 1
            continue

        fence = re.match(r"^```", line.strip())
        if fence:
            i += 1
            code_lines: list[str] = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            if i < len(lines):
                i += 1
            out.append(f"<pre><code>{escape_text(chr(10).join(code_lines))}</code></pre>")
            continue

        spec = window_spec(line)
        if spec:
            class_name, end_re = spec
            i += 1
            inner_lines: list[str] = []
            while i < len(lines) and not end_re.match(lines[i].strip()):
                inner_lines.append(lines[i])
                i += 1
            if i < len(lines):
                i += 1

            if class_name in ("wiki-window", "record-window"):
                first_idx = next(
                    (idx for idx, il in enumerate(inner_lines) if il.strip()),
                    -1,
                )
                if first_idx >= 0:
                    stripped = inner_lines[first_idx].strip()
                    if not stripped.startswith("\\"):
                        inner_lines[first_idx] = f"@rs@{stripped}@rs@"
                inner = strip_leading_escape("\n".join(inner_lines).strip("\n"))
                inner_html = render_blocks(inner, ctx)
                sep = '<p class="window-sep">----------------------------------------</p>'
                out.append(f"<br /><br />{sep}\n{inner_html}\n{sep}<br /><br />")
                continue

            if class_name in ("plain-window", "followup-window", "system-window"):
                inner = strip_leading_escape("\n".join(inner_lines).strip("\n"))
                inner_html = render_blocks(inner, ctx)
                if class_name in ("plain-window", "followup-window"):
                    out.append(f"<br />\n{inner_html}\n<br />")
                else:
                    out.append(inner_html)
                continue

            if class_name == "braun-screen":
                inner = strip_leading_escape("\n".join(inner_lines).strip("\n"))
                inner_html = render_blocks(inner, ctx)
                out.append(f'<div class="braun-screen"><br /><br />\n{inner_html}\n<br /><br /></div>')
                continue

            inner = strip_leading_escape("\n".join(inner_lines).strip("\n"))
            inner_html = render_blocks(inner, ctx)
            out.append(f'<div class="{class_name}">{inner_html}</div>')
            continue

        heading = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if heading:
            level = min(len(heading.group(1)), 6)
            out.append(f"<h{level}>{render_inline(heading.group(2), ctx)}</h{level}>")
            i += 1
            continue

        if re.match(r"^-\&-\s*$", line):
            i += 1
            continue

        if re.match(r"^~\^~\s*$", line):
            out.append('<br /><hr class="invisible-hr" /><br />')
            i += 1
            continue

        if is_hr_line(line):
            out.append("<br /><hr /><br />")
            i += 1
            continue

        if re.match(r"^>\s?", line):
            quote_lines: list[str] = []
            while i < len(lines) and re.match(r"^>\s?", lines[i]):
                quote_lines.append(re.sub(r"^>\s?", "", lines[i]))
                i += 1
            out.append(f"<blockquote>{render_blocks(chr(10).join(quote_lines), ctx)}</blockquote>")
            continue

        if re.match(r"^([-+*]|\d+\.)\s+\S", line):
            html_list, i = render_list(lines, i, ctx)
            out.append(html_list)
            continue

        paragraph_lines = [line]
        i += 1
        while i < len(lines) and lines[i].strip() and not is_block_start(lines[i]):
            paragraph_lines.append(lines[i])
            i += 1

        paragraph = "\n".join(paragraph_lines)
        standalone_image = render_standalone_image_paragraph(paragraph, ctx)
        if standalone_image is not None:
            out.append(standalone_image)
        else:
            out.append(f"<p>{render_inline(paragraph, ctx)}</p>")

    return "\n".join(out)


def xhtml_page(title: str, body: str) -> str:
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" '
        '"http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">\n'
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
    if not identifier:
        identifier = f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, book_title)}"

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
    if not identifier:
        identifier = f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, book_title)}"
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


def chapter_output_name(position: int, chapter: Chapter) -> str:
    title = safe_id(chapter.title.replace(".", ""), f"chapter_{position}")
    return f"{position:04d}_{title}.xhtml"


def build_translation(tl_path: Path, args: argparse.Namespace) -> Path | None:
    metadata_path = tl_path / "metadata.md"
    if not metadata_path.exists():
        print(f"Skipping {tl_path.name}: no metadata.md")
        return None

    master_meta, master_content = load_markdown(metadata_path)
    book_id = metadata_text(master_meta.get("metaBook"), tl_path.parent.name)
    tl_name = metadata_text(master_meta.get("metaTl"), tl_path.name)
    book_title = metadata_text(master_meta.get("title"), f"{book_id} - {tl_name}")

    chapter_files = sorted(path for path in tl_path.glob("*.md") if path.name != "metadata.md")
    if args.limit:
        chapter_files = chapter_files[: args.limit]
    if not chapter_files:
        print(f"Skipping {tl_path.name}: no chapter markdown files")
        return None

    print(f"Processing {book_id}/{tl_name}: {len(chapter_files)} chapter(s)")

    chapters: list[Chapter] = []
    for fallback, path in enumerate(chapter_files):
        metadata, content = load_markdown(path)
        title = first_heading(content) or metadata_text(metadata.get("title"), path.stem)
        slug = metadata_text(metadata.get("slug"), path.stem)
        chapters.append(
            Chapter(
                path=path,
                metadata=metadata,
                content=content,
                title=title,
                index=sort_value(metadata, fallback),
                slug=slug,
            )
        )

    chapters.sort(key=lambda chapter: (chapter.index, chapter.path.name))

    tweet_cache = load_tweet_cache()
    assets: dict[Path, EpubAsset] = {}
    asset_names: set[str] = set()

    cover_asset: EpubAsset | None = None
    cover_item: EpubItem | None = None
    cover_image_path = IMAGES_ROOT / book_id / "cover.webp"
    if cover_image_path.exists():
        cover_name = unique_asset_name(cover_image_path, "cover.webp", asset_names)
        cover_asset = EpubAsset(
            source_path=cover_image_path,
            href=f"Images/{cover_name}",
            media_type=media_type_for(cover_image_path),
        )
        assets[cover_image_path] = cover_asset
        cover_body = (
            '<div class="cover-page">'
            f'<img src="../{escape_attr(cover_asset.href)}" alt="Cover" class="cover-image" />'
            "</div>"
        )
        cover_item = EpubItem(
            item_id="cover",
            href="Text/cover.xhtml",
            title="Cover",
            body=cover_body,
        )
        print(f"  Cover: {cover_asset.href}")

    items: list[EpubItem] = []

    today = dt.date.today()
    pretty_date = f"{today:%B} {today.day}, {today:%Y}"
    master_content = master_content.replace("{{DATE}}", pretty_date)

    info_ctx = RenderContext(book_id, metadata_path, assets, asset_names, tweet_cache, not args.no_fetch_twitter)
    info_body = render_blocks(master_content, info_ctx)
    items.append(
        EpubItem(
            item_id="xhtml0000",
            href="Text/0000_Information.xhtml",
            title="Information",
            body=info_body,
        )
    )

    for position, chapter in enumerate(chapters, start=1):
        print(f"  [{position}/{len(chapters)}] {chapter.title}")
        ctx = RenderContext(book_id, chapter.path, assets, asset_names, tweet_cache, not args.no_fetch_twitter)
        body = render_blocks(chapter.content, ctx)
        href = f"Text/{chapter_output_name(position, chapter)}"
        items.append(
            EpubItem(
                item_id=f"xhtml{position:04d}",
                href=href,
                title=chapter.title,
                body=body,
            )
        )

    output_name = sanitize_filename(f"{book_title} - {tl_name} [Default].epub", "book.epub")
    epub_path = OUTPUT_DIR / output_name
    write_epub(epub_path, book_title, master_meta, items, assets, cover_item, cover_asset)
    save_tweet_cache(tweet_cache)
    print(f"  Done -> {epub_path}")
    return epub_path


def find_translation_paths(args: argparse.Namespace) -> list[Path]:
    if args.path:
        return [Path(args.path).resolve()]

    root = CHAPTERS_ROOT / args.book
    fantl = root / "fantl"
    if fantl.exists():
        return [fantl]
    if root.exists():
        return sorted(path for path in root.iterdir() if path.is_dir())
    return []


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build WebToEpub-style EPUBs from chapter markdown.")
    parser.add_argument("--book", default="gsgw", help="Book folder under chapters/ to build.")
    parser.add_argument("--path", help="Specific translation folder to build.")
    parser.add_argument("--limit", type=int, help="Build only the first N chapters, useful for testing.")
    parser.add_argument(
        "--no-fetch-twitter",
        action="store_true",
        help="Use cached Twitter WebPs only; leave missing tweet images as links.",
    )
    return parser.parse_args()


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = parse_args()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TWITTER_IMG_DIR.mkdir(parents=True, exist_ok=True)

    built: list[Path] = []
    for tl_path in find_translation_paths(args):
        if not tl_path.exists() or not tl_path.is_dir():
            print(f"Skipping missing path: {tl_path}")
            continue
        epub_path = build_translation(tl_path, args)
        if epub_path:
            built.append(epub_path)

    if not built:
        print("No EPUBs built.")
        return

    print("\nBuilt EPUBs:")
    for path in built:
        print(f"  {path}")


if __name__ == "__main__":
    main()
