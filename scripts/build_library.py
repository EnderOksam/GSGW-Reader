import json
import re
import shutil
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
REPO_ROOT = SCRIPT_DIR.parent

ALTTEXT_OUTPUT_PATH = REPO_ROOT / "website/src/lib/alttext.json"

ANNOUNCEMENTS_MD = SCRIPT_DIR / "announcements.md"
ANNOUNCEMENTS_OUTPUT_PATH = REPO_ROOT / "website/src/lib/announcements.json"

REFERENCES_DIR = REPO_ROOT / "images" / "gsgw" / "references"
STATIC_DIR = REPO_ROOT / "website" / "static" / "characters"
OUTPUT_PATH = REPO_ROOT / "website" / "src" / "lib" / "reader" / "characters.json"

DEBUT_REFERENCES_DIR = REPO_ROOT / "images" / "dod" / "references"
DEBUT_STATIC_DIR = REPO_ROOT / "website" / "static" / "debut-characters"
DEBUT_OUTPUT_PATH = REPO_ROOT / "website" / "src" / "lib" / "reader" / "debut-characters.ts"
DEBUT_IMAGE_SUFFIXES = (".webp", ".png", ".jpg", ".jpeg")

UNKNOWN = "\u25a0\u25a0"


# =========================================================
# ALT TEXT
# =========================================================

def parse_alttext_md(md_path):
    if not md_path.exists():
        return {"variants": []}

    content = md_path.read_text(encoding="utf-8")
    variants = []

    for line in content.splitlines():
        stripped = line.strip()

        if not stripped:
            continue

        if stripped.startswith("## "):
            heading = stripped[3:].strip()
            if heading:
                variants.append({"name": heading, "description": "", "searches": [], "options": []})
            continue

        if stripped.startswith("#"):
            continue

        if variants and "->" in stripped:
            parts = stripped.split("->", 1)
            searches = [s.strip() for s in parts[0].split(",") if s.strip()]
            options = [o.strip() for o in parts[1].split(",") if o.strip()]
            variants[-1]["searches"] = searches
            variants[-1]["options"] = options
        elif variants and not stripped.startswith("#") and "->" not in stripped:
            desc = stripped.strip("()")
            if desc:
                variants[-1]["description"] = desc

    variants = [v for v in variants if v["searches"] and v["options"]]
    return {"variants": variants}


def build_alttext():
    alttext_md = REPO_ROOT / "chapters" / "gsgw" / "alttext.md"
    data = parse_alttext_md(alttext_md)
    ALTTEXT_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    ALTTEXT_OUTPUT_PATH.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Alt text config written: {ALTTEXT_OUTPUT_PATH} ({len(data['variants'])} variants)")
    return data


# =========================================================
# ANNOUNCEMENTS
# =========================================================

def parse_announcement_date(value: str):
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y", "%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(value.strip(), fmt)
        except ValueError:
            continue
    return None


def parse_announcements_md(md_path):
    if not md_path.exists():
        return {"announcements": []}

    content = md_path.read_text(encoding="utf-8")
    announcements = []
    current = None
    paragraph = []

    def flush_paragraph():
        nonlocal paragraph
        if current is not None and paragraph:
            text = " ".join(paragraph).strip()
            if text:
                if not current["short"]:
                    current["short"] = text
                else:
                    current["long"] = f"{current['long']}\n\n{text}".strip() if current["long"] else text
        paragraph = []

    for raw in content.splitlines():
        stripped = raw.strip()

        if stripped.startswith("## "):
            flush_paragraph()
            heading = stripped[3:].strip()
            title = heading
            date = ""
            match = re.search(r"\[([^\]]+)\]\s*$", heading)
            if match:
                date = match.group(1).strip()
                title = heading[:match.start()].strip()
            current = {"title": title, "date": date, "short": "", "long": ""}
            announcements.append(current)
            continue

        if not stripped:
            flush_paragraph()
            continue

        if stripped.startswith("#"):
            continue

        if current is not None:
            paragraph.append(stripped)

    flush_paragraph()

    for announcement in announcements:
        if not announcement["long"]:
            announcement["long"] = announcement["short"]

    announcements = [a for a in announcements if a["title"]]

    dated = [a for a in announcements if parse_announcement_date(a["date"])]
    undated = [a for a in announcements if not parse_announcement_date(a["date"])]
    dated.sort(key=lambda a: parse_announcement_date(a["date"]), reverse=True)
    announcements = dated + undated

    return {"announcements": announcements}


def build_announcements():
    data = parse_announcements_md(ANNOUNCEMENTS_MD)
    ANNOUNCEMENTS_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    ANNOUNCEMENTS_OUTPUT_PATH.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Announcements written: {ANNOUNCEMENTS_OUTPUT_PATH} ({len(data['announcements'])} announcements)")
    return data


# =========================================================
# CHARACTERS
# =========================================================

def derive_id(folder_name: str) -> str:
    s = folder_name.strip()
    s = re.sub(r"[\s-]", "", s)
    s = re.sub(r"[^a-zA-Z0-9]", "", s)
    return s


def scan_character(folder: Path) -> dict | None:
    folder_name = folder.name
    cid = derive_id(folder_name)

    info_path = folder / "character.json"
    if not info_path.exists():
        print(f"  Skipped (no character.json)")
        return None

    try:
        info = json.loads(info_path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as e:
        print(f"  Warning: invalid JSON in {info_path.name}: {e}")
        return None

    files = [f.name for f in folder.iterdir() if f.suffix.lower() == ".webp"]

    cid = info.get("id", cid)
    name = info.get("name", folder_name)

    def resolve_image(cfg_key: str, convention: str) -> str | None:
        override = info.get(cfg_key)
        if override:
            return override if override in files else None
        return convention if convention in files else None

    manwha_image = resolve_image("manwhaImage", f"{cid}Manwha.webp")
    webnovel_image = resolve_image("webnovelImage", f"{cid}Webnovel.webp")

    has_manwha = info.get("hasManwha", manwha_image is not None)
    first_appearance = info.get("firstAppearance")
    birthday = info.get("birthday", UNKNOWN)
    blood_type = info.get("alias", UNKNOWN)
    faction = info.get("faction")
    preferred_alt = info.get("preferredAlt")
    alts_config = info.get("alts", [])

    if isinstance(first_appearance, str):
        try:
            first_appearance = int(first_appearance)
        except ValueError:
            first_appearance = None

    alts = []
    seen_ids = set()

    for alt_cfg in alts_config:
        alt_id = alt_cfg.get("id", "alt")
        if alt_id in seen_ids:
            continue
        seen_ids.add(alt_id)
        alt_label = alt_id.capitalize() if alt_id != "alt" else ""

        alt_manwha_convention = f"{cid}ManwhaAlt{alt_label}.webp" if alt_label else f"{cid}ManwhaAlt.webp"
        alt_webnovel_convention = f"{cid}WebnovelAlt{alt_label}.webp" if alt_label else f"{cid}WebnovelAlt.webp"

        alt_manwha = alt_cfg.get("manwhaImage")
        if alt_manwha:
            alt_manwha = alt_manwha if alt_manwha in files else None
        else:
            alt_manwha = alt_manwha_convention if alt_manwha_convention in files else None

        alt_webnovel = alt_cfg.get("webnovelImage")
        if alt_webnovel:
            alt_webnovel = alt_webnovel if alt_webnovel in files else None
        else:
            alt_webnovel = alt_webnovel_convention if alt_webnovel_convention in files else None

        alts.append({
            "id": alt_id,
            "name": alt_cfg.get("name", f"{name} ({alt_id})"),
            "chapter": alt_cfg.get("chapter"),
            "toggleable": alt_cfg.get("toggleable", True),
            "hasManwha": alt_cfg.get("hasManwha", alt_manwha is not None),
            "hasWebnovel": alt_cfg.get("hasWebnovel", alt_webnovel is not None),
            "manwhaImage": alt_manwha,
            "webnovelImage": alt_webnovel,
        })

    return {
        "id": cid,
        "name": name,
        "hasManwha": has_manwha,
        "hasManwhaImage": manwha_image is not None,
        "hasWebnovelImage": webnovel_image is not None,
        "manwhaImage": manwha_image,
        "webnovelImage": webnovel_image,
        "firstAppearance": first_appearance,
        "birthday": birthday,
        "alias": blood_type,
        "faction": faction,
        "preferredAlt": preferred_alt,
        "alts": alts,
    }


def build_characters():
    STATIC_DIR.mkdir(parents=True, exist_ok=True)

    if not REFERENCES_DIR.exists():
        print(f"References directory not found: {REFERENCES_DIR}")
        return

    folders = sorted([
        f for f in REFERENCES_DIR.iterdir()
        if f.is_dir()
    ])

    characters = []
    copied_files = set()
    for folder in folders:
        cid = derive_id(folder.name)
        print(f"Processing {folder.name} ({cid})...")

        char = scan_character(folder)
        if char is None:
            continue
        characters.append(char)

        for f in folder.iterdir():
            if f.suffix.lower() == ".webp":
                dest = STATIC_DIR / f.name
                shutil.copy2(str(f), str(dest))
                copied_files.add(f.name)
                print(f"  Copied {f.name}")

    # Remove stale images from static directory
    if STATIC_DIR.exists():
        for f in STATIC_DIR.iterdir():
            if f.suffix.lower() == ".webp" and f.name not in copied_files:
                f.unlink()
                print(f"  Removed stale: {f.name}")

    characters.sort(key=lambda c: (
        0 if c["firstAppearance"] is not None else 1,
        c["firstAppearance"] if c["firstAppearance"] is not None else 9999
    ))

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(characters, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print(f"\n{'='*60}")
    print(f"  Generated {len(characters)} characters")
    print(f"{'='*60}")
    for ch in characters:
        alts_list = ch.get("alts", [])
        alts_str = f", {len(alts_list)} alt(s): " + ", ".join([f"{a['id']}" for a in alts_list]) if alts_list else ""
        mw = "M" if ch["manwhaImage"] else "-"
        wn = "W" if ch["webnovelImage"] else "-"
        app = f"ch.{ch['firstAppearance']}" if ch["firstAppearance"] else "???"
        print(f"  [{mw}{wn}] {ch['name']:25s} (first: {app:5s}){alts_str}")
    print(f"{'='*60}")
    print(f"  Output: {OUTPUT_PATH}")

    return characters


def build_debut_characters():
    """Build the Debut or Die reference list from one folder per character."""
    if not DEBUT_REFERENCES_DIR.exists():
        print(f"Debut references directory not found: {DEBUT_REFERENCES_DIR}")
        return

    DEBUT_STATIC_DIR.mkdir(parents=True, exist_ok=True)
    characters = []
    copied_files = set()

    folders = sorted(
        (folder for folder in DEBUT_REFERENCES_DIR.iterdir() if folder.is_dir()),
        key=lambda folder: folder.name.casefold(),
    )

    for folder in folders:
        info_path = folder / "character.json"
        if not info_path.exists():
            print(f"Skipping {folder.name}: no character.json")
            continue

        try:
            info = json.loads(info_path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError as error:
            print(f"Skipping {folder.name}: invalid character.json ({error})")
            continue

        def copy_debut_image(filename):
            if not filename:
                return None
            image_name = Path(filename).name
            image_path = folder / image_name
            if image_path.is_file() and image_path.suffix.lower() in DEBUT_IMAGE_SUFFIXES:
                destination = DEBUT_STATIC_DIR / image_name
                shutil.copy2(str(image_path), str(destination))
                copied_files.add(image_name)
                return f"/debut-characters/{image_name}"
            else:
                print(f"  Missing image for {folder.name}: {image_name}")
                return None

        def resolve_debut_image(entry, field, convention):
            # An explicit null disables this portrait instead of guessing a file.
            if field in entry:
                return copy_debut_image(entry[field])
            if field == "manwhaImage" and "image" in entry:
                return copy_debut_image(entry["image"])
            for suffix in DEBUT_IMAGE_SUFFIXES:
                candidate = f"{convention}{suffix}"
                if (folder / candidate).is_file():
                    return copy_debut_image(candidate)
            return None

        character_id = info.get("id", derive_id(folder.name))
        manwha_image = resolve_debut_image(
            info, "manwhaImage", f"{character_id}Manhwa",
        )
        webnovel_image = resolve_debut_image(
            info, "webnovelImage", f"{character_id}Webnovel",
        )

        chapter = info.get("firstNovelChapter")
        if isinstance(chapter, str):
            try:
                chapter = int(chapter)
            except ValueError:
                chapter = None
        if not isinstance(chapter, int):
            chapter = None

        alts = []
        for alt in info.get("alts", []):
            if not isinstance(alt, dict):
                continue
            alt_id = alt.get("id", "alt")
            alt_parts = re.findall(r"[a-zA-Z0-9]+", alt_id)
            alt_label = "".join(part[:1].upper() + part[1:] for part in alt_parts) if alt_id != "alt" else ""
            manwha_convention = f"{character_id}ManhwaAlt{alt_label}" if alt_label else f"{character_id}ManhwaAlt"
            webnovel_convention = f"{character_id}WebnovelAlt{alt_label}" if alt_label else f"{character_id}WebnovelAlt"
            alts.append({
                "id": alt_id,
                "name": alt.get("name", info.get("name", folder.name)),
                **({"nicknames": alt["nicknames"]} if alt.get("nicknames") else {}),
                "birthday": alt.get("birthday"),
                "mbti": alt.get("mbti"),
                "firstNovelChapter": alt.get("firstNovelChapter"),
                "manwhaImage": resolve_debut_image(alt, "manwhaImage", manwha_convention),
                "webnovelImage": resolve_debut_image(alt, "webnovelImage", webnovel_convention),
            })

        characters.append({
            "id": character_id,
            "sortOrder": info.get("sortOrder", 9999),
            "name": info.get("name", folder.name),
            **({"nicknames": info["nicknames"]} if info.get("nicknames") else {}),
            "birthday": info.get("birthday", "Not confirmed"),
            "mbti": info.get("mbti") or "\u2014",
            "group": info.get("group", "TeSTAR"),
            "groupRole": info.get("groupRole", "Member"),
            "firstNovelChapter": chapter,
            "manwhaImage": manwha_image,
            "webnovelImage": webnovel_image,
            "alts": alts,
        })

    for image_path in DEBUT_STATIC_DIR.iterdir():
        if image_path.is_file() and image_path.suffix.lower() in DEBUT_IMAGE_SUFFIXES and image_path.name not in copied_files:
            image_path.unlink()
            print(f"  Removed stale Debut portrait: {image_path.name}")

    characters.sort(key=lambda character: (character["sortOrder"], character["name"].casefold()))
    output_characters = [
        {key: value for key, value in character.items() if key != "sortOrder"}
        for character in characters
    ]

    interface = """export interface DebutCharacterAlt {
  id: string;
  name: string;
  nicknames?: string[];
  birthday?: string | null;
  mbti?: string | null;
  firstNovelChapter?: number | null;
  manwhaImage: string | null;
  webnovelImage: string | null;
}

export interface DebutCharacter {
  id: string;
  name: string;
  nicknames?: string[];
  birthday: string;
  mbti: string;
  group: string;
  groupRole: string;
  firstNovelChapter: number | null;
  manwhaImage: string | null;
  webnovelImage: string | null;
  alts: DebutCharacterAlt[];
}

export const debutCharacters: DebutCharacter[] = [
"""
    entries = "\n".join(
        "  " + json.dumps(character, ensure_ascii=False) + ","
        for character in output_characters
    )
    DEBUT_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    DEBUT_OUTPUT_PATH.write_text(interface + entries + "\n];\n", encoding="utf-8")
    print(f"Generated {len(output_characters)} Debut characters: {DEBUT_OUTPUT_PATH}")
    return output_characters


def main():
    build_alttext()
    build_announcements()
    build_characters()
    build_debut_characters()


if __name__ == "__main__":
    main()
