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

  const LONG_TEXT_THRESHOLD = 200;

  // Marks zones whose scare page holds more than LONG_TEXT_THRESHOLD characters
  // of text as data-long, so the CSS snaps them to the top instead of centering
  // them middle-out in the viewport.
  const seenZones = new Set<Element>();
  const markLongSections = () => {
    const zones = getZones();
    if (zones.length === seenZones.size && zones.every((z) => seenZones.has(z))) {
      return;
    }
    seenZones.clear();
    for (const zone of zones) {
      seenZones.add(zone);
      const page = zone.querySelector<HTMLElement>(".scare-page");
      const text = (page?.textContent ?? "").trim();
      if (text.length > LONG_TEXT_THRESHOLD) {
        zone.dataset.long = "true";
      } else {
        delete zone.dataset.long;
      }
    }
  };

  // The editor and dynamically-loaded pages replace the article's DOM after
  // init, so re-mark long sections whenever scare zones appear/disappear.
  const observer = new MutationObserver(markLongSections);
  observer.observe(document.body, { childList: true, subtree: true });

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
      let nextState: string;
      if (progress <= 0.02) {
        nextState = "approaching";
      } else if (progress < 0.16) {
        nextState = "catching";
      } else if (progress < 0.84) {
        nextState = "stuck";
      } else {
        nextState = "releasing";
      }

      // The pinned window keeps its own internal scroll position, so returning
      // to a long scare section could otherwise reopen at its bottom. Whenever
      // we re-enter the stuck state, reset the window so the section snaps back
      // to its top.
      if (nextState === "stuck" && zone.dataset.state !== "stuck") {
        const win = zone.querySelector<HTMLElement>(".scare-window");
        if (win && win.scrollTop > 0) win.scrollTop = 0;
      }
      zone.dataset.state = nextState;

      zone.style.setProperty("--scare-progress", progress.toFixed(4));
      zone.style.setProperty("--scare-percent", `${(progress * 100).toFixed(2)}%`);

      lastScrollTop = scrollTop;
    }
  };

  markLongSections();
  updateZones();
  if (isWindow) window.addEventListener("scroll", updateZones, { passive: true });
  else scrollEl.addEventListener("scroll", updateZones, { passive: true });

  return () => {
    if (isWindow) window.removeEventListener("scroll", updateZones);
    else scrollEl.removeEventListener("scroll", updateZones);
    if (snapTimer) clearTimeout(snapTimer);
    observer.disconnect();
    isSnapping = false;
  };
}