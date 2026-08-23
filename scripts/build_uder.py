import re
import json
import zipfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
REPO_ROOT = SCRIPT_DIR.parent
RECORDS_DIR = REPO_ROOT / "chapters" / "uder" / "records"
STATIC_THUMBS = REPO_ROOT / "website" / "static" / "chapters" / "uder" / "thumbnails"
META_PATH = REPO_ROOT / "website" / "src" / "lib" / "meta.json"

ALLOWED_TYPES = {"record", "exploration", "character", "item"}
ALLOWED_FACTIONS = {"Daydream Inc.", "Disaster Management Bureau", "Church of the Luminous Unknown"}

TYPE_LABELS = {
    "record": "Record",
    "exploration": "Exploration Record",
    "character": "Character",
    "item": "Item",
}


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def parse_scalar(raw):
    raw = raw.strip()
    if raw == "null" or raw == "":
        return None
    m = re.match(r'^"((?:[^"\\]|\\.)*)"$', raw)
    if m:
        return m.group(1).replace("\\\\", "\\").replace('\\"', '"').replace("\\n", "\n")
    return raw


def parse_frontmatter(text):
    text = text.replace("\ufeff", "")
    lines = text.split("\n")

    start = 0
    while start < len(lines) and lines[start].strip() == "":
        start += 1

    if not lines[start] or lines[start].strip() != "---":
        raise ValueError("frontmatter needs opening ---")

    close = None
    for i in range(start + 1, len(lines)):
        if lines[i].strip() == "---":
            close = i
            break

    if close is None:
        raise ValueError("frontmatter needs closing ---")

    yaml_lines = lines[start + 1 : close]
    body = "\n".join(lines[close + 1 :]).lstrip("\n")

    data = {}
    i = 0
    while i < len(yaml_lines):
        line = yaml_lines[i]
        trimmed = line.strip()
        if not trimmed or trimmed.startswith("#"):
            i += 1
            continue

        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", trimmed)
        if not m:
            i += 1
            continue

        key = m.group(1)
        value = m.group(2)

        if key == "records":
            records = []
            i += 1
            while i < len(yaml_lines) and re.match(r"^\s+-\s+", yaml_lines[i]):
                title_line = re.sub(r"^\s*-\s*", "", yaml_lines[i]).strip()
                title_m = re.match(r"^title:\s*(.*)$", title_line)
                title = parse_scalar(title_m.group(1)) if title_m else ""
                content = ""
                if i + 1 < len(yaml_lines):
                    content_m = re.match(r"^\s{4,}content:\s*(.*)$", yaml_lines[i + 1])
                    if content_m:
                        content = parse_scalar(content_m.group(1)) or ""
                        i += 1
                records.append({"title": title, "content": content})
                i += 1
            data["records"] = records
            continue

        next_line = yaml_lines[i + 1] if i + 1 < len(yaml_lines) else None
        if value == "" and next_line and re.match(r"^\s*-\s*", next_line):
            items = []
            i += 1
            while i < len(yaml_lines) and re.match(r"^\s*-\s*", yaml_lines[i]):
                items.append(parse_scalar(re.sub(r"^\s*-\s*", "", yaml_lines[i])) or "")
                i += 1
            data[key] = items
            continue

        data[key] = parse_scalar(value)
        i += 1

    return data, body


def copy_thumbnail(uder_path, slug, thumb_path):
    """Copy the thumbnail out of the archive as static webp."""
    if not thumb_path:
        return None
    try:
        with zipfile.ZipFile(uder_path, "r") as zf:
            data = zf.read(thumb_path)
    except KeyError:
        return None
    dest = STATIC_THUMBS / f"{slug}.webp"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return f"/chapters/uder/thumbnails/{slug}.webp"


def main():
    if not RECORDS_DIR.exists():
        print(f"No records directory: {RECORDS_DIR}")
        return

    uder_files = sorted(RECORDS_DIR.glob("*.uder"))
    if not uder_files:
        print("No .uder files found.")
        return

    print(f"Found {len(uder_files)} .uder files.")

    STATIC_THUMBS.mkdir(parents=True, exist_ok=True)

    # drop stale thumbnails for records that no longer exist
    live_slugs = {slugify(p.stem) for p in uder_files}
    for old in STATIC_THUMBS.glob("*.webp"):
        if old.stem not in live_slugs:
            old.unlink()
            print(f"  Removed stale thumbnail: {old.name}")

    meta = {}
    if META_PATH.exists():
        try:
            meta = json.loads(META_PATH.read_text(encoding="utf-8"))
        except Exception:
            meta = {}

    meta.setdefault("uder", {})
    meta["uder"]["records"] = []

    for uder_path in uder_files:
        slug = slugify(uder_path.stem)
        print(f"  Processing: {uder_path.name} -> {slug}")

        try:
            with zipfile.ZipFile(uder_path, "r") as zf:
                names = zf.namelist()

                if "metadata.md" not in names:
                    print(f"    SKIP: no metadata.md")
                    continue

                raw_md = zf.read("metadata.md").decode("utf-8")
                meta_data, _body = parse_frontmatter(raw_md)

                has_interactive = "interactive.json" in names
        except Exception as e:
            print(f"    SKIP: failed to read archive ({e})")
            continue

        title = meta_data.get("title", slug)
        record_type = meta_data.get("type", "record")
        if record_type not in ALLOWED_TYPES:
            record_type = "record"
        faction = meta_data.get("faction")
        if faction and faction not in ALLOWED_FACTIONS:
            faction = None
        summary = meta_data.get("summary", "") or ""
        code = meta_data.get("code", "") or ""
        classification = meta_data.get("classification", "") or ""
        thumbnail = meta_data.get("thumbnail")

        thumb_url = copy_thumbnail(uder_path, slug, thumbnail)
        if thumbnail and not thumb_url:
            print(f"    WARN: thumbnail '{thumbnail}' not found in archive")

        meta["uder"]["records"].append({
            "title": title,
            "slug": slug,
            "type": record_type,
            "typeLabel": TYPE_LABELS.get(record_type, "Record"),
            "faction": faction,
            "code": code,
            "classification": classification,
            "summary": summary,
            "thumb": thumb_url,
            "hasInteractive": has_interactive,
        })

    META_PATH.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nUpdated: {META_PATH}")
    print(f"Built {len(uder_files)} records.")


if __name__ == "__main__":
    main()
