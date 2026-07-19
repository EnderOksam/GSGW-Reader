import { browser } from "$app/environment";

const DB_NAME = "gsgw-character-cache";
const DB_VERSION = 1;

function openCacheDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    if (!browser) { reject(new Error("not browser")); return; }
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains("json")) {
        db.createObjectStore("json", { keyPath: "folder" });
      }
      if (!db.objectStoreNames.contains("images")) {
        db.createObjectStore("images", { keyPath: "key" });
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

export async function getCachedJson(folder: string): Promise<string | null> {
  try {
    const db = await openCacheDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction("json", "readonly");
      const store = tx.objectStore("json");
      const req = store.get(folder);
      req.onsuccess = () => resolve(req.result?.data ?? null);
      req.onerror = () => reject(req.error);
    });
  } catch { return null; }
}

export async function setCachedJson(folder: string, data: string): Promise<void> {
  try {
    const db = await openCacheDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction("json", "readwrite");
      const store = tx.objectStore("json");
      store.put({ folder, data });
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
  } catch {}
}

export async function getCachedImage(folder: string, filename: string): Promise<Blob | null> {
  try {
    const db = await openCacheDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction("images", "readonly");
      const store = tx.objectStore("images");
      const req = store.get(`${folder}/${filename}`);
      req.onsuccess = () => resolve(req.result?.blob ?? null);
      req.onerror = () => reject(req.error);
    });
  } catch { return null; }
}

export async function setCachedImage(folder: string, filename: string, blob: Blob): Promise<void> {
  try {
    const db = await openCacheDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction("images", "readwrite");
      const store = tx.objectStore("images");
      store.put({ key: `${folder}/${filename}`, blob });
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
  } catch {}
}

export async function removeCachedImage(folder: string, filename: string): Promise<void> {
  try {
    const db = await openCacheDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction("images", "readwrite");
      const store = tx.objectStore("images");
      store.delete(`${folder}/${filename}`);
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
  } catch {}
}

export async function getCachedImageUrl(folder: string, filename: string): Promise<string | null> {
  const blob = await getCachedImage(folder, filename);
  if (!blob) return null;
  return URL.createObjectURL(blob);
}

export async function listCachedImageKeys(folder: string): Promise<string[]> {
  try {
    const db = await openCacheDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction("images", "readonly");
      const store = tx.objectStore("images");
      const req = store.getAllKeys();
      req.onsuccess = () => {
        const keys: string[] = [];
        for (const key of req.result as string[]) {
          if (key.startsWith(folder + "/")) {
            keys.push(key.slice(folder.length + 1));
          }
        }
        resolve(keys);
      };
      req.onerror = () => reject(req.error);
    });
  } catch { return []; }
}

export async function deleteCachedJson(folder: string): Promise<void> {
  try {
    const db = await openCacheDB();
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction("json", "readwrite");
      const store = tx.objectStore("json");
      store.delete(folder);
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
  } catch {}
}
