import os
import re
import subprocess
import frontmatter
import datetime
from collections import defaultdict

# --- CONFIGURATION & SETUP ---
# List of source directories containing the raw markdown chapters
paths = [
    "../chapters/gsgw/goblintl/",
    "../chapters/gsgw/mtl/",
    "../chapters/temp/tempfolder/",
]

# Ensure the output directory for finished Ebooks exists
os.makedirs("./epub", exist_ok=True)

# Generate a formatted date string for the title page/metadata
today = datetime.date.today().strftime("%B %d, %Y")

# Iterate through each book/translation path defined above
for path in paths:
    print(f"{'='*100}\n\n{'-'*10} Starting build for: {path} {'-'*10}")
    
    # Identify all chapter files (ignoring the 0000.md master metadata file)
    files = [f for f in os.listdir(path) if f.endswith(".md") and f != "0000.md"]
    chapters = defaultdict(list)

    # --- STEP 1: INDEXING ---
    # Read each markdown file and group them by their "section" (e.g., Vol 1, Vol 2)
    for file in files:
        post = frontmatter.load(path + file)
        metadata = post.metadata
        content = post.content
        # Combine content and metadata into a list categorized by section
        chapters[metadata["section"]].append({**metadata, "content": content})

    print(f"{'-'*5}> Indexed {len(files)} files across {len(chapters)} sections.")
    
    # Load the master metadata file which acts as the book's backbone/template
    masterMD = frontmatter.load(path + "0000.md")
    # Replace the date placeholder in the master template
    masterMD.content = masterMD.content.replace("{{DATE}}", today)

    # --- STEP 2: CONTENT ASSEMBLY ---
    print(f"{'-'*5}> Replacing Sections")
    for section in chapters:
        # Sort chapters within the section based on their index number
        chapters[section].sort(key=lambda x: int(x["index"]))
        print(f"Processing section: {section} ({len(chapters[section])} chapters)")
        
        section_content = ""
        for chapter in chapters[section]:
            # Clean up whitespace and append a horizontal rule and social links to each chapter
            text = chapter["content"].strip()
            section_content += f"""{text}

___
- [Read Comments](https://github.com/Bittu5134/LOTM-Reader/discussions/{chapter["discussion"]})
- [Discord](https://discord.gg/XmzJVsyuTQ)

"""

        # Extract book info for filenames and metadata
        bookTitle = masterMD["title"][0]["text"]
        bookID = masterMD["metaBook"]
        bookTL = masterMD["metaTl"]
        
        # Inject the compiled section content into the master template's placeholder tag
        masterMD.content = masterMD.content.replace(f"<!-- [{section}] -->", section_content)

    # --- STEP 3: EPUB GENERATION ---
    print(f"{'-'*5}> Producing Epubs")

    # Generate two versions: "Default" (Modern) and "Legacy" (For older E-readers/Kindles)
    for build_type in ["Default", "Legacy"]:
        # Setup specific formats and folders based on the build type
        if build_type == "Default":
            img_folder = "./images_default"
            img_format = ".webp"
            epub_version = "epub3"  # Modern standard
        else:
            img_folder = "./images_legacy"
            img_format = ".jpg"     # Better compatibility for older devices
            epub_version = "epub2"  # Legacy standard

        # Prepare the final string content without mutating the original master object
        current_content = masterMD.content
        current_content = current_content.replace("{{TYPE}}", build_type)
        current_content = current_content.replace("../../../images", img_folder)

        # Update all image extensions in the text to match the build type (e.g., .webp -> .jpg)
        current_content = re.sub(r"\.(jpe?g|png|webp)", img_format, current_content)

        # Define file paths for the final EPUB and a temporary markdown file for Pandoc
        epub_filename = f"{bookTitle} - {bookTL} [{build_type}].epub"
        md_filename = f"{bookID}_{bookTL}_{build_type}.md"

        epub_path = os.path.join("./epub", epub_filename)
        md_path = os.path.join("./epub", md_filename)

        # Save the fully assembled text to a temporary markdown file
        temp_post = frontmatter.Post(current_content, **masterMD.metadata)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(frontmatter.dumps(temp_post))

        print(f"\nConverting to {build_type} ({epub_version}) using {img_folder}...")

        # --- STEP 4: PANDOC EXECUTION ---
        # Construct the command line arguments for Pandoc to handle the heavy lifting
        cmd = [
            "pandoc",
            md_path,
            "-o", epub_path,
            f"--to={epub_version}",
            "--css", "./scripts/epub.css", # Styling for the Ebook
            "--toc",                      # Generate Table of Contents
            "--toc-depth=3",
            "--split-level=2",            # Defines how the book is split into files internally
            f"--epub-cover-image={img_folder}/{bookID}/cover{img_format}",
            "--epub-title-page=false",
        ]

        # Execute Pandoc and check for success
        subprocess.run(cmd, check=True)
        print(f"Done! {build_type} EPUB available at: {epub_path}")

    print("")