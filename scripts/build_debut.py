import os
import json
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
# BUILD TASK (reuses build_web's convert/process)
# =========================================================

def process_task(task, template_str):
    html_content = bw.convert_chapter(task["content"])

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


def build_pages():
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
    print("=== Debut or Die Build Script ===")

    if not TEMPLATE_PATH.exists():
        print(f"Template not found: {TEMPLATE_PATH}")
        return

    build_pages()

    print("=== Done ===")


if __name__ == "__main__":
    main()
