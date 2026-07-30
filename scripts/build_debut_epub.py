#!/usr/bin/env python3
"""Build Debut or Die EPUB with windows rendered as WebP images.

Uses playwright to render each window div as a transparent WebP image,
then embeds those images in the EPUB instead of CSS-styled HTML.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import json
import re
import subprocess
import sys
import uuid
import zipfile
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
import asyncio
import os
import urllib.parse
from typing import Any

SCRIPT_DIR = Path(__file__).parent.resolve()
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

import build_epub as epub
import build_web as bw

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Error: playwright required. pip install playwright && playwright install chromium")
    sys.exit(1)

try:
    from PIL import Image
except ImportError:
    Image = None

CHAPTERS_ROOT = REPO_ROOT / "chapters"
IMAGES_ROOT = REPO_ROOT / "images"
CSS_PATH = SCRIPT_DIR / "epub.css"
READER_CSS_PATH = REPO_ROOT / "website/src/routes/(reader)/reader.css"
READER_WINDOWS_CSS_PATH = REPO_ROOT / "website/src/lib/reader/reader-windows.css"
OUTPUT_DIR = SCRIPT_DIR / "epub"

DEBUT_WINDOW_RE = re.compile(r"★-\n(.*?)\n-★", re.DOTALL)
DEBUT_ALERT_RE = re.compile(r"★!\n(.*?)\n!★", re.DOTALL)
DEBUT_ACHIEVE_RE = re.compile(r"★=\n(.*?)\n=★", re.DOTALL)
SMS_WINDOW_RE = re.compile(r"★:\n([\s\S]*?)\n:★", re.DOTALL)
COMMENT_WINDOW_RE = re.compile(r"★\$\n([\s\S]*?)\n\$★", re.DOTALL)

from build_epub import WINDOW_CSS, WindowInfo, find_window_divs, render_window_to_webp


def convert_chapter_debut(content: str) -> str:
    """Convert debut markdown to HTML using the same pipeline as build_debut.py."""
    content = bw.process_twitter_urls(content)

    tw_placeholders: dict[str, str] = {}
    def protect_twitter(text: str) -> str:
        def save(m: re.Match) -> str:
            key = f"\x00TW{len(tw_placeholders)}\x00"
            tw_placeholders[key] = m.group(0)
            return key
        return re.sub(r'<div class="twitter-embed"[^>]*>.*?</div>\s*</div>', save, text, flags=re.DOTALL)
    content = protect_twitter(content)

    content = bw.SHAKE_RE.sub(r'<span class="shake">\1</span>', content)
    content = bw.SHAKE_CHAR_RE.sub(bw.shake_char_replacer, content)
    content = bw.WAVE_RE.sub(bw.wave_char_replacer, content)
    content = bw.VISIBLE_HR_RE.sub('<hr class="visible-hr">', content)
    content = bw.INVISIBLE_HR_RE.sub('<hr class="invisible-hr">', content)
    content = bw.SUBTLEDISTORT_RE.sub(bw.subtle_replacer, content)
    content = bw.GROW_RE.sub(bw.grow_replacer, content)
    content = bw.SHRINK_RE.sub(bw.shrink_replacer, content)

    img_placeholders: dict[str, str] = {}
    def protect_patterns(text: str) -> str:
        def save(key_store: dict) -> callable:
            def save_inner(m: re.Match) -> str:
                key = f"\x00IMG{len(key_store)}\x00"
                key_store[key] = m.group(0)
                return key
            return save_inner
        text = re.sub(r'!\[.*?\]\(.*?\)', save(key_store=img_placeholders), text)
        text = re.sub(r'~~[^~]+?~~', save(key_store=img_placeholders), text)
        return text
    content = protect_patterns(content)

    for pattern, repl in bw.SIMPLE_REPLACEMENTS:
        content = pattern.sub(repl, content)

    content = re.sub(r"\$\$(.*?)\$\$", r'<span class="handwritten">\1</span>', content)
    content = bw.SMOKE_RE.sub(bw.smoke_replacer, content)
    content = bw.AURORA_RE.sub(bw.aurora_replacer, content)
    content = bw.GOLD_RE.sub(r'<span class="gold-text">\1</span>', content)
    content = bw.SPARKLE_RE.sub(r'<span class="sparkle-text">\1</span>', content)
    content = bw.MOON_RE.sub(r'<span class="moon-text">\1</span>', content)
    content = bw.SILVER_RE.sub(bw.silver_replacer, content)

    for key, val in img_placeholders.items():
        content = content.replace(key, val)
    for key, val in tw_placeholders.items():
        content = content.replace(key, val)

    content = bw.DISTORT_RE.sub(bw.distorted_replacer, content)
    content = bw.WIKI_WINDOW_RE.sub(bw.wiki_window_replacer, content)
    content = bw.BLACK_WINDOW_RE.sub(lambda m: bw.make_window("black-window", m.group(1)), content)
    content = bw.SYSTEM_WINDOW_RE.sub(bw.system_window_replacer, content)
    content = bw.PLAIN_WINDOW_RE.sub(lambda m: bw.make_window("plain-window", m.group(1)), content)
    content = bw.RECORD_WINDOW_RE.sub(bw.record_window_replacer, content)
    content = bw.FOLLOWUP_WINDOW_RE.sub(lambda m: bw.make_window("plain-window", m.group(1)), content)
    content = bw.AMPERSAND_WINDOW_RE.sub(lambda m: bw.make_window("followup-window", m.group(1)), content)
    content = bw.NOTE_WINDOW_RE.sub(bw.note_window_replacer, content)
    content = bw.STICKY_WINDOW_RE.sub(lambda m: bw.make_window("sticky-window", m.group(1)), content)
    content = bw.BRAUN_WINDOW_RE.sub(lambda m: bw.make_window("braun-screen", m.group(1)), content)

    # Star windows
    content = DEBUT_ALERT_RE.sub(bw.debut_alert_replacer, content)
    content = DEBUT_WINDOW_RE.sub(bw.debut_window_replacer, content)
    content = DEBUT_ACHIEVE_RE.sub(bw.debut_achieve_replacer, content)
    content = SMS_WINDOW_RE.sub(bw.sms_window_replacer, content)
    content = COMMENT_WINDOW_RE.sub(bw.comment_window_replacer, content)

    try:
        proc = subprocess.run(
            ["pandoc", "--from", "markdown-superscript", "--to", "html", "--quiet"],
            input=content.encode("utf-8"),
            capture_output=True,
            timeout=120,
        )
        if proc.returncode != 0:
            err = proc.stderr.decode().strip()
            print(f"      Pandoc error: {err}")
            return f"<p>Error converting content: {err}</p>"
        return proc.stdout.decode("utf-8")
    except subprocess.TimeoutExpired:
        print("      Pandoc timed out")
        return "<p>Chapter skipped due to timeout.</p>"


async def _async_render_one(
    semaphore: asyncio.Semaphore,
    browser: Any,
    idx: int,
    window: WindowInfo,
    webp_path: Path,
) -> tuple[int, Path, bool]:
    async with semaphore:
        page = await browser.new_page(device_scale_factor=1)
        try:
            html_page = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>{WINDOW_CSS}</style>
</head>
<body>
<div class="reader-container">
<div class="{html.escape(window.class_name)}">{window.inner_html}</div>
</div>
</body>
</html>"""
            await page.set_content(html_page, wait_until="domcontentloaded")
            png_bytes = await page.screenshot(full_page=True, omit_background=True)
            if not png_bytes:
                return idx, webp_path, False
            if Image is None:
                webp_path.write_bytes(png_bytes)
                return idx, webp_path, True
            img = Image.open(BytesIO(png_bytes))
            bbox = img.getbbox()
            if bbox:
                img = img.crop(bbox)
            img.save(webp_path, "WEBP", quality=90, method=4)
            return idx, webp_path, webp_path.exists() and webp_path.stat().st_size > 0
        except Exception as e:
            print(f"      Screenshot error: {e}")
            return idx, webp_path, False
        finally:
            await page.close()


IMG_SRC_RE = re.compile(r'<img\s+src="([^"]+)"', re.IGNORECASE)


def _resolve_chapter_images(
    chapter_html: str,
    chapter_path: Path,
    book_id: str,
    assets: dict[Path, epub.EpubAsset],
    asset_names: set[str],
) -> str:
    """Resolve bare image filenames to actual files and register as EPUB assets."""
    def replace_img(m: re.Match) -> str:
        src = m.group(1)
        if re.match(r'https?://', src, re.IGNORECASE) or src.startswith('../') or src.startswith('/'):
            return m.group(0)

        clean_src = urllib.parse.unquote(src.split("#", 1)[0].split("?", 1)[0])
        src_path = Path(clean_src.replace("/", "\\"))
        candidates = [
            chapter_path.parent / src_path,
            IMAGES_ROOT / book_id / "illustrations" / src_path,
            IMAGES_ROOT / "dod" / "illustrations" / src_path,
            IMAGES_ROOT / book_id / src_path,
            IMAGES_ROOT / "dod" / src_path,
            IMAGES_ROOT / src_path,
        ]

        image_path = None
        for candidate in candidates:
            if candidate.exists() and candidate.is_file():
                image_path = candidate
                break

        if not image_path:
            print(f"      Warning: image not found: {src}")
            return m.group(0)

        image_path_resolved = image_path.resolve()
        if image_path_resolved not in assets:
            name = epub.unique_asset_name(image_path, src, asset_names)
            assets[image_path_resolved] = epub.EpubAsset(
                source_path=image_path_resolved,
                href=f"Images/{name}",
                media_type=epub.media_type_for(image_path),
            )
        asset = assets[image_path_resolved]
        return f'<img src="../{epub.escape_attr(asset.href)}"'

    return IMG_SRC_RE.sub(replace_img, chapter_html)


def build_debut_part_epub(
    part_chapters: list[Any],
    book_title: str,
    master_meta: dict[str, Any],
    master_content: str,
    part_def: dict[str, Any],
    variant: dict[str, str],
    args: argparse.Namespace,
) -> Path | None:
    """Build a single Debut part EPUB with windows rendered as WebP images."""
    variant_label = variant["label"]
    part_label = part_def["label"]
    full_name = epub.sanitize_filename(book_title)
    output_name = f"{full_name} - {part_label} [{variant_label}]"
    output_name = re.sub(r'[ ,]', '.', output_name).replace('[', '').replace(']', '')
    output_name = re.sub(r'\.+', '.', output_name) + '.epub'
    epub_path = OUTPUT_DIR / output_name

    print(f"  {part_label} ({part_def['range']}): {len(part_chapters)} chapters")
    window_dir = OUTPUT_DIR / "window_images"
    window_dir.mkdir(parents=True, exist_ok=True)

    assets: dict[Path, epub.EpubAsset] = {}
    asset_names: set[str] = set()

    cover_asset: epub.EpubAsset | None = None
    cover_item: epub.EpubItem | None = None
    cover_image_path = IMAGES_ROOT / "dod" / "cover.webp"
    if cover_image_path.exists():
        cover_name = epub.unique_asset_name(cover_image_path, "cover.webp", asset_names)
        cover_asset = epub.EpubAsset(
            source_path=cover_image_path,
            href=f"Images/{cover_name}",
            media_type=epub.media_type_for(cover_image_path),
        )
        assets[cover_image_path] = cover_asset
        cover_body = (
            '<div class="cover-page">'
            f'<img src="../{epub.escape_attr(cover_asset.href)}" alt="Cover" class="cover-image" />'
            "</div>"
        )
        cover_item = epub.EpubItem(
            item_id="cover",
            href="Text/cover.xhtml",
            title="Cover",
            body=cover_body,
        )
        print(f"    Cover: {cover_asset.href}")

    today = dt.date.today()
    pretty_date = f"{today:%B} {today.day}, {today:%Y}"
    mc = master_content.replace("{{DATE}}", pretty_date)

    info_html = convert_chapter_debut(mc)
    items: list[epub.EpubItem] = [
        epub.EpubItem(
            item_id="xhtml0000",
            href="Text/0000_Information.xhtml",
            title="Information",
            body=info_html,
        )
    ]

    @dataclass
    class ChapterInfo:
        position: int
        chapter_path: Path
        meta: Any
        content: str
        title: str
        chapter_html: str
        windows: list[WindowInfo]

    chapter_infos: list[ChapterInfo] = []
    render_tasks: list[tuple[int, WindowInfo, Path]] = []
    window_counter = 0

    for position, chapter in enumerate(part_chapters, start=1):
        short = chapter.title[:60] if chapter.title else chapter.path.stem
        print(f"    [{position}/{len(part_chapters)}] {short}")
        chapter_html = convert_chapter_debut(chapter.content)
        chapter_html = _resolve_chapter_images(chapter_html, chapter.path, "debut", assets, asset_names)
        windows = find_window_divs(chapter_html)
        if windows:
            print(f"      {len(windows)} window(s) to render")
        chapter_infos.append(ChapterInfo(position, chapter.path, chapter.metadata, chapter.content, chapter.title, chapter_html, windows))
        for window in windows:
            webp_path = window_dir / f"window_{window_counter:04d}.webp"
            render_tasks.append((window_counter, window, webp_path))
            window_counter += 1

    total_windows = len(render_tasks)
    print(f"    {len(chapter_infos)} chapters, {total_windows} windows to render")

    render_results: dict[int, tuple[Path, bool]] = {}

    if total_windows > 0:
        num_workers = min(os.cpu_count() or 4, 8)
        print(f"    Rendering {total_windows} windows with {num_workers} workers...")

        async def _render_all() -> dict[int, tuple[Path, bool]]:
            from playwright.async_api import async_playwright

            results: dict[int, tuple[Path, bool]] = {}
            semaphore = asyncio.Semaphore(num_workers)
            async with async_playwright() as ap:
                browser = await ap.chromium.launch()
                coros = [
                    _async_render_one(semaphore, browser, idx, window, webp_path)
                    for idx, window, webp_path in render_tasks
                ]
                done_count = 0
                for coro in asyncio.as_completed(coros):
                    idx, webp_path, success = await coro
                    results[idx] = (webp_path, success)
                    done_count += 1
                    if done_count % 50 == 0 or done_count == total_windows:
                        print(f"      Rendered {done_count}/{total_windows}")
                await browser.close()
            return results

        render_results = asyncio.run(_render_all())
        print(f"    Window rendering complete ({sum(1 for v in render_results.values() if v[1])}/{total_windows} succeeded)")

    window_counter = 0
    for ch in chapter_infos:
        parts: list[str] = []
        last_end = 0
        for window in ch.windows:
            parts.append(ch.chapter_html[last_end:window.start])
            idx = window_counter
            webp_path, success = render_results.get(idx, (None, False))
            if success and webp_path and webp_path.exists():
                webp_name = webp_path.name
                webp_path_resolved = webp_path.resolve()
                if webp_path_resolved not in assets:
                    name = epub.unique_asset_name(webp_path, webp_name, asset_names)
                    assets[webp_path_resolved] = epub.EpubAsset(
                        source_path=webp_path_resolved,
                        href=f"Images/{name}",
                        media_type="image/webp",
                    )
                asset = assets[webp_path_resolved]
                alt_text = html.escape(window.class_name.replace("-", " "))
                parts.append(
                    f'<div class="image-block">'
                    f'<img src="../{epub.escape_attr(asset.href)}" alt="{alt_text}" />'
                    f"</div>"
                )
            else:
                parts.append(f'<div class="{epub.escape_attr(window.class_name)}">{window.inner_html}</div>')
            last_end = window.end
            window_counter += 1
        parts.append(ch.chapter_html[last_end:])
        assembled_html = "".join(parts)

        href = f"Text/{epub.chapter_output_name(ch.position, epub.Chapter(ch.chapter_path, ch.meta, ch.content, ch.title, ch.position, ch.chapter_path.stem))}"
        items.append(epub.EpubItem(
            item_id=f"xhtml{ch.position:04d}",
            href=href,
            title=ch.title,
            body=assembled_html,
        ))

    epub.write_epub(epub_path, book_title, master_meta, items, assets, cover_item, cover_asset)
    print(f"    Done -> {epub_path}")
    return epub_path


def build_debut_epub(args: argparse.Namespace) -> list[Path]:
    """Build per-part Debut EPUBs with windows rendered as WebP images."""
    book_id = "debut"
    chapter_dirs = epub.find_chapter_dirs(book_id)
    if not chapter_dirs:
        print("No chapter directories found for Debut")
        return []

    metadata_path = chapter_dirs[0] / "metadata.md"
    if not metadata_path.exists():
        print(f"No metadata.md at {metadata_path}")
        return []

    master_meta, master_content = epub.load_markdown(metadata_path)
    book_title = epub.metadata_text(master_meta.get("title"), "Debut or Die")
    part_defs = epub.PART_DEFS.get(book_id, [])

    if not part_defs:
        print("No part definitions for Debut")
        return []

    chapters = epub.load_all_chapters(chapter_dirs, args.limit)
    if not chapters:
        print("No chapters found")
        return []

    print(f"Building {book_title}: {len(chapters)} chapters total")

    built: list[Path] = []
    for part_def in part_defs:
        part_chapters = [c for c in chapters if epub.chapter_in_part(c, part_def)]
        if not part_chapters:
            print(f"  {part_def['label']}: no chapters, skipping")
            continue

        epub_path = build_debut_part_epub(
            part_chapters, book_title, master_meta, master_content,
            part_def, {"id": "windows", "label": "Windows"}, args,
        )
        if epub_path:
            built.append(epub_path)

    return built


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build per-part Debut EPUBs with WebP windows.")
    parser.add_argument("--limit", type=int, help="Build only the first N chapters total, useful for testing.")
    return parser.parse_args()


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = parse_args()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    built = build_debut_epub(args)

    if not built:
        print("No EPUBs built.")
        return

    print("\nBuilt EPUBs:")
    for path in built:
        print(f"  {path}")


if __name__ == "__main__":
    main()
