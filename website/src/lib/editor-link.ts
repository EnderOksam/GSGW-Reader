export interface EditorBook {
  slug: string;
  label: string;
  translations: string[];
}

export const EDITOR_BOOKS: EditorBook[] = [
  { slug: "gsgw", label: "Ghost Story, Gotta Work", translations: ["fantl", "MTL", "unformattedtl"] },
  { slug: "debut", label: "Debut Or Die", translations: ["debutplaintxt", "debutformatted"] },
];

export function canonicalEditorTranslation(book: string, tl: string): string | null {
  const config = EDITOR_BOOKS.find((b) => b.slug === book);
  if (!config) return null;
  if (book === "gsgw" && tl === "mtl") return "MTL";
  return config.translations.includes(tl) ? tl : null;
}

export function editorChapterFile(book: string, chapter: number): string | null {
  if (!EDITOR_BOOKS.some((b) => b.slug === book)) return null;
  if (!Number.isInteger(chapter) || chapter < 0) return null;
  const number = chapter + (book === "debut" ? 0 : 1);
  return `${String(number).padStart(4, "0")}.md`;
}

export function editorChapterHref(book: string, tl: string, chapter: number): string | null {
  const translation = canonicalEditorTranslation(book, tl);
  const file = editorChapterFile(book, chapter);
  if (!translation || !file) return null;
  return `/edit/${encodeURIComponent(book)}/${encodeURIComponent(tl)}/${chapter}`;
}
