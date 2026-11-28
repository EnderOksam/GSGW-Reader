import { writable } from "svelte/store";

const STORAGE_KEY = "gsgw-broken-avatars";

function loadBroken(): Set<string> {
  if (typeof sessionStorage === "undefined") return new Set();
  try {
    const stored = JSON.parse(sessionStorage.getItem(STORAGE_KEY) || "[]");
    return new Set(Array.isArray(stored) ? stored.filter((url): url is string => typeof url === "string") : []);
  } catch {
    return new Set();
  }
}

export const brokenAvatars = writable<Set<string>>(loadBroken());

const icon = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" fill="#e5e7eb"/><circle cx="32" cy="25" r="11" fill="#9ca3af"/><path d="M12 64c0-12 9-20 20-20s20 8 20 20z" fill="#9ca3af"/></svg>`;
export const DEFAULT_AVATAR_SRC = `data:image/svg+xml,${encodeURIComponent(icon)}`;

export function markAvatarBroken(src: string): void {
  brokenAvatars.update((broken) => {
    if (broken.has(src)) return broken;
    const next = new Set(broken);
    next.add(src);
    if (typeof sessionStorage !== "undefined") {
      try {
        sessionStorage.setItem(STORAGE_KEY, JSON.stringify([...next]));
      } catch {
        /* ignore */
      }
    }
    return next;
  });
}
