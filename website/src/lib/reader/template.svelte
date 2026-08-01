<script lang="ts">

  import css from "../../../../reader.css?url";
  import "$lib/reader/reader-windows.css";

  import { readerState } from "$lib/reader.svelte";
  import { hydrateTwitterEmbeds } from "$lib/reader/twitter-embeds";
  import { consumeSnippetTarget } from "$lib/content-search";

  import { untrack, onMount } from 'svelte';



  let ch_meta = null;

  let html_content = "";

  let footnotes = "";



  $effect(() => {

    if (ch_meta) {

      untrack(() => {

        readerState.ch_meta = ch_meta;

      });

    }

  });

  $effect(() => {
    readerState.footnotes = footnotes;
  });

  onMount(() => {
    const target = consumeSnippetTarget();
    if (!target) return;
    const { query } = target;
    setTimeout(() => {
      const article = document.querySelector("article.reader-container");
      if (!article) return;
      const q = query.toLowerCase();
      const all = article.querySelectorAll("p, span, div, h1, h2, h3, h4, strong, em");
      for (const el of all) {
        const text = el.textContent?.toLowerCase() || "";
        if (text.includes(q)) {
          el.scrollIntoView({ behavior: "smooth", block: "center" });
          el.classList.add("search-highlight");
          setTimeout(() => el.classList.remove("search-highlight"), 2500);
          return;
        }
      }
    }, 300);
  });



  $effect(() => {
    hydrateTwitterEmbeds();
  });

  // Smart footnote tooltips: work on tap (mobile) and hover (desktop), stay
  // inside the viewport, and the card back-link lands on the reference.
  // The tooltip renders into a single portal element on <body> so ancestor
  // transforms/overflow (e.g. the reader's translateX panes) can never clip
  // it or break its fixed positioning.
  const FOOTNOTE_GAP = 10;
  const FOOTNOTE_MIN_PAD = 8;
  let activeRef: HTMLElement | null = null;
  let repositionQueued = false;

  function getTipPortal(): HTMLElement {
    let portal = document.querySelector<HTMLElement>(".fn-tip-portal");
    if (!portal) {
      portal = document.createElement("div");
      portal.className = "fn-tip fn-tip-portal";
      document.body.appendChild(portal);
    }
    return portal;
  }

  function clamp(v: number, lo: number, hi: number) {
    return Math.max(lo, Math.min(v, hi));
  }

  function positionFootnoteTip(ref: HTMLElement) {
    const portal = getTipPortal();
    const refRect = ref.getBoundingClientRect();
    const vw = window.innerWidth;
    const vh = window.innerHeight;

    if (refRect.bottom < 0 || refRect.top > vh) {
      hideFootnoteTip();
      return;
    }

    const tipWidth = portal.offsetWidth;
    const tipHeight = portal.offsetHeight;

    const cx = refRect.left + refRect.width / 2;
    const left = clamp(cx - tipWidth / 2, FOOTNOTE_MIN_PAD, vw - tipWidth - FOOTNOTE_MIN_PAD);
    portal.style.left = `${left}px`;

    portal.style.setProperty("--fn-arrow-left", `${clamp(cx - left, 16, tipWidth - 16)}px`);

    const spaceBelow = vh - refRect.bottom;
    const spaceAbove = refRect.top;
    if (spaceBelow >= tipHeight + FOOTNOTE_GAP || spaceBelow >= spaceAbove) {
      portal.classList.add("fn-tip-flip");
      portal.style.bottom = "auto";
      portal.style.top = `${Math.min(refRect.bottom + FOOTNOTE_GAP, vh - tipHeight - FOOTNOTE_MIN_PAD)}px`;
    } else {
      portal.classList.remove("fn-tip-flip");
      portal.style.top = "auto";
      portal.style.bottom = `${Math.max(vh - refRect.top + FOOTNOTE_GAP, FOOTNOTE_MIN_PAD)}px`;
    }
  }

  function showFootnoteTip(ref: HTMLElement) {
    const inline = ref.querySelector(".fn-tip") as HTMLElement | null;
    if (!inline) return;
    const portal = getTipPortal();
    portal.innerHTML = inline.innerHTML;
    portal.classList.remove("fn-tip-flip");
    portal.style.display = "block";
    portal.style.maxWidth = `min(320px, ${window.innerWidth - 16}px)`;
    activeRef = ref;
    positionFootnoteTip(ref);
  }

  function hideFootnoteTip() {
    activeRef = null;
    const portal = document.querySelector<HTMLElement>(".fn-tip-portal");
    if (portal) portal.style.display = "none";
  }

  function queueReposition() {
    if (repositionQueued || !activeRef) return;
    repositionQueued = true;
    requestAnimationFrame(() => {
      repositionQueued = false;
      if (activeRef && activeRef.isConnected) positionFootnoteTip(activeRef);
      else hideFootnoteTip();
    });
  }

  function openFootnote(ref: HTMLElement) {
    ref.classList.add("fn-open");
    showFootnoteTip(ref);
  }

  function closeFootnote(ref: HTMLElement) {
    ref.classList.remove("fn-open");
    hideFootnoteTip();
  }

  function closeAllFootnotes() {
    document.querySelectorAll(".fn-ref.fn-open").forEach((el) => el.classList.remove("fn-open"));
    hideFootnoteTip();
  }

  function onFootnoteMouseOver(e: Event) {
    const ref = (e.target as HTMLElement).closest(".fn-ref") as HTMLElement | null;
    if (ref) showFootnoteTip(ref);
  }

  function onFootnoteMouseOut(e: Event) {
    const ref = (e.target as HTMLElement).closest(".fn-ref") as HTMLElement | null;
    if (!ref) return;
    const to = (e as MouseEvent).relatedTarget as Node | null;
    if (to && ref.contains(to)) return;
    if (to && document.querySelector(".fn-tip-portal")?.contains(to)) return;
    if (ref.classList.contains("fn-open")) return;
    hideFootnoteTip();
  }

  function handleFootnoteClick(e: MouseEvent) {
    const target = e.target as HTMLElement;
    const back = target.closest<HTMLElement>(".fn-back");
    if (back) {
      e.preventDefault();
      closeAllFootnotes();
      const id = back.getAttribute("href")?.replace(/^#/, "");
      const dest = id ? document.getElementById(id) : null;
      if (dest) dest.scrollIntoView({ behavior: "smooth", block: "center" });
      return;
    }

    const ref = target.closest<HTMLElement>(".fn-ref");
    if (ref) {
      if (ref.classList.contains("fn-open")) {
        closeFootnote(ref);
      } else {
        closeAllFootnotes();
        openFootnote(ref);
      }
      return;
    }
    if (document.querySelector(".fn-ref.fn-open")) {
      closeAllFootnotes();
    }
  }

  $effect(() => {
    const article = document.querySelector("article.reader-container") as HTMLElement | null;
    if (!article) return;
    article.addEventListener("mouseover", onFootnoteMouseOver as EventListener);
    article.addEventListener("mouseout", onFootnoteMouseOut as EventListener);
    document.addEventListener("click", handleFootnoteClick as EventListener);
    window.addEventListener("scroll", queueReposition, { passive: true });
    window.addEventListener("resize", queueReposition);
    return () => {
      article.removeEventListener("mouseover", onFootnoteMouseOver as EventListener);
      article.removeEventListener("mouseout", onFootnoteMouseOut as EventListener);
      document.removeEventListener("click", handleFootnoteClick as EventListener);
      window.removeEventListener("scroll", queueReposition);
      window.removeEventListener("resize", queueReposition);
      document.querySelector(".fn-tip-portal")?.remove();
    };
  });

</script>



<svelte:head>

  <link rel="stylesheet" href={css}>

</svelte:head>



<article

  class="reader-container"

>

  {@html html_content}

</article>

