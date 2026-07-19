"""
PDF generator for GSGW chapters.
Combines all fantl chapters into a single PDF using Playwright.

Usage:
    python build_pdf.py                         # all fantl chapters -> GSGW.pdf
    python build_pdf.py chapters/gsgw/fantl/0001.md   # single chapter
    python build_pdf.py --output book.pdf       # custom output name
"""

import re
import sys
import json
import asyncio
import urllib.request
from pathlib import Path

import frontmatter
from playwright.async_api import async_playwright

SCRIPT_DIR = Path(__file__).parent.resolve()
REPO_ROOT = SCRIPT_DIR

CHAPTERS_DIR = REPO_ROOT / "chapters" / "gsgw" / "fantl"
TEMPLATE_PATH = REPO_ROOT / "website/src/lib/reader/template.svelte"
READER_CSS_PATH = REPO_ROOT / "website/src/routes/(reader)/reader.css"

TWITTER_RE = re.compile(
    r'<div class="twitter-embed"[^>]*data-user="([^"]*)"[^>]*data-tweet-id="([^"]*)"[^>]*data-photo="([^"]*)"[^>]*>',
    re.IGNORECASE,
)

sys.path.insert(0, str(REPO_ROOT / "scripts"))
from build_web import convert_chapter


def get_template_styles() -> str:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    return template.split("<style>")[1].split("</style>")[0]


def fetch_tweet_image(user: str, tweet_id: str, photo_idx: str = "1") -> str | None:
    """Fetch tweet image URL from fxtwitter API."""
    try:
        url = f"https://api.fxtwitter.com/{user}/status/{tweet_id}"
        req = urllib.request.Request(url, headers={"User-Agent": "GSGW-Reader-PDF"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        tweet = data.get("tweet") or {}
        photos = (tweet.get("media") or {}).get("photos") or []
        idx = int(photo_idx) - 1
        if 0 <= idx < len(photos):
            return photos[idx].get("url")
        if photos:
            return photos[0].get("url")
    except Exception as e:
        print(f"      Warning: failed to fetch tweet {tweet_id}: {e}")
    return None


def replace_twitter_embeds(html: str) -> str:
    """Replace twitter-embed divs with actual images from fxtwitter API."""
    def repl(m):
        user = m.group(1)
        tweet_id = m.group(2)
        photo_idx = m.group(3)
        img_url = fetch_tweet_image(user, tweet_id, photo_idx)
        if img_url:
            return f'<div style="text-align:center;margin:1.5rem auto;"><img src="{img_url}" style="max-width:100%;border-radius:12px;" /></div>'
        return f'<p style="text-align:center;color:#888;font-size:0.9em;">[Illustration: <a href="https://x.com/{user}/status/{tweet_id}" style="color:#1d9bf0;">view on X</a>]</p>'
    return TWITTER_RE.sub(repl, html)


def remove_first_h1(html: str) -> str:
    """Remove the first H1 from the HTML content."""
    match = re.search(r'<h1[^>]*>.*?</h1>', html, re.DOTALL)
    if match:
        return html[:match.start()] + html[match.end():]
    return html


def chapter_html(chapter_md_path: Path) -> str:
    post = frontmatter.load(chapter_md_path)
    meta = post.metadata
    content = convert_chapter(post.content)
    content = remove_first_h1(content)
    content = replace_twitter_embeds(content)
    title = meta.get("title", chapter_md_path.stem)
    section = meta.get("section", "")
    return f"""
    <div class="chapter-page">
      <div class="chapter-header">
        <span class="section">{section}</span>
        <h1>{title}</h1>
      </div>
      {content}
    </div>
    """


def metadata_html() -> str:
    """Build the metadata page as the first page."""
    meta_path = CHAPTERS_DIR / "metadata.md"
    if not meta_path.exists():
        return ""
    post = frontmatter.load(meta_path)
    content = convert_chapter(post.content)
    return f"""
    <div class="chapter-page metadata-page">
      {content}
    </div>
    """


def build_full_html(chapter_parts: list[str]) -> str:
    reader_css = READER_CSS_PATH.read_text(encoding="utf-8")
    template_css = get_template_styles()
    chapters_body = "\n<hr class='chapter-break' />\n".join(chapter_parts)

    return f"""<!DOCTYPE html>
<html lang="en" data-theme="sunset">
<head>
<meta charset="UTF-8">
<title>GSGW - Fan Translation</title>
<link href="https://fonts.googleapis.com/css2?family=Alegreya:wght@400;500;700;800&family=Caveat:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Alegreya:ital,wght@0,400..800;1,400..800&display=swap');

  :root {{
    --chapter-font: 'Alegreya', serif;
    --chapter-size: 20px;
    --chapter-weight: 450;
    --chapter-lh: 2.2;
    --chapter-indent: 0;
    --chapter-align: left;
    --chapter-hyphens: none;
    --window-bg: #1e1e2e;
    --window-border: #3a3a5c;
    --window-text: #ffffff !important;
    --window-accent: #ff4d00;
  }}

  * {{ margin: 0; padding: 0; box-sizing: border-box; }}

  body {{
    background: #1a1a2e;
    color: #e0e0e0;
    font-family: var(--chapter-font);
    font-size: var(--chapter-size);
    font-weight: var(--chapter-weight);
    line-height: var(--chapter-lh);
    text-align: var(--chapter-align);
    hyphens: var(--chapter-hyphens);
  }}

  .reader-container {{
    max-width: 800px;
    margin: 0 auto;
    padding: 2rem;
    line-height: var(--chapter-lh);
    color: #e0e0e0;
    font-family: var(--chapter-font);
  }}

  .reader-container p {{
    margin: 0.8em 0;
    line-height: var(--chapter-lh);
  }}

  .chapter-page {{
    page-break-before: always;
    padding-top: 1rem;
  }}

  .chapter-page:first-child {{
    page-break-before: avoid;
  }}

  .metadata-page {{
    page-break-after: always;
  }}

  .chapter-header {{
    text-align: center;
    padding: 2rem 0 1rem;
    border-bottom: 1px solid rgba(255,255,255,0.1);
    margin-bottom: 2rem;
  }}

  .chapter-header h1 {{
    font-size: 1.5rem;
    font-weight: 700;
    color: #fb8462;
    margin-bottom: 0.25rem;
  }}

  .chapter-header .section {{
    font-size: 0.85rem;
    opacity: 0.5;
    font-family: monospace;
  }}

  .chapter-break {{
    border: none;
    border-top: 1px solid rgba(255,255,255,0.15);
    margin: 3rem 0;
  }}

  {reader_css}
  {template_css}
</style>
</head>
<body>
  <div class="reader-container">
    {chapters_body}
  </div>
</body>
</html>"""


async def generate_pdf(html: str, output_path: Path):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.set_content(html, wait_until="networkidle")
        await page.pdf(
            path=str(output_path),
            format="A4",
            margin={"top": "1in", "bottom": "1in", "left": "0.8in", "right": "0.8in"},
            print_background=True,
        )
        await browser.close()
    print(f"PDF saved to {output_path}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Build PDF from GSGW chapters.")
    parser.add_argument("chapter", nargs="?", help="Single chapter .md file to build.")
    parser.add_argument("-o", "--output", help="Output PDF file path.")
    parsed = parser.parse_args()

    output_path = Path(parsed.output) if parsed.output else None
    single_chapter = Path(parsed.chapter) if parsed.chapter else None

    if single_chapter:
        if not single_chapter.is_absolute():
            single_chapter = REPO_ROOT / single_chapter
        if not single_chapter.exists():
            print(f"Chapter not found: {single_chapter}")
            sys.exit(1)
        if not output_path:
            output_path = Path.cwd() / f"{single_chapter.stem}.pdf"
        chapter_files = [single_chapter]
    else:
        chapter_files = sorted(f for f in CHAPTERS_DIR.glob("*.md") if f.name != "metadata.md")
        if not output_path:
            output_path = Path.cwd() / "GSGW.pdf"

    if not chapter_files:
        print("No chapters found.")
        sys.exit(1)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Building HTML for {len(chapter_files)} chapter(s)...")
    parts = []

    if not single_chapter:
        meta_html = metadata_html()
        if meta_html:
            parts.append(meta_html)

    for idx, path in enumerate(chapter_files, 1):
        print(f"  [{idx}/{len(chapter_files)}] {path.name}")
        parts.append(chapter_html(path))

    print("Rendering PDF with Playwright...")
    asyncio.run(generate_pdf(build_full_html(parts), output_path))
    print(f"Done: {output_path}")


if __name__ == "__main__":
    main()
