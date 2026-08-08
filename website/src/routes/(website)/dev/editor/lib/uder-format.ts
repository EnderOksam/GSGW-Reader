import JSZip from "jszip";
import { downloadBlob } from "./zip-tools";

/**
 * A .uder file is just a zip. Inside it is one text file plus some images.
 *
 *   my-record.uder  (a zip, not a text file, even though it says .uder)
 *   - metadata.md   (the frontmatter + the text of the record)
 *   - images/
 *     - 0001.webp
 *     - 0002.webp
 *
 */

// What the editor has in memory. This is the shape we write to the zip.
export interface UderSource {
  title: string;
  type: "record" | "exploration";
  faction: string | null;
  code: string; // the identification code thing
  classification: string;
  summary: string; // the short description
  thumbnailUrl: string | null; // object url of the cover image
  mediaUrls: string[]; // object urls of the extra images
  content: string; // the main text
  records: { title: string; content: string }[]; // the exploration records
}

// What we get back when someone imports a .uder file.
export interface UderImport {
  title: string;
  type: "record" | "exploration";
  faction: string | null;
  code: string;
  classification: string;
  summary: string;
  thumbnailUrl: string | null; // made into a new object url
  mediaUrls: string[]; // made into new object urls
  content: string; // the main text, images point at object urls now
  records: { title: string; content: string }[];
  images: { name: string; url: string }[]; // every image that was in images/
}

// Nobody needs more than this.
const MAX_TOTAL_UNCOMPRESSED_BYTES = 50 * 1024 * 1024; // 50 MB unpacked
const MAX_IMAGE_FILES = 200;

// Stops a giant image from
// blowing up the browser tab when it gets decoded.
const MAX_IMAGE_PIXELS = 25_000_000;

const ALLOWED_FACTIONS = [
  "Daydream Inc.",
  "Disaster Management Bureau",
  "Church of the Luminous Unknown",
];

// zip bomb guard
function checkZipSize(zip: JSZip): void {
  let total = 0;
  let count = 0;
  for (const entry of Object.values(zip.files)) {
    if (entry.dir) continue;
    // this is not in jszip's types but it is there when you run it
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

// helper used by sanitizeHtml. It looks for links that try to run code.
function isBadUrl(value: string, key: string): boolean {
  // href and src are the two places people try to hide javascript:
  if (key === "href" || key === "src") {
    return value.trim().toLowerCase().startsWith("javascript:");
  }
  return false;
}

// XSS guard
export function sanitizeHtml(html: string): string {
  // The page is also built once without a browser (prerender). With no DOM
  // there is nothing to clean, so just hand it back as it is.
  if (typeof DOMParser === "undefined") return html;
  const doc = new DOMParser().parseFromString(html, "text/html");
  // tags that carry or run code get deleted whole
  const unsafeTags = new Set(["script", "style", "iframe", "object", "embed"]);
  for (const el of Array.from(doc.body.querySelectorAll("*"))) {
    const tag = el.tagName.toLowerCase();
    if (unsafeTags.has(tag)) {
      el.remove();
      continue;
    }
    for (const attr of Array.from(el.attributes)) {
      const name = attr.name.toLowerCase();
      // onerror/onclick and the rest run on their own, remove any on*
      if (name.startsWith("on")) {
        el.removeAttribute(attr.name);
        continue;
      }
      // javascript: links are the same trick, also remove those
      if (isBadUrl(attr.value, name)) {
        el.removeAttribute(attr.name);
      }
    }
  }
  return doc.body.innerHTML;
}


// Gives back the front matter and the body text, or throws.
function parseScalar(raw: string): string | null {
  if (raw === "null" || raw === "") return null;
  const m = /^"((?:[^"\\]|\\.)*)"$/.exec(raw.trim());
  if (m) {
    // undo the escape trick in the same order it was added, so a real
    // backslash is not eaten by accident
    return m[1].replace(/\\\\/g, "\\").replace(/\\"/g, '"').replace(/\\n/g, "\n");
  }
  return raw.trim();
}

function parseFrontmatter(text: string): { data: Record<string, any>; body: string } {
  // drop a utf-8 bom and split on plain crlf too, so files that were saved or
  // touched by hand (even notepad) still open
  const lines = text.replace(/^\uFEFF/, "").split(/\r?\n/);

  // the real start is the very first ---; a blank line in front of it is fine
  let start = 0;
  while (start < lines.length && lines[start].trim() === "") start++;
  if (!lines[start] || lines[start].trim() !== "---")
    throw new Error("frontmatter needs to start with ---");

  // the ending --- is the first --- that comes after the opening one. a body
  // that itself begins with --- survives, because it shows up after that
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
      // each record is two lines, a title line then a content line:
      //   - title: "One"
      //     content: "the text"
      const records: { title: string; content: string }[] = [];
      i += 1;
      while (i < yaml.length && /^\s+-\s+/.test(yaml[i])) {
        const titleLine = yaml[i].replace(/^\s*-\s*/, "").trim();
        const titleMatch = /^title:\s*(.*)$/.exec(titleLine);
        const title = titleMatch ? (parseScalar(titleMatch[1]) ?? "") : "";
        let content = "";
        const next = yaml[i + 1];
        if (next) {
          // the content line sits right under the title, indented more
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

    // "media:" with no value means a list comes on the next line:
    //   - "images/0001.webp"
    //   - "images/0002.webp"
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

// write the record back out as the text file that sits in the zip
function serializeMetadata(src: UderSource, thumbnail: string | null, media: string[]): string {
  const lines: string[] = []; // we build the yaml by hand, it is easier to read
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
  lines.push(src.content); // the body of the file is the record text
  return lines.join("\n");
}

// gets every [illustration|something] link out of a text, in order
function illustrationUrls(text: string): string[] {
  const out: string[] = [];
  const re = /\[illustration\|([^\]]*)\]/g;
  let m;
  while ((m = re.exec(text)) !== null) {
    out.push(m[1].trim());
  }
  return out;
}

// swaps each [illustration|link] in text for whatever the map function says
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

// tries to turn an image into webp in the browser. If the browser says no,
// we give back the original image and the build tool can worry about it.
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

// ---------------------------------------------------------------------------
// export
// ---------------------------------------------------------------------------
export async function exportUderZip(src: UderSource): Promise<{ blob: Blob; slug: string }> {
  // 1. pick the order the images get numbered: cover first, then any extra
  //    media, then images in the main text, then images in the records
  const ordered: string[] = [];
  const push = (url: string) => { if (url && !ordered.includes(url)) ordered.push(url); };
  push(src.thumbnailUrl ?? "");
  src.mediaUrls.forEach(push);
  illustrationUrls(src.content).forEach(push);
  src.records.forEach((r) => illustrationUrls(r.content).forEach(push));

  // 2. grab every image and put it in the zip as a numbered file
  const map: Record<string, string> = {}; // the object url -> file name like images/0001.webp
  const files: { name: string; blob: Blob }[] = [];

  for (let i = 0; i < ordered.length; i++) {
    const url = ordered[i];
    let blob: Blob;
    try {
      blob = await (await fetch(url)).blob(); // you can fetch an object url
    } catch {
      continue; // one broken image should not kill the whole export
    }
    const webp = await toWebp(blob);
    const name = `images/${String(i + 1).padStart(4, "0")}.${webp ? "webp" : extensionOf(blob, "png")}`;
    map[url] = name;
    files.push({ name, blob: webp ?? blob });
  }

  // 3. write metadata.md, with images called by their new names, and put all
  //    of that in a zip with the image files
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

// ---------------------------------------------------------------------------
// import
// ---------------------------------------------------------------------------
export async function importUderZip(file: File): Promise<UderImport> {
  // reading the listing does not open every file yet, so this is the spot to
  // stop a big zip before we actually unpack anything
  const zip = await JSZip.loadAsync(file);
  checkZipSize(zip);

  // a .uder zip must have the one text file, no file means no record
  const metaEntry = zip.file("metadata.md");
  if (!metaEntry) throw new Error("this .uder file has no metadata.md");
  const metaText = await metaEntry.async("string");
  const { data, body } = parseFrontmatter(metaText);

  // 2. only the files in images/ are real. anything else in the zip (scripts,
  //    weird paths) is ignored, that is how a zip cannot smuggle a file in.
  const imagePaths: string[] = [];
  zip.forEach((path, entry) => {
    if (entry.dir) return;
    if (path.startsWith("images/")) imagePaths.push(path);
  });

  // turn every image into a fresh object url, keep the original names
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

  // turns every image link found in the text back into an object url
  const resolve = (text: string): string =>
    replaceIllustrations(text, (k) => urlByName[k] ?? k);

  // fix up the fields we use, and only keep values from the lists we trust
  const type = data.type === "exploration" ? "exploration" : "record";
  const faction = ALLOWED_FACTIONS.find((f) => f === data.faction) ?? null;

  const thumbnail = typeof data.thumbnail === "string" ? urlByName[data.thumbnail] ?? null : null;
  // media is a list of image names, turn them into object urls and drop any
  // name that does not match an image we actually found
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