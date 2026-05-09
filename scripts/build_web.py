import os
import re
import asyncio
import json
import shutil
from pathlib import Path
import frontmatter
import imagesize

# --- CONFIGURATION ---
SCRIPT_DIR = Path(__file__).parent.resolve()
REPO_ROOT = SCRIPT_DIR.parent
IMG_STORAGE_DIR = REPO_ROOT / "website/static/assets/images"
IMG_PUBLIC_PREFIX = "/assets/images"
TEMPLATE_PATH = REPO_ROOT / "website/src/lib/reader/template.svelte"
META_OUTPUT_PATH = REPO_ROOT / "website/src/lib/meta.json"
OUTPUT_ROOT = REPO_ROOT / "website/src/routes/(reader)/read/"

MAX_CONCURRENT_TASKS = 75
semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)

completed_count = 0

# --- CORE LOGIC ---

def process_html_images(html_content):
    """
    Scans HTML for <img> tags, updates paths to .webp, and adds width/height attributes.
    """
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

async def convert_chapter(content):
    """
    Converts raw Markdown content to HTML using Pandoc, 
    with pre-processing for the Wiki Window syntax.
    """
    # PRE-PROCESS: Convert %%text%% into shaking text span
    content = re.sub(r'%%(.*?)%%', r'<span class="shake">\1</span>', content)

    # PRE-PROCESS: Convert {style="..."} blocks into Pandoc fenced divs
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

    # PRE-PROCESS: Automatically wrap +--- text ---+ in a wiki-window div
    # This regex looks for lines starting with +--- and ending with ---+
    content = re.sub(
        r'\+[-+]+\n(.*?)\n[-+]+\+', 
        r'\n::: {.wiki-window}\n\1\n:::\n', 
        content, 
        flags=re.DOTALL
    )

    async with semaphore:
        cmd = [
            "pandoc",
            "--from", "markdown",
            "--to", "html",
            "--quiet"
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate(input=content.encode("utf-8"))

        if process.returncode != 0:
            print(f"Pandoc error: {stderr.decode().strip()}")
            return f"<p>Error converting content: {stderr.decode().strip()}</p>"

        html_output = stdout.decode("utf-8")
        return process_html_images(html_output)

async def process_task(task, template_str):
    """
    Integrates converted HTML into the Svelte template and writes to disk.
    """
    global completed_count
    html_content = await convert_chapter(task["content"])
    
    # Move the escaping logic out of the f-string to avoid SyntaxError
    safe_html = html_content.replace("`", "\\`").replace("${", "$\\{")

    # Inject metadata and content into the template string
    output = re.sub(
        r'let ch_meta = null;', 
        f'let ch_meta = {json.dumps(task["meta"])};', 
        template_str
    )
    
    # Use the safe_html variable here
    output = output.replace('let html_content = "";', f'let html_content = `{safe_html}`;')

    with open(task["dest"], "w", encoding="utf-8") as f:
        f.write(output)
    
    completed_count += 1
    if completed_count % 10 == 0:
        print(f"Generated {completed_count} chapters...")

async def main():
    if not TEMPLATE_PATH.exists():
        print(f"Error: Template not found at {TEMPLATE_PATH}")
        return

    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        template_str = f.read()

    # Paths to scan for chapters
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
        
        if bookID not in meta_map: meta_map[bookID] = {}
        if bookTL not in meta_map[bookID]: meta_map[bookID][bookTL] = []

        files = sorted([f for f in os.listdir(path) if f.endswith(".md") and f != "0000.md"])
        for file in files:
            post = frontmatter.load(path / file)
            slug = post.metadata.get("slug")
            if not slug: continue

            meta_map[bookID][bookTL].append(post.metadata)
            out_dir = OUTPUT_ROOT / str(bookID) / str(bookTL) / str(slug)
            out_dir.mkdir(parents=True, exist_ok=True)
            
            tasks_data.append({
                "content": post.content, 
                "meta": post.metadata, 
                "dest": out_dir / "+page.svelte"
            })

    # Save the global metadata index
    with open(META_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(meta_map, f, indent=2)

    if tasks_data:
        print(f"Starting build for {len(tasks_data)} chapters...")
        await asyncio.gather(*[process_task(t, template_str) for t in tasks_data])
        print("Build complete.")

if __name__ == "__main__":
    asyncio.run(main())