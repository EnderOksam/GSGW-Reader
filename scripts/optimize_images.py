import os
import subprocess
import re
from concurrent.futures import ProcessPoolExecutor, as_completed

# ============================================================
# CONFIGURATION
# ============================================================
SOURCE_DIR = "./images"


def gh_log(msg, type="info"):
    """Format logs for GitHub Actions UI"""
    if type == "group":
        print(f"::group::{msg}", flush=True)
    elif type == "endgroup":
        print("::endgroup::", flush=True)
    elif type == "error":
        print(f"::error::{msg}", flush=True)
    else:
        print(msg, flush=True)


# ============================================================
# UTILS
# ============================================================
def get_clean_filename(filename):
    """
    1. Strip extension.
    2. Remove non-alphanumeric chars (keep underscores).
    3. Truncate to 30 chars.
    4. Force .webp extension.
    """
    name_no_ext = os.path.splitext(filename)[0]

    # Regex: Replace anything that is NOT a-z, A-Z, 0-9, or _ with empty string
    clean_name = re.sub(r"[^a-zA-Z0-9_]", "", name_no_ext)

    # Truncate to 30 chars
    clean_name = clean_name[:30]

    # Handle empty strings (fallback)
    if not clean_name:
        clean_name = "img"

    return f"{clean_name}.webp"


# ============================================================
# IMAGE PROCESSOR
# ============================================================
def process_image(file_path):
    """
    In-place processing:
    - If WebP: Rename it (if name is dirty).
    - If Other: Convert to WebP -> Delete Original.
    """
    directory = os.path.dirname(file_path)
    original_filename = os.path.basename(file_path)

    # Generate the new clean filename
    new_filename = get_clean_filename(original_filename)
    output_path = os.path.join(directory, new_filename)

    try:
        _, ext = os.path.splitext(original_filename)

        # CASE 1: Input is ALREADY WebP
        if ext.lower() == ".webp":
            # If the name is already clean/correct, do nothing
            if file_path == output_path:
                return f"✨ Skipped (Already clean): {original_filename}"

            # Just Rename (Move)
            # This effectively "deletes" the old name and keeps the new one
            os.rename(file_path, output_path)
            return f"✏️ Renamed: {original_filename} -> {new_filename}"

        # CASE 2: Input is NOT WebP (jpg, png, etc.)
        # 1. Convert to WebP
        cmd = [
            "magick",
            file_path,
            "-quality",
            "85",
            "-define",
            "webp:method=6",
            "-strip",
            output_path,
        ]

        # Check if we are overwriting a file that already exists (rare edge case)
        # We proceed anyway as per standard conversion logic

        subprocess.run(cmd, check=True, capture_output=True)

        # 2. Delete the original source file only after successful conversion
        os.remove(file_path)

        return f"✅ Converted & Deleted Original: {original_filename} -> {new_filename}"

    except subprocess.CalledProcessError as e:
        return f"❌ ERROR converting {original_filename}: {e.stderr.decode().strip()}"
    except OSError as e:
        return f"❌ ERROR filesystem {original_filename}: {str(e)}"
    except Exception as e:
        return f"❌ CRITICAL {original_filename}: {str(e)}"


# ============================================================
# MAIN PIPELINE
# ============================================================
def run_pipeline():
    gh_log("📷 Starting In-Place Image Optimization", "group")

    valid_exts = (".jpg", ".jpeg", ".png", ".tiff", ".webp", ".avif")
    tasks = []

    if not os.path.exists(SOURCE_DIR):
        gh_log(f"Source directory {SOURCE_DIR} not found.", "error")
        return

    print(f"Scanning {SOURCE_DIR}...")
    for root, _, files in os.walk(SOURCE_DIR):
        for file in files:
            if file.lower().endswith(valid_exts):
                full_path = os.path.join(root, file)
                tasks.append(full_path)

    if not tasks:
        gh_log("No images found.", "info")
        gh_log("", "endgroup")
        return

    print(f"Found {len(tasks)} images. Processing with {os.cpu_count()} cores...")
    gh_log("", "endgroup")

    gh_log(f"Processing {len(tasks)} Images...", "group")

    with ProcessPoolExecutor() as executor:
        # Submit all tasks
        future_to_image = {executor.submit(process_image, task): task for task in tasks}

        for i, future in enumerate(as_completed(future_to_image)):
            result = future.result()

            # Show errors immediately, only show some success logs
            if "ERROR" in result or "CRITICAL" in result:
                gh_log(result, "error")
            # elif i % 10 == 0:
            else:
                print(f"[{i+1}/{len(tasks)}] {result}", flush=True)

    gh_log("All images processed successfully.", "endgroup")


if __name__ == "__main__":
    run_pipeline()
