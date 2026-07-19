const CUSTOM_TRANSLATIONS_KEY = "editor-custom-translations";

function customStorageKey(tl: string): string {
  return `editor-cache-custom-${tl}`;
}

export function loadCustomTranslations(): string[] {
  try {
    const saved = localStorage.getItem(CUSTOM_TRANSLATIONS_KEY);
    if (saved) return JSON.parse(saved);
  } catch {}
  return [];
}

export function saveCustomTranslations(translations: string[]): void {
  try {
    localStorage.setItem(CUSTOM_TRANSLATIONS_KEY, JSON.stringify(translations));
  } catch {}
}

export function loadCustomChapterList(tl: string): string[] {
  try {
    const data = localStorage.getItem(customStorageKey(tl));
    if (!data) return [];
    return Object.keys(JSON.parse(data)).sort();
  } catch { return []; }
}

export function loadCustomChapterContent(tl: string, file: string): string | null {
  try {
    const data = JSON.parse(localStorage.getItem(customStorageKey(tl)) || "{}");
    return data[file] ?? null;
  } catch { return null; }
}

export function saveCustomChapter(tl: string, file: string, content: string): void {
  try {
    const data = JSON.parse(localStorage.getItem(customStorageKey(tl)) || "{}");
    data[file] = content;
    localStorage.setItem(customStorageKey(tl), JSON.stringify(data));
  } catch {}
}

export function deleteCustomChapter(tl: string, file: string): void {
  try {
    const data = JSON.parse(localStorage.getItem(customStorageKey(tl)) || "{}");
    delete data[file];
    localStorage.setItem(customStorageKey(tl), JSON.stringify(data));
  } catch {}
}

export function renameCustomTranslation(oldName: string, newName: string): void {
  const data = localStorage.getItem(customStorageKey(oldName));
  if (data) localStorage.setItem(customStorageKey(newName), data);
  localStorage.removeItem(customStorageKey(oldName));
}

export function deleteCustomTranslation(tl: string): void {
  try {
    localStorage.removeItem(customStorageKey(tl));
  } catch {}
}
