import os
import subprocess
import time
import re
from concurrent.futures import ProcessPoolExecutor, as_completed

# ============================================================
# CONFIGURATION
# ============================================================
# Input folder containing high-quality source images
SOURCE_DIR = "./images"
# Output directory for modern EPUBs (WebP format, high resolution)
WEBP_DIR = "./images_default"
# Output directory for legacy EPUBs (JPEG format, grayscale, lower res)
JPEG_DIR = "./images_legacy"


def gh_log(msg, log_type="info"):
    """
    Helper to format logs for GitHub Actions. 
    Wraps messages in 'groups' to make the UI expandable/collapsible.
    """
    safe_msg = msg.encode("ascii", "ignore").decode("ascii")
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
    """
    The core image processor. For every input, it creates TWO versions:
    1. A modern WebP for high-end readers.
    2. A grayscale JPEG for E-ink devices (Kindles).
    """
    input_path, relative_path = paths
    filename = os.path.basename(input_path)

    # Define final destination paths
    webp_path = os.path.join(WEBP_DIR, relative_path)
    jpeg_path = os.path.join(JPEG_DIR, os.path.splitext(relative_path)[0] + ".jpg")

    # Create subdirectories if the source has a nested folder structure
    os.makedirs(os.path.dirname(webp_path), exist_ok=True)
    os.makedirs(os.path.dirname(jpeg_path), exist_ok=True)

    try:
        # 1. High-Quality WebP Generation
        # -resize 1600x1600> downsizes large images but never upscales small ones
        # -strip removes metadata (EXIF) to save file size
        cmd_webp = [
            "magick", input_path,
            "-resize", "1600x1600>",
            "-quality", "85",
            "-strip",
            webp_path,
        ]
        subprocess.run(cmd_webp, check=True, capture_output=True)

        # 2. Legacy JPEG Generation (Optimized for E-ink screens)
        # -colorspace gray converts to 8-bit grayscale (drastically smaller)
        # -gamma 1.1 brightens the image slightly so it doesn't look "muddy" on E-ink
        # -interlace plane creates a Progressive JPEG for better loading
        cmd_jpeg = [
            "magick", input_path,
            "-resize", "800x800>",
            "-colorspace", "gray",
            "-gamma", "1.1",
            "-interlace", "plane",
            "-quality", "70",
            "-strip",
            jpeg_path,
        ]
        subprocess.run(cmd_jpeg, check=True, capture_output=True)

        return {"status": "success", "file": filename}

    except subprocess.CalledProcessError as e:
        err_msg = e.stderr.decode().strip() if e.stderr else str(e)
        return {"status": "error", "file": filename, "msg": err_msg}
    except Exception as e:
        return {"status": "critical", "file": filename, "msg": str(e)}


# ============================================================
# MAIN PIPELINE
# ============================================================
def run_pipeline():
    """
    Orchestrates the parallel processing of the image library.
    """
    start_time = time.time()
    gh_log("🚀 Starting EPUB Image Suite Generation", "group")

    valid_exts = ".webp"
    tasks = []

    # Check if the source folder exists
    if not os.path.exists(SOURCE_DIR):
        gh_log(f"Source directory {SOURCE_DIR} not found.", "error")
        return

    # 1. Scan the source directory for all WebP images to process
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

    # 2. Parallel Processing Execution
    # ProcessPoolExecutor runs multiple ImageMagick instances at once for speed
    gh_log(f"Generating Suite for {len(tasks)} Images...", "group")
    success_count = 0
    error_count = 0

    with ProcessPoolExecutor() as executor:
        # Submit all images to the pool
        future_to_image = {executor.submit(process_image_suite, t): t for t in tasks}

        # Handle results as they finish
        for i, future in enumerate(as_completed(future_to_image)):
            result = future.result()
            if result["status"] == "success":
                success_count += 1
                print(f"[{i+1}/{len(tasks)}] ✅ Suite created: {result['file']}", flush=True)
            else:
                error_count += 1
                gh_log(f"❌ Failed: {result['file']} -> {result['msg']}", "error")

    gh_log("", "endgroup")

    # 3. Final Summary Report
    duration = time.time() - start_time
    gh_log("📊 Suite Generation Summary", "group")
    print(f"Total Time: {duration:.2f}s | Success: {success_count} | Failed: {error_count}")
    gh_log("", "endgroup")


if __name__ == "__main__":
    run_pipeline()