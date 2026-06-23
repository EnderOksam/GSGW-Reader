# How to Contribute

Welcome to the **GSGW-Reader** project!

First off, **thank you** for considering contributing. This project relies on fans like you to fix typos, improve formatting, and ensure the reading experience is perfect for everyone.

**Don't worry if you are not a programmer or have never used GitHub before.** This guide is written specifically for you! You cannot "break" the website, so feel free to jump in.

---

## Quick Links

| Resource | What it is |
|----------|------------|
| [Discord Server](https://discord.gg/XmzJVsyuTQ) | Report issues, ask questions, or suggest improvements |

---

## 🚀 How to Edit (Browser)

### Step 1: Find the Chapter
1.  Navigate to the `chapters` folder in this repository.
2.  Click on the story folder.
3.  Click on the translation source folder.
4.  Find the `.md` file for the chapter (e.g., `1.md`).

### Step 2: Click the Pencil
1.  Click the **Pencil Icon** (✏️) at the top-right of the file view.
2.  *No GitHub account?* Sign up — it's free and takes a minute.
3.  GitHub will create a "fork" (your own copy) automatically.

### Step 3: Make Your Changes
1.  Edit in the web editor.
2.  Use the **Preview** tab to check how it looks.
3.  Use the tags below to format text.

### Step 4: Save & Submit
1.  Scroll to **"Commit changes"** at the bottom.
2.  Write a short description (e.g., "Fixed typo in paragraph 3").
3.  Click **"Propose changes"** → **"Create pull request"** → **"Create pull request"**.

🎉 Done! A maintainer will review and merge your changes.

---

## 📝 Formatting Tags

This project uses **custom formatting tags** for text effects, colored text, styled windows, and more. **Standard Markdown** (bold, italic, headers) also works.

### Basic Rules
- Tags are **case-sensitive** — use exact capitalization shown
- Don't use HTML unless you know what you're doing
- Keep formatting consistent with other chapters
- Look at other chapters if you're unsure

### Windows / Boxes

| Tag | What It's For |
|-----|---------------|
| `+-` & `-+` | Info/record (DER) window (has titlebar) |
| `&-` & `-&` | Disaster Management Bureau record window (has titlebar) |
| `+~` & `~+` | System/notification window |
| `+=` & `=+` | Screen display window (subtle CRT effect) |
| `+$` & `$+` | Follow-up (DER) window (no titlebar) |
| `&$` & `$&` | Follow up (DMB) window (no titlebar) |
| `!-` & `-!` | Notepad window (pale yellow, blue header) |
| `!$` & `$!` | Sticky note |

To add a titlebar, put text on the first line inside the window. Put `\` before bold/italic text on the first line to cancel the titlebar.

| Style | How to Type |
|-------|-------------|
| With titlebar | `+-\nDark Exploration Records\n...-+` |
| Without titlebar | `+-\n\**Title**\n...-+` |

### Text Effects

| Tag | Effect |
|-----|--------|
| `%%text%%` | Shaking text (whole block) |
| `%~text~%` | Shaking text (individual letters) |
| `%^text^%` | Wave text (per letter, right to left) |
| `@@text@@` | Distorted / glitch text |
| `@_@text@_@` | Subtle glitch text |
| `#^#text#^#` | Growing text (sizes up left to right) |
| `#v#text#v#` | Shrinking text (sizes down left to right) |
| `$s text s$` | Smoke text |

### Colored Text

| Tag | Color |
|-----|-------|
| `#rtextr#` | Bold red |
| `#btextb#` | Bold blue |
| `#ytexty#` | Bold yellow |
| `#ptextp#` | Bold magenta |
| `#gtextg#` | Bold green |
| `#otexto#` | Bold orange |

### Highlight Colors

| Tag | Color |
|-----|-------|
| `;rtextr;` | Red highlight |
| `;btextb;` | Blue highlight |
| `;ytexty;` | Yellow highlight |
| `;ptextp;` | Magenta highlight |
| `;gtextg;` | Green highlight |
| `;otexto;` | Orange highlight |

### Fade Effects

| Tag | Effect |
|-----|--------|
| `#f#text#f#` | Faded text (nearly invisible, reveals on hover) |
| `#f>#text#f>#` | Fade from left to right |
| `#f<#text#f<#` | Fade from right to left |

### Text Size & Alignment

| Tag | Effect |
|-----|--------|
| `#*text*#` | Large bold text |
| `#><text><#` | Large bold text, centered |
| `@ll@text@ll@` | Monospace, bold, left-aligned |
| `@rr@text@rr@` | Monospace, bold, right-aligned |
| `@l@text@l@` | Left-aligned |
| `@r@text@r@` | Right-aligned |

### Other

| Tag | Effect |
|-----|--------|
| `-# text #-` | Sub/small text |
| `_text_` | Underline |
| `~text~` | Strikethrough |
| `---` or `~~~` | Scene break / horizontal divider |
| `* * *` | Scene break / horizontal divider |
| `\_` | Literal underscore (escape) |
| `\~` | Literal tilde (escape) |

