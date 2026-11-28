const ANIMATED_SELECTOR = [
  ".shake",
  ".wave-up",
  ".glitch-text",
  ".glitch-subtle",
  ".glitch-d",
  ".aurora-text",
  ".hex-aurora",
  ".hex-aurora-static",
  ".hex-aurora-up",
  ".hex-aurora-up-static",
  ".gold-text",
  ".silver-text",
  ".moon-text",
  ".sparkle-text",
  ".smoke-text",
  ".scroll-wrap",
  ".transition-text",
  ".hex-outline",
].join(",");

const EFFECT_CONTAINER_SELECTOR = [
  ".scare-window",
  ".transition-text",
  ".scroll-wrap",
  "p",
  "li",
  "blockquote",
].join(",");

let animationVisibilityObserver: IntersectionObserver | null = null;
let observedEffectContainers: Element[] = [];

export function observeAnimationVisibility(): (() => void) | undefined {
  if (typeof IntersectionObserver === "undefined") return;

  animationVisibilityObserver?.disconnect();
  for (const el of observedEffectContainers) el.removeAttribute("data-anim-off");
  observedEffectContainers = [];

  const observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        const el = entry.target as HTMLElement;
        if (entry.isIntersecting) el.removeAttribute("data-anim-off");
        else el.setAttribute("data-anim-off", "");
      }
    },
    { rootMargin: "250px 0px" },
  );
  animationVisibilityObserver = observer;

  document
    .querySelectorAll("article.reader-container")
    .forEach((article) => {
      const targets = new Set<Element>();
      article.querySelectorAll(ANIMATED_SELECTOR).forEach((el) => {
        const target = el.closest(EFFECT_CONTAINER_SELECTOR) ?? el;
        if (target !== el) el.removeAttribute("data-anim-off");
        targets.add(target);
      });
      article.querySelectorAll(".scare-window").forEach((el) => targets.add(el));
      observedEffectContainers.push(...targets);
      for (const target of targets) observer.observe(target);
    });

  return () => {
    observer.disconnect();
    for (const el of observedEffectContainers) el.removeAttribute("data-anim-off");
    observedEffectContainers = [];
    if (animationVisibilityObserver === observer) animationVisibilityObserver = null;
  };
}

// Per-character animation effects rely on randomized (negative) animation-delays
// so neighbouring characters run at different phases. Without this every char
// starts at the same phase and the effect looks like a single mechanical jitter.
export function randomizeAnimationDelays(root: ParentNode = document): void {
  root.querySelectorAll("article.reader-container").forEach((article) => {
    article.querySelectorAll("span.shake").forEach((el) => {
      if (!(el as HTMLElement).style.animationDelay) {
        (el as HTMLElement).style.animationDelay = `-${Math.random() * 0.5}s`;
      }
    });

    article.querySelectorAll("span.wave-up").forEach((el) => {
      if (!(el as HTMLElement).style.animationDelay) {
        (el as HTMLElement).style.animationDelay = `-${Math.random() * 0.6}s`;
      }
    });

    article.querySelectorAll(".glitch-text .char").forEach((el) => {
      if (!(el as HTMLElement).style.animationDelay) {
        (el as HTMLElement).style.animationDelay = `-${Math.random() * 0.25}s`;
      }
    });

    article.querySelectorAll(".glitch-subtle .char").forEach((el) => {
      if (!(el as HTMLElement).style.animationDelay) {
        (el as HTMLElement).style.animationDelay = `-${Math.random() * 2.0}s`;
      }
    });

    article.querySelectorAll(".glitch-d").forEach((el) => {
      if (!(el as HTMLElement).style.animationDelay) {
        (el as HTMLElement).style.animationDelay = `-${Math.random() * 1.6}s`;
      }
    });
  });
}
