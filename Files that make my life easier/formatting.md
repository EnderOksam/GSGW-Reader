# Formatting Guide

This guide shows you how to format chapter text files. These special tags help make the story look great on the website!

> [!TIP]
> **New to contributing?** Read the [How to Contribute guide](CONTRIBUTING.md) first to learn how to edit files.

---

## Basic Rules

- Chapter files are simple `.txt` (text) files
- You don't need to create new files—they already exist in the `/chapters` folder
- Use the special tags shown below to format different types of text
- Tags are case-sensitive (use exact capitalization shown)
- The website automatically converts these tags into pretty formatted text


## Quick Tips

- Always use tags exactly as shown (they're case-sensitive!)
- Don't use HTML code directly unless you really know what you're doing
- Keep formatting consistent with other chapters
- If you're not sure, look at how other chapters do it
- Your changes will appear on the website after they're approved

---

## Quick Reference Table

Here's a handy table to quickly find the tag you need:

| Tag | What It's For | Example |
|-----|---------------|---------|
| `+-` & `-+`  | Info/record window | `+-\n...-+` |
| `+~` & `~+`  | System window | `+~\n...~+` |
| `+=` & `=+`  | screen display window (subtle CRT effect) | `+=\n...=+` |
| `%%text%%` | Shaking text (whole block) | `%%scary%%` |
| `%~text~%` | Shaking text (per letter, left to right) | `%~scary~%` |
| `%^text^%` | Wave text (per letter, right to left) | `%^scary^%` |
| `#rtextr#` | Bold red text | `#rimportantr#` |
| `#btextb#` | Bold blue text | `#bnoticeb#` |
| `#ytexty#` | Bold yellow text | `#ywarningy#` |
| `#*text*#` | Large bold text | `#*notice*#` |
| `#><text><#` | Large bold text, centered | `#><title><#` |
| `@ll@text@ll@` | Monospace, bold, left | `@ll@note@ll@` |
| `@rr@text@rr@` | Monospace, bold, right | `@rr@source@rr@` |
| `@l@text@l@` | Left-aligned | `@l@note@l@` |
| `@r@text@r@` | Right-aligned | `@r@source@r@` |
| `~text~` | Strikethrough | `~oops~` |
| `~~~ or * * *` | Horizontal divider line | `~~~` or `* * *`   |

### Window Metadata

The first line inside a `+- ... -+` window is treated as metadata (smaller, muted, right-aligned).  
Put `\` or `\` before the first bold/italic text to cancel this:

| Style | Markdown |
|-------|----------|
| With metadata line | `+-\nDark Exploration Records / Ghost Story\n...-+` |
| Without metadata (bold title) | `+-\n\**[Title]**\n...-+` |
