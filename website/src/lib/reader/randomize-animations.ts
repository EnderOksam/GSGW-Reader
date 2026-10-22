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

let animationVisibilityObserver: IntersectionObserver | null = null;

export function observeAnimationVisibility(): void {
  if (typeof IntersectionObserver === "undefined") return;

  animationVisibilityObserver?.disconnect();
  animationVisibilityObserver = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        const el = entry.target as HTMLElement;
        if (entry.isIntersecting) el.removeAttribute("data-anim-off");
        else el.setAttribute("data-anim-off", "");
      }
    },
    { rootMargin: "250px 0px" },
  );

  document
    .querySelectorAll("article.reader-container")
    .forEach((article) => {
      const targets = new Set<Element>();
      article.querySelectorAll(`${ANIMATED_SELECTOR},.scare-window`).forEach((el) => {
        // Use the stable wrapper for scares rather than the transformed text
        // inside. Its descendants share one visibility state after reveal.
        const target = el.closest(".scare-window") ?? el;
        if (target !== el) el.removeAttribute("data-anim-off");
        targets.add(target);
      });
      for (const target of targets) animationVisibilityObserver!.observe(target);
    });
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
