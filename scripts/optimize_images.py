import os
import sys
import re
from concurrent.futures import ProcessPoolExecutor, as_completed
from PIL import Image

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ============================================================
# CONFIGURATION
# ============================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE_DIR = os.path.join(SCRIPT_DIR, "..", "images")


def gh_log(msg, type="info"):
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
    name_no_ext = os.path.splitext(filename)[0]
    clean_name = re.sub(r"[^a-zA-Z0-9_]", "", name_no_ext)
    clean_name = clean_name[:30]
    if not clean_name:
        clean_name = "img"
    return f"{clean_name}.webp"


# ============================================================
# IMAGE PROCESSOR
# ============================================================
def process_image(file_path):
    directory = os.path.dirname(file_path)
    original_filename = os.path.basename(file_path)
    new_filename = get_clean_filename(original_filename)
    output_path = os.path.join(directory, new_filename)

    try:
        _, ext = os.path.splitext(original_filename)

        if ext.lower() == ".webp":
            if file_path == output_path:
                return f"* Skipped (Already clean): {original_filename}"
            os.rename(file_path, output_path)
            return f"* Renamed: {original_filename} -> {new_filename}"

        img = Image.open(file_path)
        img.save(output_path, "WEBP", quality=85, method=6)
        img.close()
        os.remove(file_path)
        return f"* Converted & Deleted Original: {original_filename} -> {new_filename}"

    except Exception as e:
        return f"! ERROR {original_filename}: {str(e)}"


# ============================================================
# MAIN PIPELINE
# ============================================================
def run_pipeline():
    gh_log("Starting In-Place Image Optimization", "group")

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
        future_to_image = {executor.submit(process_image, task): task for task in tasks}

        for i, future in enumerate(as_completed(future_to_image)):
            result = future.result()
            if result.startswith("!"):
                gh_log(result, "error")
            else:
                print(f"[{i+1}/{len(tasks)}] {result}", flush=True)

    gh_log("All images processed successfully.", "endgroup")


if __name__ == "__main__":
    run_pipeline()
