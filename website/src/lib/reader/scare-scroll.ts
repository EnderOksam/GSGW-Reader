export function initScareScroll(scrollEl: Window | HTMLElement): () => void {
  const isWindow = scrollEl === window;

  if (!isWindow) {
    const container = scrollEl as HTMLElement;

    const markPreviewZones = () => {
      const zones = container.querySelectorAll<HTMLElement>(".scare-zone");
      for (const z of zones) {
        z.dataset.preview = "true";
      }
    };

    markPreviewZones();
    const previewObserver = new MutationObserver(markPreviewZones);
    previewObserver.observe(container, { childList: true, subtree: true });

    return () => previewObserver.disconnect();
  }

  const LOCK_DURATION = 800;
  const REVEAL_DELAY = 180;
  const EASE_BACK_MS = 240;
  const SETTLE_WAIT_MS = 900;

  const triggered = new Set<Element>();
  let lockTimer: ReturnType<typeof setTimeout> | null = null;
  let revealTimer: ReturnType<typeof setTimeout> | null = null;
  let scrollLocked = false;
  let returnAnim = false;
  let lockScrollY = 0;

  const onWheel = (e: WheelEvent) => {
    if (scrollLocked) {
      e.preventDefault();
      e.stopPropagation();
    }
  };

  const onTouchMove = (e: TouchEvent) => {
    if (scrollLocked) {
      e.preventDefault();
      e.stopPropagation();
    }
  };

  // Ease back to the locked position instead of yanking instantly — keeps the
  // "can't look away" tension without the mechanical snap.
  function easeBackTo(targetY: number) {
    if (returnAnim) return;
    returnAnim = true;
    const startY = window.scrollY;
    const startTime = performance.now();
    const step = (now: number) => {
      const t = Math.min((now - startTime) / EASE_BACK_MS, 1);
      const eased = 1 - Math.pow(1 - t, 3);
      window.scrollTo(0, startY + (targetY - startY) * eased);
      if (t < 1) requestAnimationFrame(step);
      else returnAnim = false;
    };
    requestAnimationFrame(step);
  }

  const onScroll = () => {
    if (scrollLocked && window.scrollY !== lockScrollY) {
      easeBackTo(lockScrollY);
    }
  };

  window.addEventListener("wheel", onWheel, { passive: false });
  window.addEventListener("touchmove", onTouchMove, { passive: false });
  window.addEventListener("scroll", onScroll, { passive: true });

  function setLock(y: number) {
    lockScrollY = y;
    scrollLocked = true;
  }

  function endLock() {
    scrollLocked = false;
    returnAnim = false;
    if (lockTimer) clearTimeout(lockTimer);
    if (revealTimer) clearTimeout(revealTimer);
    window.removeEventListener("click", onClickCancel);
    const article = document.querySelector<HTMLElement>("article[data-scared]");
    if (article) article.removeAttribute("data-scared");
  }

  const onClickCancel = () => endLock();

  function snapToCenter(win: HTMLElement) {
    const rect = win.getBoundingClientRect();
    const target =
      window.scrollY + rect.top + rect.height / 2 - window.innerHeight / 2;
    window.scrollTo({ top: target, behavior: "smooth" });
    return target;
  }

  // Wait for the smooth scroll to settle before locking so the lock never
  // fights the animated arrival. Falls back to a max wait so the forced
  // pause still engages if the reader interrupts the scroll.
  function lockWhenSettled(target: number) {
    const startedAt = performance.now();
    const settle = () => {
      if (
        Math.abs(window.scrollY - target) < 2 ||
        performance.now() - startedAt > SETTLE_WAIT_MS
      ) {
        setLock(target);
      } else {
        requestAnimationFrame(settle);
      }
    };
    requestAnimationFrame(settle);
  }

  function activate(zone: HTMLElement) {
    if (triggered.has(zone)) return;
    triggered.add(zone);

    const win = zone.querySelector<HTMLElement>(".scare-window");
    if (!win) return;

    const article = zone.closest("article");
    if (article) article.setAttribute("data-scared", "");

    const target = snapToCenter(win);
    lockWhenSettled(target);
    window.addEventListener("click", onClickCancel, { passive: true });

    // Reveal the horror a beat after the world dims around it.
    revealTimer = setTimeout(() => {
      zone.classList.add("scare-active");
    }, REVEAL_DELAY);

    if (lockTimer) clearTimeout(lockTimer);
    lockTimer = setTimeout(endLock, LOCK_DURATION);
  }

  const observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          const zone = (entry.target as HTMLElement).closest<HTMLElement>(
            ".scare-zone"
          );
          if (zone) activate(zone);
        }
      }
    },
    { rootMargin: "-40% 0px -40% 0px", threshold: 0 }
  );

  const getWindows = (): HTMLElement[] =>
    Array.from(document.querySelectorAll<HTMLElement>(".scare-window"));

  const observeWindows = () => {
    for (const win of getWindows()) {
      const zone = win.closest<HTMLElement>(".scare-zone");
      if (zone && !triggered.has(zone)) {
        observer.observe(win);
      }
    }
  };

  observeWindows();
  const domObserver = new MutationObserver(observeWindows);
  domObserver.observe(document.body, { childList: true, subtree: true });

  return () => {
    observer.disconnect();
    domObserver.disconnect();
    window.removeEventListener("wheel", onWheel);
    window.removeEventListener("touchmove", onTouchMove);
    window.removeEventListener("scroll", onScroll);
    endLock();
  };
}