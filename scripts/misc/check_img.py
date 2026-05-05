import os
import re

# --- CONFIGURATION ---
# Set to True to actually delete the files. Keep False to just see the list.
DELETE_UNUSED = False

# The base directories
IMAGE_BASE = "./images"
CONTENT_BASE = "./chapters"


def find_unused_images():
    # 1. Gather all image filenames from subdirectories ONLY
    all_images = {}  # Filename -> Full Path
    gh_log("🔍 Scanning image directories (excluding root)...", "group")

    if not os.path.exists(IMAGE_BASE):
        gh_log(f"Error: Base image directory {IMAGE_BASE} not found.", "error")
        return

    # Convert to absolute path for reliable comparison
    abs_image_base = os.path.abspath(IMAGE_BASE)

    for root, dirs, files in os.walk(IMAGE_BASE):
        # Skip files that are directly in the IMAGE_BASE folder
        if os.path.abspath(root) == abs_image_base:
            continue

        for file in files:
            if file.lower().endswith(
                (".png", ".jpg", ".jpeg", ".webp", ".gif", ".avif")
            ):
                # Store absolute path to ensure deletion works correctly
                all_images[file] = os.path.abspath(os.path.join(root, file))

    print(f"Found {len(all_images)} images in subdirectories.")
    print("::endgroup::")

    # 2. Scan ALL Markdown files in ALL subdirectories of chapters/
    used_images = set()
    md_files = []

    gh_log("📄 Analyzing all Markdown files in chapters/", "group")
    if not os.path.exists(CONTENT_BASE):
        gh_log(f"Error: Base chapters directory {CONTENT_BASE} not found.", "error")
        return

    for root, dirs, files in os.walk(CONTENT_BASE):
        for file in files:
            if file.lower().endswith(".md"):
                md_files.append(os.path.join(root, file))

    # Regex to catch filenames inside paths (handles /path/img.webp or \path\img.webp)
    image_pattern = re.compile(
        r"[\/\\]([^\/\s\\]+\.(?:png|jpg|jpeg|webp|gif|avif))", re.IGNORECASE
    )

    for md_path in md_files:
        try:
            with open(md_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                matches = image_pattern.findall(content)
                for match in matches:
                    used_images.add(match)
        except Exception as e:
            print(f"⚠️ Could not read {md_path}: {e}")

    print(f"Scanned {len(md_files)} Markdown files.")
    print("::endgroup::")

    # 3. Filter Unused
    unused_paths = []
    for img_name, full_path in all_images.items():
        if img_name not in used_images:
            unused_paths.append(full_path)

    # --- OUTPUT & DELETION ---
    print("\n" + "=" * 45)
    print(f"📊 DYNAMIC AUDIT SUMMARY")
    print(f"Total Images Found:    {len(all_images)}")
    print(f"Unused (Candidates):   {len(unused_paths)}")
    print("=" * 45)

    if not unused_paths:
        print("✨ All subdirectory images are currently in use!")
        return

    if DELETE_UNUSED:
        gh_log("🗑️ DELETING UNUSED IMAGES", "group")
        for path in sorted(unused_paths):
            try:
                os.remove(path)
                print(f"✅ Deleted: {path}")
            except Exception as e:
                print(f"❌ Failed to delete {path}: {e}")
        print("::endgroup::")
        print(f"\nCleanup complete. {len(unused_paths)} files removed.")
    else:
        print("\n🚫 DRY RUN MODE: No files were deleted.")
        print("Set 'DELETE_UNUSED = True' to perform cleanup.")
        print("\nUnused Image Paths (Subdirectories only):")
        for path in sorted(unused_paths):
            rel = os.path.relpath(path, os.getcwd())
            print(f"  [ ] {rel}")


def gh_log(msg, type="info"):
    if type == "group":
        print(f"::group::{msg}", flush=True)
    elif type == "error":
        print(f"::error::{msg}", flush=True)
    else:
        print(msg, flush=True)


if __name__ == "__main__":
    find_unused_images()
