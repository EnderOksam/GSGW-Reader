import zipfile
import re
import os
import json
from pathlib import Path
from xml.etree import ElementTree as ET

SCRIPT_DIR = Path(__file__).parent.resolve()
REPO_ROOT = SCRIPT_DIR.parent

EPUB_PATH = SCRIPT_DIR / "epub" / "Got Dropped into a Ghost Story, Still Gotta Work - Part 1.epub"
CHAPTERS_DIR = REPO_ROOT / "chapters" / "gsgw" / "fantl"
IMAGES_DIR = REPO_ROOT / "images" / "gsgw" / "extracted-illustrations"

SKIP_FILES = {"0000_Information.xhtml", "titlepage.xhtml"}
HEAD_NS = "http://www.w3.org/1999/xhtml"


def h(text):
    key = text.lower().replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    if key in HTML_ESCAPE_MAP:
        return HTML_ESCAPE_MAP[key]
    return text

def unescape(text):
    text = text.replace("&amp;", "&")
    text = text.replace("&lt;", "<")
    text = text.replace("&gt;", ">")
    text = text.replace("&quot;", '"')
    text = text.replace("&#39;", "'")
    text = text.replace("&#34;", '"')
    text = text.replace("&nbsp;", " ")
    text = text.replace("\u00a0", " ")
    return text


def extract_inner(element, img_seq, epub_zip):
    parts = []
    if element.text:
        parts.append(unescape(element.text))
    for child in element:
        parts.append(convert_inline(child, img_seq, epub_zip))
        if child.tail:
            parts.append(unescape(child.tail))
    return "".join(parts)


def convert_inline(element, img_seq, epub_zip):
    tag = element.tag
    if isinstance(tag, str) and tag.startswith("{"):
        tag = tag.split("}")[1]

    if tag == "br":
        return "\n"
    if tag == "strong" or tag == "b":
        inner = extract_inner(element, img_seq, epub_zip)
        return f"**{inner}**"
    if tag == "em" or tag == "i":
        inner = extract_inner(element, img_seq, epub_zip)
        return f"*{inner}*"
    if tag == "span":
        inner = extract_inner(element, img_seq, epub_zip)
        style = (element.get("style") or "").replace(" ", "")
        if "color:#ff4d00" in style or "color:#ff0000" in style:
            return f"#r{inner}r#"
        if "font-size" in style or "display:inline" in style:
            pass
        return inner
    if tag == "a":
        return extract_inner(element, img_seq, epub_zip)
    if tag == "img":
        src = element.get("src", "")
        alt = element.get("alt", "")
        if src:
            img_seq[0] += 1
            seq = img_seq[0]
            data = resolve_image(src, epub_zip)
            if data:
                ch_num = img_seq[1]
                ext = Path(src).suffix or ".png"
                fname = f"ch{ch_num}_{seq}{ext}"
                path = IMAGES_DIR / fname
                with open(path, "wb") as f:
                    f.write(data)
                return f"![{alt}]({fname})"
        return ""
    if tag == "sub":
        return f"<sub>{extract_inner(element, img_seq, epub_zip)}</sub>"
    if tag == "sup":
        return f"<sup>{extract_inner(element, img_seq, epub_zip)}</sup>"
    return extract_inner(element, img_seq, epub_zip)


def resolve_image(src, epub_zip):
    name = Path(src).name
    candidates = [
        f"EPUB/imgs/{name}",
        f"EPUB/xhtml/epubgtmsq/OEBPS/Images/{name}",
    ]
    if src.startswith("../"):
        candidates.append(f"EPUB/xhtml/epubgtmsq/OEBPS/{src}")
    for c in candidates:
        c = c.replace("\\", "/")
        try:
            return epub_zip.read(c)
        except KeyError:
            continue
    return None


def collect_text(el):
    return unescape("".join(el.itertext()).strip())


def is_sep(el):
    if el.tag != f"{{{HEAD_NS}}}p":
        return False
    t = collect_text(el)
    return bool(re.match(r"^[=\-*]{4,}$", t))


def get_nstag(tag):
    if isinstance(tag, str) and tag.startswith("{"):
        return tag.split("}")[1]
    return tag


def extract_chapter_number(title_text):
    m = re.search(r"Chapter\s+(\d+)", title_text)
    return int(m.group(1)) if m else 0


def get_subtitle(title_text):
    m = re.search(r"Chapter\s+\d+\s*-\s*(.*)", title_text)
    result = m.group(1) if m else title_text
    return unescape(result.strip())


def build_h1(ch_num, subtitle):
    return f"# Chapter {ch_num} - {subtitle}"


def has_content(el):
    tag = get_nstag(el.tag)
    t = "".join(el.itertext()).strip().replace("\u00a0", "").replace("&nbsp;", "")
    return bool(t)

def process_body(body, epub_zip, img_seq, ch_num):
    img_seq[1] = ch_num
    lines = []
    children = list(body)
    i = 0
    while i < len(children):
        el = children[i]
        tag = get_nstag(el.tag)

        if tag == "h1":
            i += 1
            continue

        if tag == "p":
            text_content = collect_text(el)
            stripped = text_content.replace("\u00a0", "").strip()
            if not stripped:
                i += 1
                continue

            if stripped.replace(" ", "").replace("\u00a0", "") == "***":
                lines.append("")
                lines.append("* * *")
                lines.append("")
                i += 1
                continue

            if is_sep(el):
                kind = ""
                if re.match(r"^=+$", stripped):
                    kind = "eq"
                elif re.match(r"^-+$", stripped):
                    kind = "dash"
                else:
                    i += 1
                    continue

                if kind in ("eq", "dash"):
                    wiki_indices = []
                    j = i + 1
                    found_closing = False
                    while j < len(children):
                        nxt = children[j]
                        if get_nstag(nxt.tag) == "p" and is_sep(nxt):
                            nxt_text = collect_text(nxt).replace("\u00a0", "").strip()
                            if re.match(r"^=+$", nxt_text) or re.match(r"^-+$", nxt_text):
                                found_closing = True
                                break
                        if has_content(children[j]):
                            wiki_indices.append(j)
                        j += 1

                    if found_closing and wiki_indices:
                        lines.append("")
                        lines.append("+-")
                        for wi in wiki_indices:
                            wel = children[wi]
                            cnt = extract_inner(wel, img_seq, epub_zip)
                            if cnt.strip():
                                lines.append(cnt)
                        lines.append("-+")
                        lines.append("")
                        i = j + 1
                        continue
                    else:
                        i += 1
                        continue

            content = extract_inner(el, img_seq, epub_zip)
            if content.strip():
                lines.append(content)
                lines.append("")
            i += 1
            continue

        if tag == "img":
            src = el.get("src", "")
            alt = el.get("alt", "")
            if src:
                img_seq[0] += 1
                seq = img_seq[0]
                data = resolve_image(src, epub_zip)
                if data:
                    ext = Path(src).suffix or ".png"
                    fname = f"ch{ch_num}_{seq}{ext}"
                    path = IMAGES_DIR / fname
                    with open(path, "wb") as f:
                        f.write(data)
                    lines.append(f"![{alt}]({fname})")
                    lines.append("")
            i += 1
            continue

        if tag == "hr":
            lines.append("---")
            lines.append("")
            i += 1
            continue

        if tag == "blockquote":
            for child in el:
                if get_nstag(child.tag) == "p":
                    c = extract_inner(child, img_seq, epub_zip)
                    if c.strip():
                        lines.append(f"> {c}")
            lines.append("")
            i += 1
            continue

        if tag in ("ul", "ol"):
            for li in el:
                if get_nstag(li.tag) == "li":
                    c = extract_inner(li, img_seq, epub_zip)
                    if c.strip():
                        lines.append(f"- {c}")
            lines.append("")
            i += 1
            continue

        if tag == "div":
            for child in el:
                if get_nstag(child.tag) == "p":
                    c = extract_inner(child, img_seq, epub_zip)
                    if c.strip():
                        lines.append(c)
                        lines.append("")
            i += 1
            continue

        i += 1

    text = "\n".join(lines).strip()
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text


def main():
    os.makedirs(IMAGES_DIR, exist_ok=True)

    with zipfile.ZipFile(EPUB_PATH) as z:
        all_xhtml = sorted(
            n for n in z.namelist()
            if n.startswith("EPUB/xhtml/epubgtmsq/OEBPS/Text/") and n.endswith(".xhtml")
        )

        file_counter = 5
        for fpath in all_xhtml:
            fname = Path(fpath).name
            if fname in SKIP_FILES:
                print(f"  Skip {fname}")
                continue

            with z.open(fpath) as f:
                raw = f.read()
            try:
                html = raw.decode("utf-8")
            except:
                html = raw.decode("utf-8", errors="replace")

            m = re.search(r"<title>(.*?)</title>", html)
            if not m:
                print(f"  No title in {fname}, skip")
                continue
            title_text = m.group(1)

            ch_num = extract_chapter_number(title_text)
            if ch_num <= 3:
                print(f"  Skip {fname} (ch {ch_num} exists)")
                continue

            html = re.sub(r"<br\s*/?>", "<br/>", html)
            html = re.sub(r"(<br/>\s*)+", "<br/>", html)

            root = ET.fromstring(html)
            body = root.find(f".//{{{HEAD_NS}}}body")
            if body is None:
                body = root.find("body")
            if body is None:
                print(f"  No body in {fname}, skip")
                continue

            img_seq = [0, ch_num]
            md = process_body(body, z, img_seq, ch_num)

            subtitle = get_subtitle(title_text)
            h1_line = build_h1(ch_num, subtitle)
            md = f"{h1_line}\n\n{md}"

            yaml_title = json.dumps(subtitle, ensure_ascii=False)
            frontmatter = (
                "---\n"
                f"title: {yaml_title}\n"
                f'category: "Chapter {ch_num}"\n'
                f"discussion: {ch_num}\n"
                f"index: {ch_num}\n"
                f'section: "Chapter {ch_num}"\n'
                f'slug: "{ch_num}"\n'
                "---\n\n"
            )

            out = CHAPTERS_DIR / f"{file_counter:04d}.md"
            with open(out, "w", encoding="utf-8") as f:
                f.write(frontmatter)
                f.write(md)
                f.write("\n")

            print(f"  {out.name} <- {fname} (ch{ch_num})")
            file_counter += 1

    print(f"\nDone. Images -> {IMAGES_DIR}")


if __name__ == "__main__":
    main()
