import { writable } from "svelte/store";

export type UderPhase = "idle" | "fade-in" | "hold" | "fade-out" | "back-hold" | "back-fade";

export const uderTransition = writable<UderPhase>("idle");
