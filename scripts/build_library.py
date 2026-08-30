import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
REPO_ROOT = SCRIPT_DIR.parent

ALTTEXT_OUTPUT_PATH = REPO_ROOT / "website/src/lib/alttext.json"


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
