import os
import re
import json
import subprocess
from pathlib import Path

import frontmatter

import sys
sys.path.insert(0, str(Path(__file__).parent.resolve()))

import build_web as bw



# =========================================================
# PATHS
# =========================================================

SCRIPT_DIR = Path(__file__).parent.resolve()
REPO_ROOT = SCRIPT_DIR.parent

DEBUT_MD_DIR = REPO_ROOT / "chapters" / "debut" / "Plaintext"

META_OUTPUT_PATH = REPO_ROOT / "website/src/lib/meta.json"
TEMPLATE_PATH = REPO_ROOT / "website/src/lib/reader/template.svelte"
OUTPUT_ROOT = REPO_ROOT / "website/src/routes/(reader)/read/"

BOOK_ID = "debut"
TL_NAME = "Plaintext"



# =========================================================
# DEBUT-SPECIFIC REGEX (star windows)
# =========================================================

DEBUT_WINDOW_RE = re.compile(r"★-\n(.*?)\n-★", re.DOTALL)
DEBUT_ALERT_RE = re.compile(r"★!\n(.*?)\n!★", re.DOTALL)


# =========================================================
# STAR WINDOW REPLACERS
# =========================================================

def debut_window_replacer(match):
    inner = match.group(1)
    lines = inner.split("\n")
    title = lines[0].strip()
    if title.startswith("\\"):
        title = ""
        lines[0] = lines[0].lstrip("\\").strip()
    body_lines = []
    for line in (lines[1:] if title else lines):
        m = re.match(r"^\s*\[(.+?)\]\s*$", line)
        if m:
            body_lines.append(f'<div class="debut-window-label">{m.group(1)}</div>')
        else:
            body_lines.append(line)
    body = "\n".join(body_lines).strip()
    title_html = f'<div class="debut-window-title">{title}</div>\n\n' if title else ""
    return bw.make_window("debut-window", title_html + body)


def debut_alert_replacer(match):
    return bw.make_window("debut-alert", match.group(1))


# =========================================================
# DEBUT CONVERTER (same as build_web but skips + / & windows, adds star windows)
# =========================================================

def convert_chapter(content):

    content = bw.process_twitter_urls(content)

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

    content = bw.SHAKE_RE.sub(r'<span class="shake">\1</span>', content)

    content = bw.SHAKE_CHAR_RE.sub(bw.shake_char_replacer, content)

    content = bw.WAVE_RE.sub(bw.wave_char_replacer, content)

    content = bw.VISIBLE_HR_RE.sub('<hr class="visible-hr">', content)
    content = bw.INVISIBLE_HR_RE.sub('<hr class="invisible-hr">', content)

    content = bw.SUBTLEDISTORT_RE.sub(bw.subtle_replacer, content)

    content = bw.GROW_RE.sub(bw.grow_replacer, content)

    content = bw.SHRINK_RE.sub(bw.shrink_replacer, content)

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

    for pattern, repl in bw.SIMPLE_REPLACEMENTS:
        content = pattern.sub(repl, content)

    content = re.sub(r"\$\$(.*?)\$\$", r'<span class="handwritten">\1</span>', content)

    content = bw.SMOKE_RE.sub(bw.smoke_replacer, content)

    content = bw.AURORA_RE.sub(bw.aurora_replacer, content)

    content = bw.GOLD_RE.sub(r'<span class="gold-text">\1</span>', content)

    content = bw.SPARKLE_RE.sub(r'<span class="sparkle-text">\1</span>', content)

    content = bw.MOON_RE.sub(r'<span class="moon-text">\1</span>', content)

    # restore protected patterns
    for key, val in img_placeholders.items():
        content = content.replace(key, val)
    for key, val in tw_placeholders.items():
        content = content.replace(key, val)

    content = bw.DISTORT_RE.sub(bw.distorted_replacer, content)

    # only ! windows — skip + and & windows
    content = bw.NOTE_WINDOW_RE.sub(bw.note_window_replacer, content)
    content = bw.STICKY_WINDOW_RE.sub(
        lambda m: bw.make_window("sticky-window", m.group(1)),
        content
    )
    content = bw.BRAUN_WINDOW_RE.sub(
        lambda m: bw.make_window("braun-screen", m.group(1)),
        content
    )

    # star windows (debut-specific)
    content = DEBUT_ALERT_RE.sub(debut_alert_replacer, content)
    content = DEBUT_WINDOW_RE.sub(debut_window_replacer, content)

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
        return bw.process_html_images(proc.stdout.decode("utf-8"))
    except subprocess.TimeoutExpired:
        print("Pandoc timed out on a chapter — skipping")
        return "<p>Chapter skipped due to conversion timeout.</p>"



# =========================================================
# BUILD TASK (uses debut-specific converter)
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


def build_pages(slug_filter=None):
    metadata_path = DEBUT_MD_DIR / "metadata.md"
    if not metadata_path.exists():
        print(f"metadata.md not found at {metadata_path}")
        return False

    master = frontmatter.load(metadata_path)
    bookID = master.get("metaBook", BOOK_ID)
    metaTl = master.get("metaTl", TL_NAME).lower()

    md_files = sorted(
        f for f in os.listdir(DEBUT_MD_DIR)
        if f.endswith(".md") and f != "metadata.md"
    )

    if not md_files:
        print("No chapter markdown files found.")
        return False

    template_str = TEMPLATE_PATH.read_text(encoding="utf-8")

    tasks_data = []
    meta_list = []

    for file in md_files:
        post = frontmatter.load(DEBUT_MD_DIR / file)

        slug = post.metadata.get("slug")
        if not slug:
            continue

        if slug_filter is not None and slug != slug_filter:
            continue

        meta_list.append(post.metadata)

        out_dir = OUTPUT_ROOT / str(bookID) / str(metaTl) / str(slug)
        out_dir.mkdir(parents=True, exist_ok=True)

        tasks_data.append({
            "content": post.content,
            "meta": post.metadata,
            "dest": out_dir / "+page.svelte",
        })

    existing_meta = {}
    if META_OUTPUT_PATH.exists():
        existing_meta = json.loads(META_OUTPUT_PATH.read_text(encoding="utf-8"))

    existing_meta[bookID] = {metaTl: meta_list}
    META_OUTPUT_PATH.write_text(
        json.dumps(existing_meta, indent=2),
        encoding="utf-8"
    )

    total = len(tasks_data)
    print(f"Building {total} chapters for {bookID}/{metaTl}...")

    errors = 0
    for i, task in enumerate(tasks_data, 1):
        try:
            process_task(task, template_str)
        except Exception as e:
            print(f"Failed: {task['dest'].name} — {e}")
            errors += 1

        if i % 10 == 0 or i == total:
            print(f"Generated {i}/{total} chapters ({errors} errors)...")

    print(f"Build complete with {errors} errors.")
    return True



# =========================================================
# MAIN
# =========================================================

def main():
    import sys
    slug_filter = None
    if len(sys.argv) > 1:
        if sys.argv[1] == "--slug" and len(sys.argv) > 2:
            slug_filter = sys.argv[2]

    print("=== Debut or Die Build Script ===")

    if not TEMPLATE_PATH.exists():
        print(f"Template not found: {TEMPLATE_PATH}")
        return

    build_pages(slug_filter)

    print("=== Done ===")


if __name__ == "__main__":
    main()
