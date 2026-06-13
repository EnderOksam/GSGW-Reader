import os
import json
import shutil
import re
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
REPO_ROOT = SCRIPT_DIR.parent

REFERENCES_DIR = REPO_ROOT / "images" / "gsgw" / "references"
STATIC_DIR = REPO_ROOT / "website" / "static" / "characters"
OUTPUT_PATH = REPO_ROOT / "website" / "src" / "lib" / "reader" / "characters.json"

UNKNOWN = "\u25a0\u25a0"

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
        info = json.loads(info_path.read_text(encoding="utf-8"))
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
    blood_type = info.get("bloodType", UNKNOWN)
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
        "bloodType": blood_type,
        "preferredAlt": preferred_alt,
        "alts": alts,
    }

def main():
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

if __name__ == "__main__":
    main()
