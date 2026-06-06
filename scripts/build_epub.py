import os
import re
import json
import subprocess
import urllib.request
import frontmatter
import datetime
from io import BytesIO
from pathlib import Path
from PIL import Image

SCRIPT_DIR = Path(__file__).parent.resolve()
REPO_ROOT = SCRIPT_DIR.parent

CSS_PATH = SCRIPT_DIR / "epub.css"
IMG_ROOT = REPO_ROOT / "images"

OUTPUT_DIR = SCRIPT_DIR / "epub"
OUTPUT_DIR.mkdir(exist_ok=True)

TWITTER_IMG_DIR = OUTPUT_DIR / "twitter_images"
TWITTER_IMG_DIR.mkdir(exist_ok=True)

today = datetime.date.today().strftime("%B %d, %Y")
CHAPTERS_DIR = REPO_ROOT / "chapters" / "gsgw"

TWITTER_RE = re.compile(
    r"https?://(?:x|twitter)\.com/([A-Za-z0-9_]+)/status/(\d+)(?:/photo/(\d+))?(?:\?[^\s<>\"'\)]*)?"
)

UA = "GSGW-Reader/1.0"


TWEET_CACHE_PATH = TWITTER_IMG_DIR / "cache.json"


def _load_tweet_cache() -> dict:
    if TWEET_CACHE_PATH.exists():
        try:
            with open(str(TWEET_CACHE_PATH), "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_tweet_cache(cache: dict) -> None:
    with open(str(TWEET_CACHE_PATH), "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False)


def resolve_twitter_images(text: str) -> str:
    tweet_cache = _load_tweet_cache()

    def _replace(m):
        user = m.group(1)
        tweet_id = m.group(2)
        photo_index = int(m.group(3) or 1)

        cache_key = f"{tweet_id}_{photo_index}"
        img_webp = TWITTER_IMG_DIR / f"{cache_key}.webp"
        img_jpg = TWITTER_IMG_DIR / f"{cache_key}.jpg"

        if img_webp.exists():
            cached = tweet_cache.get(tweet_id, {})
            author_screen = cached.get("author_screen", user)
            return f"![Illustration by @{author_screen} on X](twitter_images/{cache_key}.webp)"

        api_url = f"https://api.fxtwitter.com/{user}/status/{tweet_id}"
        try:
            req = urllib.request.Request(api_url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            tweet = data.get("tweet") or {}
            author = tweet.get("author", {})
            author_screen = author.get("screen_name", user)

            tweet_cache[tweet_id] = {"author_screen": author_screen}

            photos = tweet.get("media", {}).get("photos", [])
            idx = photo_index - 1
            if 0 <= idx < len(photos):
                photo_url = photos[idx].get("url", "")
                if photo_url:
                    req_img = urllib.request.Request(
                        photo_url, headers={"User-Agent": UA}
                    )
                    with urllib.request.urlopen(req_img, timeout=30) as img_resp:
                        img_data = img_resp.read()
                    img = Image.open(BytesIO(img_data))

                    img.save(str(img_webp), "WEBP", quality=85)

                    jpg_img = img.convert("RGB")
                    jpg_img.save(str(img_jpg), "JPEG", quality=85)

                    print(f"      Downloaded tweet image: {cache_key}")
                    _save_tweet_cache(tweet_cache)
                    return f"![Illustration by @{author_screen} on X](twitter_images/{cache_key}.webp)"
        except Exception as e:
            print(f"      Warning: failed to fetch tweet {tweet_id}: {e}")

        return m.group(0)

    return TWITTER_RE.sub(_replace, text)


def apply_inline_formatting(s: str) -> str:
    placeholders = {}
    def _protect(m):
        key = f"\x00IMG{len(placeholders)}\x00"
        placeholders[key] = m.group(0)
        return key

    s = re.sub(r'!\[.*?\]\(.*?\)', _protect, s)

    s = re.sub(r"#\*(.*?)\*#", r'<span class="text-large">\1</span>', s, flags=re.DOTALL)

    s = re.sub(r"(?<!\*)\*\*\*(.+?)\*\*\*(?!\*)", r"<em><strong>\1</strong></em>", s)
    s = re.sub(r"(?<!\*)\*\*(.+?)\*\*(?!\*)", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<!\*)\*(.+?)\*(?!\*)", r"<em>\1</em>", s)

    s = re.sub(r"^~~~\s*$", '<hr class="visible-hr">', s, flags=re.MULTILINE)

    s = re.sub(r"%%(.*?)%%", r"\1", s, flags=re.DOTALL)
    s = re.sub(r"%~(.*?)~%", r"\1", s, flags=re.DOTALL)
    s = re.sub(r"%\^(.*?)\^%", r"\1", s, flags=re.DOTALL)

    s = re.sub(r"@@(.+?)@@", r'<span class="distorted">\1</span>', s, flags=re.DOTALL)
    s = re.sub(r"@_@(.+?)@_@", r'<span class="distorted">\1</span>', s, flags=re.DOTALL)

    s = re.sub(r"(?<!\\)_(.+?)(?<!\\)_", r"[\1]{.underline}", s)
    s = re.sub(r"(?<!\\)~(.+?)(?<!\\)~", r"~~\1~~", s)

    s = re.sub(r"@ll@(.*?)@ll@", r'<span class="mono mono-left">\1</span>', s, flags=re.DOTALL)
    s = re.sub(r"@rr@(.*?)@rr@", r'<span class="mono mono-right">\1</span>', s, flags=re.DOTALL)

    s = re.sub(r"@l@(.*?)@l@", r'<span class="align-left">\1</span>', s, flags=re.DOTALL)
    s = re.sub(r"@r@(.*?)@r@", r'<span class="align-right">\1</span>', s, flags=re.DOTALL)

    s = re.sub(r"#r(.*?)r#", r'<span class="text-red">\1</span>', s, flags=re.DOTALL)
    s = re.sub(r"#b(.*?)b#", r'<span class="text-blue">\1</span>', s, flags=re.DOTALL)
    s = re.sub(r"#y(.*?)y#", r'<span class="text-yellow">\1</span>', s, flags=re.DOTALL)
    s = re.sub(r"#p(.*?)p#", r'<span class="text-magenta">\1</span>', s, flags=re.DOTALL)
    s = re.sub(r"#g(.*?)g#", r'<span class="text-green">\1</span>', s, flags=re.DOTALL)
    s = re.sub(r"#o(.*?)o#", r'<span class="text-orange">\1</span>', s, flags=re.DOTALL)

    s = re.sub(r"#f#(.*?)#f#", r"\1", s, flags=re.DOTALL)
    s = re.sub(r"#f>#(.*?)#f>#", r"\1", s, flags=re.DOTALL)
    s = re.sub(r"#f<#(.*?)#f<#", r"\1", s, flags=re.DOTALL)

    s = re.sub(r"#\^#(.*?)#\^#", r'<span class="text-grow">\1</span>', s, flags=re.DOTALL)
    s = re.sub(r"#v#(.*?)#v#", r'<span class="text-grow">\1</span>', s, flags=re.DOTALL)

    s = re.sub(r"#><(.*?)><#", r'\n\n\n\n<div style="text-align:center;font-size:1.2em">\1</div>\n\n\n\n', s, flags=re.DOTALL)

    s = re.sub(r";r(.*?)r;", r'<span class="hl-red">\1</span>', s, flags=re.DOTALL)
    s = re.sub(r";b(.*?)b;", r'<span class="hl-blue">\1</span>', s, flags=re.DOTALL)
    s = re.sub(r";y(.*?)y;", r'<span class="hl-yellow">\1</span>', s, flags=re.DOTALL)
    s = re.sub(r";p(.*?)p;", r'<span class="hl-magenta">\1</span>', s, flags=re.DOTALL)
    s = re.sub(r";g(.*?)g;", r'<span class="hl-green">\1</span>', s, flags=re.DOTALL)
    s = re.sub(r";o(.*?)o;", r'<span class="hl-orange">\1</span>', s, flags=re.DOTALL)

    for key, val in placeholders.items():
        s = s.replace(key, val)

    return s


def convert_windows(s: str) -> str:
    def regular_window(m):
        inner = m.group(1).strip()
        lines = inner.split("\n")
        first = lines[0].lstrip("\\") if lines else ""
        rest = "\n".join(lines[1:]).strip()

        parts = []
        parts.append('<div class="wiki-window">')
        parts.append("")
        parts.append("---")
        parts.append("")
        parts.append('<div style="text-align:right">')
        parts.append("")
        parts.append(first)
        parts.append("")
        parts.append("</div>")
        parts.append("")
        if rest:
            parts.append(rest)
            parts.append("")
        parts.append("---")
        parts.append("")
        parts.append("</div>")
        return "\n".join(parts)

    def follow_up_window(m):
        inner = m.group(1).strip()
        return f"\n\n\n\n{inner}\n\n\n\n"

    def sticky_window(m):
        inner = m.group(1).strip()
        return f'<div class="sticky-window">\n\n{inner}\n\n</div>'

    def black_window(m):
        inner = m.group(1).strip()
        return f'<div class="black-window">\n\n{inner}\n\n</div>'

    def system_window(m):
        inner = m.group(1).strip()
        return f'<div class="system-window">\n\n{inner}\n\n</div>'

    s = re.sub(r'\+[-+]+\n(.*?)\n[-+]+\+', regular_window, s, flags=re.DOTALL)
    s = re.sub(r'\+[=]+\n(.*?)\n[=]+\+', black_window, s, flags=re.DOTALL)
    s = re.sub(r'\+[~]+\n(.*?)\n[~]+\+', system_window, s, flags=re.DOTALL)
    s = re.sub(r'\+\$\n(.*?)\n\$\+', follow_up_window, s, flags=re.DOTALL)
    s = re.sub(r'&[-]+\n(.*?)\n[-]+&', regular_window, s, flags=re.DOTALL)
    s = re.sub(r'&\$\n(.*?)\n\$&', follow_up_window, s, flags=re.DOTALL)
    s = re.sub(r'![-]+\n(.*?)\n[-]+!', lambda m: f'<div class="note-window">\n\n{m.group(1).strip()}\n\n</div>', s, flags=re.DOTALL)
    s = re.sub(r'!\$\n(.*?)\n\$!', sticky_window, s, flags=re.DOTALL)
    s = re.sub(r'!\[\n(.*?)\n\]!', lambda m: f'\n\n<div class="braun-dialogue">\n\n[{m.group(1).strip()}]\n\n</div>\n\n', s, flags=re.DOTALL)
    return s


translations = sorted([d.name for d in CHAPTERS_DIR.iterdir() if d.is_dir()])

print(f"Found {len(translations)} translation(s): {translations}\n")

for tl_name in translations:
    tl_path = CHAPTERS_DIR / tl_name

    master_path = tl_path / "metadata.md"
    if not master_path.exists():
        print(f"Skipping {tl_name}: no metadata.md found")
        continue

    print(f"{'='*100}\n\nProcessing translation: {tl_name}")

    master_md = frontmatter.load(str(master_path))
    master_md.content = master_md.content.replace("{{DATE}}", today)

    files = sorted([
        f for f in os.listdir(str(tl_path))
        if f.endswith(".md") and f != "metadata.md"
    ])

    if not files:
        print(f"  Skipping {tl_name}: no chapter files found\n")
        continue

    print(f"  Found {len(files)} file(s)")

    chapter_list = []
    errors = 0
    for fname in files:
        try:
            post = frontmatter.load(str(tl_path / fname))
            meta = post.metadata
            chapter_list.append({
                "meta": meta,
                "content": post.content,
                "file": fname,
            })
        except Exception as e:
            errors += 1
            print(f"    Warning: could not parse {fname}: {e}")

    total_ch = len(chapter_list)
    print(f"  Parsed {total_ch} chapter(s)" +
          (f", {errors} error(s)" if errors else ""))

    chapter_list.sort(key=lambda x: int(x["meta"].get("index", x["meta"].get("slug", 0))))

    all_content = ""
    for i, ch in enumerate(chapter_list):
        ch_text = ch["content"].strip()
        ch_text = resolve_twitter_images(ch_text)
        ch_text = apply_inline_formatting(ch_text)
        ch_text = convert_windows(ch_text)
        print(f"    [{i+1}/{total_ch}] {ch['meta'].get('title', ch['file'])}")
        all_content += f"{ch_text}\n\n---\n\n"

    title_data = master_md.metadata.get("title", [])
    if isinstance(title_data, list) and title_data:
        book_title = title_data[0].get("text", f"GSGW - {tl_name}")
    else:
        book_title = str(title_data) if title_data else f"GSGW - {tl_name}"

    book_id = master_md.metadata.get("metaBook", "gsgw")
    book_tl = master_md.metadata.get("metaTl", tl_name)

    master_md.content += all_content

    build_type = "Default"
    img_format = ".webp"
    epub_version = "epub3"

    print(f"\n  Producing EPUB: {book_title}")

    content = master_md.content
    content = content.replace("{{TYPE}}", build_type)
    content = content.replace("../../../images", "../../images")
    content = re.sub(r"\.(jpe?g|png|webp)", img_format, content)

    epub_name = f"{book_title} - {book_tl} [{build_type}].epub"
    md_name = f"{book_id}_{book_tl}_{build_type}.md"

    epub_path = OUTPUT_DIR / epub_name
    md_path = OUTPUT_DIR / md_name

    temp_post = frontmatter.Post(content, **master_md.metadata)
    with open(str(md_path), "w", encoding="utf-8") as f:
        f.write(frontmatter.dumps(temp_post))

    print(f"    Converting ({epub_version})...")

    cover_path = IMG_ROOT / book_id / f"cover{img_format}"

    cmd = [
        "pandoc",
        str(md_path),
        "-o", str(epub_path),
        f"--to={epub_version}",
        "--from=markdown-fenced_code_blocks",
        "--css", str(CSS_PATH),
        "--resource-path", str(OUTPUT_DIR),
        "--resource-path", str(IMG_ROOT / "gsgw" / "illustrations"),
        "--resource-path", str(IMG_ROOT / "gsgw"),
        "--toc",
        "--toc-depth=3",
        "--split-level=1",
        "--epub-title-page=false",
    ]

    if cover_path.exists():
        cmd.append(f"--epub-cover-image={str(cover_path)}")
    else:
        print(f"    Warning: cover image not found at {cover_path}")

    try:
        subprocess.run(cmd, check=True)
        print(f"    Done! -> {epub_path}")
    except subprocess.CalledProcessError as e:
        print(f"    Pandoc failed: {e}")

    print()
