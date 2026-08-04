from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import json
import posixpath
import re
import sys
import urllib.parse
import urllib.request
import uuid
import zipfile
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any

try:
    from PIL import Image
except Exception:  # Pillow is optional unless Twitter images need conversion.
    Image = None

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None


SCRIPT_DIR = Path(__file__).parent.resolve()
REPO_ROOT = SCRIPT_DIR.parent
CHAPTERS_ROOT = REPO_ROOT / "chapters"
IMAGES_ROOT = REPO_ROOT / "images"
CSS_PATH = SCRIPT_DIR / "epub.css"

OUTPUT_DIR = SCRIPT_DIR / "epub"
TWITTER_IMG_DIR = OUTPUT_DIR / "twitter_images"
TWEET_CACHE_PATH = TWITTER_IMG_DIR / "cache.json"

EPUB_SOURCE_URL = "https://ireum.pages.dev"

UA = "GSGW-Reader-EPUB/2.0"

TWITTER_RE = re.compile(
    r"https?://(?:x|twitter)\.com/([A-Za-z0-9_]+)/status/(\d+)"
    r"(?:/photo/(\d+))?(?:\?[^\s<>\"')]+)?",
    re.IGNORECASE,
)

IMAGE_RE = re.compile(r"!\[([\s\S]*?)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
LINK_RE = re.compile(r"(?<!!)\[([^\]]+)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")


# ── Part & variant definitions ──────────────────────────────────────────

PART_DEFS: dict[str, list[dict[str, Any]]] = {
    "gsgw": [
        {"id": "part1", "label": "Part 1", "range": "Chapters 0–208", "max_index": 208},
        {"id": "part2", "label": "Part 2", "range": "Chapters 209–371", "min_index": 209, "max_index": 371},
        {"id": "part3", "label": "Part 3", "range": "Chapter 372 – Current", "min_index": 372},
    ],
    "debut": [
        {"id": "part1", "label": "Part 1", "range": "Chapters 1–147", "max_index": 146},
        {"id": "part2", "label": "Part 2", "range": "Chapters 148–364", "min_index": 147, "max_index": 363},
        {"id": "part3", "label": "Part 3", "range": "Chapters 365–451", "min_index": 364, "max_index": 450},
        {"id": "part4", "label": "Part 4", "range": "Chapters 452–644", "min_index": 451},
    ],
}

VARIANTS: dict[str, list[dict[str, str]]] = {
    "gsgw": [
        {"id": "plaintext", "label": "PlainText"},
        {"id": "windows", "label": "Windows"},
    ],
    "debut": [
        {"id": "windows", "label": "Windows"},
    ],
}

BOOK_SHORT_NAME: dict[str, str] = {
    "gsgw": "Ghost.Story",
    "debut": "Debut.or.Die",
}


# ── Window-rendering code (shared with build_debut_epub.py) ────────────

@dataclass
class WindowInfo:
    start: int
    end: int
    class_name: str
    inner_html: str
    width: int = 430


WINDOW_CSS_FALLBACK = """
:root {
  --window-bg: #1e1e2e;
  --window-border: #3a3a5c;
  --window-text: #ffffff;
  --window-accent: #ff4d00;
}

* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  background: transparent;
  font-family: 'Inter', system-ui, -apple-system, sans-serif;
  line-height: 1.6;
  color: #fff;
}

.reader-container {
  max-width: 600px;
  margin: 0 auto;
  padding: 3rem 2rem;
  color: #fff;
  font-family: 'Inter', system-ui, sans-serif;
}

p { margin: 0.5em 0; line-height: 1.6; }
strong, b { font-weight: 700; }
em, i { font-style: italic; }
del { text-decoration: line-through; }
.underline { text-decoration: underline; }

.debut-window {
  position: relative;
  width: min(430px, 90%);
  margin: 2rem auto;
  padding: 2rem 2.5rem;
  color: #fff !important;
  text-align: center;
  background: #1e1e30;
  border: 2px solid rgba(255,255,255,.85);
  box-shadow: 0 0 10px rgba(255,255,255,.45), 0 0 25px rgba(170,210,255,.25), inset 0 0 25px rgba(255,255,255,.08);
}
.debut-window::before { content: ""; position: absolute; inset: 8px; border: 1px solid rgba(255,255,255,.55); pointer-events: none; }
.debut-window p { color: #fff; }
.debut-window .debut-window-label { display: block; padding: .15rem 1.2rem; background: rgba(255,255,255,.25); border-radius: 4px; font-size: .85em; text-align: center; width: fit-content; margin: .3rem auto; }
.debut-window .debut-window-title { position: absolute; top: -.6rem; left: 50%; transform: translateX(-50%); padding: .05rem .9rem; font-size: .75em; background: #1e1e30; border: 2px solid rgba(255,255,255,.8); text-transform: uppercase; letter-spacing: .08em; font-weight: 700; text-align: center; white-space: nowrap; box-shadow: 0 0 10px rgba(255,255,255,.4), inset 0 0 8px rgba(255,255,255,.08); }

.debut-alert {
  position: relative;
  width: min(430px, 95%);
  margin: 2rem auto;
  padding: 2rem 2.5rem;
  color: #fff !important;
  text-align: left;
  background: #b01030;
  border: 2px solid rgba(255,120,140,.9);
  box-shadow: 0 0 10px rgba(255,50,80,.6), 0 0 25px rgba(255,50,80,.3), inset 0 0 25px rgba(255,50,80,.12);
}
.debut-alert::before { content: ""; position: absolute; inset: 8px; border: 1px solid rgba(255,120,140,.55); pointer-events: none; }
.debut-alert p { color: #fff; }
.debut-alert-center { text-align: center; }

.debut-achievement {
  position: relative;
  width: min(430px, 90%);
  margin: 2rem auto;
  padding: 2rem 2.5rem;
  color: #fff !important;
  text-align: center;
  background: #234670;
  border: 2px solid rgba(255,255,255,.85);
  box-shadow: 0 0 10px rgba(100,160,255,.45), 0 0 25px rgba(100,160,255,.25), inset 0 0 25px rgba(100,160,255,.08);
}
.debut-achievement::before { content: ""; position: absolute; inset: 8px; border: 1px solid rgba(255,255,255,.4); pointer-events: none; }
.debut-achievement p { color: #fff; }
.debut-achievement-sub { display: block; padding: .15rem .75rem; margin: .3rem auto; background: rgba(255,255,255,.25); font-size: .85em; text-align: center; width: fit-content; }
.debut-achievement-list { border: 4px solid rgba(255,255,255,.6); background: #305582; font-size: .95em; display: block; margin: .3rem auto; width: fit-content; text-align: center; box-shadow: 0 0 12px rgba(100,160,255,.35); }
.debut-achievement-list-item { padding: .5rem 1.25rem; }
.debut-achievement-list-divider { height: 1px; background: linear-gradient(to right, transparent, rgba(100,160,255,.5) 20%, rgba(100,160,255,.5) 80%, transparent); }
.debut-achievement-sub-left, .debut-achievement-sub-right, .alert-sub-left, .alert-sub-right {
  --border: rgba(255,255,255,.85); --outline: rgba(180,220,255,.35);
  position: relative; display: inline-block; padding: .35rem 1.25rem; font-size: .9em; color: white;
  background: linear-gradient(180deg, #6fa8ff 0%, #4f86db 40%, #3568b7 100%);
  border: 3px solid var(--border); clip-path: polygon(10px 0, 100% 0, 100% calc(100% - 10px), calc(100% - 10px) 100%, 0 100%, 0 10px);
  box-shadow: 0 0 12px var(--outline), inset 0 0 6px rgba(255,255,255,.1);
}
.alert-sub-left, .alert-sub-right { --border: rgba(255,120,140,.9); --outline: rgba(255,50,80,.35); background: linear-gradient(180deg, #d03050 0%, #b01030 40%, #8a0a25 100%); }
.alert-sub-left { margin-right: .5rem; }
.alert-sub-right { margin-left: .5rem; }
.debut-achievement-sub-left::before, .debut-achievement-sub-right::before, .alert-sub-left::before, .alert-sub-right::before {
  content: ""; position: absolute; left: -7px; top: -7px; width: 22px; height: 22px; border-top: 3px solid var(--border); border-left: 3px solid var(--border); opacity: .9;
}
.debut-achievement-sub-left::after, .debut-achievement-sub-right::after, .alert-sub-left::after, .alert-sub-right::after {
  content: ""; position: absolute; right: -7px; bottom: -7px; width: 22px; height: 22px; border-right: 3px solid var(--border); border-bottom: 3px solid var(--border); opacity: .9;
}

.sms-window {
  position: relative; width: min(430px, 95%); margin: 2rem auto; padding: 1rem 1rem;
  background: var(--window-bg); color: #fff !important; text-align: left;
  border: 2px solid #555; border-radius: 12px; box-shadow: 0 0 0 6px #444, 0 0 0 8px #555;
  overflow: hidden; display: flex; flex-direction: column; gap: 6px;
}
.sms-bubble { max-width: 80%; padding: 8px 14px; border-radius: 14px; font-size: 0.95em; line-height: 1.45; position: relative; z-index: 2; word-wrap: break-word; }
.sms-left { align-self: flex-start; background: #3a3a4e; border-bottom-left-radius: 4px; }
.sms-right { align-self: flex-end; background: #eae391; color: #222; border-bottom-right-radius: 4px; }
.sms-center { align-self: center; background: transparent; font-style: italic; opacity: 0.8; font-size: 0.85em; }

.alert-window {
  position: relative; width: min(430px, 95%); margin: 2rem auto; padding: 0;
  background: #fff; color: #222 !important; text-align: left;
  border: 2px solid #555; border-radius: 12px; box-shadow: 0 0 0 6px #bbb, 0 0 0 8px #555; overflow: hidden;
}
.alert-window p { color: #222; }
.comment-post-header { padding: 1.25rem 1.5rem 0.75rem; background: transparent; border-bottom: 1px solid #d0d0d0; }
.comment-post-title { text-align: left; font-size: 1.2em; font-weight: 700; color: #111; margin-bottom: 0.2rem; }
.comment-post-desc { text-align: justify; font-size: 0.82em; color: #777; font-style: italic; }
.comment-section { padding: 0.5rem 1.25rem 1rem; }
.comment { padding: 0.5rem 0.6rem; margin: 0.7rem 0; background: #eee; border: 1px solid #ccc; border-radius: 7px; font-size: 0.92em; color: #333; line-height: 1.5; }
.comment-reply { display: flex; align-items: flex-start; gap: 0.35rem; padding: 0.35rem 0.6rem; border-radius: 6px; font-size: 0.88em; margin-top: 0.5rem; }
.comment-reply.depth-1 { margin-left: 1.2rem; background: #d2d2d2; border: 1px solid #bbb; }
.comment-reply.depth-2 { margin-left: 2rem; background: #c8c8c8; border: 1px solid #aaa; }
.comment-reply.depth-3 { margin-left: 2.8rem; background: #bebebe; border: 1px solid #999; }
.reply-icon { flex-shrink: 0; font-size: 0.7em; color: #999; line-height: 1.6; }
.reply-body { color: #444; text-align: justify; }

.wiki-window {
  margin: 2.5rem auto; background: linear-gradient(145deg, #1c1c30, #1e1e2e);
  border: 1px solid rgba(140, 160, 255, 0.1); border-radius: 10px; max-width: 98%;
  position: relative; box-shadow: 0 4px 24px rgba(0,0,0,0.4); padding: 1em 1em 0.75em; text-align: left; color: var(--window-text) !important;
}
.wiki-window::before { content: "\\2014  \\25A1  X"; display: flex; justify-content: flex-end; background: var(--window-border); color: #ffffff; padding: 0.375em 0.875em; font-family: monospace; font-size: 1em; letter-spacing: 0.375em; margin: -1em -1em 0.75em; border-bottom: 1px solid var(--window-border); border-radius: 10px 10px 0 0; }
.wiki-window p { color: var(--window-text) !important; margin: 0.6em 0; line-height: 1.7; text-align: left; }
.wiki-window:not(.no-meta) p:first-of-type { font-size: 0.75em; opacity: 0.5; text-align: right; margin-bottom: 0.5em; letter-spacing: 0.05em; }
.wiki-window strong, .wiki-window b { color: inherit; font-weight: 700; }
.wiki-window p strong:only-child, .wiki-window p strong:first-child:not(b strong) { display: block; font-size: 1.2em; letter-spacing: 0.03em; margin: 0.5em 0 0.4em; color: rgba(200, 215, 255, 0.9); }

.record-window {
  margin: 2.5rem auto; background: linear-gradient(145deg, #121a3a, #1d2350);
  border: 1px solid rgba(120, 180, 255, 0.1); border-radius: 10px; max-width: 98%;
  position: relative; box-shadow: 0 4px 24px rgba(0,0,0,0.4); padding: 1em 1em 0.75em; text-align: left; color: #ffffff !important;
}
.record-window::before { content: "\\2014  \\25A1  X"; display: flex; justify-content: flex-end; background: rgba(0,0,0,0.25); color: #ffffff; padding: 0.375em 0.875em; font-family: monospace; font-size: 1em; letter-spacing: 0.375em; margin: -1em -1em 0.75em; border-bottom: 1px solid rgba(255,255,255,0.1); border-radius: 10px 10px 0 0; }
.record-window p { color: #ffffff !important; margin: 0.6em 0; line-height: 1.7; text-align: left; }
.record-window:not(.no-meta) p:first-of-type { font-size: 0.75em; opacity: 0.5; text-align: right; margin-bottom: 0.5em; letter-spacing: 0.05em; }
.record-window strong, .record-window b { color: inherit; font-weight: 700; }
.record-window p strong:only-child, .record-window p strong:first-child:not(b strong) { display: block; font-size: 1.2em; letter-spacing: 0.03em; margin: 0.5em 0 0.4em; color: rgba(160, 210, 255, 0.9); }

.plain-window {
  margin: 2.5rem auto; background: linear-gradient(145deg, #1c1c30, #1e1e2e);
  border: 1px solid rgba(140, 160, 255, 0.1); border-radius: 10px; max-width: 98%;
  position: relative; box-shadow: 0 4px 24px rgba(0,0,0,0.4); padding: 1.5em 2em 1em; text-align: left; color: var(--window-text) !important;
}
.plain-window p { color: var(--window-text) !important; margin: 0.6em 0; line-height: 1.7; text-align: left; }

.bare-window {
  margin: 2.5rem auto; background: transparent; border: 1px solid rgba(220, 220, 220, 0.55);
  border-radius: 4px; max-width: 90%; padding: 1.5em 2em; text-align: center;
  position: relative; box-shadow: 0 0 0 1px rgba(240, 240, 240, 0.05) inset, 0 4px 24px rgba(0,0,0,0.35);
  color: var(--window-text) !important;
}
.bare-window p { color: var(--window-text) !important; margin: 0.5em 0; line-height: 1.7; text-align: center; }

.followup-window {
  margin: 2.5rem auto; background: linear-gradient(145deg, #121a3a, #1d2350);
  border: 1px solid rgba(120, 180, 255, 0.1); border-radius: 10px; max-width: 98%;
  position: relative; box-shadow: 0 4px 24px rgba(0,0,0,0.4); padding: 1.5em 2em 1em; text-align: left; color: #ffffff !important;
}
.followup-window p { color: #ffffff !important; margin: 0.6em 0; line-height: 1.7; text-align: left; }

.note-window {
  margin: 2.5rem auto; background: #fefce8; border: 1px solid #e6dec0; border-radius: 4px;
  max-width: 98%; position: relative; box-shadow: -4px 4px 0 #d4c060, 0 4px 24px rgba(0,0,0,0.12);
  padding: 1em 1.25em 0.75em; text-align: left; overflow: hidden;
}
.note-window::before { content: ""; display: block; background: #edd44d; height: 0.875em; margin: -1em -1.25em 0.75em; border-radius: 4px 4px 0 0; }
.note-window p { color: #000000; margin: 0.8em 0; line-height: 1.7; text-align: left; }
.note-window:not(.no-meta) p:first-of-type { color: #4a6fa5; font-size: 1.35em; font-weight: 600; }

.sticky-window {
  margin: 2.5rem auto; background: #fefce8; border: 1px solid #e6dec0; border-radius: 2px;
  max-width: 25em; min-height: 15.625em; display: flex; flex-direction: column; justify-content: center; align-items: center;
  position: relative; box-shadow: -3px 3px 0 #d4c060, 0 4px 24px rgba(0,0,0,0.12);
  padding: 1.5em; text-align: center; color: #000000 !important;
}
.sticky-window p { color: #000000 !important; margin: 0.3em 0; line-height: 1.7; text-align: center; }

.black-window {
  margin: 2.5rem auto; background: #000000; border: 1px solid #333; border-radius: 4px;
  max-width: 88%; position: relative; box-shadow: 0 0 20px rgba(0,0,0,0.6);
  padding: 1.5em 2em 1em; text-align: center; font-weight: 700; font-size: 1.3em;
  color: #ffffff !important; text-shadow: 0 0 10px rgba(255,255,255,0.7), 0 0 20px rgba(255,255,255,0.4);
  background-image: repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(255,255,255,0.03) 2px, rgba(255,255,255,0.03) 4px);
}
.black-window p { color: #ffffff; margin: 0.8em 0; line-height: 1.6; text-align: center; }
.black-window p, .black-window a, .black-window strong, .black-window b, .black-window em, .black-window i, .black-window li, .black-window h1, .black-window h2, .black-window h3, .black-window h4, .black-window h5, .black-window h6, .black-window code, .black-window blockquote { color: #ffffff !important; }

.system-window {
  margin: 2.5rem auto; background: #1a1a1a; border: 1px solid #444; border-radius: 4px;
  max-width: 88%; position: relative; box-shadow: 0 0 20px rgba(0,0,0,0.6);
  padding: 1.5em 2em 1em; text-align: center; font-weight: 700; color: #ffffff !important;
}
.system-window::before { content: ''; position: absolute; inset: 8px; box-shadow: inset 0 0 0 1px #888, inset 0 0 0 5px #888; pointer-events: none; }
.system-window p { color: #ffffff !important; margin: 0.8em 0; line-height: 1.6; text-align: center; }
.system-window:not(.no-fl-dividers) > p:first-of-type {
  padding: 0.75em 0; font-size: 1.25em;
  background-image: linear-gradient(90deg, transparent, #888, transparent), linear-gradient(90deg, transparent, #888, transparent);
  background-repeat: no-repeat; background-size: 80% 1px; background-position: center top, center bottom;
}

.braun-screen {
  margin: 2.5rem auto; background: radial-gradient(ellipse at center, #050504 0%, #030302 60%, #020201 100%);
  border: 10px solid #4f4642; border-radius: 36px; max-width: 90%;
  position: relative; box-shadow: 0 0 30px rgba(0,0,0,0.8), inset 0 0 60px rgba(0,0,0,0.3);
  padding: 6em 0.5em; text-align: center; font-family: 'Courier New', Courier, monospace;
  font-size: 2em; color: #ffffff !important; text-shadow: 0 0 5px rgba(255,255,255,0.4), 0 0 15px rgba(255,255,255,0.15); overflow: hidden;
}
.braun-screen::before {
  content: ''; position: absolute; inset: 0; border-radius: 22px;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='150' height='150'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='150' height='150' filter='url(%23n)' opacity='0.8'/%3E%3C/svg%3E");
  background-repeat: repeat; background-size: 150px 150px; opacity: 0.20; pointer-events: none; z-index: 2; mix-blend-mode: screen;
}
.braun-screen::after {
  content: ''; position: absolute; inset: 0; border-radius: 22px;
  background: repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(255,255,255,0.02) 2px, rgba(255,255,255,0.02) 4px), radial-gradient(ellipse at center, transparent 50%, rgba(0,0,0,0.5) 100%);
  pointer-events: none; z-index: 1;
}
.braun-screen p { color: #ffffff; margin: 0.8em 0; line-height: 1.6; text-align: center; position: relative; z-index: 3; }

.window-small { font-size: 0.85em; }
.text-large { font-size: 1.04em; font-weight: bold; }
.text-large-centered { display: block; text-align: center; font-size: 1.35em; font-weight: bold; }
.text-red { color: #ff4d00; font-weight: bold; }
.text-blue { color: #2244fa; font-weight: bold; }
.text-yellow { color: #fff700; font-weight: bold; }
.text-magenta { color: #d946ef; font-weight: bold; }
.text-green { color: #22c55e; font-weight: bold; }
.text-orange { color: #fb8246; font-weight: bold; }
.text-light-purple { color: #a78bfa; font-weight: bold; }
.text-cyan { color: #22d3ee; font-weight: bold; }
.text-sub { font-size: 0.75em; opacity: 0.6; }
.text-faded { opacity: 0.35; }
.mono { font-family: "Courier New", Courier, monospace; font-weight: bold; }
.mono-left { display: block; text-align: left; }
.mono-center { display: block; text-align: center; }
.mono-right { display: block; text-align: right; }
.align-left { display: block; text-align: left; }
.align-center { display: block; text-align: center; }
.align-right { display: block; text-align: right; }
.handwritten { font-family: 'Caveat', cursive; font-size: 1.2em; }
.contaminated { font-family: 'Comic Sans MS', cursive; }
.eb-garamond { font-family: 'EB Garamond', serif; }
.glitch-text { opacity: 0.8; text-shadow: 1px 0 0 #cc2200, -1px 0 0 #2255cc; }
.glitch-subtle { opacity: 0.9; text-shadow: 0.5px 0.5px 0 #777; }
.shake { display: inline-block; font-weight: 700; }
.aurora-text {
  display: inline-block; font-weight: 800;
  background: linear-gradient(135deg, #00c2ff, #33ff8c, #ffc640, #e54cff, #00c2ff);
  background-size: 300% 300%; background-position: 50% 50%;
  -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
  filter: drop-shadow(0 0 6px rgba(0,194,255,0.2)) drop-shadow(0 0 15px rgba(229,76,255,0.1));
}
.hex-aurora {
  display: inline-block; font-weight: 800;
  background: linear-gradient(135deg, var(--ha-c1) 0%, var(--ha-c2) 25%, var(--ha-c3) 50%, var(--ha-c2) 75%, var(--ha-c1) 100%);
  background-size: 300% 300%; background-position: 50% 50%;
  -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
  filter: drop-shadow(0 0 6px var(--ha-c2)) drop-shadow(0 0 15px var(--ha-c3));
}
.hex-aurora-static {
  display: inline-block; font-weight: 800;
  background: linear-gradient(135deg, var(--ha-c1) 0%, var(--ha-c2) 50%, var(--ha-c3) 100%);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
  filter: drop-shadow(0 0 6px var(--ha-c2));
}
.hex-aurora-up {
  display: inline-block; font-weight: 800;
  background: linear-gradient(135deg, var(--ha-c1) 0%, var(--ha-c2) 25%, var(--ha-c3) 50%, var(--ha-c2) 75%, var(--ha-c1) 100%);
  background-size: 300% 300%; background-position: 50% 50%;
  -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
  filter: drop-shadow(0 0 6px var(--ha-c2)) drop-shadow(0 0 15px var(--ha-c3));
}
.hex-aurora-up-static {
  display: inline-block; font-weight: 800;
  background: linear-gradient(135deg, var(--ha-c1) 0%, var(--ha-c2) 50%, var(--ha-c3) 100%);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
  filter: drop-shadow(0 0 6px var(--ha-c2));
}
.hex-outline {
  display: inline-block; font-weight: 700; letter-spacing: 0.2em;
  -webkit-text-stroke: 1.5px var(--hxo-color); text-stroke: 1.5px var(--hxo-color);
  color: var(--hxo-color);
  text-shadow: .08em 0 0 var(--hxo-color), -.08em 0 0 var(--hxo-color), 0 .08em 0 var(--hxo-color), 0 -.08em 0 var(--hxo-color), .06em .06em 0 var(--hxo-color), -.06em .06em 0 var(--hxo-color), .06em -.06em 0 var(--hxo-color), -.06em -.06em 0 var(--hxo-color);
}
.smoke-text {
  font-weight: 700; letter-spacing: 0.2em; color: black;
  text-shadow: .06em 0 0 rgba(255,200,0,.9), -.06em 0 0 rgba(255,200,0,.9), 0 .06em 0 rgba(255,200,0,.9), 0 -.06em 0 rgba(255,200,0,.9), .04em .04em 0 rgba(255,200,0,.9), -.04em .04em 0 rgba(255,200,0,.9), .04em -.04em 0 rgba(255,200,0,.9), -.04em -.04em 0 rgba(255,200,0,.9), .08em 0 0 rgba(255,200,0,.9), -.08em 0 0 rgba(255,200,0,.9), 0 .08em 0 rgba(255,200,0,.9), 0 -.08em 0 rgba(255,200,0,.9);
}
.gold-text {
  position: relative; display: inline-block; font-weight: 800;
  background: linear-gradient(90deg, transparent 25%, rgba(255,255,255,0.3) 46%, rgba(255,255,255,0.5) 50%, rgba(255,255,255,0.3) 54%, transparent 75%), repeating-linear-gradient(65deg, transparent 0px, transparent 3px, rgba(255,215,100,0.08) 3px, rgba(255,215,100,0.08) 5px), #E8C24A;
  background-size: 200px 100%, auto, auto;
  -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
  -webkit-text-stroke: 1.2px #5b3912; text-stroke: 1.2px #5b3912;
  filter: drop-shadow(0 0 5px rgba(212,160,23,0.35));
}
.silver-text {
  position: relative; display: inline-block; font-weight: 800;
  background: linear-gradient(90deg, transparent 25%, rgba(255,255,255,0.3) 46%, rgba(255,255,255,0.5) 50%, rgba(255,255,255,0.3) 54%, transparent 75%), repeating-linear-gradient(65deg, transparent 0px, transparent 3px, rgba(192,192,192,0.08) 3px, rgba(192,192,192,0.08) 5px), #C0C0C0;
  background-size: 200px 100%, auto, auto;
  -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
  -webkit-text-stroke: 1.2px #666; text-stroke: 1.2px #666;
  filter: drop-shadow(0 0 5px rgba(160,160,160,0.35));
}
.sparkle-text { position: relative; display: inline-block; }
.moon-text {
  position: relative; display: inline-block; font-weight: 800;
  background: linear-gradient(90deg, transparent 25%, rgba(255,255,255,0.35) 46%, rgba(255,255,255,0.55) 50%, rgba(255,255,255,0.35) 54%, transparent 75%), repeating-linear-gradient(65deg, transparent 0px, transparent 3px, rgba(180,220,255,0.08) 3px, rgba(180,220,255,0.08) 5px), linear-gradient(135deg, #8ab8e0 0%, #c0dff5 35%, #e8f4ff 65%, #ffffff 100%);
  background-size: 200px 100%, auto, auto;
  -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
  -webkit-text-stroke: 1.2px #6aacdf; text-stroke: 1.2px #6aacdf;
  filter: drop-shadow(0 0 5px rgba(100,180,230,0.35));
}
"""

READER_CSS_PATH = REPO_ROOT / "website" / "src" / "routes" / "(reader)" / "reader.css"
READER_WINDOWS_CSS_PATH = REPO_ROOT / "website" / "src" / "lib" / "reader" / "reader-windows.css"

WINDOW_CSS_PREAMBLE = """\
/* Screenshot page base: mirrors the website reader so window images match 1:1. */
* { box-sizing: border-box; margin: 0; padding: 0; }
:root {
  --window-bg: oklch(0.2 0.02 280);
  --window-border: oklch(0.28 0.03 280);
  --window-text: oklch(0.95 0 0);
  --window-accent: oklch(0.55 0.22 30);
  --bc: oklch(0.95 0 0);
  --chapter-font: 'Alegreya', 'Iowan Old Style', 'Palatino Linotype', Georgia, serif;
  --chapter-size: 18px;
  --chapter-weight: 450;
  --chapter-lh: 1.8;
  --chapter-indent: 0;
  --chapter-align: left;
  --chapter-hyphens: none;
}
body {
  background: transparent;
  color: oklch(0.95 0 0);
  font-family: var(--chapter-font, 'Inter', system-ui, sans-serif);
  font-size: var(--chapter-size, 18px);
  font-weight: var(--chapter-weight, 450);
  line-height: var(--chapter-lh, 1.8);
}
"""


def build_screenshot_css() -> str:
    """Assemble the CSS used to screenshot windows, matching the website 1:1.

    Uses the site's real reader stylesheets (reader.css + reader-windows.css)
    so the rendered window images are identical to the website. Falls back to
    the embedded WINDOW_CSS_FALLBACK if the website files are unavailable.
    """
    try:
        reader_css = READER_CSS_PATH.read_text(encoding="utf-8")
        windows_css = READER_WINDOWS_CSS_PATH.read_text(encoding="utf-8")
    except OSError:
        return WINDOW_CSS_FALLBACK
    return "\n".join((WINDOW_CSS_PREAMBLE, reader_css, windows_css))


WINDOW_CSS = build_screenshot_css()


ALL_WINDOW_CLASSES = (
    "debut-window(?!-)|debut-alert(?!-)|debut-achievement(?!-)|sms-window|alert-window|"
    "wiki-window|record-window|black-window|system-window|plain-window|bare-window|"
    "followup-window|note-window|sticky-window|braun-screen"
)

WINDOW_CLASS_RE = re.compile(
    rf'<div class="((?:{ALL_WINDOW_CLASSES})[^"]*)">'
)


def find_window_divs(html_content: str) -> list[WindowInfo]:
    results: list[WindowInfo] = []
    for match in WINDOW_CLASS_RE.finditer(html_content):
        class_name = match.group(1)
        start = match.start()
        depth = 1
        pos = match.end()
        while depth > 0 and pos < len(html_content):
            next_open = html_content.find("<div", pos)
            next_close = html_content.find("</div>", pos)
            if next_close == -1:
                break
            if next_open != -1 and next_open < next_close:
                depth += 1
                pos = next_open + 4
            else:
                depth -= 1
                if depth == 0:
                    end = next_close + 6
                    inner = html_content[match.end():next_close]
                    width = 430
                    if "sms-window" in class_name or "alert-window" in class_name:
                        width = 430
                    results.append(WindowInfo(start, end, class_name, inner, width))
                pos = next_close + 6
    return results


def render_window_to_webp(
    page: Any,
    window: WindowInfo,
    output_path: Path,
) -> bool:
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
    try:
        page.set_content(html_page, wait_until="domcontentloaded")
        png_bytes = page.screenshot(full_page=True, omit_background=True)
        if not png_bytes:
            return False
        if Image is None:
            output_path.write_bytes(png_bytes)
            return True
        img = Image.open(BytesIO(png_bytes))
        bbox = img.getbbox()
        if bbox:
            img = img.crop(bbox)
        img.save(output_path, "WEBP", quality=85, method=4)
        return output_path.exists() and output_path.stat().st_size > 0
    except Exception as e:
        print(f"      Screenshot error: {e}")
        return False


@dataclass
class EpubAsset:
    source_path: Path
    href: str
    media_type: str


@dataclass
class Chapter:
    path: Path
    metadata: dict[str, Any]
    content: str
    title: str
    index: int
    slug: str


@dataclass
class EpubItem:
    item_id: str
    href: str
    title: str
    body: str


class RenderContext:
    def __init__(
        self,
        book_id: str,
        chapter_path: Path,
        assets: dict[Path, EpubAsset],
        asset_names: set[str],
        tweet_cache: dict[str, Any],
        fetch_twitter: bool,
    ) -> None:
        self.book_id = book_id
        self.chapter_path = chapter_path
        self.assets = assets
        self.asset_names = asset_names
        self.tweet_cache = tweet_cache
        self.fetch_twitter = fetch_twitter


def normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    text = normalize_newlines(text)
    if not text.startswith("---\n"):
        return {}, text

    match = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.DOTALL)
    if not match:
        return {}, text

    return parse_simple_yaml(match.group(1)), match.group(2)


def split_key_value(line: str) -> tuple[str, str] | None:
    if ":" not in line:
        return None
    key, value = line.split(":", 1)
    return key.strip(), value.strip()


def parse_scalar(value: str) -> Any:
    value = value.strip()
    if value == "":
        return ""
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if value in {"null", "Null", "~"}:
        return None

    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        value = value[1:-1]
        return (
            value.replace(r"\"", '"')
            .replace(r"\'", "'")
            .replace(r"\\", "\\")
        )

    if re.fullmatch(r"-?\d+", value):
        try:
            return int(value)
        except ValueError:
            pass

    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [parse_scalar(part.strip()) for part in inner.split(",")]

    return value


def parse_indented_block(lines: list[str], start: int) -> tuple[Any, int]:
    items: list[Any] = []
    mapping: dict[str, Any] = {}
    i = start

    while i < len(lines):
        raw = lines[i]
        if not raw.strip() or raw.lstrip().startswith("#"):
            i += 1
            continue
        if raw == raw.lstrip():
            break

        stripped = raw.strip()
        if stripped.startswith("- "):
            item_text = stripped[2:].strip()
            key_value = split_key_value(item_text)
            if key_value:
                key, value = key_value
                item: dict[str, Any] = {key: parse_scalar(value)}
                i += 1
                while i < len(lines):
                    next_raw = lines[i]
                    if not next_raw.strip() or next_raw.lstrip().startswith("#"):
                        i += 1
                        continue
                    next_stripped = next_raw.strip()
                    if next_raw == next_raw.lstrip() or next_stripped.startswith("- "):
                        break
                    nested = split_key_value(next_stripped)
                    if nested:
                        nested_key, nested_value = nested
                        item[nested_key] = parse_scalar(nested_value)
                    i += 1
                items.append(item)
                continue

            items.append(parse_scalar(item_text))
            i += 1
            continue

        key_value = split_key_value(stripped)
        if key_value:
            key, value = key_value
            mapping[key] = parse_scalar(value)
        i += 1

    return (items if items else mapping), i


def parse_simple_yaml(raw: str) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    lines = raw.splitlines()
    i = 0

    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        if line != line.lstrip():
            i += 1
            continue

        key_value = split_key_value(line)
        if not key_value:
            i += 1
            continue

        key, value = key_value
        if value:
            metadata[key] = parse_scalar(value)
            i += 1
            continue

        block, next_i = parse_indented_block(lines, i + 1)
        metadata[key] = block
        i = next_i

    return metadata


def load_markdown(path: Path) -> tuple[dict[str, Any], str]:
    return split_frontmatter(path.read_text(encoding="utf-8-sig"))


def metadata_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, dict):
        if "text" in value:
            return metadata_text(value["text"], default)
        for item in value.values():
            text = metadata_text(item, "")
            if text:
                return text
        return default
    if isinstance(value, list):
        for item in value:
            text = metadata_text(item, "")
            if text:
                return text
        return default
    return str(value)


def sort_value(metadata: dict[str, Any], fallback: int) -> int:
    value = metadata.get("index", metadata.get("slug", fallback))
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def strip_markup(text: str) -> str:
    text = re.sub(r"^#+\s*", "", text.strip())
    text = re.sub(r"!\[([\s\S]*?)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"([*_~`])", "", text)
    text = re.sub(r"#><(.*?)><#", r"\1", text)
    text = re.sub(r"#([rbygpo])(.+?)\1#", r"\2", text)
    text = re.sub(r";([rbygpo])(.+?)\1;", r"\2", text)
    text = re.sub(r"[@%#~^<>]+", "", text)
    return html.unescape(text).strip()


def first_heading(content: str) -> str | None:
    for line in normalize_newlines(content).splitlines():
        match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if match:
            return strip_markup(match.group(2))
    return None


def sanitize_filename(name: str, fallback: str = "book") -> str:
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "-", name)
    name = re.sub(r"\s+", " ", name).strip(" .")
    return name or fallback


def safe_id(value: str, fallback: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_-]+", "_", value).strip("_")
    return value or fallback


def valid_identifier(value: str, book_title: str) -> str:
    """Return a valid dc:identifier for the OPF/NCX.

    urn:uuid values must be well-formed UUIDs; anything else falls back to a
    deterministic UUID derived from the book title.
    """
    value = (value or "").strip()
    if not value:
        return f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, book_title)}"
    if value.lower().startswith("urn:uuid:"):
        try:
            uuid.UUID(value[len("urn:uuid:"):])
            return value
        except ValueError:
            pass
    return f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, book_title)}"


def media_type_for(path: Path) -> str:
    suffix = path.suffix.lower()
    return {
        ".css": "text/css",
        ".gif": "image/gif",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".svg": "image/svg+xml",
        ".webp": "image/webp",
        ".xhtml": "application/xhtml+xml",
        ".ncx": "application/x-dtbncx+xml",
    }.get(suffix, "application/octet-stream")


def convert_to_png(source_path: Path, output_dir: Path) -> Path | None:
    """Convert an image to PNG (a core EPUB media type). Returns the PNG path, or None on failure."""
    if Image is None:
        return None
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{source_path.stem}.png"
        with Image.open(source_path) as img:
            img.save(output_path, "PNG", optimize=True)
        return output_path if output_path.exists() and output_path.stat().st_size > 0 else None
    except Exception:
        return None


def unique_asset_name(source_path: Path, preferred: str, used: set[str]) -> str:
    preferred = sanitize_filename(preferred.replace(" ", "_"), "asset")
    stem = Path(preferred).stem or "asset"
    suffix = Path(preferred).suffix or source_path.suffix
    candidate = f"{stem}{suffix}"
    if candidate not in used:
        used.add(candidate)
        return candidate

    digest = hashlib.sha1(str(source_path).encode("utf-8")).hexdigest()[:8]
    candidate = f"{stem}_{digest}{suffix}"
    counter = 2
    while candidate in used:
        candidate = f"{stem}_{digest}_{counter}{suffix}"
        counter += 1
    used.add(candidate)
    return candidate


def register_asset(ctx: RenderContext, source_path: Path, preferred: str | None = None) -> EpubAsset:
    source_path = source_path.resolve()
    existing = ctx.assets.get(source_path)
    if existing:
        return existing

    name = unique_asset_name(source_path, preferred or source_path.name, ctx.asset_names)
    asset = EpubAsset(
        source_path=source_path,
        href=f"Images/{name}",
        media_type=media_type_for(source_path),
    )
    ctx.assets[source_path] = asset
    return asset


def load_tweet_cache() -> dict[str, Any]:
    if not TWEET_CACHE_PATH.exists():
        return {}
    try:
        return json.loads(TWEET_CACHE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_tweet_cache(cache: dict[str, Any]) -> None:
    TWITTER_IMG_DIR.mkdir(parents=True, exist_ok=True)
    TWEET_CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def request_json(url: str) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def request_bytes(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=40) as response:
        return response.read()


def fetch_twitter_webp(username: str, tweet_id: str, photo_index: int) -> tuple[Path | None, str | None]:
    cache_key = f"{tweet_id}_{photo_index}"
    webp_path = TWITTER_IMG_DIR / f"{cache_key}.webp"
    if webp_path.exists():
        return webp_path, None

    if Image is None:
        print(f"      Pillow is unavailable; cannot convert tweet {tweet_id} to WebP")
        return None, None

    api_url = f"https://api.fxtwitter.com/{username}/status/{tweet_id}"
    data = request_json(api_url)
    tweet = data.get("tweet") or {}
    screen_name = ((tweet.get("user") or {}).get("screen_name")) or username
    photos = ((tweet.get("media") or {}).get("photos") or [])
    idx = photo_index - 1
    if idx < 0 or idx >= len(photos):
        print(f"      Tweet {tweet_id} has no photo #{photo_index}")
        return None, None

    photo_url = photos[idx].get("url")
    if not photo_url:
        print(f"      Tweet {tweet_id} photo #{photo_index} has no URL")
        return None, None

    image_bytes = request_bytes(photo_url)
    image = Image.open(BytesIO(image_bytes))
    TWITTER_IMG_DIR.mkdir(parents=True, exist_ok=True)
    image.save(webp_path, "WEBP", quality=88, method=6)
    return webp_path, screen_name


def twitter_image_html(match: re.Match[str], ctx: RenderContext) -> str:
    username = match.group(1)
    tweet_id = match.group(2)
    photo_index = int(match.group(3) or 1)
    cache_key = f"{tweet_id}_{photo_index}"
    webp_path = TWITTER_IMG_DIR / f"{cache_key}.webp"

    cached_entry = ctx.tweet_cache.get(cache_key)
    screen_name = None

    if cached_entry:
        screen_name = cached_entry.get("screen_name")

    if not webp_path.exists() and ctx.fetch_twitter:
        try:
            print(f"      Fetching tweet image {tweet_id}/{photo_index}")
            webp_path, api_screen_name = fetch_twitter_webp(username, tweet_id, photo_index)
            screen_name = api_screen_name or screen_name
            if webp_path:
                ctx.tweet_cache[cache_key] = {
                    "username": username,
                    "screen_name": screen_name or username,
                    "tweet_id": tweet_id,
                    "photo": photo_index,
                    "path": str(webp_path),
                }
                save_tweet_cache(ctx.tweet_cache)
        except Exception as exc:
            print(f"      Warning: failed to fetch tweet {tweet_id}: {exc}")

    if webp_path.exists():
        png_path = convert_to_png(webp_path, TWITTER_IMG_DIR / "png") or webp_path
        asset = register_asset(ctx, png_path, "twitter_image.png" if png_path.suffix.lower() == ".png" else png_path.name)
        display_name = screen_name or username
        alt = f"Illustration from @{display_name} on X"
        return image_block_html(f"../{asset.href}", alt)

    url = match.group(0)
    return f'<p><a href="{escape_attr(url)}">{escape_text(url)}</a></p>'


def resolve_local_image(src: str, ctx: RenderContext) -> Path | None:
    clean_src = urllib.parse.unquote(src.split("#", 1)[0].split("?", 1)[0])
    src_path = Path(clean_src.replace("/", "\\"))

    candidates = []
    if src_path.is_absolute():
        candidates.append(src_path)
    else:
        candidates.extend(
            [
                ctx.chapter_path.parent / src_path,
                IMAGES_ROOT / ctx.book_id / "illustrations" / src_path,
                IMAGES_ROOT / ctx.book_id / src_path,
                IMAGES_ROOT / src_path,
                OUTPUT_DIR / src_path,
            ]
        )

    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def escape_text(value: Any) -> str:
    return html.escape(str(value), quote=False)


def escape_attr(value: Any) -> str:
    return html.escape(str(value), quote=True)


def image_block_html(src: str, alt: str = "") -> str:
    alt_attr = escape_attr(strip_markup(alt))
    img = f'<img src="{escape_attr(src)}" alt="{alt_attr}" />'
    if alt_attr:
        return f'<div class="image-block">{img}<div class="thumbcaption">{alt_attr}</div></div>'
    return f'<div class="image-block">{img}</div>'


def markdown_image_html(alt: str, src: str, ctx: RenderContext) -> str:
    src = src.strip()
    twitter_match = TWITTER_RE.fullmatch(src)
    if twitter_match:
        return twitter_image_html(twitter_match, ctx)

    if re.match(r"https?://", src, re.IGNORECASE):
        return image_block_html(src, alt)

    image_path = resolve_local_image(src, ctx)
    if not image_path:
        print(f"      Warning: image not found for {ctx.chapter_path.name}: {src}")
        return f'<p>{escape_text(alt or src)}</p>'

    if image_path.suffix.lower() == ".webp":
        png = convert_to_png(image_path, OUTPUT_DIR / "converted_images")
        if png:
            image_path = png
    asset = register_asset(ctx, image_path)
    return image_block_html(f"../{asset.href}", alt)


def stash_html(store: dict[str, str], value: str) -> str:
    key = f"\x00HTML{len(store)}\x00"
    store[key] = value
    return key


def protect_escapes(text: str, store: dict[str, str]) -> str:
    out: list[str] = []
    i = 0
    escapable = "\\`*_{}[]()#+-.!<>~"

    while i < len(text):
        if text[i] == "\\" and i + 1 < len(text) and text[i + 1] in escapable:
            out.append(stash_html(store, escape_text(text[i + 1])))
            i += 2
            continue
        out.append(text[i])
        i += 1

    return "".join(out)


def wrap_inline(
    text: str,
    pattern: str,
    wrapper: str,
    store: dict[str, str],
    ctx: RenderContext,
    flags: int = re.DOTALL,
) -> str:
    regex = re.compile(pattern, flags)

    def repl(match: re.Match[str]) -> str:
        inner = render_inline(match.group(1), ctx)
        return stash_html(store, wrapper.format(inner=inner))

    return regex.sub(repl, text)


def char_span_html(text: str, class_name: str, ctx: RenderContext) -> str:
    rendered = render_inline(text, ctx)
    return f'<span class="{class_name}">{rendered}</span>'


def render_inline(text: str, ctx: RenderContext) -> str:
    text = normalize_newlines(text)
    text = re.sub(r" {2,}\n", "\n<br />\n", text)
    text = text.replace("\n", " ")

    store: dict[str, str] = {}
    text = protect_escapes(text, store)

    def br_repl(match: re.Match[str]) -> str:
        return stash_html(store, "<br /><br />")

    text = re.sub(r"<br\s*/?>", br_repl, text, flags=re.IGNORECASE)

    def code_repl(match: re.Match[str]) -> str:
        return stash_html(store, f"<code>{escape_text(match.group(1))}</code>")

    text = re.sub(r"`([^`]+)`", code_repl, text)

    def image_repl(match: re.Match[str]) -> str:
        return stash_html(store, markdown_image_html(match.group(1), match.group(2), ctx))

    text = IMAGE_RE.sub(image_repl, text)

    def link_repl(match: re.Match[str]) -> str:
        label = render_inline(match.group(1), ctx)
        url = escape_attr(match.group(2))
        return stash_html(store, f'<a href="{url}">{label}</a>')

    text = LINK_RE.sub(link_repl, text)

    custom_wrappers = [
        (r"@@(.+?)@@", '<span class="glitch-text">{inner}</span>'),
        (r"@_@(.+?)@_@", '<span class="glitch-subtle">{inner}</span>'),
        (r"\$s(.+?)s\$", '<span class="smoke-text">{inner}</span>'),
        (r"@ll@(.+?)@ll@", '<span class="mono mono-left">{inner}</span>'),
        (r"@cc@(.+?)@cc@", '<span class="mono mono-center">{inner}</span>'),
        (r"@rr@(.+?)@rr@", '<span class="mono mono-right">{inner}</span>'),
        (r"@l@(.+?)@l@", '<span class="align-left">{inner}</span>'),
        (r"@c@(.+?)@c@", '<span class="align-center">{inner}</span>'),
        (r"@r@(.+?)@r@", '<span class="align-right">{inner}</span>'),
        (r"@rs@(.+?)@rs@", '<span class="align-right window-small">{inner}</span>'),
        (r"#><(.+?)><#", '<span class="text-large-centered">{inner}</span>'),
        (r"#\*(.+?)\*#", '<span class="text-large">{inner}</span>'),
        (r"#f>#(.+?)#f>#", '<span class="text-fade-right">{inner}</span>'),
        (r"#f<#(.+?)#f<#", '<span class="text-fade-left">{inner}</span>'),
        (r"#f#(.+?)#f#", '<span class="text-faded">{inner}</span>'),
        (r"(?<!\\)\-#\s*(.+?)\s*#-(?!\\)", '<span class="text-sub">{inner}</span>'),
        (r"#r(.+?)r#", '<span class="text-red">{inner}</span>'),
        (r"#b(.+?)b#", '<span class="text-blue">{inner}</span>'),
        (r"#y(.+?)y#", '<span class="text-yellow">{inner}</span>'),
        (r"#p(.+?)p#", '<span class="text-magenta">{inner}</span>'),
        (r"#g(.+?)g#", '<span class="text-green">{inner}</span>'),
        (r"#o(.+?)o#", '<span class="text-orange">{inner}</span>'),
        (r";r(.+?)r;", '<span class="hl-red">{inner}</span>'),
        (r";b(.+?)b;", '<span class="hl-blue">{inner}</span>'),
        (r";y(.+?)y;", '<span class="hl-yellow">{inner}</span>'),
        (r";p(.+?)p;", '<span class="hl-magenta">{inner}</span>'),
        (r";g(.+?)g;", '<span class="hl-green">{inner}</span>'),
        (r";o(.+?)o;", '<span class="hl-orange">{inner}</span>'),
        (r"%%(.+?)%%", '<span class="shake">{inner}</span>'),
        (r"%~(.+?)~%", '<span class="shake">{inner}</span>'),
        (r"%\^(.+?)\^%", '<span class="wave-up">{inner}</span>'),
        (r"#\^#(.+?)#\^#", '<span class="text-grow">{inner}</span>'),
        (r"#v#(.+?)#v#", '<span class="text-grow">{inner}</span>'),
        (r"\$\$(.+?)\$\$", '<span class="handwritten">{inner}</span>'),
        (r"\$c(.+?)c\$", '<span class="contaminated">{inner}</span>'),
        (r"\$Eb(.+?)Eb\$", '<span class="eb-garamond">{inner}</span>'),
        (r"\$a(.+?)a\$", '<span class="aurora-text">{inner}</span>'),
        (r"\$g(.+?)g\$", '<span class="gold-text">{inner}</span>'),
        (r"\$\*(.+?)\*\$", '<span class="sparkle-text">{inner}</span>'),
        (r"\$\((.+?)\)\$", '<span class="moon-text">{inner}</span>'),
        (r"\$ag(.+?)ag\$", '<span class="silver-text">{inner}</span>'),
        (r"#lp(.+?)lp#", '<span class="text-light-purple">{inner}</span>'),
        (r"#cy(.+?)cy#", '<span class="text-cyan">{inner}</span>'),
        (r"\$wo(.+?)wo\$", '<span class="outline-white">{inner}</span>'),
        (r"\$bo(.+?)bo\$", '<span class="outline-black">{inner}</span>'),
    ]

    for pattern, wrapper in custom_wrappers:
        text = wrap_inline(text, pattern, wrapper, store, ctx)

    markdown_wrappers = [
        (r"~~(.+?)~~", "<del>{inner}</del>"),
        (r"(?<!\*)\*\*\*(.+?)\*\*\*(?!\*)", "<strong><em>{inner}</em></strong>"),
        (r"(?<!\*)\*\*(.+?)\*\*(?!\*)", "<strong>{inner}</strong>"),
        (r"(?<!\*)\*(.+?)\*(?!\*)", "<em>{inner}</em>"),
        (r"_(.+?)_", '<span class="underline">{inner}</span>'),
    ]

    for pattern, wrapper in markdown_wrappers:
        text = wrap_inline(text, pattern, wrapper, store, ctx)

    hex_re = re.compile(r"#hx\(([^)]+)\)(.*?)hx#", re.DOTALL)
    def hex_repl(match: re.Match) -> str:
        color = match.group(1)
        inner = render_inline(match.group(2), ctx)
        return stash_html(store, f'<span style="color:{color}">{inner}</span>')
    text = hex_re.sub(hex_repl, text)

    hxo_re = re.compile(r"\$hxo\(([^)]+)\)(.*?)hxo#", re.DOTALL)
    def hxo_repl(match: re.Match) -> str:
        color = match.group(1)
        inner = render_inline(match.group(2), ctx)
        return stash_html(
            store,
            f'<span class="hex-outline" style="--hxo-color:{color}">{inner}</span>',
        )
    text = hxo_re.sub(hxo_repl, text)

    hxa_re = re.compile(r"\$hxa\(([^)]+)\)\(([^)]+)\)\(([^)]+)\)(.*?)hxa\$", re.DOTALL)
    def hxa_repl(match: re.Match) -> str:
        c1, c2, c3 = match.group(1), match.group(2), match.group(3)
        inner = render_inline(match.group(4), ctx)
        return stash_html(
            store,
            f'<span class="hex-aurora" style="--ha-c1:{c1};--ha-c2:{c2};--ha-c3:{c3}">{inner}</span>',
        )
    text = hxa_re.sub(hxa_repl, text)

    hxas_re = re.compile(r"\$hxas\(([^)]+)\)\(([^)]+)\)\(([^)]+)\)(.*?)hxas\$", re.DOTALL)
    def hxas_repl(match: re.Match) -> str:
        c1, c2, c3 = match.group(1), match.group(2), match.group(3)
        inner = render_inline(match.group(4), ctx)
        return stash_html(
            store,
            f'<span class="hex-aurora-static" style="--ha-c1:{c1};--ha-c2:{c2};--ha-c3:{c3}">{inner}</span>',
        )
    text = hxas_re.sub(hxas_repl, text)

    hxau_re = re.compile(r"\$hxau\(([^)]+)\)\(([^)]+)\)\(([^)]+)\)(.*?)hxau\$", re.DOTALL)
    def hxau_repl(match: re.Match) -> str:
        c1, c2, c3 = match.group(1), match.group(2), match.group(3)
        inner = render_inline(match.group(4), ctx)
        return stash_html(
            store,
            f'<span class="hex-aurora-up" style="--ha-c1:{c1};--ha-c2:{c2};--ha-c3:{c3}">{inner}</span>',
        )
    text = hxau_re.sub(hxau_repl, text)

    hxaus_re = re.compile(r"\$hxaus\(([^)]+)\)\(([^)]+)\)\(([^)]+)\)(.*?)hxaus\$", re.DOTALL)
    def hxaus_repl(match: re.Match) -> str:
        c1, c2, c3 = match.group(1), match.group(2), match.group(3)
        inner = render_inline(match.group(4), ctx)
        return stash_html(
            store,
            f'<span class="hex-aurora-up-static" style="--ha-c1:{c1};--ha-c2:{c2};--ha-c3:{c3}">{inner}</span>',
        )
    text = hxaus_re.sub(hxaus_repl, text)

    escaped = escape_text(text)
    resolved: dict[str, str] = {}

    def resolve_placeholder(key: str, seen: set[str]) -> str:
        if key in resolved:
            return resolved[key]
        value = store[key]
        for nested_key in store:
            if nested_key not in value:
                continue
            if nested_key in seen:
                value = value.replace(nested_key, "")
            else:
                value = value.replace(
                    nested_key,
                    resolve_placeholder(nested_key, seen | {nested_key}),
                )
        resolved[key] = value
        return value

    for key in sorted(store, key=len, reverse=True):
        if key in escaped:
            escaped = escaped.replace(key, resolve_placeholder(key, {key}))
    return escaped


def is_hr_line(line: str) -> bool:
    stripped = line.strip()
    return stripped in {"~~~", "---", "***", "* * *"}


WINDOW_PATTERNS = [
    ("wiki-window", re.compile(r"^\+-+$"), re.compile(r"^-+\+$")),
    ("record-window", re.compile(r"^&-+$"), re.compile(r"^-+&$")),
    ("black-window", re.compile(r"^\+=$"), re.compile(r"^=\+$")),
    ("system-window", re.compile(r"^\+~$"), re.compile(r"^~\+$")),
    ("plain-window", re.compile(r"^\+\$$"), re.compile(r"^\$\+$")),
    ("bare-window", re.compile(r"^\+\.$"), re.compile(r"^\.\+$")),
    ("followup-window", re.compile(r"^&\$$"), re.compile(r"^\$&$")),
    ("note-window", re.compile(r"^!-+$"), re.compile(r"^-+!$")),
    ("sticky-window", re.compile(r"^!\$$"), re.compile(r"^\$!$")),
    ("braun-screen", re.compile(r"^!\[$"), re.compile(r"^\]!$")),
    ("braun-tv-text", re.compile(r"^\$Brt$"), re.compile(r"^Brt\$$")),
    ("braun-doll-text", re.compile(r"^\$Brd$"), re.compile(r"^Brd\$$")),
    ("sms-window", re.compile(r"^★:$"), re.compile(r"^:★$")),
    ("alert-window", re.compile(r"^★\$$"), re.compile(r"^\$★$")),
]


def window_spec(line: str) -> tuple[str, re.Pattern[str]] | None:
    stripped = line.strip()
    for class_name, start_re, end_re in WINDOW_PATTERNS:
        if start_re.match(stripped):
            return class_name, end_re
    return None


def strip_leading_escape(inner: str) -> str:
    match = re.search(r"\S", inner)
    if match and inner[match.start()] == "\\":
        return inner[: match.start()] + inner[match.start() + 1 :]
    return inner


SMS_SPEAKER_COLORS = {
    "PMD": "#FFF8D9",
    "SAH": "#FFF0E1",
    "BSJ": "#EDF5FF",
    "LSJ": "#F2ECFF",
    "KRB": "#FDE8F1",
    "CE": "#FFE5E5",
    "RCW": "#EAF8F2",
}


def render_sms_window(inner_lines: list[str], ctx: RenderContext) -> str:
    parts: list[str] = []
    for raw in inner_lines:
        trimmed = raw.strip()
        if not trimmed:
            continue
        dash_left = re.match(r"^[-–—]\s*(.+)", trimmed)
        dash_right = re.match(r"(.+)\s*[-–—]$", trimmed)
        if dash_left:
            content = dash_left.group(1).strip()
            sp = re.match(r"^(PMD|SAH|BSJ|LSJ|KRB|CE|RCW):\s*", content)
            body = render_inline(content[sp.end() :] if sp else content, ctx)
            style = (
                f' style="background:{SMS_SPEAKER_COLORS[sp.group(1)]};color:#222"'
                if sp
                else ""
            )
            parts.append(f'<div class="sms-bubble sms-left"{style}>{body}</div>')
        elif dash_right:
            content = dash_right.group(1).strip()
            sp = re.match(r"^(PMD|SAH|BSJ|LSJ|KRB|CE|RCW):\s*", content)
            body = render_inline(content[sp.end() :] if sp else content, ctx)
            style = (
                f' style="background:{SMS_SPEAKER_COLORS[sp.group(1)]};color:#222"'
                if sp
                else ""
            )
            parts.append(f'<div class="sms-bubble sms-right"{style}>{body}</div>')
        else:
            parts.append(f'<div class="sms-bubble sms-center">{render_inline(trimmed, ctx)}</div>')
    return "\n\n".join(parts)


def render_comment_window(inner_lines: list[str], ctx: RenderContext) -> str:
    title = ""
    desc = ""
    items: list[tuple[str, int]] = []
    in_comments = False

    for raw in inner_lines:
        line = raw.strip()
        if line.startswith("["):
            title = render_inline(line.strip(), ctx)
        elif line.startswith(":"):
            desc = render_inline(line.replace(":", "", 1).strip(), ctx)
        elif line.startswith(("-", "\u2013", "\u2014")):
            in_comments = True
            content = re.sub(r"^[\u2014\u2013-]", "", line).strip()
            items.append((render_inline(content, ctx), 0))
        elif line.startswith(("\u2937", "\u2514", "\u221F")):
            in_comments = True
            depth = 0
            content = line
            while content.startswith(("\u2937", "\u2514", "\u221F")):
                depth += 1
                content = re.sub(r"^[\u2937\u2514\u221F]", "", content).lstrip()
            if depth > 3:
                depth = 3
            items.append((render_inline(content.strip(), ctx), depth))
        elif line and not in_comments:
            desc += ("" if not desc else "</p>\n<p>") + render_inline(line, ctx)

    parts: list[str] = []
    if title or desc:
        parts.append('<div class="comment-post-header">')
        if title:
            parts.append(f'<div class="comment-post-title">{title}</div>')
        if desc:
            parts.append(f'<div class="comment-post-desc"><p>{desc}</p></div>')
        parts.append("</div>")
    if items:
        parts.append('<div class="comment-section">')
        for text, depth in items:
            if depth == 0:
                parts.append(f'<div class="comment">{text}</div>')
            else:
                parts.append(
                    f'<div class="comment-reply depth-{depth}">'
                    f'<span class="reply-icon">\u2937</span>'
                    f'<span class="reply-body">{text}</span></div>'
                )
        parts.append("</div>")
    return "\n\n".join(parts)


def is_block_start(line: str) -> bool:
    return bool(
        window_spec(line)
        or is_hr_line(line)
        or re.match(r"^\^\^\s*$", line)
        or re.match(r"^#{1,6}\s+", line)
        or re.match(r"^(```|~~~[A-Za-z0-9_-]+)", line.strip())
        or re.match(r"^>\s?", line)
        or re.match(r"^([-+*]|\d+\.)\s+\S", line)
    )


def render_list(lines: list[str], start: int, ctx: RenderContext) -> tuple[str, int]:
    first = lines[start]
    ordered = bool(re.match(r"^\d+\.\s+\S", first))
    tag = "ol" if ordered else "ul"
    items: list[str] = []
    i = start

    while i < len(lines):
        line = lines[i]
        match = re.match(r"^(?:[-+*]|\d+\.)\s+(.+)$", line)
        if not match:
            break
        items.append(f"<li>{render_inline(match.group(1), ctx)}</li>")
        i += 1

    return f"<{tag}>" + "".join(items) + f"</{tag}>", i


def render_standalone_image_paragraph(text: str, ctx: RenderContext) -> str | None:
    stripped = text.strip()
    twitter_match = TWITTER_RE.fullmatch(stripped)
    if twitter_match:
        return twitter_image_html(twitter_match, ctx)

    matches = list(IMAGE_RE.finditer(stripped))
    if not matches:
        return None

    cursor = 0
    parts: list[str] = []
    for match in matches:
        if stripped[cursor : match.start()].strip():
            return None
        parts.append(markdown_image_html(match.group(1), match.group(2), ctx))
        cursor = match.end()

    if stripped[cursor:].strip():
        return None
    return "\n".join(parts)


def render_blocks(text: str, ctx: RenderContext) -> str:
    lines = normalize_newlines(text).splitlines()
    out: list[str] = []
    i = 0

    while i < len(lines):
        line = lines[i]

        if not line.strip():
            i += 1
            continue

        fence = re.match(r"^```", line.strip())
        if fence:
            i += 1
            code_lines: list[str] = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            if i < len(lines):
                i += 1
            out.append(f"<pre><code>{escape_text(chr(10).join(code_lines))}</code></pre>")
            continue

        spec = window_spec(line)
        if spec:
            class_name, end_re = spec
            opener_idx = i
            i += 1
            inner_lines: list[str] = []
            while i < len(lines) and not end_re.match(lines[i].strip()):
                inner_lines.append(lines[i])
                i += 1
            if i >= len(lines):
                # Unmatched opener: never swallow the rest of the chapter as one
                # giant window. Drop the dangling delimiter and keep rendering
                # the remaining content as normal blocks.
                print(
                    f"  Warning: unclosed {class_name} window near line "
                    f"{opener_idx + 1} (no closing delimiter '{end_re.pattern}' "
                    f"found); rendering the rest normally"
                )
                i = opener_idx + 1
                continue
            i += 1

            extra_cls = ""
            if class_name in ("wiki-window", "record-window"):
                first_idx = next(
                    (idx for idx, il in enumerate(inner_lines) if il.strip()),
                    -1,
                )
                if first_idx >= 0:
                    stripped = inner_lines[first_idx].strip()
                    if stripped.startswith("\\"):
                        extra_cls = " no-meta"
                    else:
                        inner_lines[first_idx] = f"@rs@{stripped}@rs@"
            elif class_name == "note-window":
                first_idx = next(
                    (idx for idx, il in enumerate(inner_lines) if il.strip()),
                    -1,
                )
                if first_idx >= 0 and inner_lines[first_idx].strip().startswith("\\"):
                    extra_cls = " no-meta"
            elif class_name == "system-window":
                first_idx = next(
                    (idx for idx, il in enumerate(inner_lines) if il.strip()),
                    -1,
                )
                if first_idx >= 0 and inner_lines[first_idx].strip().startswith("\\"):
                    extra_cls = " no-fl-dividers"

            if class_name == "sms-window":
                inner_html = render_sms_window(inner_lines, ctx)
            elif class_name == "alert-window":
                inner_html = render_comment_window(inner_lines, ctx)
            elif class_name in ("braun-tv-text", "braun-doll-text"):
                inner = strip_leading_escape("\n".join(inner_lines).strip("\n"))
                parts = [p for p in re.split(r"\n+", inner) if p.strip()]
                inner_html = "<br />".join(render_inline(p, ctx) for p in parts)
            else:
                inner = strip_leading_escape("\n".join(inner_lines).strip("\n"))
                inner_html = render_blocks(inner, ctx)
            out.append(f'<div class="{class_name}{extra_cls}">{inner_html}</div>')
            continue

        heading = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if heading:
            level = min(len(heading.group(1)), 6)
            out.append(f"<h{level}>{render_inline(heading.group(2), ctx)}</h{level}>")
            i += 1
            continue

        if re.match(r"^-\&-\s*$", line):
            i += 1
            continue

        if re.match(r"^~\^~\s*$", line):
            out.append('<br /><hr class="invisible-hr" /><br />')
            i += 1
            continue

        if is_hr_line(line):
            out.append("<br /><hr /><br />")
            i += 1
            continue

        if re.match(r"^>\s?", line):
            quote_lines: list[str] = []
            while i < len(lines) and re.match(r"^>\s?", lines[i]):
                quote_lines.append(re.sub(r"^>\s?", "", lines[i]))
                i += 1
            out.append(f"<blockquote>{render_blocks(chr(10).join(quote_lines), ctx)}</blockquote>")
            continue

        if re.match(r"^([-+*]|\d+\.)\s+\S", line):
            html_list, i = render_list(lines, i, ctx)
            out.append(html_list)
            continue

        paragraph_lines = [line]
        i += 1
        while i < len(lines) and lines[i].strip() and not is_block_start(lines[i]):
            paragraph_lines.append(lines[i])
            i += 1

        paragraph = "\n".join(paragraph_lines)
        standalone_image = render_standalone_image_paragraph(paragraph, ctx)
        if standalone_image is not None:
            out.append(standalone_image)
        else:
            out.append(f"<p>{render_inline(paragraph, ctx)}</p>")

    return "\n".join(out)


def xhtml_page(title: str, body: str) -> str:
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<!DOCTYPE html>\n'
        '<html xmlns="http://www.w3.org/1999/xhtml">'
        f"<head><title>{escape_text(title)}</title>"
        '<link href="../Styles/stylesheet.css" type="text/css" rel="stylesheet" />'
        f"</head><body>{body}</body></html>\n"
    )


def nav_xhtml(book_title: str, items: list[EpubItem]) -> str:
    links = "\n".join(
        f'<li><a href="{escape_attr(item.href)}">{escape_text(item.title)}</a></li>'
        for item in items
    )
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<!DOCTYPE html>\n'
        '<html xmlns="http://www.w3.org/1999/xhtml" '
        'xmlns:epub="http://www.idpf.org/2007/ops">'
        f"<head><title>{escape_text(book_title)} Table of Contents</title>"
        '<link href="Styles/stylesheet.css" type="text/css" rel="stylesheet" />'
        "</head><body>"
        '<nav epub:type="toc" id="toc"><h1>Table of Contents</h1>'
        f"<ol>{links}</ol></nav></body></html>\n"
    )


def content_opf(
    book_title: str,
    metadata: dict[str, Any],
    items: list[EpubItem],
    assets: list[EpubAsset],
    modified: str,
    cover_asset: EpubAsset | None = None,
    cover_item: EpubItem | None = None,
) -> str:
    language = metadata_text(metadata.get("language"), "en")
    creator = metadata_text(metadata.get("creator"), "unknown")
    contributor = metadata_text(metadata.get("contributor"), "")
    publisher = metadata_text(metadata.get("publisher"), "GSGW-Reader")
    description = metadata_text(metadata.get("description"), "")
    rights = metadata_text(metadata.get("rights"), "")
    identifier = metadata_text(metadata.get("identifier"), "")
    identifier = valid_identifier(identifier, book_title)

    manifest_items = [
        '<item href="Styles/stylesheet.css" id="stylesheet" media-type="text/css"/>',
        '<item href="toc.ncx" id="ncx" media-type="application/x-dtbncx+xml"/>',
        '<item href="nav.xhtml" id="nav" media-type="application/xhtml+xml" properties="nav"/>',
    ]
    if cover_item:
        manifest_items.append(
            f'<item href="{escape_attr(cover_item.href)}" id="{cover_item.item_id}" '
            'media-type="application/xhtml+xml"/>'
        )
    for item in items:
        manifest_items.append(
            f'<item href="{escape_attr(item.href)}" id="{item.item_id}" '
            'media-type="application/xhtml+xml"/>'
        )
    for idx, asset in enumerate(assets):
        if cover_asset and asset.source_path == cover_asset.source_path:
            manifest_items.append(
                f'<item href="{escape_attr(asset.href)}" id="cover-image" '
                f'media-type="{escape_attr(asset.media_type)}" properties="cover-image"/>'
            )
        else:
            manifest_items.append(
                f'<item href="{escape_attr(asset.href)}" id="image{idx:04d}" '
                f'media-type="{escape_attr(asset.media_type)}"/>'
            )

    spine_items = []
    if cover_item:
        spine_items.append(f'<itemref idref="{cover_item.item_id}"/>')
    spine_items.extend(f'<itemref idref="{item.item_id}"/>' for item in items)
    spine = "\n".join(spine_items)

    meta_lines = [
        f'<dc:title>{escape_text(book_title)}</dc:title>',
        f'<dc:language>{escape_text(language)}</dc:language>',
        f'<dc:identifier id="BookId">{escape_text(identifier)}</dc:identifier>',
        f'<dc:creator>{escape_text(creator)}</dc:creator>',
        f'<dc:publisher>{escape_text(publisher)}</dc:publisher>',
        f'<dc:date>{escape_text(dt.date.today().isoformat())}</dc:date>',
        f'<meta property="dcterms:modified">{escape_text(modified)}</meta>',
        f'<dc:source>{escape_text(EPUB_SOURCE_URL)}</dc:source>',
    ]
    if cover_asset:
        meta_lines.append('<meta name="cover" content="cover-image"/>')
    if contributor:
        meta_lines.append(f'<dc:contributor>{escape_text(contributor)}</dc:contributor>')
    if description:
        meta_lines.append(f'<dc:description>{escape_text(description)}</dc:description>')
    if rights:
        meta_lines.append(f'<dc:rights>{escape_text(rights)}</dc:rights>')

    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<package xmlns="http://www.idpf.org/2007/opf" version="3.0" '
        'unique-identifier="BookId">'
        '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">'
        + "".join(meta_lines)
        + "</metadata><manifest>"
        + "".join(manifest_items)
        + f'</manifest><spine toc="ncx">{spine}</spine></package>\n'
    )


def toc_ncx(book_title: str, identifier: str, items: list[EpubItem]) -> str:
    nav_points = []
    for order, item in enumerate(items, start=1):
        nav_points.append(
            f'<navPoint id="navPoint-{order}" playOrder="{order}">'
            f"<navLabel><text>{escape_text(item.title)}</text></navLabel>"
            f'<content src="{escape_attr(item.href)}"/>'
            "</navPoint>"
        )

    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">'
        "<head>"
        f'<meta name="dtb:uid" content="{escape_attr(identifier)}"/>'
        '<meta name="dtb:depth" content="1"/>'
        '<meta name="dtb:totalPageCount" content="0"/>'
        '<meta name="dtb:maxPageNumber" content="0"/>'
        "</head>"
        f"<docTitle><text>{escape_text(book_title)}</text></docTitle>"
        "<navMap>"
        + "".join(nav_points)
        + "</navMap></ncx>\n"
    )


def container_xml() -> str:
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
        "<rootfiles>"
        '<rootfile full-path="OEBPS/content.opf" '
        'media-type="application/oebps-package+xml"/>'
        "</rootfiles></container>\n"
    )


def write_epub(
    epub_path: Path,
    book_title: str,
    metadata: dict[str, Any],
    items: list[EpubItem],
    assets: dict[Path, EpubAsset],
    cover_item: EpubItem | None = None,
    cover_asset: EpubAsset | None = None,
) -> None:
    css = CSS_PATH.read_text(encoding="utf-8")
    modified = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    identifier = metadata_text(metadata.get("identifier"), "")
    identifier = valid_identifier(identifier, book_title)
    asset_list = sorted(assets.values(), key=lambda asset: asset.href)

    epub_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(epub_path, "w") as zf:
        mimetype = zipfile.ZipInfo("mimetype")
        mimetype.compress_type = zipfile.ZIP_STORED
        zf.writestr(mimetype, "application/epub+zip")

        def write_text(name: str, data: str) -> None:
            zf.writestr(name, data.encode("utf-8"), compress_type=zipfile.ZIP_DEFLATED)

        write_text("META-INF/container.xml", container_xml())
        write_text("OEBPS/Styles/stylesheet.css", css)
        write_text("OEBPS/content.opf", content_opf(book_title, metadata, items, asset_list, modified, cover_asset, cover_item))
        write_text("OEBPS/toc.ncx", toc_ncx(book_title, identifier, items))
        write_text("OEBPS/nav.xhtml", nav_xhtml(book_title, items))

        if cover_item:
            write_text(f"OEBPS/{cover_item.href}", xhtml_page(cover_item.title, cover_item.body))

        for item in items:
            write_text(f"OEBPS/{item.href}", xhtml_page(item.title, item.body))

        for asset in asset_list:
            zf.write(asset.source_path, f"OEBPS/{asset.href}", compress_type=zipfile.ZIP_DEFLATED)


def chapter_output_name(position: int, chapter: Chapter) -> str:
    title = safe_id(chapter.title.replace(".", ""), f"chapter_{position}")
    return f"{position:04d}_{title}.xhtml"


def build_translation(tl_path: Path, args: argparse.Namespace) -> Path | None:
    metadata_path = tl_path / "metadata.md"
    if not metadata_path.exists():
        print(f"Skipping {tl_path.name}: no metadata.md")
        return None

    master_meta, master_content = load_markdown(metadata_path)
    book_id = metadata_text(master_meta.get("metaBook"), tl_path.parent.name)
    tl_name = metadata_text(master_meta.get("metaTl"), tl_path.name)
    book_title = metadata_text(master_meta.get("title"), f"{book_id} - {tl_name}")

    chapter_files = sorted(path for path in tl_path.glob("*.md") if path.name != "metadata.md")
    if args.limit:
        chapter_files = chapter_files[: args.limit]
    if not chapter_files:
        print(f"Skipping {tl_path.name}: no chapter markdown files")
        return None

    print(f"Processing {book_id}/{tl_name}: {len(chapter_files)} chapter(s)")

    chapters: list[Chapter] = []
    for fallback, path in enumerate(chapter_files):
        metadata, content = load_markdown(path)
        title = first_heading(content) or metadata_text(metadata.get("title"), path.stem)
        slug = metadata_text(metadata.get("slug"), path.stem)
        chapters.append(
            Chapter(
                path=path,
                metadata=metadata,
                content=content,
                title=title,
                index=sort_value(metadata, fallback),
                slug=slug,
            )
        )

    chapters.sort(key=lambda chapter: (chapter.index, chapter.path.name))

    tweet_cache = load_tweet_cache()
    assets: dict[Path, EpubAsset] = {}
    asset_names: set[str] = set()

    cover_asset: EpubAsset | None = None
    cover_item: EpubItem | None = None
    cover_image_path = IMAGES_ROOT / book_id / "cover.webp"
    if cover_image_path.exists():
        cover_src = convert_to_png(cover_image_path, OUTPUT_DIR / "cover_images") or cover_image_path
        cover_name = unique_asset_name(cover_src, "cover.png" if cover_src.suffix.lower() == ".png" else cover_src.name, asset_names)
        cover_asset = EpubAsset(
            source_path=cover_src,
            href=f"Images/{cover_name}",
            media_type=media_type_for(cover_src),
        )
        assets[cover_src] = cover_asset
        cover_body = (
            '<div class="cover-page">'
            f'<img src="../{escape_attr(cover_asset.href)}" alt="Cover" class="cover-image" />'
            "</div>"
        )
        cover_item = EpubItem(
            item_id="cover",
            href="Text/cover.xhtml",
            title="Cover",
            body=cover_body,
        )
        print(f"  Cover: {cover_asset.href}")

    items: list[EpubItem] = []

    today = dt.date.today()
    pretty_date = f"{today:%B} {today.day}, {today:%Y}"
    master_content = master_content.replace("{{DATE}}", pretty_date)

    info_ctx = RenderContext(book_id, metadata_path, assets, asset_names, tweet_cache, not args.no_fetch_twitter)
    info_body = render_blocks(master_content, info_ctx)
    items.append(
        EpubItem(
            item_id="xhtml0000",
            href="Text/0000_Information.xhtml",
            title="Information",
            body=info_body,
        )
    )

    for position, chapter in enumerate(chapters, start=1):
        print(f"  [{position}/{len(chapters)}] {chapter.title}")
        ctx = RenderContext(book_id, chapter.path, assets, asset_names, tweet_cache, not args.no_fetch_twitter)
        body = render_blocks(chapter.content, ctx)
        href = f"Text/{chapter_output_name(position, chapter)}"
        items.append(
            EpubItem(
                item_id=f"xhtml{position:04d}",
                href=href,
                title=chapter.title,
                body=body,
            )
        )

    output_name = f"{book_title} - {tl_name} [Default].epub"
    epub_path = OUTPUT_DIR / output_name
    write_epub(epub_path, book_title, master_meta, items, assets, cover_item, cover_asset)
    save_tweet_cache(tweet_cache)
    print(f"  Done -> {epub_path}")
    return epub_path


def find_chapter_dirs(book_id: str) -> list[Path]:
    root = CHAPTERS_ROOT / book_id
    if book_id == "gsgw":
        return [root / "fantl", root / "unfinishedtl", root / "MTL"]
    if book_id == "debut":
        return [root / "DebutFormatted", root / "DebutPlainTxt"]
    return []


def load_all_chapters(chapter_dirs: list[Path], limit: int | None = None) -> list[Chapter]:
    chapters: list[Chapter] = []
    total_files = 0
    for dir_path in chapter_dirs:
        chapter_files = sorted(path for path in dir_path.glob("*.md") if path.name != "metadata.md")
        remaining = None
        if limit is not None:
            remaining = limit - total_files
            if remaining <= 0:
                break
            chapter_files = chapter_files[:remaining]
        for fallback, path in enumerate(chapter_files):
            metadata, content = load_markdown(path)
            title = first_heading(content) or metadata_text(metadata.get("title"), path.stem)
            slug = metadata_text(metadata.get("slug"), path.stem)
            chapters.append(
                Chapter(
                    path=path, metadata=metadata, content=content,
                    title=title, index=sort_value(metadata, fallback), slug=slug,
                )
            )
            total_files += 1
    chapters.sort(key=lambda c: (c.index, c.path.name))
    return chapters


def chapter_in_part(chapter: Chapter, part_def: dict[str, Any]) -> bool:
    if "category" in part_def:
        return chapter.metadata.get("category") == part_def["category"]
    if "max_index" in part_def and chapter.index > part_def["max_index"]:
        return False
    if "min_index" in part_def and chapter.index < part_def["min_index"]:
        return False
    return True


def build_plaintext_part_epub(
    epub_path: Path,
    book_title: str,
    metadata: dict[str, Any],
    items: list[EpubItem],
    assets: dict[Path, EpubAsset],
    asset_names: set[str],
    cover_item: EpubItem | None = None,
    cover_asset: EpubAsset | None = None,
) -> None:
    css = CSS_PATH.read_text(encoding="utf-8")
    modified = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    identifier = metadata_text(metadata.get("identifier"), "")
    identifier = valid_identifier(identifier, book_title)
    asset_list = sorted(assets.values(), key=lambda asset: asset.href)

    epub_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(epub_path, "w") as zf:
        mimetype = zipfile.ZipInfo("mimetype")
        mimetype.compress_type = zipfile.ZIP_STORED
        zf.writestr(mimetype, "application/epub+zip")

        def write_text(name: str, data: str) -> None:
            zf.writestr(name, data.encode("utf-8"), compress_type=zipfile.ZIP_DEFLATED)

        write_text("META-INF/container.xml", container_xml())
        write_text("OEBPS/Styles/stylesheet.css", css)
        write_text("OEBPS/content.opf", content_opf(book_title, metadata, items, asset_list, modified, cover_asset, cover_item))
        write_text("OEBPS/toc.ncx", toc_ncx(book_title, identifier, items))
        write_text("OEBPS/nav.xhtml", nav_xhtml(book_title, items))

        if cover_item:
            write_text(f"OEBPS/{cover_item.href}", xhtml_page(cover_item.title, cover_item.body))

        for item in items:
            write_text(f"OEBPS/{item.href}", xhtml_page(item.title, item.body))

        for asset in asset_list:
            zf.write(asset.source_path, f"OEBPS/{asset.href}", compress_type=zipfile.ZIP_DEFLATED)


def build_windows_part_epub(
    epub_path: Path,
    book_title: str,
    metadata: dict[str, Any],
    items: list[EpubItem],
    assets: dict[Path, EpubAsset],
    asset_names: set[str],
    cover_item: EpubItem | None = None,
    cover_asset: EpubAsset | None = None,
) -> None:
    css = CSS_PATH.read_text(encoding="utf-8")
    modified = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    identifier = metadata_text(metadata.get("identifier"), "")
    identifier = valid_identifier(identifier, book_title)
    asset_list = sorted(assets.values(), key=lambda asset: asset.href)

    epub_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(epub_path, "w") as zf:
        mimetype = zipfile.ZipInfo("mimetype")
        mimetype.compress_type = zipfile.ZIP_STORED
        zf.writestr(mimetype, "application/epub+zip")

        def write_text(name: str, data: str) -> None:
            zf.writestr(name, data.encode("utf-8"), compress_type=zipfile.ZIP_DEFLATED)

        write_text("META-INF/container.xml", container_xml())
        write_text("OEBPS/Styles/stylesheet.css", css)
        write_text("OEBPS/content.opf", content_opf(book_title, metadata, items, asset_list, modified, cover_asset, cover_item))
        write_text("OEBPS/toc.ncx", toc_ncx(book_title, identifier, items))
        write_text("OEBPS/nav.xhtml", nav_xhtml(book_title, items))

        if cover_item:
            write_text(f"OEBPS/{cover_item.href}", xhtml_page(cover_item.title, cover_item.body))

        for item in items:
            write_text(f"OEBPS/{item.href}", xhtml_page(item.title, item.body))

        for asset in asset_list:
            zf.write(asset.source_path, f"OEBPS/{asset.href}", compress_type=zipfile.ZIP_DEFLATED)


def render_windows_and_assemble(
    chapters: list[Chapter],
    book_id: str,
    chapter_htmls: list[str],
    args: argparse.Namespace,
) -> tuple[list[str], dict[Path, EpubAsset], set[str]]:
    tweet_cache = load_tweet_cache()
    assets: dict[Path, EpubAsset] = {}
    asset_names: set[str] = set()
    window_dir = OUTPUT_DIR / "window_images"
    window_dir.mkdir(parents=True, exist_ok=True)

    render_tasks: list[tuple[int, WindowInfo, Path]] = []
    all_windows: list[list[WindowInfo]] = []
    window_counter = 0

    for ch_html in chapter_htmls:
        windows = find_window_divs(ch_html)
        all_windows.append(windows)
        for window in windows:
            img_path = window_dir / f"window_{window_counter:04d}.webp"
            render_tasks.append((window_counter, window, img_path))
            window_counter += 1

    total_windows = len(render_tasks)
    render_results: dict[int, tuple[Path, bool]] = {}

    if total_windows > 0 and sync_playwright is not None:
        import os as _os
        num_workers = min(_os.cpu_count() or 4, 8)
        print(f"  Rendering {total_windows} windows with {num_workers} workers...")

        import asyncio as _asyncio
        from playwright.async_api import async_playwright as _async_playwright

        async def _render_all() -> dict[int, tuple[Path, bool]]:
            results: dict[int, tuple[Path, bool]] = {}
            semaphore = _asyncio.Semaphore(num_workers)

            async def _render_one(
                sem: _asyncio.Semaphore,
                browser: Any,
                idx: int,
                window: WindowInfo,
                img_path: Path,
            ) -> tuple[int, Path, bool]:
                async with sem:
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
                            return idx, img_path, False
                        if Image is None:
                            img_path.write_bytes(png_bytes)
                            return idx, img_path, True
                        img = Image.open(BytesIO(png_bytes))
                        bbox = img.getbbox()
                        if bbox:
                            img = img.crop(bbox)
                        img.save(img_path, "WEBP", quality=85, method=4)
                        return idx, img_path, img_path.exists() and img_path.stat().st_size > 0
                    except Exception as e:
                        print(f"      Screenshot error: {e}")
                        return idx, img_path, False
                    finally:
                        await page.close()

            async with _async_playwright() as ap:
                browser = await ap.chromium.launch()
                coros = [_render_one(semaphore, browser, idx, window, img_path) for idx, window, img_path in render_tasks]
                done_count = 0
                for coro in _asyncio.as_completed(coros):
                    idx, img_path, success = await coro
                    results[idx] = (img_path, success)
                    done_count += 1
                    if done_count % 50 == 0 or done_count == total_windows:
                        print(f"    Rendered {done_count}/{total_windows}")
                await browser.close()
            return results

        render_results = _asyncio.run(_render_all())
        print(f"  Window rendering complete ({sum(1 for v in render_results.values() if v[1])}/{total_windows} succeeded)")
    elif total_windows > 0:
        print(f"  Warning: playwright not available, {total_windows} windows will use CSS fallback")

    assembled_htmls: list[str] = []
    window_counter = 0
    for ch_html, windows in zip(chapter_htmls, all_windows):
        parts: list[str] = []
        last_end = 0
        for window in windows:
            parts.append(ch_html[last_end:window.start])
            idx = window_counter
            img_path, success = render_results.get(idx, (None, False))
            if success and img_path and img_path.exists():
                img_name = img_path.name
                img_path_resolved = img_path.resolve()
                if img_path_resolved not in assets:
                    name = unique_asset_name(img_path, img_name, asset_names)
                    assets[img_path_resolved] = EpubAsset(
                        source_path=img_path_resolved,
                        href=f"Images/{name}",
                        media_type=media_type_for(img_path),
                    )
                asset = assets[img_path_resolved]
                alt_text = html.escape(window.class_name.replace("-", " "))
                parts.append(
                    f'<div class="image-block">'
                    f'<img src="../{escape_attr(asset.href)}" alt="{alt_text}" />'
                    f"</div>"
                )
            else:
                parts.append(f'<div class="{escape_attr(window.class_name)}">{window.inner_html}</div>')
            last_end = window.end
            window_counter += 1
        parts.append(ch_html[last_end:])
        assembled_htmls.append("".join(parts))

    save_tweet_cache(tweet_cache)
    return assembled_htmls, assets, asset_names


def build_book(args: argparse.Namespace) -> list[Path]:
    book_id = args.book
    chapter_dirs = find_chapter_dirs(book_id)
    if not chapter_dirs:
        print(f"No chapter directories found for book '{book_id}'")
        return []

    metadata_path = chapter_dirs[0] / "metadata.md"
    if not metadata_path.exists():
        print(f"No metadata.md found in {chapter_dirs[0]}")
        return []

    master_meta, master_content = load_markdown(metadata_path)
    book_title = metadata_text(master_meta.get("title"), book_id)
    short_name = BOOK_SHORT_NAME.get(book_id, sanitize_filename(book_title))
    part_defs = PART_DEFS.get(book_id, [])
    variants = VARIANTS.get(book_id, [])

    if not part_defs:
        print(f"No part definitions for book '{book_id}'")
        return []

    chapters = load_all_chapters(chapter_dirs, args.limit)
    if not chapters:
        print("No chapters found")
        return []

    print(f"Loaded {len(chapters)} chapters for {book_title}")

    today = dt.date.today()
    pretty_date = f"{today:%B} {today.day}, {today:%Y}"
    master_content = master_content.replace("{{DATE}}", pretty_date)

    built: list[Path] = []
    cover_asset_base: EpubAsset | None = None
    cover_item_base: EpubItem | None = None
    cover_image_path_base = IMAGES_ROOT / book_id / "cover.webp"

    if cover_image_path_base.exists():
        cover_src = convert_to_png(cover_image_path_base, OUTPUT_DIR / "cover_images") or cover_image_path_base
        asset_names_cover: set[str] = set()
        cover_name = unique_asset_name(cover_src, "cover.png" if cover_src.suffix.lower() == ".png" else cover_src.name, asset_names_cover)
        cover_asset_base = EpubAsset(
            source_path=cover_src,
            href=f"Images/{cover_name}",
            media_type=media_type_for(cover_src),
        )
        cover_body = (
            '<div class="cover-page">'
            f'<img src="../{escape_attr(cover_asset_base.href)}" alt="Cover" class="cover-image" />'
            "</div>"
        )
        cover_item_base = EpubItem(
            item_id="cover",
            href="Text/cover.xhtml",
            title="Cover",
            body=cover_body,
        )
        print(f"  Cover: {cover_asset_base.href}")

    tweet_cache = load_tweet_cache()

    for variant in variants:
        variant_label = variant["label"]
        print(f"\nBuilding {variant_label} variant...")

        for part_def in part_defs:
            part_chapters = [c for c in chapters if chapter_in_part(c, part_def)]
            if not part_chapters:
                print(f"  {part_def['label']}: no chapters, skipping")
                continue

            print(f"  {part_def['label']} ({part_def['range']}): {len(part_chapters)} chapters")

            full_name = sanitize_filename(book_title)
            output_name = f"{full_name} - {part_def['label']} [{variant_label}]"
            output_name = re.sub(r'[ ,]', '.', output_name).replace('[', '').replace(']', '')
            output_name = re.sub(r'\.+', '.', output_name) + '.epub'
            epub_path = OUTPUT_DIR / output_name

            assets: dict[Path, EpubAsset] = {}
            asset_names: set[str] = set()
            cover_asset = None
            cover_item = None

            if cover_asset_base:
                assets[cover_image_path_base] = cover_asset_base
                asset_names.add(cover_name)
                cover_asset = cover_asset_base
                cover_item = cover_item_base

            info_ctx = RenderContext(book_id, metadata_path, assets, asset_names, tweet_cache, not args.no_fetch_twitter)
            info_body = render_blocks(master_content, info_ctx)

            items: list[EpubItem] = [
                EpubItem(
                    item_id="xhtml0000",
                    href="Text/0000_Information.xhtml",
                    title="Information",
                    body=info_body,
                )
            ]

            chapter_htmls: list[str] = []
            for position, chapter in enumerate(part_chapters, start=1):
                print(f"    [{position}/{len(part_chapters)}] {chapter.title}")
                ctx = RenderContext(book_id, chapter.path, assets, asset_names, tweet_cache, not args.no_fetch_twitter)
                body = render_blocks(chapter.content, ctx)
                href = f"Text/{chapter_output_name(position, chapter)}"
                chapter_htmls.append(body)
                items.append(
                    EpubItem(
                        item_id=f"xhtml{position:04d}",
                        href=href,
                        title=chapter.title,
                        body=body,
                    )
                )

            if variant["id"] == "windows":
                assembled_htmls, window_assets, extra_names = render_windows_and_assemble(
                    part_chapters, book_id, chapter_htmls, args
                )
                assets.update(window_assets)
                asset_names.update(extra_names)
                for i, body in enumerate(assembled_htmls):
                    items[i + 1].body = body

            if variant["id"] == "windows":
                build_windows_part_epub(epub_path, book_title, master_meta, items, assets, asset_names, cover_item, cover_asset)
            else:
                build_plaintext_part_epub(epub_path, book_title, master_meta, items, assets, asset_names, cover_item, cover_asset)

            print(f"    Done -> {epub_path}")
            built.append(epub_path)

    save_tweet_cache(tweet_cache)
    return built


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build per-part EPUBs from chapter markdown.")
    parser.add_argument("--book", default="gsgw", help="Book folder under chapters/ to build.")
    parser.add_argument("--limit", type=int, help="Build only the first N chapters total, useful for testing.")
    parser.add_argument(
        "--no-fetch-twitter",
        action="store_true",
        help="Use cached Twitter WebPs only; leave missing tweet images as links.",
    )
    return parser.parse_args()


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = parse_args()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TWITTER_IMG_DIR.mkdir(parents=True, exist_ok=True)

    built = build_book(args)

    if not built:
        print("No EPUBs built.")
        return

    print("\nBuilt EPUBs:")
    for path in built:
        print(f"  {path}")


if __name__ == "__main__":
    main()
