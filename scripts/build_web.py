import os
import re
import asyncio
import json
import shutil
from pathlib import Path
import frontmatter
import imagesize

# --- CONFIGURATION ---
# Resolves the absolute path of the script for reliable file referencing
SCRIPT_DIR = Path(__file__).parent.resolve()

# Locates the project root relative to this script
REPO_ROOT = SCRIPT_DIR.parent

# Physical location of optimized .webp images on the disk
IMG_STORAGE_DIR = REPO_ROOT / "website/static/assets/images"

# Virtual URL path used by SvelteKit to serve images
IMG_PUBLIC_PREFIX = "/assets/images"

# Path to the base Svelte component used to wrap chapter content
TEMPLATE_PATH = REPO_ROOT / "website/src/lib/reader/template.svelte"

# Path for the generated global book/chapter index
META_OUTPUT_PATH = REPO_ROOT / "website/src/lib/meta.json"

# Target directory for the generated SvelteKit route files
OUTPUT_ROOT = REPO_ROOT / "website/src/routes/(reader)/read/"

# Limits the number of simultaneous Pandoc processes to prevent CPU/RAM exhaustion
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

        # Extracts the 'src' attribute value from the current img tag
        src_match = re.search(r'src=["\'](.*?)["\']', full_tag)
        if not src_match:
            return full_tag 

        old_path = src_match.group(1)

        # Normalizes slashes and extracts the relative image path after 'images/'
        normalized_path = old_path.replace("\\", "/")

        if "/images/" in normalized_path:
            relative_part = normalized_path.split("/images/")[-1]
        elif "images/" in normalized_path:
            relative_part = normalized_path.split("images/")[-1]
        else:
            relative_part = Path(old_path).name

        # Forces the file extension to .webp for the web version
        rel_path_obj = Path(relative_part).with_suffix(".webp")

        # Generates the final URL path for the browser
        new_src = f"{IMG_PUBLIC_PREFIX}/{rel_path_obj.as_posix()}"

        # Locates the image on the local machine to calculate dimensions
        local_file_path = IMG_STORAGE_DIR / rel_path_obj

        width_attr = ""
        height_attr = ""

        # Automatically fetches image dimensions to prevent layout shift (CLS)
        if local_file_path.exists():
            try:
                w, h = imagesize.get(local_file_path)
                width_attr = f' width="{w}"'
                height_attr = f' height="{h}"'
            except:
                pass 

        tag_clean = re.sub(r'\s+(width|height)=["\']?.*?["\']?', '', full_tag)
        tag_clean = re.sub(r'src=["\'].*?["\']', f'src="{new_src}"', tag_clean)
        
        if "/>" in tag_clean:
            return tag_clean.replace("/>", f"{width_attr}{height_attr} />")
        return tag_clean.replace(">", f"{width_attr}{height_attr}>")

        return new_tag

    # Replaces all img tags found in the provided HTML string
    return re.sub(r"<img\s+[^>]*?>", replacer, html_content, flags=re.DOTALL)


async def convert_chapter(
    post_content, post_meta, output_file, total_tasks, template_str
):
    """
    Converts a single Markdown chapter to a Svelte page using Pandoc.
    """
    global completed_count
    async with semaphore:
        # Runs Pandoc as an external process to convert Markdown to HTML
        process = await asyncio.create_subprocess_exec(
            "pandoc", "-f", "markdown", "-t", "html",
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate(input=post_content.encode("utf-8"))

        html_content = stdout.decode("utf-8").strip()
        
        # Clean up malformed tags that crash the Svelte compiler
        html_content = html_content.replace("<<", "<")
        html_content = process_html_images(html_content)

        # 1. Inject Metadata into the JS block
        final_content = re.sub(
            r'let ch_meta\s*=\s*null;', 
            f"let ch_meta = {json.dumps(post_meta)};", 
            template_str
        )
        
        # 2. Escape backticks and interpolation to keep the JS string valid
        safe_html = html_content.replace("`", "\\`").replace("${", "\\${")
        
        # 3. Inject HTML Data into the JS variable to avoid direct markup parsing
        final_content = re.sub(
            r'let html_content\s*=\s*["\'].*?["\'];', 
            f"let html_content = `{safe_html}`;", 
            final_content
        )

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(final_content)

        completed_count += 1
        if completed_count % 50 == 0 or completed_count == total_tasks:
            print(f"Progress: [{completed_count}/{total_tasks}]")

async def main():
    paths = ["../chapters/gsgw/goblintl/", "../chapters/gsgw/mtl/", "../chapters/temp/goblintl/"]
    
    if not TEMPLATE_PATH.exists():
        print(f"Error: Template not found at {TEMPLATE_PATH}")
        return

    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        template_str = f.read()

    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)

    tasks_data, meta_map = [], {}

    for p in paths:
        path = (SCRIPT_DIR / p).resolve()
        if not path.exists() or not (path / "0000.md").exists():
            continue

        master = frontmatter.load(path / "0000.md")
        bookID = master.get("metaBook", "gsgw")
        bookTL = master.get("metaTl", "goblintl").lower()
        
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

    with open(META_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(meta_map, f, indent=2)

    if tasks_data:
        await asyncio.gather(*[
            convert_chapter(td["content"], td["meta"], td["dest"], len(tasks_data), template_str) 
            for td in tasks_data
        ])
        print("Build Complete.")
    else:
        print("No chapters found to process.")

if __name__ == "__main__":
    asyncio.run(main())