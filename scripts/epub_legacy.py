"""Legacy EPUB 2 presentation, calibrated for the 600 x 800 Nook Simple Touch.

Keep this separate from the modern edition: old Adobe RMSDK engines cannot
reliably render generated content, web fonts, flexbox, or viewport units.
"""

from __future__ import annotations

import hashlib
import datetime as dt
import html
import urllib.parse
import zipfile
import math
import re
import unicodedata
import xml.etree.ElementTree as ET
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from build_new_epub import EpubAsset, EpubItem


def information_text(content: str) -> str:
    """Adapt the information page only for the Legacy edition."""
    content = re.sub(r"^!\[\]\((?:wikiwindow|smswindow|commentwindow|debutwindow)_epub\.webp\)\s*$", "", content, flags=re.M)
    content = re.sub(r"This EPUB also uses some custom formatting\..*?EPUB3 files\.",
                     "This legacy EPUB uses embedded fonts and authored alignment. Enable publisher defaults in your reader. Window examples below use plain text markers.", content, flags=re.S)
    return re.sub(r"Compare the following windows.*?\(window image may not be the same size as rendered window\)\.", "", content, flags=re.S)


def register_remaining_images(builder: Any, body: str, ctx: Any) -> str:
    """Register wrapped tags and recover smart-quoted image width hints."""
    body = re.sub(r"<img\s+", "<img ", body, flags=re.I)

    def recover_width(match: re.Match) -> str:
        tag = match[0]
        source = builder.SRC_RE.search(tag)
        if source:
            decoded = urllib.parse.unquote(html.unescape(source[1]))
            size = re.fullmatch(r'''(.+?)\s+[“”‘’"'](\d+(?:\.\d+)?(?:px|%))[“”‘’"']''', decoded)
            if size:
                tag = tag.replace(source[0], f'src="{builder.escape_attr(size[1])}"')
                tag = tag.replace("<img ", f'<img title="{size[2]}" ', 1)
        return tag

    body = builder.IMG_TAG_RE.sub(recover_width, body)
    return builder.process_html_images(body, ctx)


@dataclass(frozen=True)
class LegacyLayout:
    # 30px side/top margins, 20px bottom margin, plus room for reader chrome.
    width: int = 540
    height: int = 700
    font_size: float = 18
    line_height: float = 1.5


TEXT_WINDOWS = {
    "wiki-window", "record-window", "plain-window", "followup-window",
    "system-window", "note-window", "sticky-window", "black-window",
    "braun-screen", "sms-window", "alert-window", "paper-boat",
    "debut-window", "debut-alert", "debut-achievement",
}
SPACED_BLOCKS = TEXT_WINDOWS | {"padding-window", "braun-tv-text", "braun-doll-text", "bare-window", "nook-horizontal-break"}
RULED_WINDOWS = {"wiki-window", "record-window"}
# CSS 2 approximations of the website's styled windows. The four DMB window
# classes intentionally keep their existing plaintext presentation.
BOX_WINDOWS = {
    "bare-window": {"border": "1px solid #000", "padding": "1.5em 1em", "background-color": "#fff", "color": "#000", "text-align": "center"},
    "black-window": {"border": "1px solid #555", "padding": "1.5em 1em", "background-color": "#000", "color": "#fff", "text-align": "center"},
    "braun-screen": {"border": "6px solid #555", "padding": "3em 1em", "background-color": "#000", "color": "#fff", "text-align": "center"},
}

BLOCKS = {"div", "p", "blockquote", "li", "h1", "h2", "h3", "h4", "h5", "h6"}
HTML_TAGS = set("""a abbr acronym address area b base bdo big blockquote body br
caption cite code col colgroup dd del dfn div dl dt em h1 h2 h3 h4 h5 h6 head hr
html i img ins kbd li link map meta object ol p param pre q ruby rb rbc rp rt rtc
samp script small span strong style sub sup table tbody td tfoot th thead title tr
tt u ul var section aside nav figure figcaption mark marquee""".split())
TYPOGRAPHY = {
    "font-family", "font-size", "font-style", "font-weight", "text-align",
    "text-decoration", "text-transform", "vertical-align", "color", "opacity",
}


def escape_unknown_tags(body: str) -> str:
    """Keep literal angle-bracketed prose from becoming invisible HTML.

    For example, a source line contains the unescaped <Cheerful Theme Park>.
    Preserve its case and spelling before the tolerant XHTML serializer runs.
    """
    import html

    return re.sub(r"</?([A-Za-z][\w:-]*)(?:\s[^<>]*?)?/?>",
                  lambda match: match[0] if match[1].lower() in HTML_TAGS else html.escape(match[0]), body)


def css_rules(css: str):
    """Yield top-level rules; skip nested media/keyframe rules as a unit."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    start = 0
    depth = 0
    quote = ""
    escaped = False
    opening = 0
    for i, char in enumerate(css):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if quote:
            if char == quote:
                quote = ""
            continue
        if char in "\"'":
            quote = char
        elif char == "{":
            if depth == 0:
                opening = i
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                yield css[start:opening].strip(), css[opening + 1:i].strip()
                start = i + 1


def declarations(body: str, allowed: set[str]) -> dict[str, str]:
    result = {}
    for declaration in body.split(";"):
        name, sep, value = declaration.partition(":")
        name, value = name.strip().lower(), value.strip()
        if not sep or name not in allowed or re.search(r"(?:calc|clamp|var|min|max)\(|\d(?:vh|vw|rem)\b", value):
            continue
        result[name] = value
    return result


def stylesheet(source: str, layout: LegacyLayout) -> str:
    """Retain basic typography, then supply a small CSS 2 layout."""
    out = []
    for label in ("CJK", "Math", "Symbols", "Gujarati"):
        out.append(f'@font-face {{ font-family: "GSGW Nook {label}"; src: url("../Fonts/GSGWNook{label}-Regular.ttf") format("truetype"); font-weight: 400; font-style: normal; }}')
    for selector, body in css_rules(source):
        if selector == "@font-face":
            body = re.sub(r"font-display\s*:[^;]+;?", "", body)
            weights = re.search(r"font-weight:\s*(\d+)\s+(\d+)\s*;", body)
            if weights:
                wanted = {200, 300, 400, 500, 600, 700}
                if 'font-family: "Noto Emoji"' in body:
                    wanted = {500}
                if 'font-family: "IBM Plex Sans"' in body:
                    # The bundled variable files support 100–700 even though
                    # the website deliberately declares only its light faces.
                    wanted = {200, 300, 400, 500, 600}
                else:
                    wanted = {weight for weight in wanted if int(weights[1]) <= weight <= int(weights[2])}
                for weight in sorted(wanted or {int(weights[1])}):
                    static = body[:weights.start()] + f"font-weight: {weight};" + body[weights.end():]
                    out.append(f"{selector} {{{static}}}")
            else:
                out.append(f"{selector} {{{body}}}")
            continue
        if selector.startswith("@"):
            continue
        # Filter each selector separately: an unsupported selector in a list
        # can make an old engine discard the entire rule.
        selectors = [s.strip() for s in selector.split(",") if not re.search(r"[:\[\]]", s)]
        props = declarations(body, TYPOGRAPHY)
        # Plaintext windows do not inherit the website's light-on-dark ink.
        # Authored text-color classes and inline colors still retain their ink.
        layout_ink = TEXT_WINDOWS | {"bare-window", "sms-bubble", "sms-left", "sms-right", "sms-center"}
        if any(re.search(r"\." + re.escape(name) + r"\b", selector) for name in layout_ink):
            props.pop("color", None)
        if selectors and props:
            out.append(", ".join(selectors) + " {" + "; ".join(f"{k}: {v}" for k, v in props.items()) + ";}")
    # Include supplied italic/Korean faces that the old EPUB stylesheet omitted.
    # Explicit character selection handles the website's unicode-range splits.
    reader_dir = Path(__file__).resolve().parent.parent / "website/src"
    registered = set()
    registered_files = set()
    families = set()
    for selector, body in css_rules("\n".join(out)):
        if selector == "@font-face":
            family = re.search(r'font-family:\s*[\'"]([^\'"]+)', body)[1]
            weight = int(re.search(r"font-weight:\s*(\d+)", body)[1])
            italic = bool(re.search(r"font-style:\s*italic", body))
            name = Path(re.search(r'url\([\'"]?([^\)\'\"]+)', body)[1]).name
            families.add(family)
            registered.add((family, weight, italic))
            registered_files.add((family, weight, italic, name))
    for selector, body in css_rules((reader_dir / "app.css").read_text(encoding="utf-8")):
        if selector != "@font-face":
            continue
        family_match = re.search(r'font-family:\s*[\'"]([^\'"]+)', body)
        source_match = re.search(r'url\([\'"]?([^\)\'\"]+)', body)
        weight_match = re.search(r"font-weight:\s*(\d+)(?:\s+(\d+))?", body)
        if not family_match or not source_match or not weight_match or family_match[1] not in families:
            continue
        family, name = family_match[1], Path(source_match[1]).name
        if not (reader_dir.parent / "static/fonts" / name).exists():
            continue
        italic = bool(re.search(r"font-style:\s*italic", body))
        weights = {int(weight_match[1])} if not weight_match[2] else {weight for weight in (200, 300, 400, 500, 600, 700) if int(weight_match[1]) <= weight <= int(weight_match[2])}
        for weight in sorted(weights):
            key = family, weight, italic
            if key not in registered or ("unicode-range" in body and (*key, name) not in registered_files):
                out.append(f'@font-face {{ font-family: "{family}"; src: url("../Fonts/{name}"); font-weight: {weight}; font-style: {"italic" if italic else "normal"}; }}')
                registered.add(key)
                registered_files.add((*key, name))
    # Use the website's authored font choices and relative sizes, while leaving
    # its animation, layout, colors, and user-selected plaintext modes behind.
    font_classes = set()
    for selector, body in css_rules(source):
        if "font-family" in body and not selector.startswith("@"):
            font_classes.update(s.strip() for s in selector.split(",") if re.fullmatch(r"\.[\w-]+", s.strip()))
    for path in (reader_dir / "routes/(reader)/reader.css", reader_dir / "lib/reader/reader-windows.css"):
        for selector, body in css_rules(path.read_text(encoding="utf-8")):
            if selector.startswith("@"):
                continue
            selectors = []
            for original in selector.split(","):
                simple = original.strip().removeprefix(".reader-container ")
                simple = simple.replace(':not([class^="text-"])', "")
                first = simple.split()[0] if simple else ""
                if first in font_classes and not re.search(r"[:\[\]]", simple):
                    selectors.append(simple)
            props = declarations(body, {"font-family", "font-size", "font-weight", "font-style", "vertical-align"})
            if selectors and props:
                out.append(", ".join(selectors) + " {" + "; ".join(f"{k}: {v}" for k, v in props.items()) + ";}")
    out.append(f"""
@page {{ margin: 30px 30px 20px 30px; }}
html, body {{ margin: 0; padding: 0; }}
body {{ font-family: "Libron", serif; line-height: {layout.line_height:g}; color: #000; background-color: #fff; }}
p {{ margin: 0 0 9px 0; padding: 0; text-indent: 0; line-height: {layout.line_height:g}; }}
h1, h2, h3, h4, h5, h6 {{ margin: 18px 0; text-align: center; line-height: 1.25; }}
img {{ display: block; margin: 0 auto; padding: 0; max-width: 100%; }}
.thumbcaption {{ margin: 4px 0 9px 0; font-size: 0.8em; text-align: center; }}
img.inline {{ display: inline; }}
pre {{ white-space: pre-wrap; }}
.invisible-hr {{ visibility: hidden; margin: 9px 0; }}
.nook-window, .padding-window, .braun-tv-text, .braun-doll-text, .bare-window {{ display: block; margin: 0; padding: 0; }}
.nook-block-spacer {{ display: block; margin: 0; padding: 0; text-indent: 0; }}
.nook-horizontal-break hr {{ display: block; margin: 0 auto; padding: 0; width: 100%; border: 0; border-top: 1px solid #000; }}
.nook-window-rule {{ margin: 4px 0; padding: 0; text-align: left; font-family: monospace; font-size: 1em; }}
.nook-window-meta {{ font-size: 0.75em; color: #666; }}
.nook-window p, .nook-window span {{ background-color: transparent; }}
.nook-window .nook-window {{ margin: 0; }}
.black-window, .braun-screen {{ padding: 12px; text-align: center; background-color: #000; }}
.braun-screen {{ font-size: 2em; height: auto; white-space: normal; page-break-inside: avoid; }}
.braun-screen p {{ font-size: 1em; line-height: {layout.line_height:g}; white-space: normal; }}

.comment, .comment-reply {{ display: block; margin: 18px 0; padding: 0; text-align: left; font-size: 1em; }}
.comment-reply {{ margin-left: 36px; text-indent: -18px; }}
.depth-2 {{ margin-left: 54px; }}
.depth-3 {{ margin-left: 72px; }}
.reply-icon {{ font-size: 1em; }}
.alert-window, .sms-window {{ font-family: monospace; }}
.comment-post-header {{ margin: 0; padding: 0; text-align: left; }}
.nook-comment-rule {{ margin: 0; padding: 0; font-size: 1em; font-style: normal; }}
.comment-post-title {{ margin: 18px 0; font-size: 1.1em; font-weight: 400; }}
.comment-post-desc {{ font-size: 0.9em; font-style: italic; }}
.comment-post-desc p {{ margin: 18px 0; }}
.comment-section {{ margin: 0; padding: 0; }}
.nook-note-title {{ font-size: 1.35em; font-weight: 600; text-align: left; }}
ol, ol li, ol p {{ margin-top: 0; margin-bottom: 0; padding-top: 0; padding-bottom: 0; }}
.nook-numbered-list {{ margin: 0 0 0 18px; padding: 0; }}
.nook-list-item {{ margin: 0; padding: 0; }}
.nook-list-paragraph {{ margin: 0; padding: 0; }}
.nook-list-gap {{ margin: 0; padding: 0; font-size: 0.5em; line-height: 1; }}
.sms-bubble {{ display: block; margin: 6px 0; }}
.sms-window {{ font-family: monospace; }}
.sms-left, .sms-right {{ font-style: normal; }}
.sms-left {{ text-align: left; }}
.sms-right {{ text-align: right; }}
.sms-center {{ text-align: center; font-style: italic; }}
.align-left, .mono-left {{ display: block; text-align: left !important; text-indent: 0; }}
.align-right, .mono-right {{ display: block; text-align: right !important; }}
.align-center, .mono-center, .text-large-centered {{ display: block; text-align: center !important; }}
.epub-chapter-label {{ display: none; }}
.epub-pagebreak, .epub-pagebreak-content {{ display: block; margin: 0; padding: 0; }}
.nook-scare-spacer {{ margin: 0; padding: 0; text-indent: 0; }}
.cover-page {{ margin: 0; padding: 0; text-align: center; }}
.footnotes-section {{ margin-top: 18px; }}
.footnote {{ font-size: 0.8em; margin: 9px 0; }}
.hl-red, .hl-blue, .hl-yellow, .hl-magenta, .hl-green, .hl-orange {{ text-decoration: underline; }}
.triple-strike {{ text-decoration: line-through; }}
.outline-white, .outline-black {{ font-weight: bold; }}
strong, b {{ font-size: 1em; }}
.choi-hand {{ font-size: 1.15em; }}
.crimson-old-style {{ font-size: 1.1em; }}
.epub-pagebreak {{ page-break-before: always; page-break-after: always; }}
.nook-credited-illustration {{ display: block; page-break-inside: avoid; margin: 0; padding: 0; }}
""")
    for name, properties in BOX_WINDOWS.items():
        out.append(f'.{name} {{ display: block; ' + "; ".join(f"{key}: {value}" for key, value in properties.items()) + "; }")

    return "\n".join(out)


def truetype_outlines(font) -> None:
    """Convert static CFF outlines to quadratic glyf outlines in place."""
    from fontTools.fontBuilder import FontBuilder
    from fontTools.pens.cu2quPen import Cu2QuPen
    from fontTools.pens.ttGlyphPen import TTGlyphPen

    glyph_set = font.getGlyphSet()
    glyphs = {}
    for name in font.getGlyphOrder():
        pen = TTGlyphPen(glyph_set)
        glyph_set[name].draw(Cu2QuPen(pen, max_err=font["head"].unitsPerEm / 1000, reverse_direction=True))
        glyphs[name] = pen.glyph()
    post = font["post"]
    post_values = {name: getattr(post, name) for name in (
        "italicAngle", "underlinePosition", "underlineThickness", "isFixedPitch",
    )}
    for table in ("CFF ", "CFF2", "VORG"):
        if table in font:
            del font[table]
    font.sfntVersion = "\x00\x01\x00\x00"
    builder = FontBuilder(font=font, isTTF=True)
    # For an existing font FontBuilder infers this from the (not yet added)
    # glyf table and ignores the constructor's isTTF argument.
    builder.isTTF = True
    builder.setupGlyf(glyphs)
    builder.setupMaxp()
    builder.setupPost(**post_values)


def resize_image(source: Path, cache: Path, layout: LegacyLayout) -> tuple[Path, tuple[int, int]]:
    """Bake the display bounds into the bitmap, including covers and GIFs."""
    from PIL import Image, ImageOps

    # Chapter 1 emblem (also referred to as 0001_1): halve its normal Nook
    # display bounds. Cached derivative names do not match, so later image
    # sizing/caption passes cannot apply the reduction a second time.
    if source.stem in {"ch1_1", "0001_1"}:
        layout = replace(layout, width=max(1, round(layout.width / 2)), height=max(1, round(layout.height / 2)))
    key = hashlib.sha256(source.read_bytes() + f"nook-v1:{layout.width}:{layout.height}".encode()).hexdigest()[:20]
    target = cache / f"{source.stem}-{key}.png"
    cache.mkdir(parents=True, exist_ok=True)
    if target.exists():
        with Image.open(target) as image:
            return target, image.size
    with Image.open(source) as image:
        image = ImageOps.exif_transpose(image).convert("RGBA")
        # Composite transparency on white; old e-ink renderers vary here.
        white = Image.new("RGBA", image.size, "white")
        white.alpha_composite(image)
        image = white.convert("L")
        image.thumbnail((layout.width, layout.height), Image.Resampling.LANCZOS)
        image.save(target, "PNG", optimize=True)
        return target, image.size


def official_image_refs(body: str) -> set[str]:
    root = ET.fromstring('<div xmlns:epub="http://www.idpf.org/2007/ops">' + body + "</div>")
    parents = {child: parent for parent in root.iter() for child in parent}
    result = set()
    for image in root.iter("img"):
        labels = [image.get("alt", ""), image.get("title", "")]
        parent = parents.get(image)
        if parent is not None:
            labels.extend("".join(node.itertext()) for node in parent if node.tag == "figcaption" or "thumbcaption" in classes(node))
        if any(re.match(r"^official\s+illustration\b", " ".join(label.split()), re.I) for label in labels):
            result.add(image.get("src", "").removeprefix("../"))
    return result


def replace_official_images(body: str, replacements: dict[str, list[tuple[str, tuple[int, int]]]]) -> str:
    root = ET.fromstring('<div xmlns:epub="http://www.idpf.org/2007/ops">' + body + "</div>")
    parents = {child: parent for parent in root.iter() for child in parent}
    for image in list(root.iter("img")):
        key = image.get("src", "").removeprefix("../")
        if key not in replacements:
            continue
        parent = parents[image]
        for caption in list(parent):
            if (caption.tag == "figcaption" or "thumbcaption" in classes(caption)) and re.match(
                r"^official\s+illustration\b", " ".join("".join(caption.itertext()).split()), re.I
            ):
                parent.remove(caption)
        wrapper = ET.Element("span", {"class": "nook-official-illustration", "style": "display: block; margin: 0; padding: 0; font-size: 0; line-height: 0;"})
        for href, (width, height) in replacements[key]:
            alt = image.get("alt", "")
            # The removed official credit is not used as a visible image label.
            if re.match(r"^official\s+illustration\b", alt, re.I):
                alt = "Official artwork"
            ET.SubElement(wrapper, "img", {"src": "../" + href, "alt": alt,
                "class": "nook-official-image", "width": str(width), "height": str(height),
                "style": "display: block; margin: 0 auto; padding: 0; page-break-inside: avoid;" + image.get("style", "")})
        wrapper.tail = image.tail
        parent.insert(list(parent).index(image), wrapper)
        parent.remove(image)
    return (root.text or "") + "".join(ET.tostring(child, encoding="unicode") for child in root)


def authored_image_width(style: str, layout: LegacyLayout, available: int | None = None) -> float:
    """Map website widths to the Nook column, using its 800px reader baseline."""
    available = layout.width if available is None else available
    match = re.search(r"(?:^|;)\s*width:\s*([\d.]+)(%|px)(?=\s|;|$)", style)
    if not match:
        return available
    return min(available, float(match[1]) * (available / 100 if match[2] == "%" else layout.width / 800))


def image_column_width(node: ET.Element, parents: dict, layout: LegacyLayout) -> int:
    width = layout.width
    ancestor = parents.get(node)
    while ancestor is not None:
        for name in classes(ancestor) & BOX_WINDOWS.keys():
            props = BOX_WINDOWS[name]
            effective = replace(layout, font_size=layout.font_size * (2 if name == "braun-screen" else 1))
            width -= 2 * (box_padding(props, effective)[1] + int(props["border"].split("px")[0]))
        ancestor = parents.get(ancestor)
    return max(1, width)


def box_padding(props: dict[str, str], layout: LegacyLayout) -> tuple[int, int]:
    values = props["padding"].split()
    def pixels(value: str) -> int:
        return round(float(value[:-2]) * (layout.font_size if value.endswith("em") else 1))
    return pixels(values[0]), pixels(values[-1])


def center_images(body: str, image_paths: dict[str, Path], cache: Path,
                  layout: LegacyLayout) -> tuple[str, list[tuple[Path, tuple[int, int]]]]:
    """Bake horizontal centering into every illustration's bitmap column."""
    from PIL import Image

    root = ET.fromstring('<div xmlns:epub="http://www.idpf.org/2007/ops">' + body + "</div>")
    parents = {child: parent for parent in root.iter() for child in parent}
    assets = []
    for node in root.iter("img"):
        if "nook-glyph" in classes(node):
            continue
        source = image_paths.get(node.get("src", "").removeprefix("../"))
        if source is None:
            continue
        width = image_column_width(node, parents, layout)
        background, ancestor = 255, parents.get(node)
        while ancestor is not None:
            own = classes(ancestor) & BOX_WINDOWS.keys()
            if own:
                background = int(BOX_WINDOWS[next(iter(own))]["background-color"][1] * 2, 16)
                break
            ancestor = parents.get(ancestor)
        with Image.open(source) as opened:
            image = opened.convert("L")
            image.thumbnail((width, layout.height), Image.Resampling.LANCZOS)
            if image.width == width:
                continue
            digest = hashlib.sha256(source.read_bytes() + f"horizontal-v1:{width}:{background}".encode()).hexdigest()[:20]
            target = cache / f"{source.stem}-center-{digest}.png"
            if not target.exists():
                canvas = Image.new("L", (width, image.height), background)
                canvas.paste(image, ((width - image.width) // 2, 0))
                cache.mkdir(parents=True, exist_ok=True)
                canvas.save(target, "PNG", optimize=True)
            size = width, image.height
        node.set("src", f"../Images/{target.name}")
        node.set("width", str(size[0]))
        node.set("height", str(size[1]))
        assets.append((target, size))
    return (root.text or "") + "".join(ET.tostring(child, encoding="unicode") for child in root), assets


def size_body_images(body: str, image_paths: dict[str, Path], cache: Path,
                     layout: LegacyLayout) -> tuple[str, list[tuple[Path, tuple[int, int]]]]:
    """Bake authored small widths into the actual files, not only image CSS."""
    from PIL import Image

    root = ET.fromstring('<div xmlns:epub="http://www.idpf.org/2007/ops">' + body + "</div>")
    parents = {child: parent for parent in root.iter() for child in parent}
    assets = []
    for node in root.iter("img"):
        source = image_paths.get(node.get("src", "").removeprefix("../"))
        if source is None:
            continue
        width = max(1, round(authored_image_width(node.get("style", ""), layout, image_column_width(node, parents, layout))))
        with Image.open(source) as image:
            size = image.size
        if size[0] <= width and size[1] <= layout.height:
            path = source
        else:
            path, size = resize_image(source, cache, replace(layout, width=width))
        assets.append((path, size))
        node.set("src", f"../Images/{path.name}")
        node.set("class", node.get("class", "") + " nook-sized-image")
        # It has already been mapped to the screen. Do not apply the website
        # pixel ratio or percentage a second time during XHTML conversion.
        node.set("style", re.sub(r"(?:^|;)\s*width:\s*[^;]+;?", ";", node.get("style", "")))
        node.set("width", str(size[0]))
        node.set("height", str(size[1]))
    return (root.text or "") + "".join(ET.tostring(child, encoding="unicode") for child in root), assets


def center_scare_images(body: str, image_paths: dict[str, Path], cache: Path, layout: LegacyLayout,
                        caption_font: Path | None = None) -> tuple[str, list[Path]]:
    """Center every image scare in a chapter that now shares one spine item."""
    root = ET.fromstring('<div xmlns:epub="http://www.idpf.org/2007/ops">' + body + "</div>")
    parents = {child: parent for parent in root.iter() for child in parent}
    paths = []
    for scare in list(root.iter()):
        if "epub-pagebreak" not in classes(scare):
            continue
        tail, scare.tail = scare.tail, None
        converted, path = center_scare_image(ET.tostring(scare, encoding="unicode"), image_paths, cache, layout, caption_font)
        replacement = ET.fromstring(converted)
        replacement.tail = tail
        parent = parents[scare]
        parent.insert(list(parent).index(scare), replacement)
        parent.remove(scare)
        if path:
            paths.append(path)
    return (root.text or "") + "".join(ET.tostring(child, encoding="unicode") for child in root), paths


def keep_illustration_credits(body: str, image_paths: dict[str, Path], cache: Path,
                              layout: LegacyLayout, caption_font: Path | None = None
                              ) -> tuple[str, list[tuple[Path, tuple[int, int]]]]:
    """Make each plain credit physically inseparable from its illustration.

    Linked captions remain live XHTML in a break-avoiding group; the image
    height is reduced first to reserve room for their text at the reading size.
    """
    from PIL import Image

    root = ET.fromstring('<div xmlns:epub="http://www.idpf.org/2007/ops">' + body + "</div>")
    parents = {child: parent for parent in root.iter() for child in parent}
    assets = []
    for figure in list(root.iter()):
        captions = [child for child in figure if child.tag == "figcaption" or "thumbcaption" in classes(child)]
        images = list(figure.iter("img"))
        if not captions or len(images) != 1 or "nook-official-image" in classes(images[0]):
            continue
        image = images[0]
        source = image_paths.get(image.get("src", "").removeprefix("../"))
        if source is None:
            continue
        if any(caption.find(".//a") is not None for caption in captions):
            reserve = 18 + sum(_estimate_height(caption, replace(layout, font_size=layout.font_size * 0.8), {}) for caption in captions)
            available = max(1, math.floor(layout.height - reserve))
            path, size = resize_image(source, cache, replace(layout, height=available))
            image.set("src", f"../Images/{path.name}")
            image.set("class", image.get("class", "") + " nook-linked-credit")
            image.set("width", str(size[0]))
            image.set("height", str(size[1]))
            assets.append((path, size))
            figure.set("class", figure.get("class", "") + " nook-credited-illustration")
            set_style(figure, page_break_inside="avoid", margin="0", padding="0")
            continue
        tail, figure.tail = figure.tail, None
        wrapped = '<div class="epub-pagebreak">' + ET.tostring(figure, encoding="unicode") + '</div>'
        figure_layout = replace(layout, width=image_column_width(image, parents, layout))
        composed, path = center_scare_image(wrapped, image_paths, cache, figure_layout, caption_font, full_page=False)
        if path is None:
            figure.tail = tail
            continue
        replacement = ET.fromstring(composed)[0]
        replacement.tail = tail
        replacement.set("class", replacement.get("class", "") + " nook-credited-illustration")
        set_style(replacement, page_break_inside="avoid", margin="0", padding="0", line_height="0")
        parent = parents[figure]
        parent.insert(list(parent).index(figure), replacement)
        parent.remove(figure)
        with Image.open(path) as bitmap:
            assets.append((path, bitmap.size))
    return (root.text or "") + "".join(ET.tostring(child, encoding="unicode") for child in root), assets


def center_scare_image(body: str, image_paths: dict[str, Path], cache: Path, layout: LegacyLayout,
                       caption_font: Path | None = None, full_page: bool = True) -> tuple[str, Path | None]:
    """Center a scare illustration in the bitmap itself, independent of CSS.

    Pandoc figure captions are composed below the centered artwork in the same
    canvas. Other text and linked footnotes stay in the XHTML after/before it.
    """
    from PIL import Image, ImageDraw, ImageFont

    root = ET.fromstring('<div xmlns:epub="http://www.idpf.org/2007/ops">' + body + "</div>")
    scare = next((node for node in root.iter() if "epub-pagebreak" in classes(node)), None)
    if scare is None:
        return body, None
    images = list(scare.iter("img"))
    if len(images) != 1:
        return body, None
    image_node = images[0]
    if "nook-linked-credit" in classes(image_node):
        return body, None
    parents = {child: parent for parent in scare.iter() for child in parent}
    ancestor = parents.get(image_node)
    while ancestor is not None:
        if classes(ancestor) & SPACED_BLOCKS:
            # A full-page canvas would overflow an inset window and separate
            # the picture from the other contents of that window.
            return body, None
        ancestor = parents.get(ancestor)
    source = image_paths.get(image_node.get("src", "").removeprefix("../"))
    if source is None:
        return body, None
    requested_width = max(1, round(authored_image_width(image_node.get("style", ""), layout)))
    captions = [node for node in scare.iter() if node.tag == "figcaption" or "thumbcaption" in classes(node)]
    # Do not rasterize interactive captions: their links must remain usable.
    captions = [node for node in captions if node.find(".//a") is None]
    caption = " ".join(" ".join("".join(node.itertext()).split()) for node in captions).strip()
    caption_font_bytes = caption_font.read_bytes() if caption and caption_font else b""
    digest = hashlib.sha256(source.read_bytes() + caption_font_bytes + f"center-v3:{layout}:{requested_width}:{caption}:{full_page}".encode()).hexdigest()[:20]
    target = cache / f"{'scare-centered' if full_page else 'credited'}-{digest}.png"
    cache.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        lines = []
        font = None
        line_height = 0
        if caption:
            if caption_font:
                from fontTools.ttLib import TTFont
                font_path = cache / ("caption-font-" + hashlib.sha256(caption_font_bytes).hexdigest()[:16] + ".ttf")
                if not font_path.exists():
                    with TTFont(caption_font) as face:
                        face.flavor = None
                        face.save(font_path)
                font = ImageFont.truetype(str(font_path), max(12, round(layout.font_size * 0.8)))
            else:
                font = ImageFont.load_default(size=max(12, round(layout.font_size * 0.8)))
            line = ""
            for word in caption.split():
                trial = (line + " " + word).strip()
                if line and font.getlength(trial) > layout.width - 16:
                    lines.append(line)
                    line = word
                else:
                    line = trial
            if line:
                lines.append(line)
            bounds = font.getbbox("Ag")
            line_height = bounds[3] - bounds[1] + 4
        credit_height = len(lines) * line_height + (6 if lines else 0)
        with Image.open(source) as image:
            image = image.convert("L")
            image.thumbnail((max(1, min(layout.width, requested_width)), max(1, layout.height - (2 if full_page else 1) * credit_height)), Image.Resampling.LANCZOS)
            canvas_height = layout.height if full_page else image.height + credit_height
            canvas = Image.new("L", (layout.width, canvas_height), 255)
            top = (layout.height - image.height) // 2 if full_page else 0
            canvas.paste(image, ((layout.width - image.width) // 2, top))
            if lines:
                draw = ImageDraw.Draw(canvas)
                y = top + image.height + 6
                for line in lines:
                    draw.text(((layout.width - font.getlength(line)) / 2, y), line, font=font, fill=0, anchor="lt")
                    y += line_height
            canvas.save(target, "PNG", optimize=True)
    parents = {child: parent for parent in scare.iter() for child in parent}
    for node in captions:
        parents[node].remove(node)
    if caption:
        image_node.set("title", caption)
        if not image_node.get("alt"):
            image_node.set("alt", caption)
    image_node.set("src", f"../Images/{target.name}")
    image_node.attrib.pop("style", None)
    image_node.attrib.pop("width", None)
    image_node.attrib.pop("height", None)
    return (root.text or "") + "".join(ET.tostring(child, encoding="unicode") for child in root), target


def classes(element: ET.Element) -> set[str]:
    return set(element.get("class", "").split())


def set_style(element: ET.Element, **props: str) -> None:
    style = element.get("style", "").rstrip("; ")
    additions = "; ".join(f"{key.replace('_', '-')}: {value}" for key, value in props.items())
    element.set("style", (style + "; " if style else "") + additions + ";")


def _estimate_height(element: ET.Element, layout: LegacyLayout, scales: dict[str, float]) -> float:
    """Approximate reflow, including inline sizes, hard breaks, and bitmaps.

    This is intentionally a build-time estimate, not an e-reader emulator.
    Long content receives no spacer and remains free to span multiple pages.
    """
    total, used, line = 0.0, 0.0, 0.0

    def flush() -> None:
        nonlocal total, used, line
        if used or line:
            total += line
        used = line = 0.0

    def text(value: str | None, size: float) -> None:
        nonlocal used, line
        for word in re.findall(r"\s+|\S+", value or ""):
            if word.isspace():
                if used:
                    used += size * 0.28
                continue
            width = sum(size * (1 if unicodedata.east_asian_width(c) in {"W", "F"} else
                               0 if unicodedata.combining(c) else
                               0.28 if c in "ilI.,!|'" else 0.85 if c in "MW@" else 0.53) for c in word)
            if used and used + width > layout.width:
                flush()
            if width > layout.width:
                total_lines = math.ceil(width / layout.width) - 1
                # Long letter runs must still contribute their wrapped height.
                for _ in range(total_lines):
                    line = max(line, size * layout.line_height)
                    flush()
                width -= total_lines * layout.width
            used += width
            line = max(line, size * layout.line_height)

    def visit(node: ET.Element, parent_size: float) -> None:
        nonlocal total, line
        cls = classes(node)
        if "epub-chapter-label" in cls or "display: none" in node.get("style", ""):
            return
        size = parent_size
        for name in node.get("class", "").split():
            if name in scales:
                size = parent_size * scales[name]
        match = re.search(r"font-size:\s*([\d.]+)(em|px|%)", node.get("style", ""))
        if match:
            size = float(match[1]) * (parent_size if match[2] == "em" else parent_size / 100 if match[2] == "%" else 1)
        block = node.tag in BLOCKS or bool(cls & ({"text-large-centered", "align-left", "align-right", "align-center", "nook-block-spacer"} | SPACED_BLOCKS))
        if block:
            flush()
            for name in cls & BOX_WINDOWS.keys():
                props = BOX_WINDOWS[name]
                total += 2 * (box_padding(props, replace(layout, font_size=size))[0] + int(props["border"].split("px")[0]))
        if node.tag == "br":
            line = max(line, size * layout.line_height)
            flush()
        elif node.tag == "img":
            flush()
            total += int(node.get("height", "0"))
        else:
            text(node.text, size)
            for child in node:
                visit(child, size)
                text(child.tail, size)
        if block:
            flush()
            if node.tag == "p":
                total += 0 if "nook-block-spacer" in cls else 8 if "nook-window-rule" in cls else 9

    visit(element, layout.font_size)
    flush()
    return total


def transform_body(body: str, layout: LegacyLayout, image_sizes: dict[str, tuple[int, int]], css: str) -> str:
    """Input is balanced XHTML. All essential decoration becomes real text."""
    root = ET.fromstring('<div xmlns:epub="http://www.idpf.org/2007/ops">' + body + "</div>")
    # Pandoc renders Markdown *** scene breaks as unclassed hr elements.
    # Wrap them so two extra literal lines can surround each scene break.
    # Explicit visible/invisible rules and footnote separators keep their roles.
    for parent in list(root.iter()):
        for node in list(parent):
            if node.tag == "hr" and not node.get("class"):
                wrapper = ET.Element("div", {"class": "nook-horizontal-break"})
                wrapper.tail, node.tail = node.tail, None
                parent.insert(list(parent).index(node), wrapper)
                parent.remove(node)
                wrapper.append(node)
    parents = {child: parent for parent in root.iter() for child in parent}
    for node in root.iter():
        if node.tag == "marquee":
            node.attrib = {key: value for key, value in node.attrib.items() if key in {"class", "style", "id"}}
        node.tag = {"section": "div", "aside": "div", "nav": "div", "figure": "div", "figcaption": "div", "mark": "span", "marquee": "span"}.get(node.tag, node.tag)
        for key in list(node.attrib):
            if key.startswith(("{", "aria-", "data-")) or key in {"role", "hidden"}:
                del node.attrib[key]
        original_style = node.get("style", "")
        props = declarations(original_style, TYPOGRAPHY | {"display", "text-indent", "line-height", "page-break-before", "page-break-inside"})
        node.attrib.pop("style", None)
        if props:
            set_style(node, **props)
        cls = classes(node)
        if "epub-chapter-label" in cls:
            set_style(node, display="none")
        if node.tag == "img":
            src = node.get("src", "").removeprefix("../")
            if src not in image_sizes:
                raise ValueError(f"Legacy image is not packaged: {node.get('src')}")
            width, height = image_sizes[src]
            # Preserve authored smaller widths without allowing an enlargement.
            available = image_column_width(node, parents, layout)
            requested = available if "nook-sized-image" in cls else authored_image_width(original_style, layout, available)
            if 0 < requested < width:
                height = max(1, round(height * requested / width))
                width = max(1, round(requested))
            node.set("width", str(width))
            node.set("height", str(height))
            node.set("alt", node.get("alt", ""))
            set_style(node, width=f"{width}px", height=f"{height}px")
        if cls & TEXT_WINDOWS:
            node.set("class", node.get("class", "") + " nook-window")
        if cls & SPACED_BLOCKS and (node.text or "").strip():
            text = ET.Element("span")
            text.text, node.text = node.text, None
            node.insert(0, text)
        if node.tag in BLOCKS and len(node) and node[0].tag == "br" and not (node.text or "").strip():
            # An empty first line can be discarded by old RMSDK engines.
            # Give every leading hard-break line actual (blank) content.
            node.text = "\u00a0"
            for child in node:
                if child.tag != "br":
                    break
                if (child.tail or "").strip():
                    break
                child.tail = "\u00a0"
        for name in cls & BOX_WINDOWS.keys():
            set_style(node, **{key: value for key, value in BOX_WINDOWS[name].items() if key != "text-align"})
        if "braun-screen" in cls:
            set_style(node, font_size="2em", white_space="normal", page_break_inside="avoid")
        if cls & {"wiki-window", "record-window"}:
            if "no-meta" not in cls:
                first = next((child for child in node if child.tag == "p"), None)
                if first is not None:
                    first.set("class", first.get("class", "") + " nook-window-meta")
                    set_style(first, text_align=("right" if "wiki-window" in cls else "left") + " !important")
        if cls & RULED_WINDOWS:
            for index in (0, len(node) + 1):
                rule = ET.Element("p", {"class": "nook-window-rule"})
                # A short ASCII rule also fits at larger user-selected sizes.
                rule.text = "=" * min(22, max(3, int(layout.width / (layout.font_size * 0.65))))
                node.insert(index, rule)
        if "note-window" in cls and "no-meta" not in cls:
            first = next((child for child in node if child.tag == "p"), None)
            if first is not None:
                first.set("class", first.get("class", "") + " nook-note-title")
        if "comment" in cls:
            node.text = "- " + (node.text or "")
        if "reply-icon" in cls:
            node.text = "∟"
        if "comment-post-header" in cls and not any("ch1_1" in image.get("src", "") for image in node.iter("img")):
            for index in (0, len(node) + 1):
                rule = ET.Element("p", {"class": "nook-comment-rule"})
                rule.text = "-----------"
                node.insert(index, rule)
        if "sms-bubble" in cls:
            if cls & {"sms-left", "sms-center"}:
                node.text = "- " + (node.text or "")
            if cls & {"sms-right", "sms-center"}:
                if len(node):
                    node[-1].tail = (node[-1].tail or "") + " -"
                else:
                    node.text = (node.text or "") + " -"
        if node.tag == "u":
            node.tag = "span"
            set_style(node, text_decoration="underline")

    # Multiline alignment markup occasionally encloses full paragraphs.
    # In XHTML 1.1 those wrappers must be block containers.
    for node in reversed(list(root.iter())):
        if node.tag == "span" and any(child.tag in BLOCKS for child in node):
            node.tag = "div"

    # XHTML 1.1 omits HTML's ol/start and ol/type attributes. Bake numeric
    # continuations into the text so old readers need no CSS counter support.
    for node in root.iter():
        if node.tag != "ol":
            continue
        list_type = node.attrib.pop("type", "1")
        start = node.attrib.pop("start", "1")
        if list_type != "1":
            set_style(node, list_style_type={"a": "lower-alpha", "A": "upper-alpha", "i": "lower-roman", "I": "upper-roman"}.get(list_type, "decimal"))
        ancestor = parents.get(node)
        in_window = False
        while ancestor is not None:
            in_window |= bool(classes(ancestor) & {"wiki-window", "record-window", "plain-window", "followup-window"})
            ancestor = parents.get(ancestor)
        if list_type != "1" or not start.isdigit() or (start == "1" and not in_window):
            continue
        node.tag = "div"
        node.set("class", node.get("class", "") + " nook-numbered-list")
        for number, child in enumerate(node, int(start)):
            if child.tag != "li":
                continue
            child.tag = "div"
            child.set("class", child.get("class", "") + " nook-list-item")
            set_style(child, margin="0", padding="0")
            target = child[0] if len(child) and child[0].tag == "p" and not (child.text or "").strip() else child
            target.text = f"{number}. " + (target.text or "")

        if in_window:
            # Flatten each item's br-separated runs to ordinary paragraphs.
            # This avoids native list indentation/font changes on continuation
            # pages and makes each intentional blank line nonempty.
            for item in list(node):
                if item.tag != "div":
                    continue
                fragments = []
                paragraph = ET.Element("p", {"class": "nook-list-paragraph", "style": "margin: 0; padding: 0; font-size: 1em;"})
                paragraph.text = item.text
                def append_text(value):
                    if len(paragraph):
                        paragraph[-1].tail = (paragraph[-1].tail or "") + (value or "")
                    else:
                        paragraph.text = (paragraph.text or "") + (value or "")
                for child in list(item):
                    if child.tag == "br":
                        if not "".join(paragraph.itertext()).strip():
                            paragraph.text = "\u00a0"
                        fragments.append(paragraph)
                        paragraph = ET.Element("p", {"class": "nook-list-paragraph", "style": "margin: 0; padding: 0; font-size: 1em;"})
                        paragraph.text = child.tail
                    elif child.tag == "p":
                        if "".join(paragraph.itertext()).strip() or len(paragraph):
                            fragments.append(paragraph)
                        child.set("class", child.get("class", "") + " nook-list-paragraph")
                        set_style(child, font_size="1em", margin="0", padding="0")
                        fragments.append(child)
                        paragraph = ET.Element("p", {"class": "nook-list-paragraph", "style": "margin: 0; padding: 0; font-size: 1em;"})
                        paragraph.text = child.tail
                        child.tail = None
                    elif child.tag in BLOCKS | {"ul", "ol", "table", "pre", "dl"}:
                        if "".join(paragraph.itertext()).strip() or len(paragraph):
                            fragments.append(paragraph)
                        fragments.append(child)
                        paragraph = ET.Element("p", {"class": "nook-list-paragraph", "style": "margin: 0; padding: 0; font-size: 1em;"})
                        paragraph.text, child.tail = child.tail, None
                    else:
                        tail = child.tail
                        child.tail = None
                        paragraph.append(child)
                        append_text(tail)
                if "".join(paragraph.itertext()).strip() or len(paragraph):
                    fragments.append(paragraph)
                item.text = None
                item[:] = fragments
                for fragment in fragments:
                    if fragment.tag == "p" and not "".join(fragment.itertext()).strip() and fragment.find(".//img") is None:
                        fragment.set("class", fragment.get("class", "") + " nook-list-gap")
                        fragment.text = "\u00a0"
                        fragment.set("style", "margin: 0 !important; padding: 0 !important; font-size: 0.5em !important; line-height: 1;")
            set_style(node, margin="0", padding="0")

    def align(node: ET.Element, inherited: str | None = None) -> None:
        cls = classes(node)
        for name in cls & BOX_WINDOWS.keys():
            inherited = BOX_WINDOWS[name]["text-align"]
        direction = next((direction for direction in ("left", "right", "center")
                          if cls & {f"align-{direction}", f"mono-{direction}", f"sms-{direction}"}), inherited)
        inline = re.search(r"text-align:\s*(left|right|center|justify)", node.get("style", ""))
        if inline:
            direction = inline[1]
        if "text-large-centered" in cls:
            direction = "center"
        # A lone aligned span also needs alignment on its containing paragraph.
        if node.tag == "p" and len(node) == 1 and not (node.text or "").strip() and not (node[0].tail or "").strip():
            child_cls = classes(node[0])
            direction = next((d for d in ("left", "right", "center") if child_cls & {f"align-{d}", f"mono-{d}"}), direction)
        if direction and (node.tag in BLOCKS or cls & {"align-left", "align-right", "align-center", "mono-left", "mono-right", "mono-center"}):
            set_style(node, text_align=f"{direction} !important", text_indent="0")
        for child in node:
            align(child, direction)

    align(root)
    for node in root.iter():
        if "epub-pagebreak" in classes(node):
            for image in node.iter("img"):
                if "nook-official-image" not in classes(image):
                    set_style(image, display="inline", margin="0")
            for paragraph in node.iter("p"):
                if paragraph.find(".//img") is not None:
                    set_style(paragraph, text_align="center !important", margin="0", padding="0")
            for container in node.iter("div"):
                if any(child.tag == "img" for child in container):
                    set_style(container, text_align="center !important", margin="0", padding="0")
    # Every illustration has a full centered bitmap column and explicit
    # centering as well, including pictures outside scare pages.
    for image in root.iter("img"):
        if "nook-glyph" not in classes(image):
            set_style(image, display="block !important", margin="0 auto !important")

    # Styled boxes have one text line of CSS padding inside and one literal
    # blank line outside. Other wrappers keep their independent blank lines.
    parents = {child: parent for parent in root.iter() for child in parent}
    for node in list(root.iter()):
        if classes(node) & SPACED_BLOCKS:
            set_style(node, display="block", margin="0")
            if not classes(node) & BOX_WINDOWS.keys():
                set_style(node, padding="0")
            # Text directly on an element precedes all its children in XML.
            # Move it into a run before inserting the leading blank line.
            if node.text and node.text.strip():
                text = ET.Element("span")
                text.text = node.text
                node.text = None
                node.insert(0, text)
            boxed = bool(classes(node) & BOX_WINDOWS.keys())
            target = node
            if boxed:
                parent = parents[node]
                target = ET.Element("div", {"class": "nook-box-spacing", "style": "margin: 0; padding: 0;"})
                target.tail, node.tail = node.tail, None
                parent.insert(list(parent).index(node), target)
                parent.remove(node)
                target.append(node)
            for index in (0, len(target) + 1):
                tag = "span" if node.tag in {"span", "strong", "em", "a"} else "p"
                spacer = ET.Element(tag, {"class": "nook-block-spacer", "style": f"margin: 0; padding: 0; font-size: 1em; line-height: {layout.line_height:g};"})
                spacer.text = "\u00a0"
                if not boxed:
                    br = ET.SubElement(spacer, "br")
                    if "nook-horizontal-break" in classes(node):
                        # A trailing br alone can collapse its empty final
                        # line; give both scene-break padding lines content.
                        br.tail = "\u00a0"
                target.insert(index, spacer)
            content = [child for child in node if "nook-block-spacer" not in classes(child)]
            for child in content[:1] + content[-1:]:
                if child.tag == "p":
                    set_style(child, margin_top="0", margin_bottom="0")

    scales = {}
    for selector, declaration in css_rules(css):
        match = re.search(r"(?:^|;)\s*font-size:\s*([\d.]+)em\b", declaration)
        if match:
            for name in selector.split(","):
                if re.fullmatch(r"\.[\w-]+", name.strip()):
                    scales[name.strip()[1:]] = float(match[1])
    for node in list(root.iter()):
        if "epub-pagebreak" not in classes(node):
            continue
        if any("braun-screen" in classes(child) for child in node.iter()):
            # Its enlarged text and two-line inner padding already make a
            # substantial screen; do not vertically center the whole box.
            continue
        visible = "".join(node.itertext()).replace("\u00a0", "").strip()
        # The modern builder already identifies short/centered scares. Longer
        # text stays at the top even when a height estimate leaves spare room.
        if len(visible) >= 120 or "epub-pagebreak-center" not in classes(node):
            continue
        height = _estimate_height(node, layout, scales)
        # Leave an extra line as a guard against differences in font metrics.
        blank_lines = max(0, math.floor((layout.height - height - layout.font_size * layout.line_height) / (2 * layout.font_size * layout.line_height)))
        if blank_lines:
            spacer = ET.Element("p", {"class": "nook-scare-spacer"})
            set_style(spacer, font_size=f"{layout.font_size:g}px", line_height=f"{layout.line_height:g}", margin="0", padding="0")
            spacer.text = "\u00a0"
            for _ in range(blank_lines - 1):
                ET.SubElement(spacer, "br").tail = "\u00a0"
            node.insert(0, spacer)
    return (root.text or "") + "".join(ET.tostring(child, encoding="unicode") for child in root)


def epub2_document(document: str) -> str:
    document = document.replace('<!DOCTYPE html>', '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">')
    document = re.sub(r'<meta charset="utf-8"\s*/>', '<meta http-equiv="Content-Type" content="application/xhtml+xml; charset=utf-8" />', document)
    document = re.sub(r' xmlns:epub="[^"]+"| epub:type="[^"]+"', "", document)
    return document.replace("<nav ", "<div ").replace("</nav>", "</div>")


def epub2_package(package: str) -> str:
    package = package.replace('version="3.0"', 'version="2.0"')
    package = re.sub(r' properties="[^"]+"', "", package)
    package = re.sub(r'<meta property="dcterms:modified">[^<]*</meta>', "", package)
    return package.replace("</spine>", '</spine><guide><reference type="toc" title="Table of Contents" href="nav.xhtml" /></guide>')


COMPACT_FONT_RESET = """
html body#gsgw-legacy-compact, html body#gsgw-legacy-compact * {
  font-weight: normal !important;
  font-style: normal !important;
}
"""


def compact_document(document: str, limit: int = 300 * 1024) -> str:
    """Keep large chapters intact by sharing redundant font-reset declarations.

    Each run retains its explicit embedded font family and all other inline
    styling. The selected font already contains the bold/italic outlines, so
    the shared, high-specificity reset is equivalent to the removed properties.
    Blank paragraphs, breaks, text and anchors remain untouched.
    """
    if len(document.encode("utf-8")) < limit:
        return document

    def compact_style(match: re.Match) -> str:
        style = re.sub(r"font-(?:weight|style):\s*normal\s*!important;\s*", "", match[2])
        return match[1] + style + match[3]

    document = re.sub(r'(\sstyle=")([^"]*)(")', compact_style, document)
    if "<body>" not in document:
        raise ValueError("Large Legacy chapter has no body for font-reset styling")
    document = document.replace("<body>", '<body id="gsgw-legacy-compact">', 1)
    if len(document.encode("utf-8")) >= limit:
        raise ValueError("Legacy chapter remains above the 300 KB reader limit")
    return document


def prepare_embedded_fonts(
    builder: Any,
    css: str,
    codepoints: set[int],
    force_truetype: bool = True,
) -> tuple[str, list[EpubAsset]]:
    """Embed static fonts with the book's characters and OpenType features."""
    try:
        from fontTools import subset
        from fontTools.ttLib import TTFont
        from fontTools.varLib.instancer import instantiateVariableFont
    except ImportError as exc:
        raise RuntimeError('EPUB font conversion requires fonttools and brotli.') from exc
    converted_dir = builder.OUTPUT_DIR / 'converted_fonts'
    converted_dir.mkdir(parents=True, exist_ok=True)
    fonts: dict[str, builder.EpubAsset] = {}
    character_key = hashlib.sha256(','.join((str(value) for value in sorted(codepoints))).encode('ascii')).hexdigest()[:16]

    def convert_face(match: re.Match) -> str:
        face = match.group(0)
        source = re.search('url\\([\\\'"]?([^\\)\\\'\\"]+)', face)
        if not source:
            return face
        name = Path(urllib.parse.unquote(source.group(1))).name
        src = builder.FONTS_DIR / name
        if force_truetype and (not src.exists()):
            src = builder.SCRIPT_DIR / 'legacy_fonts' / name
        with TTFont(src) as font:
            axes = {axis.axisTag: axis.defaultValue for axis in font['fvar'].axes} if 'fvar' in font else {}
            weights = re.search('font-weight:\\s*(\\d+)\\s+(\\d+)\\s*;', face)
            if weights and 'wght' in axes:
                axes['wght'] = max(int(weights[1]), min(int(weights[2]), axes['wght']))
            if force_truetype and 'wght' in axes:
                static_weight = re.search('font-weight:\\s*(\\d+)\\s*;', face)
                if static_weight:
                    axis = next((axis for axis in font['fvar'].axes if axis.axisTag == 'wght'))
                    axes['wght'] = max(axis.minValue, min(axis.maxValue, int(static_weight[1])))
            cff = 'CFF ' in font or 'CFF2' in font
            suffix = '.otf' if cff and (not force_truetype) else '.ttf'
            axis_suffix = ''.join((f'-{tag}{value:g}' for tag, value in sorted(axes.items())))
            may_subset = not font['OS/2'].fsType & 256
            subset_suffix = f'-subset{character_key}' if may_subset else ''
            output_name = src.stem + axis_suffix + subset_suffix + ('-nook-v1' if force_truetype else '') + suffix
            dst = converted_dir / output_name
            if not dst.exists() or dst.stat().st_mtime_ns < src.stat().st_mtime_ns:
                if axes:
                    instantiateVariableFont(font, axes, inplace=True)
                if may_subset:
                    options = subset.Options()
                    options.layout_features = ['*']
                    options.name_IDs = ['*']
                    options.name_languages = ['*']
                    options.glyph_names = True
                    options.notdef_outline = True
                    options.recommended_glyphs = True
                    options.legacy_kern = True
                    subsetter = subset.Subsetter(options=options)
                    subsetter.populate(unicodes=codepoints)
                    subsetter.subset(font)
                if force_truetype and cff:
                    truetype_outlines(font)
                font.flavor = None
                font.save(dst)
            if weights:
                face = face[:weights.start()] + f"font-weight: {axes.get('wght', 400):g};" + face[weights.end():]
        font_format = 'opentype' if suffix == '.otf' else 'truetype'
        face = re.sub('url\\([^)]*\\)(?:\\s*format\\([^)]*\\))?', lambda _: f'url("../Fonts/{output_name}") format("{font_format}")', face)
        media_type = 'application/vnd.ms-opentype' if force_truetype else 'font/otf' if suffix == '.otf' else 'font/ttf'
        fonts[output_name] = builder.EpubAsset(dst, f'Fonts/{output_name}', media_type)
        return face
    css = re.sub('@font-face\\s*\\{[^}]*\\}', convert_face, css)
    return (css, list(fonts.values()))


def write_epub(
    builder: Any,
    epub_path: Path,
    book_title: str,
    metadata: dict[str, Any],
    items: list[EpubItem],
    assets: dict[Path, EpubAsset],
    cover_item: EpubItem | None = None,
    cover_asset: EpubAsset | None = None,
    identifier_override: str | None = None,
    variant: str = "legacy",
    *,
    legacy_layout: LegacyLayout | None = None,
) -> None:
    """Prepare and package Legacy without changing the original Styled writer."""
    if variant != "legacy":
        raise ValueError("The Legacy writer only accepts variant=legacy")
    legacy_layout = legacy_layout or LegacyLayout()
    css_source = builder.CSS_PATH.read_text(encoding='utf-8')
    if legacy_layout:
        css_source = stylesheet(css_source, legacy_layout)
        items = [replace(item, body=builder.to_xhtml(escape_unknown_tags(item.body))) for item in items]
        official_refs = set().union(*(official_image_refs(item.body) for item in items))
        official_replacements = {}
        image_sizes = {}
        legacy_assets = {}
        for original in assets.values():
            if original.href in official_refs:
                tiles = [resize_image(original.source_path, builder.OUTPUT_DIR / 'legacy_images', legacy_layout)]
                official_replacements[original.href] = []
                for path, size in tiles:
                    asset = builder.EpubAsset(path, f'Images/{path.name}', 'image/png')
                    legacy_assets[path] = asset
                    image_sizes[asset.href] = size
                    official_replacements[original.href].append((asset.href, size))
                continue
            path, size = resize_image(original.source_path, builder.OUTPUT_DIR / 'legacy_images', legacy_layout)
            asset = builder.EpubAsset(path, f'Images/{path.name}', 'image/png')
            legacy_assets[path] = asset
            image_sizes[asset.href] = size
            items = [replace(item, body=item.body.replace(f'../{original.href}', f'../{asset.href}')) for item in items]
            if cover_item:
                cover_item = replace(cover_item, body=cover_item.body.replace(f'../{original.href}', f'../{asset.href}'))
            if cover_asset and original.href == cover_asset.href:
                cover_asset = asset
        assets = legacy_assets
        items = [replace(item, body=replace_official_images(item.body, official_replacements)) for item in items]
        image_paths = {asset.href: asset.source_path for asset in assets.values()}
        sized_items = []
        for item in items:
            body, sized_images = size_body_images(item.body, image_paths, builder.OUTPUT_DIR / 'legacy_images', legacy_layout)
            for path, size in sized_images:
                href = f'Images/{path.name}'
                assets[path] = builder.EpubAsset(path, href, 'image/png')
                image_sizes[href] = size
                image_paths[href] = path
            sized_items.append(replace(item, body=body))
        items = sized_items
        credited_items = []
        for item in items:
            body, credited_images = keep_illustration_credits(item.body, image_paths, builder.OUTPUT_DIR / 'legacy_images', legacy_layout, builder.FONTS_DIR / 'Libron-Regular.woff2')
            for path, size in credited_images:
                href = f'Images/{path.name}'
                assets[path] = builder.EpubAsset(path, href, 'image/png')
                image_sizes[href] = size
                image_paths[href] = path
            credited_items.append(replace(item, body=body))
        items = credited_items
        centered_items = []
        for item in items:
            body, centered_images = center_scare_images(builder.to_xhtml(escape_unknown_tags(item.body)), image_paths, builder.OUTPUT_DIR / 'legacy_images', legacy_layout, builder.FONTS_DIR / 'Libron-Regular.woff2')
            for centered_image in centered_images:
                href = f'Images/{centered_image.name}'
                assets[centered_image] = builder.EpubAsset(centered_image, href, 'image/png')
                image_sizes[href] = (legacy_layout.width, legacy_layout.height)
            centered_items.append(replace(item, body=body))
        items = centered_items
        centered_items = []
        for item in items + ([cover_item] if cover_item else []):
            body, images = center_images(item.body, image_paths, builder.OUTPUT_DIR / 'legacy_images', legacy_layout)
            for path, size in images:
                href = f'Images/{path.name}'
                assets[path] = builder.EpubAsset(path, href, 'image/png')
                image_sizes[href] = size
                image_paths[href] = path
            updated = replace(item, body=body)
            if item is cover_item:
                cover_item = updated
            else:
                centered_items.append(updated)
        items = centered_items
        items = [replace(item, body=transform_body(builder.to_xhtml(escape_unknown_tags(item.body)), legacy_layout, image_sizes, css_source)) for item in items]
        if cover_item:
            cover_item = replace(cover_item, body=transform_body(builder.to_xhtml(cover_item.body), legacy_layout, image_sizes, css_source))
    text = book_title + css_source + ''.join((item.body for item in items))
    if cover_item:
        text += cover_item.body
    codepoints = {ord(char) for char in html.unescape(text)} | set(range(32, 127)) | set(range(8192, 8304))
    codepoints.update((int(value, 16) for value in re.findall('\\\\([0-9a-fA-F]{1,6})', css_source) if int(value, 16) <= 1114111))
    css, embedded_fonts = prepare_embedded_fonts(builder, css_source, codepoints, force_truetype=bool(legacy_layout))
    if legacy_layout:
        import epub_legacy_fonts
        catalog = epub_legacy_fonts.FontCatalog(css, embedded_fonts, builder.OUTPUT_DIR / 'legacy_font_faces')
        items = [replace(item, body=catalog.apply(item.body, builder.OUTPUT_DIR / 'legacy_glyphs')) for item in items]
        if cover_item:
            cover_item = replace(cover_item, body=catalog.apply(cover_item.body, builder.OUTPUT_DIR / 'legacy_glyphs'))
        css, embedded_fonts = (catalog.css, catalog.assets)
        for path, href in catalog.glyph_assets.items():
            assets[path] = builder.EpubAsset(path, href, 'image/png')
        if catalog.missing:
            missing = ', '.join((f'{char!r} U+{ord(char):04X}' for char in sorted(catalog.missing)))
            raise RuntimeError(f'No embedded Legacy font covers these original characters: {missing}')
    modified = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')
    identifier = identifier_override or builder.metadata_text(metadata.get('identifier'), '')
    identifier = builder.valid_identifier(identifier, book_title)
    unique_assets = {}
    for asset in [*assets.values(), *embedded_fonts]:
        previous = unique_assets.get(asset.href)
        if previous and previous.source_path != asset.source_path:
            raise ValueError(f"Conflicting Legacy assets: {asset.href}")
        unique_assets[asset.href] = asset
    asset_list = sorted(unique_assets.values(), key=lambda asset: asset.href)
    epub_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(epub_path, 'w') as zf:
        mimetype = zipfile.ZipInfo('mimetype')
        mimetype.compress_type = zipfile.ZIP_STORED
        zf.writestr(mimetype, 'application/epub+zip')

        def write_text(name: str, data: str) -> None:
            zf.writestr(name, data.encode('utf-8'), compress_type=zipfile.ZIP_DEFLATED)
        write_text('META-INF/container.xml', builder.container_xml())
        write_text('OEBPS/Styles/stylesheet.css', css + COMPACT_FONT_RESET)
        package_metadata = {**metadata, 'identifier': identifier}
        package = builder.content_opf(book_title, package_metadata, items, asset_list, modified, cover_asset, cover_item)
        write_text('OEBPS/content.opf', epub2_package(package) if legacy_layout else package)
        write_text('OEBPS/toc.ncx', builder.toc_ncx(book_title, identifier, items))
        nav = builder.nav_xhtml(book_title, items)
        write_text('OEBPS/nav.xhtml', epub2_document(nav) if legacy_layout else nav)

        def document(title: str, body: str) -> str:
            page = builder.xhtml_page(title, body)
            return compact_document(epub2_document(page))
        if cover_item:
            write_text(f'OEBPS/{cover_item.href}', document(cover_item.title, cover_item.body))
        for item in items:
            body = item.body if legacy_layout else builder.section_body(item.body)
            write_text(f'OEBPS/{item.href}', document(item.title, body))
        for asset in asset_list:
            zf.write(asset.source_path, f'OEBPS/{asset.href}', compress_type=zipfile.ZIP_DEFLATED)
