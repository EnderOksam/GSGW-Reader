import os
import re
import subprocess
import frontmatter
import datetime
from collections import defaultdict
from pathlib import Path

# --- CONFIGURATION ---
SCRIPT_DIR = Path(__file__).parent.resolve()
REPO_ROOT = SCRIPT_DIR.parent

# Absolute path to CSS (Fixes Pandoc "does not exist" error)
CSS_PATH = SCRIPT_DIR / "epub.css"

# Path to your actual images folder
IMG_ROOT = REPO_ROOT / "images"

# Paths to process
paths = [
    "../chapters/gsgw/goblintl/",
    "../chapters/gsgw/mtl/",
    "../chapters/temp/tempfolder/",
]

# Ensure output directory exists
OUTPUT_DIR = SCRIPT_DIR / "epub"
OUTPUT_DIR.mkdir(exist_ok=True)

today = datetime.date.today().strftime("%B %d, %Y")

for rel_path in paths:
    # Convert relative path to absolute
    path = str((SCRIPT_DIR / rel_path).resolve()) + os.sep
    
    if not os.path.exists(path):
        print(f"Skipping: {path} (Not found)")
        continue

    print(f"{'='*100}\n\n{'-'*10} Starting build for: {path} {'-'*10}")
    
    files = [f for f in os.listdir(path) if f.endswith(".md") and f != "0000.md"]
    chapters = defaultdict(list)

    for file in files:
        post = frontmatter.load(os.path.join(path, file))
        metadata = post.metadata
        content = post.content
        chapters[metadata["section"]].append({**metadata, "content": content})

    print(f"{'-'*5}> Indexed {len(files)} files across {len(chapters)} sections.")
    
    master_file = os.path.join(path, "0000.md")
    if not os.path.exists(master_file):
        print(f"Error: 0000.md missing in {path}")
        continue
        
    masterMD = frontmatter.load(master_file)
    masterMD.content = masterMD.content.replace("{{DATE}}", today)

    print(f"{'-'*5}> Replacing Sections")
    for section in chapters:
        chapters[section].sort(key=lambda x: int(x["index"]))
        print(f"Processing section: {section} ({len(chapters[section])} chapters)")
        content = ""
        for chapter_data in chapters[section]:
            ch_text = chapter_data["content"].strip()
            content += f"""{ch_text}

___
- [Read Comments](https://github.com/Bittu5134/LOTM-Reader/discussions/{chapter_data.get("discussion", "")})
- [Discord](https://discord.gg/XmzJVsyuTQ)

"""

        bookTitle = masterMD["title"][0]["text"]
        bookID = masterMD["metaBook"]
        bookTL = masterMD["metaTl"]
        masterMD.content = masterMD.content.replace(f"", content)

    print(f"{'-'*5}> Producing Epubs")

    for build_type in ["Default", "Legacy"]:
        # Match images to the actual folder structure you provided
        if build_type == "Default":
            img_format = ".webp"
            epub_version = "epub3"
        else:
            img_format = ".jpg"
            epub_version = "epub2"

        current_content = masterMD.content
        current_content = current_content.replace("{{TYPE}}", build_type)
        
        # Logic to swap relative image paths in text to absolute paths for Pandoc
        current_content = current_content.replace("../../../images", str(IMG_ROOT.as_posix()))
        current_content = re.sub(r"\.(jpe?g|png|webp)", img_format, current_content)

        epub_filename = f"{bookTitle} - {bookTL} [{build_type}].epub"
        md_filename = f"{bookID}_{bookTL}_{build_type}.md"

        epub_path = OUTPUT_DIR / epub_filename
        md_path = OUTPUT_DIR / md_filename

        temp_post = frontmatter.Post(current_content, **masterMD.metadata)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(frontmatter.dumps(temp_post))

        print(f"\nConverting to {build_type} ({epub_version})...")

        cover_path = IMG_ROOT / bookID / f"cover{img_format}"

        cmd = [
            "pandoc",
            str(md_path),
            "-o", str(epub_path),
            f"--to={epub_version}",
            "--css", str(CSS_PATH),
            "--toc",
            "--toc-depth=3",
            "--split-level=2",
            "--epub-title-page=false",
        ]

        if cover_path.exists():
            cmd.append(f"--epub-cover-image={str(cover_path)}")
        else:
            print(f"::warning:: Cover image not found at {cover_path}")

        try:
            subprocess.run(cmd, check=True)
            print(f"Done! {build_type} EPUB available at: {epub_path}")
        except subprocess.CalledProcessError as e:
            print(f"Pandoc failed for {build_type}: {e}")

    print("")