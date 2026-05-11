import os
import re
import json
import subprocess
import shutil
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import frontmatter
import imagesize

SCRIPT_DIR = Path(__file__).parent.resolve()
REPO_ROOT = SCRIPT_DIR.parent
IMG_STORAGE_DIR = REPO_ROOT / "website/static/assets/images/static-illustrations"
IMG_FALLBACK_DIR = REPO_ROOT / "images/gsgw/illustrations"
IMG_PUBLIC_PREFIX = "/assets/images/static-illustrations"
TEMPLATE_PATH = REPO_ROOT / "website/src/lib/reader/template.svelte"
META_OUTPUT_PATH = REPO_ROOT / "website/src/lib/meta.json"
OUTPUT_ROOT = REPO_ROOT / "website/src/routes/(reader)/read/"


def process_html_images(html_content):
    def replacer(match):
        full_tag = match.group(0)
        src_match = re.search(r'src="([^"]+)"', full_tag)
        if not src_match:
            return full_tag
        original_src = src_match.group(1)
        image_filename = Path(original_src).name
        webp_filename = Path(image_filename).with_suffix(".webp")
        local_image_path = IMG_STORAGE_DIR / webp_filename
        new_src = f"{IMG_PUBLIC_PREFIX}/{webp_filename}"
        new_src = f"{IMG_PUBLIC_PREFIX}/{webp_filename}"
        new_tag = full_tag.replace(original_src, new_src)
        if local_image_path.exists():
            try:
                width, height = imagesize.get(local_image_path)
                if 'width=' not in new_tag:
                    new_tag = new_tag.replace('<img', f'<img width="{width}" height="{height}"')
            except:
                pass
        return new_tag
    return re.sub(r'<img [^>]+>', replacer, html_content)


def convert_chapter(content):
    content = re.sub(r'%%(.*?)%%', r'<span class="shake">\1</span>', content)

    def shake_char_replacer(match):
        text = match.group(1)
        return ''.join(
            f'<span class="shake" style="animation-delay:-{(i * 0.05) % 0.5:.2f}s">{c}</span>'
            if c != ' ' else ' '
            for i, c in enumerate(text)
        )
    content = re.sub(r'%~(.*?)~%', shake_char_replacer, content)

    def shake_char_reverser(match):
        text = match.group(1)
        return ''.join(
            f'<span class="wave-up" style="animation-delay:-{((len(text) - 1 - i) * 0.05) % 0.5:.2f}s">{c}</span>'
            if c != ' ' else ' '
            for i, c in enumerate(text)
        )
    content = re.sub(r'%\^(.*?)\^%', shake_char_reverser, content)
    content = re.sub(r'_(.*?)_', r'[\1]{.underline}', content)
    content = re.sub(r'~(.*?)~', r'~~\1~~', content)
    content = re.sub(r'@ll@(.*?)@ll@', r'<span class="mono mono-left">\1</span>', content)
    content = re.sub(r'@rr@(.*?)@rr@', r'<span class="mono mono-right">\1</span>', content)
    content = re.sub(r'@l@(.*?)@l@', r'<span class="align-left">\1</span>', content)
    content = re.sub(r'@r@(.*?)@r@', r'<span class="align-right">\1</span>', content)
    content = re.sub(r'#r(.*?)r#', r'<span class="text-red">\1</span>', content)
    content = re.sub(r'#b(.*?)b#', r'<span class="text-blue">\1</span>', content)
    content = re.sub(r'#y(.*?)y#', r'<span class="text-yellow">\1</span>', content)
    content = re.sub(r'#\*(.*?)\*#', r'<span class="text-large">\1</span>', content)
    content = re.sub(r'#><(.*?)><#', r'<span class="text-large-centered">\1</span>', content)
    content = re.sub(r'^~~~\s*$', '<hr class="visible-hr">', content, flags=re.MULTILINE)

    style_pattern = r'^[ \t]*\{style="([^"]*)"\}\s*$'
    lines = content.split('\n')
    result = []
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(style_pattern, line)
        if m:
            style = m.group(1)
            result.append(f'::: {{style="{style}"}}')
            i += 1
            content_lines = []
            while i < len(lines) and not re.match(style_pattern, lines[i]):
                content_lines.append(lines[i])
                i += 1
            result.extend(content_lines)
            result.append(':::')
        else:
            result.append(line)
            i += 1
    content = '\n'.join(result)

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

    def wiki_window_replacer(match):
        inner = match.group(1)
        no_meta = False
        if inner.lstrip().startswith('\\'):
            idx = inner.find('\\')
            inner = inner[:idx] + inner[idx+1:]
            no_meta = True
        inner = escape_markdown_except_bold(inner)
        if no_meta:
            return f'\n::: {{.wiki-window .no-meta}}\n{inner}\n:::\n'
        return f'\n::: {{.wiki-window}}\n{inner}\n:::\n'
    content = re.sub(r'\+[-+]+\n(.*?)\n[-+]+\+', wiki_window_replacer, content, flags=re.DOTALL)

    def black_window_replacer(match):
        inner = match.group(1)
        inner = escape_markdown_except_bold(inner)
        return f'\n::: {{.black-window}}\n{inner}\n:::\n'
    content = re.sub(r'\+[=]+\n(.*?)\n[=]+\+', black_window_replacer, content, flags=re.DOTALL)

    def system_window_replacer(match):
        inner = match.group(1)
        no_dividers = False
        if inner.lstrip().startswith('\\'):
            idx = inner.find('\\')
            inner = inner[:idx] + inner[idx+1:]
            no_dividers = True
        inner = escape_markdown_except_bold(inner)
        if no_dividers:
            return f'\n::: {{.system-window .no-fl-dividers}}\n{inner}\n:::\n'
        return f'\n::: {{.system-window}}\n{inner}\n:::\n'
    content = re.sub(r'\+[~]+\n(.*?)\n[~]+\+', system_window_replacer, content, flags=re.DOTALL)

    proc = subprocess.run(
        ["pandoc", "--from", "markdown", "--to", "html", "--quiet"],
        input=content.encode("utf-8"),
        capture_output=True,
        timeout=120
    )
    if proc.returncode != 0:
        print(f"Pandoc error: {proc.stderr.decode().strip()}")
        return f"<p>Error converting content: {proc.stderr.decode().strip()}</p>"
    return process_html_images(proc.stdout.decode("utf-8"))


def process_task(task, template_str):
    html_content = convert_chapter(task["content"])
    safe_html = html_content.replace("`", "\\`").replace("${", "$\\{")
    meta_json = json.dumps(task["meta"], ensure_ascii=False)
    output = template_str.replace("let ch_meta = null;", f"let ch_meta = {meta_json};")
    output = output.replace('let html_content = "";', f'let html_content = `{safe_html}`;')
    with open(task["dest"], "w", encoding="utf-8") as f:
        f.write(output)


def ensure_images():
    if IMG_FALLBACK_DIR.exists():
        IMG_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        for f in IMG_FALLBACK_DIR.iterdir():
            if f.is_file():
                dest = IMG_STORAGE_DIR / f.name
                if not dest.exists():
                    shutil.copy2(f, dest)
                    print(f"  Copied {f.name} to static assets")


def main():
    ensure_images()
    if not TEMPLATE_PATH.exists():
        print(f"Error: Template not found at {TEMPLATE_PATH}")
        return

    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        template_str = f.read()

    paths = ["chapters/gsgw/fantl", "chapters/gsgw/mtl"]
    tasks_data = []
    meta_map = {}

    for p in paths:
        path = (REPO_ROOT / p).resolve()
        if not path.exists() or not (path / "0000.md").exists():
            continue

        master = frontmatter.load(path / "0000.md")
        bookID = master.get("metaBook", "gsgw")
        bookTL = master.get("metaTl", "fantl").lower()
        if bookID not in meta_map:
            meta_map[bookID] = {}
        if bookTL not in meta_map[bookID]:
            meta_map[bookID][bookTL] = []

        files = sorted([f for f in os.listdir(path) if f.endswith(".md") and f != "0000.md"])
        for file in files:
            post = frontmatter.load(path / file)
            slug = post.metadata.get("slug")
            if not slug:
                continue
            meta_map[bookID][bookTL].append(post.metadata)
            out_dir = OUTPUT_ROOT / str(bookID) / str(bookTL) / str(slug)
            out_dir.mkdir(parents=True, exist_ok=True)
            tasks_data.append({
                "content": post.content,
                "meta": post.metadata,
                "dest": out_dir / "+page.svelte"
            })

    with open(META_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(meta_map, f, indent=2)

    if tasks_data:
        total = len(tasks_data)
        print(f"Starting build for {total} chapters...")
        workers = min(os.cpu_count() or 4, total)
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(process_task, task, template_str): task for task in tasks_data}
            done = 0
            for future in as_completed(futures):
                done += 1
                if done % 10 == 0 or done == total:
                    print(f"Generated {done}/{total} chapters...")
        print("Build complete.")


if __name__ == "__main__":
    main()
