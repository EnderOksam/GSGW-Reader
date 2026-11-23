"""Explicit font selection and original Unicode glyphs for older Legacy readers."""

from __future__ import annotations

import hashlib
import math
import re
import unicodedata
import xml.etree.ElementTree as ET
from dataclasses import dataclass, replace
from pathlib import Path

from fontTools.ttLib import TTFont

from epub_legacy import BOX_WINDOWS, classes, css_rules, declarations, set_style


def ink_color(value, background):
    """Resolve ordinary CSS ink to RGB, flattening alpha for old renderers."""
    from PIL import ImageColor

    value = value.replace("!important", "").strip()
    if value.lower() in {"inherit", "currentcolor", "initial", "unset"}:
        return None
    rgba = re.fullmatch(r"rgba\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*\)", value)
    if rgba:
        alpha = float(rgba[4])
        return tuple(round(float(rgba[i + 1]) * alpha + background[i] * (1 - alpha)) for i in range(3))
    try:
        return ImageColor.getrgb(value)[:3]
    except ValueError:
        return None


def color_hex(color):
    return "#" + "".join(f"{value:02x}" for value in color)


def eink_ink(color, background):
    """Keep hues/gray differences while making all light-page ink legible."""
    if sum(background) < 384:
        return color
    color = tuple(round(value * 0.65) for value in color)
    luminance = sum(value * coefficient for value, coefficient in zip(color, (0.299, 0.587, 0.114)))
    if luminance > 112:
        color = tuple(round(value * 112 / luminance) for value in color)
    return color


def embolden_outlines(font, weight_steps):
    """Bake a modest weight increase into static TrueType glyph outlines.

    Use the FreeType bundled with Pillow. This preserves curve point counts,
    rather than asking old RMSDK to synthesize an unsupported 500/800 face.
    """
    import array
    import ctypes as C
    from PIL import _imagingft
    from fontTools.fontBuilder import FontBuilder
    from fontTools.ttLib.tables._g_l_y_f import Glyph, GlyphCoordinates
    from fontTools.ttLib.tables.ttProgram import Program

    class Vector(C.Structure):
        _fields_ = [("x", C.c_long), ("y", C.c_long)]
    class Outline(C.Structure):
        _fields_ = [("n_contours", C.c_ushort), ("n_points", C.c_ushort),
                    ("points", C.POINTER(Vector)), ("tags", C.POINTER(C.c_ubyte)),
                    ("contours", C.POINTER(C.c_ushort)), ("flags", C.c_int)]

    library = C.CDLL(_imagingft.__file__)
    embolden = library.FT_Outline_EmboldenXY
    embolden.argtypes = [C.POINTER(Outline), C.c_long, C.c_long]
    embolden.restype = C.c_int
    strength = round(font["head"].unitsPerEm * weight_steps / 72 * 64)
    metrics = font["hmtx"].metrics
    glyphs = {}
    for name in font.getGlyphOrder():
        coords, ends, flags = font["glyf"][name].getCoordinates(font["glyf"])
        glyph = Glyph()
        glyph.numberOfContours = len(ends)
        glyph.program = Program()
        glyph.program.fromBytecode([])
        if coords:
            points = (Vector * len(coords))(*(Vector(round(x * 64), round(y * 64)) for x, y in coords))
            tags = (C.c_ubyte * len(coords))(*(flag & 1 for flag in flags))
            contours = (C.c_ushort * len(ends))(*ends)
            outline = Outline(len(ends), len(coords), points, tags, contours, 0)
            error = embolden(C.byref(outline), strength, strength)
            if error:
                raise RuntimeError(f"FreeType could not embolden {name}: {error}")
            glyph.coordinates = GlyphCoordinates((round(p.x / 64), round(p.y / 64)) for p in points)
            glyph.endPtsOfContours = list(ends)
            glyph.flags = array.array("B", (flag & 1 for flag in flags))
        glyphs[name] = glyph
    builder = FontBuilder(font=font)
    builder.setupGlyf(glyphs)
    builder.setupMaxp()
    for name, glyph in glyphs.items():
        if glyph.numberOfContours:
            metrics[name] = (metrics[name][0], glyph.xMin)
    for table in ("fpgm", "prep", "cvt ", "VDMX", "hdmx", "LTSH"):
        if table in font:
            del font[table]


@dataclass
class Face:
    family: str
    weight: int
    italic: bool
    alias: str
    path: Path
    codepoints: set[int]


def rename_regular_face(font: TTFont, family: str) -> None:
    """Give each baked face its own unambiguous legacy family identity.

    Bold/italic outlines remain intact. Selection happens explicitly in XHTML,
    avoiding four-style-family matching and cross-book subset-name collisions.
    Copyright and license name records are retained.
    """
    ids = {1, 2, 3, 4, 6, 16, 17, 21, 22}
    font["name"].names = [record for record in font["name"].names if record.nameID not in ids]
    for name_id, value in ((1, family), (2, "Regular"), (3, family), (4, family),
                           (6, family + "-Regular"), (16, family), (17, "Regular")):
        for platform, encoding, language in ((3, 1, 0x409), (1, 0, 0)):
            font["name"].setName(value, name_id, platform, encoding, language)
    font["OS/2"].usWeightClass = 400
    font["OS/2"].fsSelection = (font["OS/2"].fsSelection & ~(1 | 32 | 64 | 512)) | 64
    font["head"].macStyle &= ~3


class FontCatalog:
    def __init__(self, css: str, assets: list, cache: Path):
        self.faces: list[Face] = []
        self.rules = []
        self.cache = cache
        self.glyph_assets: dict[Path, str] = {}
        self.missing: set[str] = set()
        self._choice_cache = {}
        self._fallback_cache = {}
        self._image_cache = {}
        cache.mkdir(parents=True, exist_ok=True)
        by_name = {Path(asset.href).name: asset for asset in assets}
        self.assets = []
        out = []
        for selector, body in css_rules(css):
            if selector != "@font-face":
                props = declarations(body, {"font-family", "font-weight", "font-style", "color", "opacity"})
                for simple in selector.split(","):
                    simple = simple.strip()
                    tokens = re.findall(r">|[^\s>]+", simple)
                    if tokens and props and all(token == ">" or re.fullmatch(r"(?:\*|[\w-]+)?(?:\.[\w-]+)*", token) for token in tokens):
                        parsed = []
                        specificity = 0
                        for token in tokens:
                            if token == ">":
                                parsed.append(">")
                            else:
                                tag, *names = token.split(".")
                                parsed.append((tag, frozenset(names)))
                                specificity += len(names) * 10 + bool(tag and tag != "*")
                        self.rules.append((parsed, specificity, props))
                out.append(f"{selector} {{{re.sub(r'opacity\s*:[^;]+;?', '', body)}}}")
                continue
            family = re.search(r'font-family:\s*[\'"]([^\'"]+)', body)[1]
            weight_match = re.search(r"font-weight:\s*(\d+)", body)
            weight = int(weight_match[1]) if weight_match else 400
            italic = bool(re.search(r"font-style:\s*(?:italic|oblique)", body))
            file_name = Path(re.search(r'url\([\'"]?([^\)\'\"]+)', body)[1]).name
            source_asset = by_name[file_name]
            digest = hashlib.sha256(source_asset.source_path.read_bytes() + f"legacy-face-v2:{family}:{weight}:{italic}".encode()).hexdigest()[:20]
            alias = "Legacy" + digest
            target = cache / f"{alias}.ttf"
            with TTFont(source_asset.source_path) as font:
                points = set(font.getBestCmap() or {})
                if not target.exists():
                    rename_regular_face(font, alias)
                    font.save(target)
            self.faces.append(Face(family, weight, italic, alias, target, points))
            self.assets.append(replace(source_asset, source_path=target, href=f"Fonts/{target.name}"))
            out.append(f'@font-face {{ font-family: "{alias}"; src: url("../Fonts/{target.name}") format("truetype"); font-weight: normal; font-style: normal; }}')
        self.css = "\n".join(out)
        self._source_faces = list(self.faces)
        self._source_aliases = {face.alias for face in self.faces}
        # CSS still provides sensible defaults for navigation and readers that
        # honor the stylesheet. Chapter text also gets direct face selection.
        for family in sorted({face.family for face in self.faces}, key=len, reverse=True):
            alias = self.choose(family, 400, False).alias
            self.css = re.sub(r"([\"'])" + re.escape(family) + r"\1", lambda _: f'"{alias}"', self.css)
            self.css = re.sub(r"(font-family:\s*)" + re.escape(family) + r"(?=\s*[,;])",
                              lambda match: match[1] + f'"{alias}"', self.css)

    def choose(self, family: str, weight: int, italic: bool) -> Face:
        key = family, weight, italic
        if key not in self._choice_cache:
            candidates = [face for face in self._source_faces if face.family == family]
            if not candidates:
                candidates = [face for face in self.faces if face.family == "Libron"] or self.faces
            wanted = min(900, weight + 100) if family == "Nanum Barun Gothic" else weight
            if family == "IBM Plex Sans":
                wanted = {200: 300, 300: 500}.get(weight, weight)
            if family == "Nanum Barun Gothic":
                lower = [face for face in candidates if face.weight <= wanted]
                best = min(lower or candidates, key=lambda face: (abs(face.weight - wanted), face.italic != italic))
                if best.weight < wanted:
                    best = self.heavier_face(best, wanted)
            else:
                best = min(candidates, key=lambda face: (abs(face.weight - wanted), face.italic != italic))
            if italic and not best.italic:
                best = self.italic_face(best)
            self._choice_cache[key] = best
        return self._choice_cache[key]


    def heavier_face(self, source: Face, weight: int) -> Face:
        alias = "Legacy" + hashlib.sha256(f"{source.alias}:weight-v1:{weight}".encode()).hexdigest()[:20]
        existing = next((face for face in self.faces if face.alias == alias), None)
        if existing:
            return existing
        path = self.cache / f"{alias}.ttf"
        if not path.exists():
            with TTFont(source.path) as font:
                embolden_outlines(font, (weight - source.weight) / 100)
                rename_regular_face(font, alias)
                font.save(path)
        face = Face(source.family, weight, source.italic, alias, path, source.codepoints)
        self.faces.append(face)
        self.assets.append(replace(self.assets[0], source_path=path, href=f"Fonts/{path.name}"))
        self.css += f'\n@font-face {{ font-family: "{alias}"; src: url("../Fonts/{path.name}") format("truetype"); font-weight: normal; font-style: normal; }}'
        return face

    def italic_face(self, source: Face) -> Face:
        """Bake browser-style oblique geometry when no true italic is supplied.

        Selecting another family or relying on the old reader's font-style
        synthesis loses the intended display face. Decompose before shearing
        so nested TrueType components are transformed exactly once.
        """
        from fontTools.fontBuilder import FontBuilder
        from fontTools.pens.recordingPen import DecomposingRecordingPen
        from fontTools.pens.transformPen import TransformPen
        from fontTools.pens.ttGlyphPen import TTGlyphPen

        alias = "Legacy" + hashlib.sha256((source.alias + ":oblique-v1").encode()).hexdigest()[:20]
        existing = next((face for face in self.faces if face.alias == alias), None)
        if existing is not None:
            return existing
        path = self.cache / f"{alias}.ttf"
        if not path.exists():
            with TTFont(source.path) as font:
                glyph_set = font.getGlyphSet()
                glyphs = {}
                for name in font.getGlyphOrder():
                    recording = DecomposingRecordingPen(glyph_set)
                    glyph_set[name].draw(recording)
                    pen = TTGlyphPen(None)
                    recording.replay(TransformPen(pen, (1, 0, 0.2, 1, 0, 0)))
                    glyphs[name] = pen.glyph()
                builder = FontBuilder(font=font)
                builder.setupGlyf(glyphs)
                builder.setupMaxp()
                for name, glyph in glyphs.items():
                    if glyph.numberOfContours:
                        advance, _ = font["hmtx"].metrics[name]
                        font["hmtx"].metrics[name] = advance, glyph.xMin
                for table in ("fpgm", "prep", "cvt ", "VDMX", "hdmx", "LTSH"):
                    if table in font:
                        del font[table]
                font["post"].italicAngle = -math.degrees(math.atan(0.2))
                rename_regular_face(font, alias)
                font.save(path)
        face = Face(source.family, source.weight, True, alias, path, source.codepoints)
        self.faces.append(face)
        self.assets.append(replace(next(asset for asset in self.assets if asset.source_path == source.path), source_path=path, href=f"Fonts/{path.name}"))
        self.css += f'\n@font-face {{ font-family: "{alias}"; src: url("../Fonts/{path.name}") format("truetype"); font-weight: normal; font-style: normal; }}'
        return face

    def fallback(self, char: str, preferred: Face) -> Face | None:
        if ord(char) in preferred.codepoints:
            return preferred
        key = char, preferred.family, preferred.weight, preferred.italic
        if key not in self._fallback_cache:
            priorities = {"Nanum Barun Gothic": 0, "GSGW Legacy CJK": 1, "Noto Sans": 2,
                          "GSGW Legacy Math": 3, "GSGW Legacy Symbols": 4, "Noto Emoji": 5}
            candidates = [face for face in self.faces if ord(char) in face.codepoints]
            donor = min(candidates, key=lambda face: (face.family != preferred.family, priorities.get(face.family, 10), abs(face.weight - preferred.weight), face.italic != preferred.italic)) if candidates else None
            if donor and donor.family == "Nanum Barun Gothic" and donor.alias in self._source_aliases:
                target_weight = min(900, donor.weight + 100)
                adjusted = self.choose(donor.family, donor.weight, preferred.italic)
                donor = adjusted if ord(char) in adjusted.codepoints else self.heavier_face(donor, target_weight)
            if donor and preferred.italic and not donor.italic:
                donor = self.italic_face(donor)
            self._fallback_cache[key] = donor
        return self._fallback_cache[key]

    def glyph_image(self, text: str, face: Face, cache: Path, background: tuple, foreground: tuple) -> ET.Element:
        """Rasterize supplementary-plane runs without changing their shapes.

        Old RMSDK builds can reject supplementary Unicode despite valid cmap
        coverage. The original text remains in alt/title for accessibility.
        BMP symbols stay selectable text in an explicitly chosen embedded font.
        """
        from PIL import Image, ImageDraw, ImageFont

        key = text, face.alias, background, foreground
        if key not in self._image_cache:
            font = ImageFont.truetype(str(face.path), 72)
            left, top, right, bottom = font.getbbox(text, anchor="ls")
            width = max(1, math.ceil(max(right, font.getlength(text)) - min(0, left)) + 4)
            height = max(1, bottom - top + 4)
            image = Image.new("RGB", (width, height), background)
            ImageDraw.Draw(image).text((2 - min(0, left), 2 - top), text, font=font, fill=foreground, anchor="ls")
            # Logical em dimensions below stay the same. Limit the stored
            # high-resolution bitmap as well, including long styled words.
            image.thumbnail((600, 700), Image.Resampling.LANCZOS)
            digest = hashlib.sha256(f"glyph-v4:{text}:{face.alias}:{background}:{foreground}".encode()).hexdigest()[:20]
            path = cache / f"glyph-{digest}.png"
            cache.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                image.save(path, "PNG", optimize=True)
            self.glyph_assets[path] = f"Images/{path.name}"
            self._image_cache[key] = (path, width, height, bottom)
        path, width, height, bottom = self._image_cache[key]
        return ET.Element("img", {"class": "legacy-glyph", "src": "../" + self.glyph_assets[path],
            "alt": text, "title": text, "width": str(max(1, round(width / 4))), "height": str(max(1, round(height / 4))),
            "style": f"display: inline !important; margin: 0 !important; padding: 0 !important; width: {width / 72:.4f}em; height: {height / 72:.4f}em; vertical-align: {-bottom / 72:.4f}em;"})

    def apply(self, body: str, cache: Path) -> str:
        root = ET.fromstring("<div>" + body + "</div>")

        def matches(tokens, chain):
            def match_atom(atom, element):
                tag, names = atom
                return (not tag or tag == "*" or tag == element.tag) and names <= classes(element)
            def search(token_index, node_index):
                if node_index < 0 or not match_atom(tokens[token_index], chain[node_index]):
                    return False
                if token_index == 0:
                    return True
                if tokens[token_index - 1] == ">":
                    return token_index >= 2 and search(token_index - 2, node_index - 1)
                return any(search(token_index - 1, parent) for parent in range(node_index - 1, -1, -1))
            return search(len(tokens) - 1, len(chain) - 1)

        def font_style(node, family, weight, italic, ancestors):
            props = {}
            priorities = {}
            for order, (selector, specificity, rule) in enumerate(self.rules):
                if matches(selector, [*ancestors, node]):
                    for name, value in rule.items():
                        priority = ("!important" in value, specificity, order)
                        if priority >= priorities.get(name, (-1, -1, -1)):
                            props[name] = value
                            priorities[name] = priority
            for name, value in declarations(node.get("style", ""), {"font-family", "font-weight", "font-style", "color", "opacity"}).items():
                if ("!important" in value, 1000, 0) >= priorities.get(name, (-1, -1, -1)):
                    props[name] = value
            if "font-family" in props and props["font-family"] != "inherit":
                family = props["font-family"].split(",")[0].strip(" '\"")
            if node.tag in {"b", "strong"}:
                weight = 700
            if node.tag in {"i", "em"}:
                italic = True
            if "font-weight" in props:
                value = props["font-weight"].split()[0]
                if value.isdigit():
                    weight = int(value)
                elif value in {"normal", "bold"}:
                    weight = 700 if value == "bold" else 400
            if "font-style" in props and props["font-style"].split()[0] in {"normal", "italic", "oblique"}:
                italic = props["font-style"].split()[0] != "normal"
            return family, weight, italic, props

        def parts(value, face, background, foreground):
            result = []
            run = ""
            last_key = None
            donor = face
            for char in value or "":
                # Layout whitespace and format controls need no visible glyph.
                # Wrapping linefeeds in a fallback span can introduce anonymous
                # inline boxes between block paragraphs on old engines.
                candidate = face if char in " \t\r\n\u00a0\ufe0e\ufe0f" or unicodedata.category(char) == "Cf" else self.fallback(char, face)
                if candidate is None:
                    if not char.isspace() and unicodedata.category(char)[0] != "C" and char not in "\ufe0e\ufe0f":
                        self.missing.add(char)
                    candidate = face
                key = candidate.alias, ord(char) > 0xFFFF
                if run and key != last_key:
                    result.append((run, donor, last_key[1]))
                    run = ""
                run += char
                donor, last_key = candidate, key
            if run:
                result.append((run, donor, last_key[1]))
            for text, donor, raster in result:
                if raster and all(ord(c) in donor.codepoints for c in text):
                    yield self.glyph_image(text, donor, cache, background, foreground)
                elif donor.alias != face.alias:
                    span = ET.Element("span", {"class": "legacy-unicode", "style": f'font-family: "{donor.alias}" !important; font-weight: normal !important; font-style: normal !important; color: {color_hex(foreground)} !important;'})
                    span.text = text
                    yield span
                else:
                    yield text

        def visit(node, family="Libron", weight=400, italic=False, background=(255, 255, 255), foreground=(0, 0, 0), opacity=1.0, fade=None, force_white=False, ancestors=()):
            family, weight, italic, own_props = font_style(node, family, weight, italic, ancestors)
            face = self.choose(family, weight, italic)
            for name in classes(node) & BOX_WINDOWS.keys():
                box_props = BOX_WINDOWS[name]
                background = ink_color(box_props["background-color"], background)
                force_white = name in {"black-window", "braun-screen"}
            # Resolve the actual cascade instead of forcing every run black.
            foreground = ink_color(own_props.get("color", "inherit"), background) or foreground
            if "opacity" in own_props:
                opacity *= float(own_props["opacity"].replace("!important", "").strip())
            if force_white:
                foreground, opacity, fade = (255, 255, 255), 1.0, None
            cls = classes(node)
            if not force_white and cls & {"text-fade-left", "text-fade-right"}:
                fade = {"position": 0, "total": max(1, len("".join(node.itertext())) - 1), "left": "text-fade-left" in cls}
            original_ink = tuple(round(foreground[i] * opacity + background[i] * (1 - opacity)) for i in range(3))
            rendered = original_ink if fade is not None else eink_ink(original_ink, background)
            node.set("style", re.sub(r"opacity\s*:[^;]+;?", "", node.get("style", "")))
            set_style(node, color=color_hex(rendered) + " !important")
            native_mono = family in {"monospace", "ui-monospace", "Courier New", "Courier", "SFMono-Regular", "Menlo", "Consolas"}
            set_style(node, font_family="monospace !important" if native_mono else f'"{face.alias}" !important',
                      font_weight=("bold" if weight >= 600 and (native_mono or face.weight < 600) else "normal") + " !important",
                      font_style=("italic" if italic and native_mono else "normal") + " !important")
            children = list(node)
            old_text = node.text
            node.text = None
            for child in children:
                node.remove(child)
            def append(value):
                if fade is not None:
                    for char in value or "":
                        progress = min(1, fade["position"] / fade["total"])
                        fade["position"] += 1
                        alpha = progress if fade["left"] else 1 - progress
                        color = tuple(round(original_ink[i] * alpha + background[i] * (1 - alpha)) for i in range(3))
                        for part in parts(char, face, background, color):
                            if isinstance(part, str):
                                span = ET.SubElement(node, "span", {"class": "legacy-fade-char", "style": f"color: {color_hex(color)} !important;"})
                                span.text = part
                            else:
                                node.append(part)
                    return
                for part in parts(value, face, background, rendered):
                    if isinstance(part, str):
                        if len(node):
                            node[-1].tail = (node[-1].tail or "") + part
                        else:
                            node.text = (node.text or "") + part
                    else:
                        node.append(part)
            append(old_text)
            for child in children:
                tail = child.tail
                child.tail = None
                visit(child, family, weight, italic, background, foreground, opacity, fade, force_white, (*ancestors, node))
                node.append(child)
                append(tail)

        for child in list(root):
            # Tail text on top-level blocks is normally whitespace. Keep it.
            visit(child)
        return (root.text or "") + "".join(ET.tostring(child, encoding="unicode") for child in root)
