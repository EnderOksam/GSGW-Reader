import os
import re
import json
import html
import shutil
import subprocess
import zipfile
import imagesize
from pathlib import Path
from io import BytesIO
from PIL import Image
from concurrent.futures import ProcessPoolExecutor, as_completed

import frontmatter



# =========================================================
# PATHS
# =========================================================

SCRIPT_DIR = Path(__file__).parent.resolve()
REPO_ROOT = SCRIPT_DIR.parent

TEMPLATE_PATH = REPO_ROOT / "website/src/lib/reader/template.svelte"
META_OUTPUT_PATH = REPO_ROOT / "website/src/lib/meta.json"

OUTPUT_ROOT = REPO_ROOT / "website/src/routes/(reader)/read/"

DISCUSSION_MAP_PATH = REPO_ROOT / "discussion_map.json"

def load_discussion_map():
    if DISCUSSION_MAP_PATH.exists():
        return json.loads(DISCUSSION_MAP_PATH.read_text(encoding="utf-8"))
    return {}

def get_discussion_number(discussion_map, book_id, book_tl, slug):
    pathname = f"read/{book_id}/{book_tl}/{slug}"
    return discussion_map.get(pathname, 0)


# =========================================================
# CACHES
# =========================================================

IMAGE_SIZE_CACHE = {}


# =========================================================
# PRECOMPILED REGEX
# =========================================================

IMG_TAG_RE = re.compile(r"<img [^>]+>")
SRC_RE = re.compile(r'src="([^"]+)"')

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

FOOTNOTE_RE = re.compile(r"\[(\d+)\]\{([^}]+)\}", re.DOTALL)

TWITTER_URL_RE = re.compile(
    r'https?://(?:x|twitter)\.com/(\w+)/status/(\d+)(?:/photo/(\d+))?[^\s<>"\']*'
)

VISIBLE_HR_RE = re.compile(r"^~~~\s*$", re.MULTILINE)
INVISIBLE_HR_RE = re.compile(r"^~\^~\s*$", re.MULTILINE)

STYLE_BLOCK_RE = re.compile(r'^[ \t]*\{style="([^"]*)"\}\s*$')

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
BRAUN_WINDOW_RE = re.compile(r"!\[\n(.*?)\n\]!", re.DOTALL)
BRAUN_TV_TEXT_RE = re.compile(r"\$Brt\n(.*?)\nBrt\$", re.DOTALL)
BRAUN_DOLL_TEXT_RE = re.compile(r"\$Brd\n(.*?)\nBrd\$", re.DOTALL)

DEBUT_WINDOW_RE = re.compile(r"★-\n(.*?)\n-★", re.DOTALL)
DEBUT_ALERT_RE = re.compile(r"★!\n(.*?)\n!★", re.DOTALL)
DEBUT_ACHIEVE_RE = re.compile(r"★=\n(.*?)\n=★", re.DOTALL)
SMS_WINDOW_RE = re.compile(r"★:\n([\s\S]*?)\n:★", re.DOTALL)
COMMENT_WINDOW_RE = re.compile(r"★\$\n([\s\S]*?)\n\$★", re.DOTALL)


SIMPLE_REPLACEMENTS = [
    (re.compile(r"(?<!\\)_(.*?)(?<!\\)_", re.DOTALL), r"[\1]{.underline}"),


    (re.compile(r"@ll@(.*?)@ll@", re.DOTALL), r'<span class="mono mono-left">\1</span>'),
    (re.compile(r"@cc@(.*?)@cc@", re.DOTALL), r'<span class="mono mono-center">\1</span>'),
    (re.compile(r"@rr@(.*?)@rr@", re.DOTALL), r'<span class="mono mono-right">\1</span>'),

    (re.compile(r"@l@(.*?)@l@", re.DOTALL), r'<span class="align-left">\1</span>'),
    (re.compile(r"@c@(.*?)@c@", re.DOTALL), r'<span class="align-center">\1</span>'),
    (re.compile(r"@r@(.*?)@r@", re.DOTALL), r'<span class="align-right">\1</span>'),

    (re.compile(r"#\*(.*?)\*#", re.DOTALL), r'<span class="text-large">\1</span>'),
    (re.compile(r"#><(.*?)><#", re.DOTALL), r'<span class="text-large-centered">\1</span>'),

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

    (re.compile(r";r(.*?)r;", re.DOTALL), r'<span class="hl-red">\1</span>'),
    (re.compile(r";b(.*?)b;", re.DOTALL), r'<span class="hl-blue">\1</span>'),
    (re.compile(r";y(.*?)y;", re.DOTALL), r'<span class="hl-yellow">\1</span>'),
    (re.compile(r";p(.*?)p;", re.DOTALL), r'<span class="hl-magenta">\1</span>'),
    (re.compile(r";g(.*?)g;", re.DOTALL), r'<span class="hl-green">\1</span>'),
    (re.compile(r";o(.*?)o;", re.DOTALL), r'<span class="hl-orange">\1</span>'),

    (re.compile(r"\$c(.*?)c\$", re.DOTALL), r'<span class="contaminated">\1</span>'),
    (re.compile(r"\$Eb(.*?)Eb\$", re.DOTALL), r'<span class="eb-garamond">\1</span>'),
    (re.compile(r"\$wo(.*?)wo\$", re.DOTALL), r'<span class="outline-white">\1</span>'),
    (re.compile(r"\$bo(.*?)bo\$", re.DOTALL), r'<span class="outline-black">\1</span>'),
]


# =========================================================
# IMAGE PROCESSING
# =========================================================

IMG_STORAGE_DIR = REPO_ROOT / "website/static/assets/images/static-illustrations"
IMG_PUBLIC_PREFIX = "/assets/images/static-illustrations"

ILLUSTRATIONS_SRC = REPO_ROOT / "images" / "gsgw" / "illustrations"


def copy_illustrations():
    if not ILLUSTRATIONS_SRC.exists():
        print(f"Illustrations source not found: {ILLUSTRATIONS_SRC}")
        return
    IMG_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    count = 0
    for img_file in ILLUSTRATIONS_SRC.glob("*.webp"):
        dest = IMG_STORAGE_DIR / img_file.name
        if not dest.exists() or img_file.stat().st_mtime > dest.stat().st_mtime:
            shutil.copy2(str(img_file), str(dest))
            count += 1
    if count:
        print(f"Copied {count} illustration(s) to {IMG_STORAGE_DIR}")


def get_image_size_cached(path):
    cached = IMAGE_SIZE_CACHE.get(path)

    if cached:
        return cached

    try:
        size = imagesize.get(path)
        IMAGE_SIZE_CACHE[path] = size
        return size
    except:
        return None


def process_html_images(html_content):

    def replacer(match):
        full_tag = match.group(0)

        src_match = SRC_RE.search(full_tag)

        if not src_match:
            return full_tag

        original_src = src_match.group(1)

        image_filename = Path(original_src).name
        webp_filename = Path(image_filename).with_suffix(".webp")

        local_image_path = IMG_STORAGE_DIR / webp_filename

        new_src = f"{IMG_PUBLIC_PREFIX}/{webp_filename}"

        new_tag = full_tag.replace(original_src, new_src)

        if local_image_path.exists():

            size = get_image_size_cached(local_image_path)

            if size:
                width, height = size

                if 'width=' not in new_tag:
                    new_tag = new_tag.replace(
                        "<img",
                        f'<img width="{width}" height="{height}"',
                        1
                    )

        return new_tag

    return IMG_TAG_RE.sub(replacer, html_content)


# =========================================================
# HELPERS
# =========================================================

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


# =========================================================
# TWITTER URL PROCESSING
# =========================================================

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


# =========================================================
# EFFECT REPLACERS
# =========================================================

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


# =========================================================
# WINDOW REPLACERS
# =========================================================

def make_window(class_name, inner, extra_class=None):

    inner = fix_underline(inner)
    inner = escape_markdown_except_bold(inner)

    cls = class_name

    if extra_class:
        cls += f" {extra_class}"

    dotted = " ".join(f".{c.lstrip('.')}" for c in cls.split())

    return f'\n::: {{{dotted}}}\n{inner}\n:::\n'


def braun_text_replacer(class_name):
    def replacer(match):
        inner = re.sub(r"\n+", "<br>", match.group(1))
        return make_window(class_name, inner)
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
    return make_window("debut-window", title_html + body)


def debut_alert_replacer(match):
    inner = match.group(1)
    if inner.lstrip().startswith("<p align="):
        inner = re.sub(r'^\s*<p\s+align="center">\s*', '', inner)
        return make_window("debut-alert debut-alert-center", inner)
    return make_window("debut-alert", inner)


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

    def sub_left(match):
        text = match.group(1).strip()
        if text.startswith("[!]"):
            return f'<span class="alert-sub alert-sub-left">{text[3:].strip()}</span>'
        return f'<span class="debut-achievement-sub debut-achievement-sub-left">{text}</span>'

    def sub_right(match):
        text = match.group(1).strip()
        if text.startswith("[!]"):
            return f'<span class="alert-sub alert-sub-right">{text[3:].strip()}</span>'
        return f'<span class="debut-achievement-sub debut-achievement-sub-right">{text}</span>'

    body = re.sub(r"\}([^\n}]+)\}", sub_left, body)
    body = re.sub(r"\{([^\n{]+)\{", sub_right, body)

    title_html = f'<div class="debut-achievement-title">{title}</div>\n\n' if title else ""
    return make_window("debut-achievement", title_html + body)


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


# =========================================================
# FOOTNOTES
# =========================================================

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

    # Protect link URLs (which may contain _ [ ] ( ) etc.) from the tag
    # replacements below, then restore the built <a> tags afterwards.
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

# =========================================================
# MAIN CONVERTER
# =========================================================

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


def convert_chapter(content):

    content = process_twitter_urls(content)

    # protect twitter-embed divs from SIMPLE_REPLACEMENTS
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

    footnotes = {}
    fn_placeholders = {}

    def footnote_ref_replacer(m):
        num = int(m.group(1))
        text = m.group(2)
        tip_html = render_footnote_text(text)
        key = f"\x00FN{len(fn_placeholders)}\x00"
        footnotes[num] = tip_html
        fn_placeholders[key] = (
            f'<span class="fn-ref" id="fn-ref-{num}" tabindex="0" role="button">'
            f'[{num}]<span class="fn-tip"><strong>{num}.</strong> {tip_html}</span></span>'
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

    # protect markdown image syntax and double-tilde strikethrough from SIMPLE_REPLACEMENTS
    img_placeholders = {}
    def protect_patterns(text):
        def save(key_store):
            def save_inner(m):
                key = f"\x00IMG{len(key_store)}\x00"
                key_store[key] = m.group(0)
                return key
            return save_inner
        text = re.sub(r'!\[.*?\]\(.*?\)', save(img_placeholders), text)
        text = re.sub(r'~~[^~]+?~~', save(img_placeholders), text)
        return text
    content = protect_patterns(content)

    for pattern, repl in SIMPLE_REPLACEMENTS:
        content = pattern.sub(repl, content)

    content = re.sub(r"\$\$(.*?)\$\$", r'<span class="handwritten">\1</span>', content)

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

    # restore protected patterns
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

    content = BRAUN_WINDOW_RE.sub(
        lambda m: make_window("braun-screen", m.group(1)),
        content
    )

    content = BRAUN_TV_TEXT_RE.sub(braun_text_replacer("braun-tv-text"), content)
    content = BRAUN_DOLL_TEXT_RE.sub(braun_text_replacer("braun-doll-text"), content)

    # star windows (debut-specific)
    content = DEBUT_ALERT_RE.sub(debut_alert_replacer, content)
    content = DEBUT_WINDOW_RE.sub(debut_window_replacer, content)
    content = DEBUT_ACHIEVE_RE.sub(debut_achieve_replacer, content)

    # sms and comment windows
    content = SMS_WINDOW_RE.sub(sms_window_replacer, content)
    content = COMMENT_WINDOW_RE.sub(comment_window_replacer, content)

    # restore footnote placeholders (tooltip HTML) before pandoc
    for key, val in fn_placeholders.items():
        content = content.replace(key, val)

    # build footnotes HTML separately (rendered as a card in the layout)
    footnotes_html = ""
    if footnotes:
        lines = []
        for num in sorted(footnotes):
            lines.append(f'<li value="{num}" id="fn-{num}">{footnotes[num]} <a href="#fn-ref-{num}" class="fn-back" aria-label="Back to reference {num} in text">↩</a></li>')
        footnotes_html = '<div class="footnotes">\n<ol>\n' + '\n'.join(lines) + '\n</ol>\n</div>\n'

    try:
        proc = subprocess.run(
            ["pandoc", "--from", "markdown", "--to", "html", "--quiet"],
            input=content.encode("utf-8"),
            capture_output=True,
            timeout=120
        )
        if proc.returncode != 0:
            err = proc.stderr.decode().strip()
            print(f"Pandoc error: {err}")
            return f"<p>Error converting content: {err}</p>", footnotes_html
        return process_html_images(proc.stdout.decode("utf-8")), footnotes_html
    except subprocess.TimeoutExpired:
        print("Pandoc timed out on a chapter — skipping")
        return "<p>Chapter skipped due to conversion timeout.</p>", footnotes_html


# =========================================================
# BUILD TASK
# =========================================================

def process_task(task, template_str):

    html_content, footnotes_html = convert_chapter(task["content"])

    safe_html = (
        html_content
        .replace("`", "\\`")
        .replace("${", "$\\{")
    )

    safe_footnotes = (
        footnotes_html
        .replace("`", "\\`")
        .replace("${", "$\\{")
    )

    meta_json = json.dumps(
        task["meta"],
        ensure_ascii=False
    )

    output = template_str.replace(
        "let ch_meta = null;",
        f"let ch_meta = {meta_json};"
    )

    output = output.replace(
        'let html_content = "";',
        f'let html_content = `{safe_html}`;'
    )

    output = output.replace(
        'let footnotes = "";',
        f'let footnotes = `{safe_footnotes}`;'
    )

    task["dest"].write_text(
        output,
        encoding="utf-8"
    )


# =========================================================
# THUMBNAIL EXTRACTION
# =========================================================

THUMB_W = 320
THUMB_H = 240

def extract_thumbnail(cbz_path, output_path, page_index=0):
    try:
        with zipfile.ZipFile(cbz_path, "r") as z:
            names = sorted(
                n for n in z.namelist()
                if not n.endswith("/") and re.search(r'\.(png|jpg|jpeg|webp)$', n, re.I)
            )
            if not names:
                return False
            idx = page_index % len(names)
            data = z.read(names[idx])
            img = Image.open(BytesIO(data))
            # Center crop to 4:3 then resize
            if img.width / img.height > 4 / 3:
                crop_w = int(img.height * 4 / 3)
                crop_h = img.height
            else:
                crop_w = img.width
                crop_h = int(img.width * 3 / 4)
            left = (img.width - crop_w) // 2
            top = (img.height - crop_h) // 2
            img = img.crop((left, top, left + crop_w, top + crop_h))
            img = img.resize((THUMB_W, THUMB_H), Image.LANCZOS)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            img.save(output_path, "WEBP", quality=80)
            return True
    except Exception as e:
        print(f"  Thumbnail error for {cbz_path.name}: {e}")
        return False


def get_thumb_page_index(thumb_dir, slug):
    idx_path = thumb_dir / f"{slug}.txt"
    if idx_path.exists():
        try:
            return int(idx_path.read_text().strip())
        except (ValueError, OSError):
            pass
    return 0


def save_thumb_page_index(thumb_dir, slug, index):
    idx_path = thumb_dir / f"{slug}.txt"
    idx_path.parent.mkdir(parents=True, exist_ok=True)
    idx_path.write_text(str(index))


# =========================================================
# MAIN
# =========================================================

def main():

    if not TEMPLATE_PATH.exists():
        print(f"Template not found: {TEMPLATE_PATH}")
        return

    template_str = TEMPLATE_PATH.read_text(
        encoding="utf-8"
    )

    copy_illustrations()

    paths = []

    for root_name in ["chapters/gsgw", "chapters/manwha"]:
        root_path = (REPO_ROOT / root_name).resolve()
        if root_path.exists():
            for d in sorted(os.listdir(root_path)):
                if (root_path / d).is_dir():
                    paths.append(os.path.join(root_name, d))

    tasks_data = []

    meta_map = {}
    if META_OUTPUT_PATH.exists():
        try:
            meta_map = json.loads(META_OUTPUT_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass

    discussion_map = load_discussion_map()
    print(f"Loaded discussion map: {len(discussion_map)} entries")

    for p in paths:

        path = (REPO_ROOT / p).resolve()

        if not path.exists():
            continue

        master_path = path / "metadata.md"

        if not master_path.exists():
            continue

        master = frontmatter.load(master_path)

        bookID = master.get("metaBook", "gsgw")
        bookTL = master.get("metaTl", "fantl").lower()

        meta_map.setdefault(bookID, {})
        meta_map[bookID][bookTL] = []

        md_files = sorted(
            f for f in os.listdir(path)
            if f.endswith(".md") and f != "metadata.md"
        )
        cbz_files = sorted(
            f for f in os.listdir(path)
            if f.endswith(".cbz")
        )

        if md_files:
            for file in md_files:

                post = frontmatter.load(path / file)

                slug = post.metadata.get("slug")

                if not slug:
                    continue

                # Inject correct discussion number from map (0 = no mapping, use pathname fallback)
                correct_discussion = get_discussion_number(discussion_map, bookID, bookTL, slug)
                post.metadata["discussion"] = correct_discussion

                meta_map[bookID][bookTL].append(post.metadata)

                out_dir = (
                    OUTPUT_ROOT
                    / str(bookID)
                    / str(bookTL)
                    / str(slug)
                )

                out_dir.mkdir(
                    parents=True,
                    exist_ok=True
                )

                tasks_data.append({
                    "content": post.content,
                    "meta": post.metadata,
                    "dest": out_dir / "+page.svelte"
                })

        elif cbz_files:
            thumbs_dir = REPO_ROOT / "chapters" / "manwha" / "thumbnails"
            static_thumbs_dir = (
                REPO_ROOT
                / "website" / "static"
                / "chapters" / "manwha"
                / "thumbnails"
            )

            for i, f in enumerate(cbz_files):
                try:
                    stem = Path(f).stem
                    slug = str(int(stem))
                except ValueError:
                    slug = str(i + 1)

                # Extract thumbnail (first page) — only if missing
                thumb_path = thumbs_dir / f"{slug}.webp"
                if not thumb_path.exists():
                    extract_thumbnail(path / f, thumb_path, 0)

                if thumb_path.exists():
                    static_thumbs_dir.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(str(thumb_path), str(static_thumbs_dir / f"{slug}.webp"))

                meta_map[bookID][bookTL].append({
                    "title": f"Chapter {slug}",
                    "category": f"Chapter {slug}",
                    "index": i,
                    "slug": slug,
                    "thumb": f"/chapters/manwha/thumbnails/{slug}.webp",
                })

    META_OUTPUT_PATH.write_text(
        json.dumps(meta_map, indent=2),
        encoding="utf-8"
    )

    if not tasks_data:
        print("No chapters found.")
        return

    total = len(tasks_data)

    print(f"Starting build for {total} chapters...")

    workers = min(
        os.cpu_count() or 4,
        total
    )

    with ProcessPoolExecutor(max_workers=workers) as executor:

        futures = {
            executor.submit(
                process_task,
                task,
                template_str
            ): task
            for task in tasks_data
        }

        done = 0
        errors = 0

        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                task = futures[future]
                print(f"Failed: {task['dest'].name} — {e}")
                errors += 1

            done += 1

            if done % 10 == 0 or done == total:
                print(f"Generated {done}/{total} chapters ({errors} errors)...")

    print(f"Build complete with {errors} errors.")


if __name__ == "__main__":
    main()