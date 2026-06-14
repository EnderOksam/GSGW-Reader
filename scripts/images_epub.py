import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from PIL import Image

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ============================================================
# CONFIGURATION
# ============================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE_DIR = os.path.join(SCRIPT_DIR, "..", "images")
WEBP_DIR = os.path.join(SCRIPT_DIR, "..", "images_default")


def gh_log(msg, log_type="info"):
    if log_type == "group":
        print(f"::group::{msg}", flush=True)
    elif log_type == "endgroup":
        print("::endgroup::", flush=True)
    elif log_type == "error":
        print(f"::error::{msg}", flush=True)
    else:
        print(msg, flush=True)


# ============================================================
# WORKER FUNCTION
# ============================================================
def process_image_suite(paths):
    input_path, relative_path = paths
    filename = os.path.basename(input_path)

    webp_path = os.path.join(WEBP_DIR, relative_path)

    os.makedirs(os.path.dirname(webp_path), exist_ok=True)

    try:
        img = Image.open(input_path)
        img.thumbnail((1600, 1600), Image.LANCZOS)
        img.save(webp_path, "WEBP", quality=85, method=6)
        img.close()

        return {"status": "success", "file": filename}

    except Exception as e:
        return {"status": "error", "file": filename, "msg": str(e)}


# ============================================================
# MAIN PIPELINE
# ============================================================
def run_pipeline():
    start_time = time.time()
    gh_log("Starting EPUB Image Suite Generation", "group")

    valid_exts = ".webp"
    tasks = []

    if not os.path.exists(SOURCE_DIR):
        gh_log(f"Source directory {SOURCE_DIR} not found.", "error")
        return

    for root, _, files in os.walk(SOURCE_DIR):
        for file in files:
            if file.lower().endswith(valid_exts):
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, SOURCE_DIR)
                tasks.append((full_path, rel_path))

    if not tasks:
        gh_log("No WebP images found in source.", "warning")
        gh_log("", "endgroup")
        return

    print(f"Found {len(tasks)} images. Processing with {os.cpu_count()} CPU cores...")
    gh_log("", "endgroup")

    gh_log(f"Generating Suite for {len(tasks)} Images...", "group")
    success_count = 0
    error_count = 0

    with ProcessPoolExecutor() as executor:
        future_to_image = {executor.submit(process_image_suite, t): t for t in tasks}

        for i, future in enumerate(as_completed(future_to_image)):
            result = future.result()
            if result["status"] == "success":
                success_count += 1
                print(f"[{i+1}/{len(tasks)}] Suite created: {result['file']}", flush=True)
            else:
                error_count += 1
                gh_log(f"Failed: {result['file']} -> {result['msg']}", "error")

    gh_log("", "endgroup")

    duration = time.time() - start_time
    gh_log("Suite Generation Summary", "group")
    print(f"Total Time: {duration:.2f}s | Success: {success_count} | Failed: {error_count}")
    gh_log("", "endgroup")


if __name__ == "__main__":
    run_pipeline()