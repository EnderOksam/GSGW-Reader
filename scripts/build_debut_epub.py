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

ALL_WINDOW_CLASSES = (
    "debut-window(?!-)|debut-alert(?!-)|debut-achievement(?!-)|sms-window|alert-window|"
    "wiki-window|record-window|black-window|system-window|plain-window|"
    "followup-window|note-window|sticky-window|braun-screen"
)

WINDOW_CLASS_RE = re.compile(
    rf'<div class="((?:{ALL_WINDOW_CLASSES})[^"]*)">'
)

WINDOW_CSS = """
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

/* Debut Window */
.debut-window {
  position: relative;
  width: min(430px, 90%);
  margin: 2rem auto;
  padding: 2rem 2.5rem;
  color: #fff !important;
  text-align: center;
  background: #1e1e30;
  border: 2px solid rgba(255,255,255,.85);
  box-shadow:
    0 0 10px rgba(255,255,255,.45),
    0 0 25px rgba(170,210,255,.25),
    inset 0 0 25px rgba(255,255,255,.08);
}
.debut-window::before {
  content: "";
  position: absolute;
  inset: 8px;
  border: 1px solid rgba(255,255,255,.55);
  pointer-events: none;
}
.debut-window p { color: #fff; }
.debut-window .debut-window-label {
  display: block;
  padding: .15rem 1.2rem;
  background: rgba(255,255,255,.25);
  border-radius: 4px;
  font-size: .85em;
  text-align: center;
  width: fit-content;
  margin: .3rem auto;
}
.debut-window .debut-window-title {
  position: absolute;
  top: -.6rem;
  left: 50%;
  transform: translateX(-50%);
  padding: .05rem .9rem;
  font-size: .75em;
  background: #1e1e30;
  border: 2px solid rgba(255,255,255,.8);
  text-transform: uppercase;
  letter-spacing: .08em;
  font-weight: 700;
  text-align: center;
  white-space: nowrap;
  box-shadow: 0 0 10px rgba(255,255,255,.4), inset 0 0 8px rgba(255,255,255,.08);
}

/* Debut Alert */
.debut-alert {
  position: relative;
  width: min(430px, 95%);
  margin: 2rem auto;
  padding: 2rem 2.5rem;
  color: #fff !important;
  text-align: left;
  background: #b01030;
  border: 2px solid rgba(255,120,140,.9);
  box-shadow:
    0 0 10px rgba(255,50,80,.6),
    0 0 25px rgba(255,50,80,.3),
    inset 0 0 25px rgba(255,50,80,.12);
}
.debut-alert::before {
  content: "";
  position: absolute;
  inset: 8px;
  border: 1px solid rgba(255,120,140,.55);
  pointer-events: none;
}
.debut-alert p { color: #fff; }
.debut-alert-center { text-align: center; }

/* Debut Achievement */
.debut-achievement {
  position: relative;
  width: min(430px, 90%);
  margin: 2rem auto;
  padding: 2rem 2.5rem;
  color: #fff !important;
  text-align: center;
  background: #234670;
  border: 2px solid rgba(255,255,255,.85);
  box-shadow:
    0 0 10px rgba(100,160,255,.45),
    0 0 25px rgba(100,160,255,.25),
    inset 0 0 25px rgba(100,160,255,.08);
}
.debut-achievement::before {
  content: "";
  position: absolute;
  inset: 8px;
  border: 1px solid rgba(255,255,255,.4);
  pointer-events: none;
}
.debut-achievement p { color: #fff; }
.debut-achievement-sub {
  display: block;
  padding: .15rem .75rem;
  margin: .3rem auto;
  background: rgba(255,255,255,.25);
  font-size: .85em;
  text-align: center;
  width: fit-content;
}
.debut-achievement-list {
  border: 4px solid rgba(255,255,255,.6);
  background: #305582;
  font-size: .95em;
  display: block;
  margin: .3rem auto;
  width: fit-content;
  text-align: center;
  box-shadow: 0 0 12px rgba(100,160,255,.35);
}
.debut-achievement-list-item { padding: .5rem 1.25rem; }
.debut-achievement-list-divider {
  height: 1px;
  background: linear-gradient(to right, transparent, rgba(100,160,255,.5) 20%, rgba(100,160,255,.5) 80%, transparent);
}
.debut-achievement-sub-left,
.debut-achievement-sub-right,
.alert-sub-left,
.alert-sub-right {
  --border: rgba(255,255,255,.85);
  --outline: rgba(180,220,255,.35);
  position: relative;
  display: inline-block;
  padding: .35rem 1.25rem;
  font-size: .9em;
  color: white;
  background: linear-gradient(180deg, #6fa8ff 0%, #4f86db 40%, #3568b7 100%);
  border: 3px solid var(--border);
  clip-path: polygon(10px 0, 100% 0, 100% calc(100% - 10px), calc(100% - 10px) 100%, 0 100%, 0 10px);
  box-shadow: 0 0 12px var(--outline), inset 0 0 6px rgba(255,255,255,.1);
}
.alert-sub-left,
.alert-sub-right {
  --border: rgba(255,120,140,.9);
  --outline: rgba(255,50,80,.35);
  background: linear-gradient(180deg, #d03050 0%, #b01030 40%, #8a0a25 100%);
}
.alert-sub-left { margin-right: .5rem; }
.alert-sub-right { margin-left: .5rem; }

.debut-achievement-sub-left::before,
.debut-achievement-sub-right::before,
.alert-sub-left::before,
.alert-sub-right::before {
  content: "";
  position: absolute;
  left: -7px;
  top: -7px;
  width: 22px;
  height: 22px;
  border-top: 3px solid var(--border);
  border-left: 3px solid var(--border);
  opacity: .9;
}

.debut-achievement-sub-left::after,
.debut-achievement-sub-right::after,
.alert-sub-left::after,
.alert-sub-right::after {
  content: "";
  position: absolute;
  right: -7px;
  bottom: -7px;
  width: 22px;
  height: 22px;
  border-right: 3px solid var(--border);
  border-bottom: 3px solid var(--border);
  opacity: .9;
}

/* SMS Window */
.sms-window {
  position: relative;
  width: min(430px, 95%);
  margin: 2rem auto;
  padding: 1rem 1rem;
  background: var(--window-bg);
  color: #fff !important;
  text-align: left;
  border: 2px solid #555;
  border-radius: 12px;
  box-shadow: 0 0 0 6px #444, 0 0 0 8px #555;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.sms-bubble {
  max-width: 80%;
  padding: 8px 14px;
  border-radius: 14px;
  font-size: 0.95em;
  line-height: 1.45;
  position: relative;
  z-index: 2;
  word-wrap: break-word;
}
.sms-left {
  align-self: flex-start;
  background: #3a3a4e;
  border-bottom-left-radius: 4px;
}
.sms-right {
  align-self: flex-end;
  background: #eae391;
  color: #222;
  border-bottom-right-radius: 4px;
}
.sms-center {
  align-self: center;
  background: transparent;
  font-style: italic;
  opacity: 0.8;
  font-size: 0.85em;
}

/* Alert/Comment Window */
.alert-window {
  position: relative;
  width: min(430px, 95%);
  margin: 2rem auto;
  padding: 0;
  background: #fff;
  color: #222 !important;
  text-align: left;
  border: 2px solid #555;
  border-radius: 12px;
  box-shadow: 0 0 0 6px #bbb, 0 0 0 8px #555;
  overflow: hidden;
}
.alert-window p { color: #222; }
.comment-post-header {
  padding: 1.25rem 1.5rem 0.75rem;
  background: transparent;
  border-bottom: 1px solid #d0d0d0;
}
.comment-post-title {
  text-align: left;
  font-size: 1.2em;
  font-weight: 700;
  color: #111;
  margin-bottom: 0.2rem;
}
.comment-post-desc {
  text-align: justify;
  font-size: 0.82em;
  color: #777;
  font-style: italic;
}
.comment-section { padding: 0.5rem 1.25rem 1rem; }
.comment {
  padding: 0.5rem 0.6rem;
  margin: 0.7rem 0;
  background: #eee;
  border: 1px solid #ccc;
  border-radius: 7px;
  font-size: 0.92em;
  color: #333;
  line-height: 1.5;
}
.comment-reply {
  display: flex;
  align-items: flex-start;
  gap: 0.35rem;
  padding: 0.35rem 0.6rem;
  border-radius: 6px;
  font-size: 0.88em;
  margin-top: 0.5rem;
}
.comment-reply.depth-1 { margin-left: 1.2rem; background: #d2d2d2; border: 1px solid #bbb; }
.comment-reply.depth-2 { margin-left: 2rem; background: #c8c8c8; border: 1px solid #aaa; }
.comment-reply.depth-3 { margin-left: 2.8rem; background: #bebebe; border: 1px solid #999; }
.reply-icon { flex-shrink: 0; font-size: 0.7em; color: #999; line-height: 1.6; }
.reply-body { color: #444; text-align: justify; }

/* --- WIKI WINDOW --- */
.wiki-window {
  margin: 2.5rem auto;
  background: var(--window-bg);
  border: 1px solid var(--window-border);
  border-radius: 8px;
  max-width: 98%;
  position: relative;
  box-shadow: 0 4px 24px rgba(0,0,0,0.4);
  padding: 1em 1em 0.75em;
  text-align: left;
  color: var(--window-text) !important;
}
.wiki-window::before {
  content: "\\2014  \\25A1  X";
  display: flex;
  justify-content: flex-end;
  background: var(--window-border);
  color: #ffffff;
  padding: 0.375em 0.875em;
  font-family: monospace;
  font-size: 1em;
  letter-spacing: 0.375em;
  margin: -1em -1em 0.75em;
  border-bottom: 1px solid var(--window-border);
  border-radius: 8px 8px 0 0;
}
.wiki-window p {
  color: var(--window-text) !important;
  margin: 0.8em 0;
  line-height: 1.6;
  text-align: left;
}
.wiki-window:not(.no-meta) p:first-of-type {
  font-size: 0.8em;
  opacity: 0.6;
  text-align: right;
  margin-bottom: 0.3em;
}
.wiki-window strong, .wiki-window b { color: inherit; font-weight: 700; }
.wiki-window p strong:only-child,
.wiki-window p strong:first-child:not(b strong) {
  display: block; font-size: 1.25em; margin: 1em 0 0.8em;
}

/* --- RECORD WINDOW --- */
.record-window {
  margin: 2.5rem auto;
  background: #1d2350;
  border: 1px solid rgba(255,255,255,0.15);
  border-radius: 8px;
  max-width: 98%;
  position: relative;
  box-shadow: 0 4px 24px rgba(0,0,0,0.4);
  padding: 1em 1em 0.75em;
  text-align: left;
  color: #ffffff !important;
}
.record-window::before {
  content: "\\2014  \\25A1  X";
  display: flex;
  justify-content: flex-end;
  background: rgba(0,0,0,0.25);
  color: #ffffff;
  padding: 0.375em 0.875em;
  font-family: monospace;
  font-size: 1em;
  letter-spacing: 0.375em;
  margin: -1em -1em 0.75em;
  border-bottom: 1px solid rgba(255,255,255,0.1);
  border-radius: 8px 8px 0 0;
}
.record-window p {
  color: #ffffff !important;
  margin: 0.8em 0;
  line-height: 1.6;
  text-align: left;
}
.record-window:not(.no-meta) p:first-of-type {
  font-size: 0.8em;
  opacity: 0.6;
  text-align: right;
  margin-bottom: 0.3em;
}
.record-window strong, .record-window b { color: inherit; font-weight: 700; }

/* --- PLAIN WINDOW --- */
.plain-window, .followup-window {
  margin: 2.5rem auto;
  background: var(--window-bg);
  border: 1px solid var(--window-border);
  border-radius: 8px;
  max-width: 98%;
  position: relative;
  box-shadow: 0 4px 24px rgba(0,0,0,0.4);
  padding: 1.5em 2em 1em;
  text-align: left;
  color: var(--window-text) !important;
}
.plain-window p, .followup-window p {
  color: var(--window-text) !important;
  margin: 0.8em 0;
  line-height: 1.6;
  text-align: left;
}

/* --- NOTE WINDOW --- */
.note-window {
  margin: 2.5rem auto;
  background: #fefce8;
  border: 1px solid #e6dec0;
  border-radius: 4px;
  max-width: 98%;
  position: relative;
  box-shadow: -4px 4px 0 #d4c060, 0 4px 24px rgba(0,0,0,0.12);
  padding: 1em 1.25em 0.75em;
  text-align: left;
  overflow: hidden;
}
.note-window::before {
  content: "";
  display: block;
  background: #edd44d;
  height: 0.875em;
  margin: -1em -1.25em 0.75em;
  border-radius: 4px 4px 0 0;
}
.note-window p {
  color: #000000;
  margin: 0.8em 0;
  line-height: 1.7;
  text-align: left;
}
.note-window:not(.no-meta) p:first-of-type {
  color: #4a6fa5;
  font-size: 1.35em;
  font-weight: 600;
}

/* --- STICKY WINDOW --- */
.sticky-window {
  margin: 2.5rem auto;
  background: #fefce8;
  border: 1px solid #e6dec0;
  border-radius: 2px;
  max-width: 25em;
  min-height: 15.625em;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  position: relative;
  box-shadow: -3px 3px 0 #d4c060, 0 4px 24px rgba(0,0,0,0.12);
  padding: 1.5em;
  text-align: center;
  color: #000000 !important;
}
.sticky-window p {
  color: #000000 !important;
  margin: 0.3em 0;
  line-height: 1.7;
  text-align: center;
}

/* --- BLACK WINDOW --- */
.black-window {
  margin: 2.5rem auto;
  background: #000000;
  border: 1px solid #333;
  border-radius: 4px;
  max-width: 88%;
  position: relative;
  box-shadow: 0 0 20px rgba(0,0,0,0.6);
  padding: 1.5em 2em 1em;
  text-align: center;
  font-weight: 700;
  font-size: 1.3em;
  color: #ffffff !important;
  text-shadow: 0 0 10px rgba(255,255,255,0.7), 0 0 20px rgba(255,255,255,0.4);
  background-image: repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(255,255,255,0.03) 2px, rgba(255,255,255,0.03) 4px);
}
.black-window p {
  color: #ffffff;
  margin: 0.8em 0;
  line-height: 1.6;
  text-align: center;
}

/* --- SYSTEM WINDOW --- */
.system-window {
  margin: 2.5rem auto;
  background: #1a1a1a;
  border: 1px solid #444;
  border-radius: 4px;
  max-width: 88%;
  position: relative;
  box-shadow: 0 0 20px rgba(0,0,0,0.6);
  padding: 1.5em 2em 1em;
  text-align: center;
  font-weight: 700;
  color: #ffffff !important;
}
.system-window::before {
  content: '';
  position: absolute;
  inset: 8px;
  box-shadow: inset 0 0 0 1px #888, inset 0 0 0 5px #888;
  pointer-events: none;
}
.system-window p {
  color: #ffffff !important;
  margin: 0.8em 0;
  line-height: 1.6;
  text-align: center;
}
.system-window:not(.no-fl-dividers) > p:first-of-type {
  padding: 0.75em 0;
  font-size: 1.25em;
  background-image:
    linear-gradient(90deg, transparent, #888, transparent),
    linear-gradient(90deg, transparent, #888, transparent);
  background-repeat: no-repeat;
  background-size: 80% 1px;
  background-position: center top, center bottom;
}

/* --- BRAUN SCREEN --- */
.braun-screen {
  margin: 2.5rem auto;
  background: radial-gradient(ellipse at center, #050504 0%, #030302 60%, #020201 100%);
  border: 10px solid #4f4642;
  border-radius: 36px;
  max-width: 90%;
  position: relative;
  box-shadow: 0 0 30px rgba(0,0,0,0.8), inset 0 0 60px rgba(0,0,0,0.3);
  padding: 6em 0.5em;
  text-align: center;
  font-family: 'Courier New', Courier, monospace;
  font-size: 2em;
  color: #ffffff !important;
  text-shadow: 0 0 5px rgba(255,255,255,0.4), 0 0 15px rgba(255,255,255,0.15);
  overflow: hidden;
}
.braun-screen::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 22px;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='150' height='150'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='150' height='150' filter='url(%23n)' opacity='0.8'/%3E%3C/svg%3E");
  background-repeat: repeat;
  background-size: 150px 150px;
  opacity: 0.20;
  pointer-events: none;
  z-index: 2;
  mix-blend-mode: screen;
}
.braun-screen::after {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 22px;
  background:
    repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(255,255,255,0.02) 2px, rgba(255,255,255,0.02) 4px),
    radial-gradient(ellipse at center, transparent 50%, rgba(0,0,0,0.5) 100%);
  pointer-events: none;
  z-index: 1;
}
.braun-screen p {
  color: #ffffff;
  margin: 0.8em 0;
  line-height: 1.6;
  text-align: center;
  position: relative;
  z-index: 3;
}

/* --- WINDOW SEP --- */
.window-sep { text-align: center; margin: 1em 0; }
.window-small { font-size: 0.85em; }

/* Inline text effects */
.text-large { font-size: 1.04em; font-weight: bold; }
.text-large-centered { display: block; text-align: center; font-size: 1.04em; font-weight: bold; }
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
.mono-right { display: block; text-align: right; }
.align-left { display: block; text-align: left; }
.align-center { display: block; text-align: center; }
.align-right { display: block; text-align: right; }
.handwritten { font-family: 'Caveat', cursive; font-size: 1.2em; }
.contaminated { font-family: 'Comic Sans MS', cursive; }
.glitch-text { opacity: 0.8; text-shadow: 1px 0 0 #cc2200, -1px 0 0 #2255cc; }
.glitch-subtle { opacity: 0.9; text-shadow: 0.5px 0.5px 0 #777; }

/* Text effects missing from window CSS */
.shake { display: inline-block; font-weight: 700; }
.aurora-text {
  display: inline-block; font-weight: 800;
  background: linear-gradient(135deg, #00c2ff, #33ff8c, #ffc640, #e54cff, #00c2ff);
  background-size: 300% 300%; background-position: 50% 50%;
  -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
  filter: drop-shadow(0 0 6px rgba(0,194,255,0.2)) drop-shadow(0 0 15px rgba(229,76,255,0.1));
}
.smoke-text {
  font-weight: 700; letter-spacing: 0.2em; color: black;
  text-shadow: .06em 0 0 rgba(255,200,0,.9), -.06em 0 0 rgba(255,200,0,.9),
    0 .06em 0 rgba(255,200,0,.9), 0 -.06em 0 rgba(255,200,0,.9),
    .04em .04em 0 rgba(255,200,0,.9), -.04em .04em 0 rgba(255,200,0,.9),
    .04em -.04em 0 rgba(255,200,0,.9), -.04em -.04em 0 rgba(255,200,0,.9),
    .08em 0 0 rgba(255,200,0,.9), -.08em 0 0 rgba(255,200,0,.9),
    0 .08em 0 rgba(255,200,0,.9), 0 -.08em 0 rgba(255,200,0,.9);
}
.gold-text {
  position: relative; display: inline-block; font-weight: 800;
  background: linear-gradient(90deg, transparent 25%, rgba(255,255,255,0.3) 46%, rgba(255,255,255,0.5) 50%, rgba(255,255,255,0.3) 54%, transparent 75%),
    repeating-linear-gradient(65deg, transparent 0px, transparent 3px, rgba(255,215,100,0.08) 3px, rgba(255,215,100,0.08) 5px),
    #E8C24A;
  background-size: 200px 100%, auto, auto;
  -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
  -webkit-text-stroke: 1.2px #5b3912; text-stroke: 1.2px #5b3912;
  filter: drop-shadow(0 0 5px rgba(212,160,23,0.35));
}
.silver-text {
  position: relative; display: inline-block; font-weight: 800;
  background: linear-gradient(90deg, transparent 25%, rgba(255,255,255,0.3) 46%, rgba(255,255,255,0.5) 50%, rgba(255,255,255,0.3) 54%, transparent 75%),
    repeating-linear-gradient(65deg, transparent 0px, transparent 3px, rgba(192,192,192,0.08) 3px, rgba(192,192,192,0.08) 5px),
    #C0C0C0;
  background-size: 200px 100%, auto, auto;
  -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
  -webkit-text-stroke: 1.2px #666; text-stroke: 1.2px #666;
  filter: drop-shadow(0 0 5px rgba(160,160,160,0.35));
}
.sparkle-text { position: relative; display: inline-block; }
.moon-text {
  position: relative; display: inline-block; font-weight: 800;
  background: linear-gradient(90deg, transparent 25%, rgba(255,255,255,0.35) 46%, rgba(255,255,255,0.55) 50%, rgba(255,255,255,0.35) 54%, transparent 75%),
    repeating-linear-gradient(65deg, transparent 0px, transparent 3px, rgba(180,220,255,0.08) 3px, rgba(180,220,255,0.08) 5px),
    linear-gradient(135deg, #8ab8e0 0%, #c0dff5 35%, #e8f4ff 65%, #ffffff 100%);
  background-size: 200px 100%, auto, auto;
  -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
  -webkit-text-stroke: 1.2px #6aacdf; text-stroke: 1.2px #6aacdf;
  filter: drop-shadow(0 0 5px rgba(100,180,230,0.35));
}
"""


@dataclass
class WindowInfo:
    start: int
    end: int
    class_name: str
    inner_html: str
    width: int = 430


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


def find_window_divs(html_content: str) -> list[WindowInfo]:
    """Find window divs in HTML and return their positions and content."""
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
    """Render a window div as a transparent WebP image using playwright."""
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
        img.save(output_path, "WEBP", quality=90, method=6)
        return output_path.exists() and output_path.stat().st_size > 0
    except Exception as e:
        print(f"      Screenshot error: {e}")
        return False


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
            img.save(webp_path, "WEBP", quality=90, method=6)
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


def build_debut_epub(args: argparse.Namespace) -> Path | None:
    """Build the debut EPUB with windows rendered as WebP images."""
    md_dir = CHAPTERS_ROOT / "debut" / "DebutFormatted"
    metadata_path = md_dir / "metadata.md"
    if not metadata_path.exists():
        print(f"No metadata.md at {metadata_path}")
        return None

    master_meta, master_content = epub.load_markdown(metadata_path)
    book_id = epub.metadata_text(master_meta.get("metaBook"), "debut")
    tl_name = epub.metadata_text(master_meta.get("metaTl"), "DebutFormatted")
    book_title = epub.metadata_text(master_meta.get("title"), "Debut or Die")

    chapter_files = sorted(
        p for p in md_dir.glob("*.md") if p.name != "metadata.md"
    )
    if not chapter_files:
        print("No chapter files found")
        return None

    print(f"Building {book_title}: {len(chapter_files)} chapters")

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
        print(f"  Cover: {cover_asset.href}")

    today = dt.date.today()
    pretty_date = f"{today:%B} {today.day}, {today:%Y}"
    master_content = master_content.replace("{{DATE}}", pretty_date)

    info_html = convert_chapter_debut(master_content)
    items: list[epub.EpubItem] = [
        epub.EpubItem(
            item_id="xhtml0000",
            href="Text/0000_Information.xhtml",
            title="Information",
            body=info_html,
        )
    ]

    # ── Phase 1: Collect ──────────────────────────────────────────────
    print("Phase 1: Converting chapters and collecting windows...")

    @dataclass
    class ChapterInfo:
        position: int
        chapter_path: Path
        meta: Any
        content: str
        title: str
        chapter_html: str
        windows: list[WindowInfo]

    chapters: list[ChapterInfo] = []
    render_tasks: list[tuple[int, WindowInfo, Path]] = []
    window_counter = 0

    for position, chapter_path in enumerate(chapter_files, start=1):
        print(f"  [{position}/{len(chapter_files)}] {chapter_path.stem}")
        meta, content = epub.load_markdown(chapter_path)
        title = epub.first_heading(content) or epub.metadata_text(meta.get("title"), chapter_path.stem)
        chapter_html = convert_chapter_debut(content)
        chapter_html = _resolve_chapter_images(chapter_html, chapter_path, book_id, assets, asset_names)
        windows = find_window_divs(chapter_html)

        if windows:
            print(f"    {len(windows)} window(s) to render")

        chapters.append(ChapterInfo(position, chapter_path, meta, content, title, chapter_html, windows))

        for window in windows:
            webp_path = window_dir / f"window_{window_counter:04d}.webp"
            render_tasks.append((window_counter, window, webp_path))
            window_counter += 1

    total_windows = len(render_tasks)
    print(f"  {len(chapters)} chapters, {total_windows} windows to render")

    # ── Phase 2: Render windows in parallel ──────────────────────────
    render_results: dict[int, tuple[Path, bool]] = {}

    if total_windows > 0:
        num_workers = min(os.cpu_count() or 4, 8)
        print(f"Phase 2: Rendering {total_windows} windows with {num_workers} workers...")

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
                        print(f"  Rendered {done_count}/{total_windows}")
                await browser.close()
            return results

        render_results = asyncio.run(_render_all())
        print("Phase 2 complete")
    else:
        print("Phase 2: No windows to render")

    # ── Phase 3: Assemble ────────────────────────────────────────────
    print("Phase 3: Assembling EPUB...")
    window_counter = 0

    for ch in chapters:
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
                    f'</div>'
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

    output_name = f"{book_title} - {tl_name} [Default].epub"
    epub_path = OUTPUT_DIR / output_name
    epub.write_epub(epub_path, book_title, master_meta, items, assets, cover_item, cover_asset)
    print(f"  Done -> {epub_path}")
    return epub_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Debut EPUB with WebP windows.")
    return parser.parse_args()


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = parse_args()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    epub_path = build_debut_epub(args)
    if epub_path:
        print(f"\nBuilt: {epub_path}")
    else:
        print("No EPUB built.")


if __name__ == "__main__":
    main()
