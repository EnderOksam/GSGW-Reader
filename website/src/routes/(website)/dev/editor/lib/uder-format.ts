import JSZip from "jszip";
import { downloadBlob } from "./zip-tools";

const ALLOWED_TYPES = ["record", "exploration", "character", "item"] as const;
export type UderRecordType = typeof ALLOWED_TYPES[number];

export interface UderSource {
  title: string;
  type: UderRecordType;
  faction: string | null;
  code: string;
  classification: string;
  summary: string;
  thumbnailUrl: string | null;
  mediaUrls: string[];
  content: string;
  records: { title: string; content: string }[];
}

export interface UderImport {
  title: string;
  type: UderRecordType;
  faction: string | null;
  code: string;
  classification: string;
  summary: string;
  thumbnailUrl: string | null;
  mediaUrls: string[];
  content: string;
  records: { title: string; content: string }[];
  images: { name: string; url: string }[];
}

const MAX_TOTAL_UNCOMPRESSED_BYTES = 50 * 1024 * 1024;
const MAX_IMAGE_FILES = 200;

const MAX_IMAGE_PIXELS = 25_000_000;

const ALLOWED_FACTIONS = [
  "Daydream Inc.",
  "Disaster Management Bureau",
  "Church of the Luminous Unknown",
];

function checkZipSize(zip: JSZip): void {
  let total = 0;
  let count = 0;
  for (const entry of Object.values(zip.files)) {
    if (entry.dir) continue;
    const size = (entry as any)._data?.uncompressedSize ?? 0;
    total += size;
    count += 1;
    if (total > MAX_TOTAL_UNCOMPRESSED_BYTES) {
      throw new Error("this .uder file is too big to unpack safely");
    }
  }
  if (count > MAX_IMAGE_FILES) {
    throw new Error("this .uder file has too many files inside");
  }
}

function isBadUrl(value: string, key: string): boolean {
  if (key === "href" || key === "src") {
    return value.trim().toLowerCase().startsWith("javascript:");
  }
  return false;
}

export function sanitizeHtml(html: string): string {
  if (typeof DOMParser === "undefined") return html;
  const doc = new DOMParser().parseFromString(html, "text/html");
  const unsafeTags = new Set(["script", "style", "iframe", "object", "embed"]);
  for (const el of Array.from(doc.body.querySelectorAll("*"))) {
    const tag = el.tagName.toLowerCase();
    if (unsafeTags.has(tag)) {
      el.remove();
      continue;
    }
    for (const attr of Array.from(el.attributes)) {
      const name = attr.name.toLowerCase();
      if (name.startsWith("on")) {
        el.removeAttribute(attr.name);
        continue;
      }
      if (isBadUrl(attr.value, name)) {
        el.removeAttribute(attr.name);
      }
    }
  }
  return doc.body.innerHTML;
}


export interface ContentPart {
  type: "html" | "illustration";
  value: string;
}

export function splitContent(text: string): ContentPart[] {
  const parts: ContentPart[] = [];
  const regex = /\[illustration\|(.*?)\]/g;
  let lastIndex = 0;
  let match;
  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push({ type: "html", value: text.slice(lastIndex, match.index) });
    }
    parts.push({ type: "illustration", value: match[1] });
    lastIndex = match.index + match[0].length;
  }
  if (lastIndex < text.length) {
    parts.push({ type: "html", value: text.slice(lastIndex) });
  }
  return parts;
}

function parseScalar(raw: string): string | null {
  if (raw === "null" || raw === "") return null;
  const m = /^"((?:[^"\\]|\\.)*)"$/.exec(raw.trim());
  if (m) {
    return m[1].replace(/\\\\/g, "\\").replace(/\\"/g, '"').replace(/\\n/g, "\n");
  }
  return raw.trim();
}

function parseFrontmatter(text: string): { data: Record<string, any>; body: string } {
  const lines = text.replace(/^\uFEFF/, "").split(/\r?\n/);

  let start = 0;
  while (start < lines.length && lines[start].trim() === "") start++;
  if (!lines[start] || lines[start].trim() !== "---")
    throw new Error("frontmatter needs to start with ---");

  const close = lines.findIndex((l, i) => i > start && l.trim() === "---");
  if (close === -1) throw new Error("frontmatter needs an ending ---");

  const yaml = lines.slice(start + 1, close);
  const body = lines.slice(close + 1).join("\n").replace(/^\n+/, "");
  const data: Record<string, any> = {};

  let i = 0;
  while (i < yaml.length) {
    const line = yaml[i];
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) { i++; continue; }
    const m = /^([A-Za-z0-9_-]+):\s*(.*)$/.exec(trimmed);
    if (!m) { i++; continue; }
    const key = m[1];
    const value = m[2];

    if (key === "records") {
      const records: { title: string; content: string }[] = [];
      i += 1;
      while (i < yaml.length && /^\s+-\s+/.test(yaml[i])) {
        const titleLine = yaml[i].replace(/^\s*-\s*/, "").trim();
        const titleMatch = /^title:\s*(.*)$/.exec(titleLine);
        const title = titleMatch ? (parseScalar(titleMatch[1]) ?? "") : "";
        let content = "";
        const next = yaml[i + 1];
        if (next) {
          const contentMatch = /^\s{4,}content:\s*(.*)$/.exec(next);
          if (contentMatch) {
            content = parseScalar(contentMatch[1]) ?? "";
            i += 1;
          }
        }
        records.push({ title, content });
        i += 1;
      }
      data.records = records;
      continue;
    }

    const next = yaml[i + 1];
    if (value === "" && next && /^\s*-\s*/.test(next)) {
      const items: string[] = [];
      i += 1;
      while (i < yaml.length && /^\s*-\s*/.test(yaml[i])) {
        items.push(parseScalar(yaml[i].replace(/^\s*-\s*/, "")) ?? "");
        i += 1;
      }
      data[key] = items;
      continue;
    }

    data[key] = parseScalar(value);
    i += 1;
  }

  return { data, body };
}

function quoteScalar(s: string): string {
  return '"' + s.replace(/\\/g, "\\\\").replace(/"/g, '\\"').replace(/\n/g, "\\n") + '"';
}

function serializeMetadata(src: UderSource, thumbnail: string | null, media: string[]): string {
  const lines: string[] = [];
  lines.push("---");
  lines.push(`uder: 1`);
  lines.push(`title: ${quoteScalar(src.title)}`);
  lines.push(`type: ${src.type}`);
  lines.push(`faction: ${src.faction ? quoteScalar(src.faction) : "null"}`);
  lines.push(`code: ${quoteScalar(src.code)}`);
  lines.push(`classification: ${quoteScalar(src.classification)}`);
  lines.push(`summary: ${quoteScalar(src.summary)}`);
  lines.push(`thumbnail: ${thumbnail ? quoteScalar(thumbnail) : "null"}`);
  lines.push("media:");
  for (const m of media) lines.push(`  - ${quoteScalar(m)}`);
  lines.push("records:");
  for (const r of src.records) {
    lines.push(`  - title: ${quoteScalar(r.title)}`);
    lines.push(`    content: ${quoteScalar(r.content)}`);
  }
  lines.push("---");
  lines.push("");
  lines.push(src.content);
  return lines.join("\n");
}

function illustrationUrls(text: string): string[] {
  const out: string[] = [];
  const re = /\[illustration\|([^\]]*)\]/g;
  let m;
  while ((m = re.exec(text)) !== null) {
    out.push(m[1].trim());
  }
  return out;
}

function replaceIllustrations(text: string, map: (name: string) => string): string {
  return text.replace(/\[illustration\|([^\]]*)\]/g, (_all, raw: string) => {
    const key = raw.trim();
    const replacement = map(key);
    return replacement === undefined ? `[illustration|${raw}]` : `[illustration|${replacement}]`;
  });
}

function slugify(title: string): string {
  const slug = title
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return slug || "untitled";
}

function toWebp(blob: Blob): Promise<Blob | null> {
  return new Promise((resolve) => {
    const img = new Image();
    const url = URL.createObjectURL(blob);
    img.onload = () => {
      URL.revokeObjectURL(url);
      const pixels = img.naturalWidth * img.naturalHeight;
      if (pixels > MAX_IMAGE_PIXELS || pixels === 0) { resolve(null); return; }
      const canvas = document.createElement("canvas");
      canvas.width = img.naturalWidth;
      canvas.height = img.naturalHeight;
      const ctx = canvas.getContext("2d");
      if (!ctx) { resolve(null); return; }
      ctx.drawImage(img, 0, 0);
      canvas.toBlob((webp) => resolve(webp), "image/webp", 0.9);
    };
    img.onerror = () => { URL.revokeObjectURL(url); resolve(null); };
    img.src = url;
  });
}

function extensionOf(blob: Blob, fallback: string): string {
  const ext = (blob.type.split("/")[1] || "").toLowerCase();
  if (ext === "jpeg") return "jpg";
  return ext || fallback;
}

export async function exportUderZip(src: UderSource): Promise<{ blob: Blob; slug: string }> {
  const ordered: string[] = [];
  const push = (url: string) => { if (url && !ordered.includes(url)) ordered.push(url); };
  push(src.thumbnailUrl ?? "");
  src.mediaUrls.forEach(push);
  illustrationUrls(src.content).forEach(push);
  src.records.forEach((r) => illustrationUrls(r.content).forEach(push));

  const map: Record<string, string> = {};
  const files: { name: string; blob: Blob }[] = [];

  for (let i = 0; i < ordered.length; i++) {
    const url = ordered[i];
    let blob: Blob;
    try {
      blob = await (await fetch(url)).blob();
    } catch {
      continue;
    }
    const webp = await toWebp(blob);
    const name = `images/${String(i + 1).padStart(4, "0")}.${webp ? "webp" : extensionOf(blob, "png")}`;
    map[url] = name;
    files.push({ name, blob: webp ?? blob });
  }

  const media = src.mediaUrls.map((u) => map[u]).filter(Boolean);
  const content = replaceIllustrations(src.content, (k) => map[k]);
  const records = src.records.map((r) => ({
    title: r.title,
    content: replaceIllustrations(r.content, (k) => map[k]),
  }));

  const zip = new JSZip();
  zip.file("metadata.md", serializeMetadata(
    { ...src, content, records },
    src.thumbnailUrl ? map[src.thumbnailUrl] ?? null : null,
    media,
  ));
  for (const f of files) zip.file(f.name, f.blob);

  const blob = await zip.generateAsync({ type: "blob" });
  return { blob, slug: slugify(src.title) };
}

export async function importUderZip(file: File): Promise<UderImport> {
  const zip = await JSZip.loadAsync(file);
  checkZipSize(zip);

  const metaEntry = zip.file("metadata.md");
  if (!metaEntry) throw new Error("this .uder file has no metadata.md");
  const metaText = await metaEntry.async("string");
  const { data, body } = parseFrontmatter(metaText);

  const imagePaths: string[] = [];
  zip.forEach((path, entry) => {
    if (entry.dir) return;
    if (path.startsWith("images/")) imagePaths.push(path);
  });

  const images: { name: string; url: string }[] = [];
  const urlByName: Record<string, string> = {};
  for (const path of imagePaths) {
    const entry = zip.file(path);
    if (!entry) continue;
    const blob = await entry.async("blob");
    const url = URL.createObjectURL(blob);
    urlByName[path] = url;
    images.push({ name: path, url });
  }

  const resolve = (text: string): string =>
    replaceIllustrations(text, (k) => urlByName[k] ?? k);

  const type = ALLOWED_TYPES.find((t) => t === data.type) ?? "record";
  const faction = ALLOWED_FACTIONS.find((f) => f === data.faction) ?? null;

  const thumbnail = typeof data.thumbnail === "string" ? urlByName[data.thumbnail] ?? null : null;
  const mediaUrls: string[] = [];
  if (Array.isArray(data.media)) {
    for (const m of data.media) {
      if (typeof m === "string" && urlByName[m]) mediaUrls.push(urlByName[m]);
    }
  }

  return {
    title: typeof data.title === "string" ? data.title : "",
    type,
    faction,
    code: typeof data.code === "string" ? data.code : "",
    classification: typeof data.classification === "string" ? data.classification : "",
    summary: typeof data.summary === "string" ? data.summary : "",
    thumbnailUrl: thumbnail,
    mediaUrls,
    content: resolve(body),
    records: (Array.isArray(data.records) ? data.records : []).map((r: any) => ({
      title: typeof r?.title === "string" ? r.title : "",
      content: resolve(typeof r?.content === "string" ? r.content : ""),
    })),
    images,
  };
}
