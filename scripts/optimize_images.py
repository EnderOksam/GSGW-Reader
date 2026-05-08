import os
import subprocess
import re
from concurrent.futures import ProcessPoolExecutor, as_completed

# ============================================================
# CONFIGURATION
# ============================================================
# Defines the base folder where images will be scanned and modified
SOURCE_DIR = "./images"


def gh_log(msg, type="info"):
    """
    Format logs for GitHub Actions UI.
    Creates collapsible 'groups' in the action logs for better readability.
    """
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
    Sanitizes filenames to be web-friendly:
    1. Removes file extension.
    2. Keeps only alphanumeric characters and underscores.
    3. Truncates length to 30 characters to avoid path issues.
    4. Appends the .webp extension.
    """
    name_no_ext = os.path.splitext(filename)[0]

    # Regex: Replace any character that is NOT a-z, A-Z, 0-9, or _ with nothing
    clean_name = re.sub(r"[^a-zA-Z0-9_]", "", name_no_ext)

    # Truncate to first 30 characters
    clean_name = clean_name[:30]

    # Fallback if regex removes everything (e.g., if the filename was just emojis)
    if not clean_name:
        clean_name = "img"

    return f"{clean_name}.webp"


# ============================================================
# IMAGE PROCESSOR
# ============================================================
def process_image(file_path):
    """
    Handles the heavy lifting for an individual image:
    - Renames WebP files if their name is not 'clean'.
    - Converts other formats (PNG, JPG, etc.) to WebP using ImageMagick.
    - Deletes the original non-WebP file after successful conversion.
    """
    directory = os.path.dirname(file_path)
    original_filename = os.path.basename(file_path)

    # Calculate what the final filename should look like
    new_filename = get_clean_filename(original_filename)
    output_path = os.path.join(directory, new_filename)

    try:
        _, ext = os.path.splitext(original_filename)

        # --- CASE 1: File is already a WebP ---
        if ext.lower() == ".webp":
            # If the current path matches the target (already clean), skip it
            if file_path == output_path:
                return f"✨ Skipped (Already clean): {original_filename}"

            # If it's WebP but has a messy name, rename it
            os.rename(file_path, output_path)
            return f"✏️ Renamed: {original_filename} -> {new_filename}"

        # --- CASE 2: File needs conversion (JPG, PNG, etc.) ---
        # ImageMagick 'magick' command:
        # -quality 85: Balanced compression
        # webp:method=6: Slowest/best compression effort
        # -strip: Remove metadata to shrink file size
        cmd = [
            "magick",
            file_path,
            "-quality", "85",
            "-define", "webp:method=6",
            "-strip",
            output_path,
        ]

        subprocess.run(cmd, check=True, capture_output=True)

        # Crucial: Only delete the original once we are sure the output exists
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
    """
    Scans the directory for images and uses a ProcessPool to handle 
    conversions in parallel across multiple CPU cores.
    """
    gh_log("📷 Starting In-Place Image Optimization", "group")

    valid_exts = (".jpg", ".jpeg", ".png", ".tiff", ".webp", ".avif")
    tasks = []

    # Initial safety check
    if not os.path.exists(SOURCE_DIR):
        gh_log(f"Source directory {SOURCE_DIR} not found.", "error")
        return

    # Recursive scan for all image files
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

    # Multi-core execution
    with ProcessPoolExecutor() as executor:
        # Kick off all processing tasks simultaneously
        future_to_image = {executor.submit(process_image, task): task for task in tasks}

        for i, future in enumerate(as_completed(future_to_image)):
            result = future.result()

            # Handle and log results
            if "ERROR" in result or "CRITICAL" in result:
                gh_log(result, "error")
            else:
                # Progress tracking [Current/Total]
                print(f"[{i+1}/{len(tasks)}] {result}", flush=True)

    gh_log("All images processed successfully.", "endgroup")


if __name__ == "__main__":
    run_pipeline()