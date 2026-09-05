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

  const LOCK_DURATION = 2500;

  const triggered = new Set<Element>();
  let lockTimer: ReturnType<typeof setTimeout> | null = null;
  let scrollLocked = false;
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

  const onScroll = () => {
    if (scrollLocked) {
      window.scrollTo(0, lockScrollY);
    }
  };

  window.addEventListener("wheel", onWheel, { passive: false });
  window.addEventListener("touchmove", onTouchMove, { passive: false });
  window.addEventListener("scroll", onScroll, { passive: true });

  function lockScroll() {
    lockScrollY = window.scrollY;
    scrollLocked = true;
  }

  function unlockScroll() {
    scrollLocked = false;
  }

  function endLock() {
    unlockScroll();
    if (lockTimer) clearTimeout(lockTimer);
    window.removeEventListener("click", onClickCancel);
    const article = document.querySelector<HTMLElement>("article[data-scared]");
    if (article) article.removeAttribute("data-scared");
  }

  const onClickCancel = () => endLock();

  function snapToCenter(win: HTMLElement) {
    const rect = win.getBoundingClientRect();
    const target =
      window.scrollY + rect.top + rect.height / 2 - window.innerHeight / 2;
    window.scrollTo(0, target);
    lockScrollY = window.scrollY;
  }

  function activate(zone: HTMLElement) {
    if (triggered.has(zone)) return;
    triggered.add(zone);

    const win = zone.querySelector<HTMLElement>(".scare-window");
    if (!win) return;

    zone.classList.add("scare-active");
    const article = zone.closest("article");
    if (article) article.setAttribute("data-scared", "");

    snapToCenter(win);
    lockScroll();
    window.addEventListener("click", onClickCancel, { passive: true });

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