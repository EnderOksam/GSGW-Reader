import re
import html
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

DEBUT_MD_DIRS = [
    REPO_ROOT / "chapters" / "debut" / "DebutPlainTxt",
    REPO_ROOT / "chapters" / "debut" / "DebutFormatted",
]

META_OUTPUT_PATH = REPO_ROOT / "website/src/lib/meta.json"
TEMPLATE_PATH = REPO_ROOT / "website/src/lib/reader/template.svelte"
OUTPUT_ROOT = REPO_ROOT / "website/src/routes/(reader)/read/"

BOOK_ID = "debut"



# =========================================================
# DEBUT-SPECIFIC REGEX (star windows)
# =========================================================

DEBUT_WINDOW_RE = re.compile(r"★-\n(.*?)\n-★", re.DOTALL)
DEBUT_ALERT_RE = re.compile(r"★!\n(.*?)\n!★", re.DOTALL)
DEBUT_ACHIEVE_RE = re.compile(r"★=\n(.*?)\n=★", re.DOTALL)

SMS_WINDOW_RE = re.compile(r"★:\n([\s\S]*?)\n:★", re.DOTALL)
COMMENT_WINDOW_RE = re.compile(r"★\$\n([\s\S]*?)\n\$★", re.DOTALL)


# =========================================================
# STAR WINDOW REPLACERS
# =========================================================

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
    return bw.make_window("debut-window", title_html + body)


def debut_alert_replacer(match):
    return bw.make_window("debut-alert", match.group(1))


def debut_achieve_replacer(match):
    import re
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
        r"\}([^}]+)\}",
        lambda m: f'<span class="debut-achievement-sub debut-achievement-sub-left">{m.group(1).strip()}</span>',
        body,
    )

    body = re.sub(
        r"\{([^{]+)\{",
        lambda m: f'<span class="debut-achievement-sub debut-achievement-sub-right">{m.group(1).strip()}</span>',
        body,
    )
    title_html = f'<div class="debut-achievement-title">{title}</div>\n\n' if title else ""
    return bw.make_window("debut-achievement", title_html + body)


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
            display = safe_html(content[sp.end():] if sp else content)
            style = f' style="background:{color};color:#222"' if color else ''
            html_parts.append(f'<div class="sms-bubble sms-left"{style}>{display}</div>')
        elif dash_right:
            content = dash_right.group(1)
            sp = re.match(r"^(PMD|SAH|BSJ|LSJ|KRB|CE|RCW):\s*", content)
            color = speaker_colors[sp.group(1)] if sp else None
            display = safe_html(content[sp.end():] if sp else content)
            style = f' style="background:{color};color:#222"' if color else ''
            html_parts.append(f'<div class="sms-bubble sms-right"{style}>{display}</div>')
        else:
            html_parts.append(f'<div class="sms-bubble sms-center">{safe_html(trimmed)}</div>')
    return bw.make_window("sms-window", "\n\n".join(html_parts))


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
            title = safe_html(line.strip())
        elif line.startswith(":"):
            desc = safe_html(line.replace(":", "", 1).strip())
        elif line.startswith("-") or line.startswith("\u2013") or line.startswith("\u2014"):
            in_comments = True
            content = re.sub(r"^[\u2014\u2013-]", "", line).strip()
            items.append((safe_html(content), 0))
        elif line.startswith("\u2937") or line.startswith("\u2514") or line.startswith("\u221F"):
            in_comments = True
            depth = 0
            content = line
            while content.startswith("\u2937") or content.startswith("\u2514") or content.startswith("\u221F"):
                depth += 1
                content = re.sub(r"^[\u2937\u2514\u221F]", "", content).lstrip()
            if depth > 3:
                depth = 3
            items.append((safe_html(content.strip()), depth))
        elif line and not in_comments:
            desc += ("" if not desc else "</p>\n<p>") + safe_html(line)

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
    return bw.make_window("alert-window", "\n\n".join(html_parts))


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

    # + windows
    content = bw.PLAIN_WINDOW_RE.sub(
        lambda m: bw.make_window("plain-window", m.group(1)),
        content
    )

    # ! windows
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
    content = DEBUT_ACHIEVE_RE.sub(debut_achieve_replacer, content)

    # sms and comment windows
    content = SMS_WINDOW_RE.sub(sms_window_replacer, content)
    content = COMMENT_WINDOW_RE.sub(comment_window_replacer, content)

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
        .replace("\\", "\\\\")
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
    template_str = TEMPLATE_PATH.read_text(encoding="utf-8")

    for md_dir in DEBUT_MD_DIRS:
        metadata_path = md_dir / "metadata.md"
        if not metadata_path.exists():
            print(f"metadata.md not found at {metadata_path}")
            continue

        master = frontmatter.load(metadata_path)
        bookID = master.get("metaBook", BOOK_ID)
        metaTl = master.get("metaTl", md_dir.name).lower()

        md_files = sorted(
            f.name for f in md_dir.iterdir()
            if f.suffix == ".md" and f.name != "metadata.md"
        )

        if not md_files:
            print(f"No chapter markdown files found in {md_dir}.")
            continue

        tasks_data = []
        meta_list = []

        for file in md_files:
            post = frontmatter.load(md_dir / file)

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

        if bookID not in existing_meta:
            existing_meta[bookID] = {}
        existing_meta[bookID][metaTl] = meta_list
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

        print(f"  Done with {bookID}/{metaTl} ({errors} errors).")

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
