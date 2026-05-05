import os
import subprocess
import time
import re
from concurrent.futures import ProcessPoolExecutor, as_completed

# ============================================================
# CONFIGURATION
# ============================================================
# The previous script outputs clean WebP files here
SOURCE_DIR = "./images"
# Output for high-quality EPUB images
WEBP_DIR = "./images_default"
# Output for B&W legacy EPUB images
JPEG_DIR = "./images_legacy"


def gh_log(msg, log_type="info"):
    """Format logs for GitHub Actions UI - Emoji safe for Windows"""
    # Strips emojis if the console encoding is problematic
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
    """Processes a clean WebP: Resizes for Default and Grayscales for Legacy."""
    input_path, relative_path = paths
    filename = os.path.basename(input_path)

    # Output paths (Preserving the .webp for default, changing to .jpg for legacy)
    webp_path = os.path.join(WEBP_DIR, relative_path)
    jpeg_path = os.path.join(JPEG_DIR, os.path.splitext(relative_path)[0] + ".jpg")

    # Ensure directories exist
    os.makedirs(os.path.dirname(webp_path), exist_ok=True)
    os.makedirs(os.path.dirname(jpeg_path), exist_ok=True)

    try:
        # 1. High-Quality WebP (Resize only if larger than 2000px)
        # Using -resize 2000x2000> ensures we don't upscaled small images
        cmd_webp = [
            "magick",
            input_path,
            "-resize",
            "1600x1600>",
            "-quality",
            "85",
            "-strip",
            webp_path,
        ]
        subprocess.run(cmd_webp, check=True, capture_output=True)

        # 2. Legacy JPEG (Small, Grayscale for old Kindles/E-readers)
        cmd_jpeg = [
            "magick",
            input_path,
            "-resize", "800x800>",
            "-colorspace", "gray",       # Forces 8-bit grayscale (saves 66% space over color)
            "-gamma", "1.1",             # Slightly boosts midtones (e-ink screens tend to look dark)
            "-interlace", "plane",       # Makes it a Progressive JPEG (loads faster/smoother)
            "-quality", "70",            # 70 is plenty for grayscale; anything higher is wasted
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
    start_time = time.time()
    gh_log("🚀 Starting EPUB Image Suite Generation", "group")

    # Only looking for webp now since the previous script converted everything
    valid_exts = ".webp"
    tasks = []

    if not os.path.exists(SOURCE_DIR):
        gh_log(f"Source directory {SOURCE_DIR} not found.", "error")
        return

    # 1. Scan for the pre-processed WebP files
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

    print(
        f"Found {len(tasks)} pre-optimized images. Processing with {os.cpu_count()} cores..."
    )
    gh_log("", "endgroup")

    # 2. Parallel Processing
    gh_log(f"Generating Suite for {len(tasks)} Images...", "group")
    success_count = 0
    error_count = 0

    with ProcessPoolExecutor() as executor:
        future_to_image = {executor.submit(process_image_suite, t): t for t in tasks}

        for i, future in enumerate(as_completed(future_to_image)):
            result = future.result()
            if result["status"] == "success":
                success_count += 1
                # if success_count % 20 == 0:
                if success_count:
                    print(
                        f"[{i+1}/{len(tasks)}] ✅ Suite created: {result['file']}",
                        flush=True,
                    )
            else:
                error_count += 1
                gh_log(f"❌ Failed: {result['file']} -> {result['msg']}", "error")

    gh_log("", "endgroup")

    # 3. Summary
    duration = time.time() - start_time
    gh_log("📊 Suite Generation Summary", "group")
    print(
        f"Total Time: {duration:.2f}s | Success: {success_count} | Failed: {error_count}"
    )
    gh_log("", "endgroup")


if __name__ == "__main__":
    run_pipeline()
