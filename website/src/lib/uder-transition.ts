import { writable } from "svelte/store";

export type UderPhase = "idle" | "fade-in" | "hold" | "fade-out";

export const uderTransition = writable<UderPhase>("idle");
