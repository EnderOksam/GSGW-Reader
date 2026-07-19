import JSZip from "jszip";
import { getCachedImage } from "./character-cache";
import { REPO, BRANCH } from "./github-api";

export interface ZipEntry {
  name: string;
  data: string;
}

export async function importZip(file: File): Promise<ZipEntry[]> {
  const zip = await JSZip.loadAsync(file);
  const entries: ZipEntry[] = [];
  const promises: Promise<void>[] = [];
  zip.forEach((path, entry) => {
    if (!entry.dir && path.endsWith(".md")) {
      promises.push(
        entry.async("string").then((data) => {
          entries.push({ name: path.split("/").pop() || path, data });
        })
      );
    }
  });
  await Promise.all(promises);
  return entries;
}

function crc32(data: Uint8Array): number {
  let crc = 0xffffffff;
  for (let i = 0; i < data.length; i++) {
    crc ^= data[i];
    for (let j = 0; j < 8; j++) crc = crc & 1 ? (crc >>> 1) ^ 0xedb88320 : crc >>> 1;
  }
  return (crc ^ 0xffffffff) >>> 0;
}

export function createZip(entries: ZipEntry[]): Uint8Array {
  const encoder = new TextEncoder();
  const localHeaders: Uint8Array[] = [];
  const centralEntries: Uint8Array[] = [];
  let offset = 0;

  for (const entry of entries) {
    const nameBytes = encoder.encode(entry.name);
    const dataBytes = encoder.encode(entry.data);
    const crcVal = crc32(dataBytes);

    const local = new Uint8Array(30 + nameBytes.length + dataBytes.length);
    const dv = new DataView(local.buffer);
    dv.setUint32(0, 0x04034b50, true);
    dv.setUint16(4, 20, true);
    dv.setUint16(6, 0, true);
    dv.setUint16(8, 0, true);
    dv.setUint16(10, 0, true);
    dv.setUint16(12, 0, true);
    dv.setUint32(14, crcVal, true);
    dv.setUint32(18, dataBytes.length, true);
    dv.setUint32(22, dataBytes.length, true);
    dv.setUint16(26, nameBytes.length, true);
    dv.setUint16(28, 0, true);
    local.set(nameBytes, 30);
    local.set(dataBytes, 30 + nameBytes.length);
    localHeaders.push(local);

    const central = new Uint8Array(46 + nameBytes.length);
    const cdv = new DataView(central.buffer);
    cdv.setUint32(0, 0x02014b50, true);
    cdv.setUint16(4, 20, true);
    cdv.setUint16(6, 20, true);
    cdv.setUint16(8, 0, true);
    cdv.setUint16(10, 0, true);
    cdv.setUint16(12, 0, true);
    cdv.setUint16(14, 0, true);
    cdv.setUint32(16, crcVal, true);
    cdv.setUint32(20, dataBytes.length, true);
    cdv.setUint32(24, dataBytes.length, true);
    cdv.setUint16(28, nameBytes.length, true);
    cdv.setUint16(30, 0, true);
    cdv.setUint16(32, 0, true);
    cdv.setUint16(34, 0, true);
    cdv.setUint16(36, 0, true);
    cdv.setUint32(38, 0, true);
    cdv.setUint32(42, offset, true);
    central.set(nameBytes, 46);
    centralEntries.push(central);

    offset += local.length;
  }

  const centralSize = centralEntries.reduce((s, e) => s + e.length, 0);
  const centralOffset = offset;
  const eocd = new Uint8Array(22);
  const ecdv = new DataView(eocd.buffer);
  ecdv.setUint32(0, 0x06054b50, true);
  ecdv.setUint16(4, 0, true);
  ecdv.setUint16(6, 0, true);
  ecdv.setUint16(8, entries.length, true);
  ecdv.setUint16(10, entries.length, true);
  ecdv.setUint32(12, centralSize, true);
  ecdv.setUint32(16, centralOffset, true);
  ecdv.setUint16(20, 0, true);

  const result = new Uint8Array(offset + centralSize + 22);
  let pos = 0;
  for (const h of localHeaders) { result.set(h, pos); pos += h.length; }
  for (const c of centralEntries) { result.set(c, pos); pos += c.length; }
  result.set(eocd, pos);
  return result;
}

export function downloadBlob(blob: BlobPart, filename: string, mimeType: string): void {
  const url = URL.createObjectURL(new Blob([blob], { type: mimeType }));
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export async function exportCharacterZip(
  folder: string,
  jsonContent: string,
  imageFiles: string[]
): Promise<void> {
  const zip = new JSZip();
  zip.file("character.json", jsonContent);
  const seen = new Set(imageFiles);
  for (const filename of seen) {
    try {
      const cached = await getCachedImage(folder, filename);
      if (cached) { zip.file(filename, cached); continue; }
      const url = `https://raw.githubusercontent.com/${REPO}/${BRANCH}/images/gsgw/references/${folder}/${filename}`;
      const res = await fetch(url);
      if (res.ok) zip.file(filename, await res.blob());
    } catch {}
  }
  const blob = await zip.generateAsync({ type: "blob" });
  downloadBlob(blob as BlobPart, `${folder}.zip`, "application/zip");
}

export async function exportAllCharactersZip(
  characters: { name: string; jsonContent: string | null; imageFiles: string[] }[]
): Promise<void> {
  const zip = new JSZip();
  let hasAny = false;
  for (const char of characters) {
    if (!char.jsonContent) continue;
    zip.file(`${char.name}/character.json`, char.jsonContent);
    hasAny = true;
    for (const filename of [...new Set(char.imageFiles)]) {
      try {
        const cached = await getCachedImage(char.name, filename);
        if (cached) { zip.file(`${char.name}/${filename}`, cached); continue; }
        const url = `https://raw.githubusercontent.com/${REPO}/${BRANCH}/images/gsgw/references/${char.name}/${filename}`;
        const res = await fetch(url);
        if (res.ok) zip.file(`${char.name}/${filename}`, await res.blob());
      } catch {}
    }
  }
  if (!hasAny) { alert("No characters to export."); return; }
  const blob = await zip.generateAsync({ type: "blob" });
  downloadBlob(blob as BlobPart, "all-characters.zip", "application/zip");
}
