const RECORD_KEY = "editor-uder-record";
const INTERACTIVE_KEY = "editor-uder-interactive";

export interface UderRecordCache {
  title: string;
  identificationCode: string;
  classification: string;
  content: string;
  shortDescription: string;
  selectedFaction: string | null;
  recordType: string;
  records: { title: string; content: string }[];
}

export interface UderInteractiveCache {
  nodes: unknown[];
  edges: unknown[];
}

export function loadRecordCache(): UderRecordCache | null {
  try {
    const raw = localStorage.getItem(RECORD_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch { return null; }
}

export function saveRecordCache(data: UderRecordCache) {
  try { localStorage.setItem(RECORD_KEY, JSON.stringify(data)); } catch {}
}

export function deleteRecordCache() {
  try { localStorage.removeItem(RECORD_KEY); } catch {}
}

export function loadInteractiveCache(): UderInteractiveCache | null {
  try {
    const raw = localStorage.getItem(INTERACTIVE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch { return null; }
}

export function saveInteractiveCache(data: UderInteractiveCache) {
  try { localStorage.setItem(INTERACTIVE_KEY, JSON.stringify(data)); } catch {}
}

export function deleteInteractiveCache() {
  try { localStorage.removeItem(INTERACTIVE_KEY); } catch {}
}
