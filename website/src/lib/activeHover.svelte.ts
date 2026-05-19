import { writable } from "svelte/store";

export const activeHover = writable<string | null>(null);

let hideTimeout: ReturnType<typeof setTimeout> | null = null;

export function clearHideTimeout() {
  if (hideTimeout !== null) {
    clearTimeout(hideTimeout);
    hideTimeout = null;
  }
}

export function scheduleHide() {
  clearHideTimeout();
  hideTimeout = setTimeout(() => {
    activeHover.set(null);
    hideTimeout = null;
  }, 250);
}
