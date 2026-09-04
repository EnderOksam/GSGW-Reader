// Scroll-driven scare pagebreak.
//
// Each <pagebreak> becomes a `.scare-zone` (tall 250dvh scroll budget) wrapping
// a sticky `.scare-window` (full-viewport) holding `.scare-page`.
//
// This module:
//   * catches the zone while scrolling down (approaches within 35% of a
//     viewport) by smoothly scrolling to its start — downward only, so
//     scrolling back up never fights the reader
//   * drives the `approaching → catching → stuck → releasing` states and the
//     `--scare-progress` / `--scare-percent` CSS variables that animate the
//     pinned page as the reader scrolls through the zone
//
// Intentionally avoids CSS scroll-snap-type: it would fight the continuous
// scroll-driven animation.

export function initScareScroll(scrollEl: Window | HTMLElement): () => void {
  const isWindow = scrollEl === window;

  let lastScrollTop = -1;
  let isSnapping = false;
  let snapTimer: ReturnType<typeof setTimeout> | null = null;

  const clamp = (value: number, min: number, max: number) =>
    Math.min(Math.max(value, min), max);

  const getScrollTop = (): number =>
    isWindow ? window.scrollY : (scrollEl as HTMLElement).scrollTop;

  const getViewportHeight = (): number =>
    isWindow ? window.innerHeight : (scrollEl as HTMLElement).clientHeight;

  const getContainerTop = (): number =>
    isWindow ? 0 : (scrollEl as HTMLElement).getBoundingClientRect().top;

  const getZones = (): HTMLElement[] => {
    const all = Array.from(
      document.querySelectorAll<HTMLElement>(".scare-zone")
    );
    if (isWindow) return all;
    return all.filter((z) => (scrollEl as HTMLElement).contains(z));
  };

  const updateZones = () => {
    const scrollTop = getScrollTop();
    const viewportHeight = getViewportHeight();
    const zones = getZones();
    if (zones.length === 0) return;

    if (lastScrollTop < 0) lastScrollTop = scrollTop;
    const scrollingDown = scrollTop > lastScrollTop;

    for (const zone of zones) {
      const containerTop = getContainerTop();
      const start = scrollTop + (zone.getBoundingClientRect().top - containerTop);
      const end = start + zone.offsetHeight - viewportHeight;

      const progress = clamp(
        (scrollTop - start) / Math.max(end - start, 1),
        0,
        1
      );

      /*
       * CATCH
       * Only catch while moving downward — prevents scrolling upward from
       * unexpectedly snapping the reader back into the pagebreak.
       */
      const distanceToStart = start - scrollTop;

      if (
        scrollingDown &&
        !isSnapping &&
        distanceToStart > 0 &&
        distanceToStart < viewportHeight * 0.35
      ) {
        isSnapping = true;
        zone.dataset.state = "catching";
        if (isWindow) window.scrollTo({ top: start, behavior: "smooth" });
        else (scrollEl as HTMLElement).scrollTo({ top: start, behavior: "smooth" });

        if (snapTimer) clearTimeout(snapTimer);
        snapTimer = setTimeout(() => {
          isSnapping = false;
        }, 450);

        lastScrollTop = scrollTop;
        continue;
      }

      /*
       * STATES
       */
      if (progress <= 0.02) {
        zone.dataset.state = "approaching";
      } else if (progress < 0.16) {
        zone.dataset.state = "catching";
      } else if (progress < 0.84) {
        zone.dataset.state = "stuck";
      } else {
        zone.dataset.state = "releasing";
      }

      zone.style.setProperty("--scare-progress", progress.toFixed(4));
      zone.style.setProperty("--scare-percent", `${(progress * 100).toFixed(2)}%`);

      lastScrollTop = scrollTop;
    }
  };

  updateZones();
  if (isWindow) window.addEventListener("scroll", updateZones, { passive: true });
  else scrollEl.addEventListener("scroll", updateZones, { passive: true });

  return () => {
    if (isWindow) window.removeEventListener("scroll", updateZones);
    else scrollEl.removeEventListener("scroll", updateZones);
    if (snapTimer) clearTimeout(snapTimer);
    isSnapping = false;
  };
}