import os
import re
import asyncio
import json
import shutil
import imagesize
from pathlib import Path
import frontmatter

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

# --- LOGGING HELPERS ---
# Formats output for GitHub Actions log visibility

def gh_log(message):
    print(message)

def gh_group(title):
    print(f"::group::{title}")

def gh_endgroup():
    print("::endgroup::")


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
                width_attr = f' width={w}'
                height_attr = f' height={h}'
            except:
                pass 
        else:
            gh_log(f"::warning::Image not found at expected path: {local_file_path}")

        # Swaps the old src with the new path and injects dimension attributes
        new_tag = re.sub(r'src=["\'].*?["\']', f'src="{new_src}"', full_tag)

        if "/>" in new_tag:
            new_tag = new_tag.replace("/>", f"{width_attr}{height_attr} />")
        else:
            new_tag = new_tag.replace(">", f"{width_attr}{height_attr}>")

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
            "pandoc",
            "-f", "markdown",
            "-t", "html",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate(input=post_content.encode("utf-8"))

        if stderr:
            gh_log(f"Pandoc Error for {post_meta.get('title', 'Unknown')}: {stderr.decode()}")

        html_content = stdout.decode("utf-8")

        # Updates image tags within the newly generated HTML
        html_content = process_html_images(html_content)

        # Injects the HTML content into the designated placeholder in the template
        final_svelte_content = template_str.replace("<!-- [DATA] -->", html_content)

        # Embeds the YAML metadata as a JSON object into the Svelte script block
        final_svelte_content = final_svelte_content.replace(
            "// [METADATA]", f"let ch_meta = {json.dumps(post_meta)}"
        )

        # Removes unused import placeholders
        final_svelte_content = final_svelte_content.replace("// [IMG_IMPORT]", "")

        # Writes the final .svelte file to the route directory
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(final_svelte_content)

        # Simple progress tracking for the console
        completed_count += 1
        if completed_count % 50 == 0 or completed_count == total_tasks:
            gh_log(f"Progress: [{completed_count}/{total_tasks}]")


async def main():
    """
    Main entry point: Indexes all markdown files and kicks off the conversion process.
    """
    paths = [
        "../chapters/gsgw/goblintl/",
        "../chapters/gsgw/mtl/",
        "../chapters/temp/goblintl/",
    ]

    gh_group("Initialization")

    # Ensures the template file exists before starting
    if not TEMPLATE_PATH.exists():
        gh_log(f"::error::Template not found at {TEMPLATE_PATH}")
        exit(1)

    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        template_str = f.read()

    # Clears the old build files to ensure a fresh output
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
        gh_log("Cleaned previous output directory.")

    tasks_data = []
    meta_map = {}

    gh_endgroup()

    gh_group("Indexing Chapters")

    for path in paths:
        if not os.path.exists(path):
            gh_log(f"Skipping: {path} (Not found)")
            continue

        # Looks for the 0000.md master file which contains book-level metadata
        master_path = os.path.join(path, "0000.md")
        if not os.path.exists(master_path):
            gh_log(f"Skipping: {path} (0000.md missing)")
            continue

        # Loads the book ID and translation type (e.g., MTL vs Human)
        masterMD = frontmatter.load(master_path)
        bookID, bookTL = masterMD["metaBook"], masterMD["metaTl"].lower()

        if bookID not in meta_map:
            meta_map[bookID] = {}
        if bookTL not in meta_map[bookID]:
            meta_map[bookID][bookTL] = []

        # Indexes all .md files in the folder (excluding the master file)
        files = [f for f in os.listdir(path) if f.endswith(".md") and f != "0000.md"]
        gh_log(f"Found {len(files)} chapters for {bookID} ({bookTL})")

        for file in files:
            post = frontmatter.load(os.path.join(path, file))
            slug = post.metadata.get("slug")
    
            # Cleans up Markdown headers (downshifts nested headers)
            post.content = re.sub(r"^#(#+)", r"\1", post.content, flags=re.MULTILINE)

            if not slug:
                continue

            # Adds chapter metadata to the global map for the search/index file
            meta_map[bookID][bookTL].append(post.metadata)

            # Creates the nested directory structure: /read/book-name/translation-type/slug/
            output_dir = OUTPUT_ROOT / str(bookID) / str(bookTL) / str(slug)
            output_dir.mkdir(parents=True, exist_ok=True)

            # Prepares the data bundle for the conversion function
            tasks_data.append(
                {
                    "content": post.content,
                    "meta": post.metadata,
                    "dest": output_dir / "+page.svelte",
                }
            )

    # Writes the meta.json file which the website uses for the Table of Contents
    with open(META_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(meta_map, f, indent=2)

    gh_endgroup()

    total = len(tasks_data)
    gh_group(f"Processing {total} Chapters")

    # Creates a list of coroutines for all chapters
    tasks = [
        convert_chapter(td["content"], td["meta"], td["dest"], total, template_str)
        for td in tasks_data
    ]

    # Executes all conversion tasks concurrently
    await asyncio.gather(*tasks)

    gh_endgroup()
    gh_log("Build Complete.")


if __name__ == "__main__":
    # Start the async event loop
    asyncio.run(main())