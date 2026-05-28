import os
import re
import json
import subprocess
import imagesize
from pathlib import Path
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

TWITTER_URL_RE = re.compile(
    r'https?://(?:x|twitter)\.com/(\w+)/status/(\d+)(?:/photo/(\d+))?[^\s<>"\']*'
)

VISIBLE_HR_RE = re.compile(r"^~~~\s*$", re.MULTILINE)

STYLE_BLOCK_RE = re.compile(r'^[ \t]*\{style="([^"]*)"\}\s*$')

WIKI_WINDOW_RE = re.compile(r"\+[-+]+\n(.*?)\n[-+]+\+", re.DOTALL)
BLACK_WINDOW_RE = re.compile(r"\+[=]+\n(.*?)\n[=]+\+", re.DOTALL)
SYSTEM_WINDOW_RE = re.compile(r"\+[~]+\n(.*?)\n[~]+\+", re.DOTALL)
PLAIN_WINDOW_RE = re.compile(r"\+\$\n(.*?)\n\$\+", re.DOTALL)

RECORD_WINDOW_RE = re.compile(r"&[-]+\n(.*?)\n[-]+&", re.DOTALL)
FOLLOWUP_WINDOW_RE = re.compile(r"\+\$\n(.*?)\n-\$", re.DOTALL)
AMPERSAND_WINDOW_RE = re.compile(r"&\$\n(.*?)\n\$&", re.DOTALL)

NOTE_WINDOW_RE = re.compile(r"![-]+\n(.*?)\n[-]+!", re.DOTALL)
STICKY_WINDOW_RE = re.compile(r"!\$\n(.*?)\n\$!", re.DOTALL)
BRAUN_WINDOW_RE = re.compile(r"!\[\n(.*?)\n\]!", re.DOTALL)


SIMPLE_REPLACEMENTS = [
    (re.compile(r"(?<!\\)_(.*?)(?<!\\)_", re.DOTALL), r"[\1]{.underline}"),
    (re.compile(r"(?<!\\)(?<!~)~(?!~)(.*?)(?<!\\)~", re.DOTALL), r"~~\1~~"),

    (re.compile(r"@ll@(.*?)@ll@", re.DOTALL), r'<span class="mono mono-left">\1</span>'),
    (re.compile(r"@rr@(.*?)@rr@", re.DOTALL), r'<span class="mono mono-right">\1</span>'),

    (re.compile(r"@l@(.*?)@l@", re.DOTALL), r'<span class="align-left">\1</span>'),
    (re.compile(r"@r@(.*?)@r@", re.DOTALL), r'<span class="align-right">\1</span>'),

    (re.compile(r"#\*(.*?)\*#", re.DOTALL), r'<span class="text-large">\1</span>'),
    (re.compile(r"#><(.*?)><#", re.DOTALL), r'<span class="text-large-centered">\1</span>'),

    (re.compile(r"#r(.*?)r#", re.DOTALL), r'<span class="text-red">\1</span>'),
    (re.compile(r"#b(.*?)b#", re.DOTALL), r'<span class="text-blue">\1</span>'),
    (re.compile(r"#y(.*?)y#", re.DOTALL), r'<span class="text-yellow">\1</span>'),
    (re.compile(r"#p(.*?)p#", re.DOTALL), r'<span class="text-magenta">\1</span>'),
    (re.compile(r"#g(.*?)g#", re.DOTALL), r'<span class="text-green">\1</span>'),
    (re.compile(r"#o(.*?)o#", re.DOTALL), r'<span class="text-orange">\1</span>'),
    (re.compile(r"#f#(.*?)#f#", re.DOTALL), r'<span class="text-faded">\1</span>'),
    (re.compile(r"#f>#(.*?)#f>#", re.DOTALL), r'<span class="text-fade-right">\1</span>'),
    (re.compile(r"#f<#(.*?)#f<#", re.DOTALL), r'<span class="text-fade-left">\1</span>'),

    (re.compile(r";r(.*?)r;", re.DOTALL), r'<span class="hl-red">\1</span>'),
    (re.compile(r";b(.*?)b;", re.DOTALL), r'<span class="hl-blue">\1</span>'),
    (re.compile(r";y(.*?)y;", re.DOTALL), r'<span class="hl-yellow">\1</span>'),
    (re.compile(r";p(.*?)p;", re.DOTALL), r'<span class="hl-magenta">\1</span>'),
    (re.compile(r";g(.*?)g;", re.DOTALL), r'<span class="hl-green">\1</span>'),
    (re.compile(r";o(.*?)o;", re.DOTALL), r'<span class="hl-orange">\1</span>'),
]


# =========================================================
# IMAGE PROCESSING
# =========================================================

IMG_STORAGE_DIR = REPO_ROOT / "website/static/assets/images/static-illustrations"
IMG_PUBLIC_PREFIX = "/assets/images/static-illustrations"

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

    text = re.sub(r'(?<!\\)\[', r'\\[', text)
    text = re.sub(r'(?<!\\)\]', r'\\]', text)

    text = re.sub(r'(?<!\\)\(', r'\\(', text)
    text = re.sub(r'(?<!\\)\)', r'\\)', text)

    text = re.sub(r'(?<!\\)_', r'\\_', text)

    text = re.sub(r'(?m)^(?<!\\):(?=\s)', r'\\:', text)
    text = re.sub(r'(?m)^(?<!\\)#(?=\s)', r'\\#', text)
    text = re.sub(r'(?m)^(?<!\\)>(?=\s)', r'\\>', text)

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

    inner = escape_markdown_except_bold(inner)

    cls = class_name

    if extra_class:
        cls += f" .{extra_class}"

    return f'\n::: {{.{cls}}}\n{inner}\n:::\n'


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

# =========================================================
# MAIN CONVERTER
# =========================================================

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

    content = SHAKE_RE.sub(r'<span class="shake">\1</span>', content)

    content = SHAKE_CHAR_RE.sub(shake_char_replacer, content)

    content = WAVE_RE.sub(wave_char_replacer, content)

    content = VISIBLE_HR_RE.sub('<hr class="visible-hr">', content)

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
            return f"<p>Error converting content: {err}</p>"
        return process_html_images(proc.stdout.decode("utf-8"))
    except subprocess.TimeoutExpired:
        print("Pandoc timed out on a chapter — skipping")
        return "<p>Chapter skipped due to conversion timeout.</p>"


# =========================================================
# BUILD TASK
# =========================================================

def process_task(task, template_str):

    html_content = convert_chapter(task["content"])

    safe_html = (
        html_content
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

    task["dest"].write_text(
        output,
        encoding="utf-8"
    )


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

    paths = [
        "chapters/gsgw/fantl",
        "chapters/gsgw/mtl"
    ]

    tasks_data = []

    meta_map = {}

    for p in paths:

        path = (REPO_ROOT / p).resolve()

        if not path.exists():
            continue

        master_path = path / "0000.md"

        if not master_path.exists():
            continue

        master = frontmatter.load(master_path)

        bookID = master.get("metaBook", "gsgw")
        bookTL = master.get("metaTl", "fantl").lower()

        meta_map.setdefault(bookID, {})
        meta_map[bookID].setdefault(bookTL, [])

        files = sorted(
            f for f in os.listdir(path)
            if f.endswith(".md") and f != "0000.md"
        )

        for file in files:

            post = frontmatter.load(path / file)

            slug = post.metadata.get("slug")

            if not slug:
                continue

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