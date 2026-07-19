export const REPO = "EnderOksam/GSGW-Reader";
export const BRANCH = "main";

export const BOOKS = [
  { slug: "gsgw", label: "Ghost Story, Gotta Work", translations: ["fantl", "MTL", "unfinishedtl"] },
  { slug: "debut", label: "Debut Or Die", translations: ["debutplaintxt", "debutformatted"] },
];

export function tlDir(book: string, tl: string): string {
  if (book === "debut" && tl === "debutplaintxt") return "DebutPlainTxt";
  if (book === "debut" && tl === "debutformatted") return "DebutFormatted";
  return tl;
}

export interface GitHubFile {
  name: string;
  type: string;
}

export async function fetchDirectory(path: string): Promise<GitHubFile[]> {
  const url = `https://api.github.com/repos/${REPO}/contents/${path}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`GitHub API: ${res.status}`);
  return res.json();
}

export async function fetchRawFile(path: string): Promise<string> {
  const url = `https://raw.githubusercontent.com/${REPO}/${BRANCH}/${path}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`fetch: ${res.status}`);
  return res.text();
}

export async function fetchChapterList(book: string, tl: string): Promise<string[]> {
  const data = await fetchDirectory(`chapters/${book}/${tlDir(book, tl)}`);
  return data
    .filter((f) => f.name.endsWith(".md") && f.name !== "metadata.md")
    .map((f) => f.name)
    .sort();
}

export async function fetchChapterFile(book: string, tl: string, file: string): Promise<string> {
  return fetchRawFile(`chapters/${book}/${tlDir(book, tl)}/${file}`);
}

export async function fetchChapterPreview(book: string, tl: string, file: string): Promise<{ title: string; index: string }> {
  const url = `https://raw.githubusercontent.com/${REPO}/${BRANCH}/chapters/${book}/${tlDir(book, tl)}/${file}`;
  const res = await fetch(url);
  if (!res.ok) return { title: "", index: "" };
  const reader = res.body?.getReader();
  if (!reader) return { title: "", index: "" };
  const decoder = new TextDecoder();
  let buf = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    if (buf.length > 2048) break;
  }
  reader.cancel();
  return extractMeta(buf);
}

export async function fetchCharacterDirs(): Promise<string[]> {
  const data = await fetchDirectory("images/gsgw/references");
  return data.filter((f) => f.type === "dir").map((f) => f.name);
}

export async function fetchCharacterJson(dir: string): Promise<any> {
  const url = `https://raw.githubusercontent.com/${REPO}/${BRANCH}/images/gsgw/references/${dir}/character.json`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`fetch: ${res.status}`);
  return res.json();
}

export async function fetchCharacterFile(folder: string, filename: string): Promise<string> {
  return fetchRawFile(`images/gsgw/references/${folder}/${filename}`);
}

export async function fetchCharacterImageUrl(folder: string, filename: string): Promise<string> {
  return `https://raw.githubusercontent.com/${REPO}/${BRANCH}/images/gsgw/references/${folder}/${filename}`;
}

export function extractMeta(text: string): { title: string; index: string } {
  const lines = text.split("\n");
  let title = "";
  let index = "";
  let inFrontmatter = false;
  for (const line of lines) {
    if (line.trim() === "---") {
      if (!inFrontmatter) { inFrontmatter = true; continue; }
      else break;
    }
    if (!inFrontmatter) continue;
    const tm = line.match(/^title:\s*(.+)/i);
    if (tm) title = tm[1].trim().replace(/^["']|["']$/g, "");
    const im = line.match(/^index:\s*(.+)/i);
    if (im) index = im[1].trim();
  }
  return { title, index };
}
