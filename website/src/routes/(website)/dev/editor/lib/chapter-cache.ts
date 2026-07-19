export interface ChapterCacheData {
  cache: Map<string, string>;
  originalContent: Map<string, string>;
  dirty: Set<string>;
}

export function loadCache(): ChapterCacheData {
  let cache = new Map<string, string>();
  let originalContent = new Map<string, string>();
  let dirty = new Set<string>();

  try {
    const saved = localStorage.getItem("editor-cache");
    if (saved) {
      const parsed = JSON.parse(saved);
      cache = new Map(Object.entries(parsed));
      dirty = new Set(cache.keys());
    }
    const originals = localStorage.getItem("editor-cache-originals");
    if (originals) {
      originalContent = new Map(Object.entries(JSON.parse(originals)));
    }
  } catch {}

  return { cache, originalContent, dirty };
}

export function saveCache(cache: Map<string, string>, originalContent: Map<string, string>): void {
  try {
    localStorage.setItem("editor-cache", JSON.stringify(Object.fromEntries(cache)));
    localStorage.setItem("editor-cache-originals", JSON.stringify(Object.fromEntries(originalContent)));
  } catch {}
}

export function saveChapterEdit(
  cache: Map<string, string>,
  originalContent: Map<string, string>,
  dirty: Set<string>,
  file: string,
  input: string,
  isSource: boolean
): { cache: Map<string, string>; dirty: Set<string> } {
  const newCache = new Map(cache);
  let newDirty = new Set(dirty);

  if (!isSource) {
    const orig = originalContent.get(file);
    if (orig !== undefined && input !== orig) {
      newDirty = new Set([...newDirty, file]);
    } else if (orig !== undefined && input === orig && newDirty.has(file)) {
      newDirty = new Set([...newDirty].filter(f => f !== file));
    }
    return { cache: newCache, dirty: newDirty };
  }

  const orig = originalContent.get(file);
  if (orig !== undefined && input !== orig) {
    newCache.set(file, input);
    newDirty = new Set([...newDirty, file]);
  } else if (orig !== undefined && input === orig && newCache.has(file)) {
    newCache.delete(file);
    newDirty = new Set([...newDirty].filter(f => f !== file));
  } else if (orig === undefined && newCache.has(file)) {
    const cached = newCache.get(file);
    if (cached !== undefined && input !== cached) {
      newCache.set(file, input);
      newDirty = new Set([...newDirty, file]);
    }
  }

  return { cache: newCache, dirty: newDirty };
}
