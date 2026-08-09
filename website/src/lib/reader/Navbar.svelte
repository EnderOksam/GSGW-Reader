<script lang="ts">
  import Icon from "@iconify/svelte";
  import { fade } from "svelte/transition";
  import { tick } from "svelte";
  import { toPng } from "html-to-image";
  import { readerState } from "$lib/reader.svelte";
  import ReferencePanel from "./ReferencePanel.svelte";
  import readerCss from "../../routes/(reader)/reader.css?inline";
  import readerWindowsCss from "./reader-windows.css?inline";
  import { searchChapterContent, renderSnippet as renderSearchSnippet, storeSnippetTarget } from "$lib/content-search";
  import type { ContentMatch } from "$lib/content-search";
  import { browser } from "$app/environment";
  import { goto } from "$app/navigation";

  // --- Types ---
  interface Chapter {
    title: string;
    slug: string | number;
  }

  // --- Props ---
  // Using Svelte 5 $props for reactive input
  let { prefs, bookSlug, bookData, navState = $bindable(), currentChapter = 0, chaptersForTL = [], currentIndex = 0, currentTL = "", nextInfoDialog = undefined as HTMLDialogElement | undefined } = $props();
  const totalChapters = $derived(chaptersForTL.length);

  // --- State ---
  // Store dialog references in a reactive object for element binding
  let modals = $state({
    chapter: null as HTMLDialogElement | null,
    settings: null as HTMLDialogElement | null,
    edit: null as HTMLDialogElement | null,
    snippet: null as HTMLDialogElement | null,
  });

  let snippetToast = $state(false);
  let snippetTimer: ReturnType<typeof setTimeout> | null = null;
  let capturedHtml = $state("");
  let snippetPreviewEl: HTMLElement | null = $state(null);
  let snippetOuterEl: HTMLElement | null = $state(null);
  let snippetImageUrl = $state("");
  let snippetLoading = $state(false);
  function loadSnippetPref<T>(key: string, fallback: T): T {
    if (!browser) return fallback;
    try {
      const saved = localStorage.getItem("snippetPrefs");
      if (saved) return (JSON.parse(saved)[key] ?? fallback) as T;
    } catch { /* ignore */ }
    return fallback;
  }
  let snippetShowDomain = $state(loadSnippetPref("showDomain", true));
  let snippetShowChapter = $state(loadSnippetPref("showChapter", true));
  let snippetShowShadow = $state(loadSnippetPref("showShadow", true));
  $effect(() => {
    const d = snippetShowDomain, c = snippetShowChapter, s = snippetShowShadow;
    if (browser) localStorage.setItem("snippetPrefs", JSON.stringify({ showDomain: d, showChapter: c, showShadow: s }));
  });
  let snippetCopied = $state(false);
  let snippetPrimaryColor = $state("oklch(var(--p))");

  // --- Selection cache (iOS coyote time) ---
  let cachedSelectionHtml = $state("");
  let selectionCacheExpiry: ReturnType<typeof setTimeout> | null = null;

  function topLevelBlock(node: Node, root: HTMLElement): HTMLElement | null {
    if (node === root) return null;
    let el: HTMLElement | null =
      node.nodeType === Node.ELEMENT_NODE ? node as HTMLElement : node.parentElement;
    if (!el) return null;
    while (el.parentElement && el.parentElement !== root) {
      el = el.parentElement;
    }
    return el === root ? null : el;
  }

  function expandRangeToParagraphs(range: Range, root: HTMLElement): Range {
    const startBlock = topLevelBlock(range.startContainer, root);
    const endBlock = topLevelBlock(range.endContainer, root);
    if (startBlock) range.setStart(startBlock, 0);
    if (endBlock) range.setEnd(endBlock, endBlock.childNodes.length);
    return range;
  }

  $effect(() => {
    function onSelectionChange() {
      const selection = window.getSelection();
      if (!selection || selection.isCollapsed || !selection.rangeCount) return;

      const range = selection.getRangeAt(0);
      const container = range.commonAncestorContainer;
      const el = container.nodeType === 1 ? container as HTMLElement : container.parentElement;
      const article = el?.closest("article");
      if (!article) return;

      const expanded = expandRangeToParagraphs(range.cloneRange(), article);
      const cloned = expanded.cloneContents();
      const wrapper = document.createElement("div");
      wrapper.appendChild(cloned);
      cachedSelectionHtml = wrapper.innerHTML;

      if (selectionCacheExpiry) clearTimeout(selectionCacheExpiry);
      selectionCacheExpiry = setTimeout(() => { cachedSelectionHtml = ""; }, 3000);
    }

    document.addEventListener("selectionchange", onSelectionChange);
    return () => {
      document.removeEventListener("selectionchange", onSelectionChange);
      if (selectionCacheExpiry) clearTimeout(selectionCacheExpiry);
    };
  });

  const BOOK_NAMES: Record<string, string> = {
    gsgw: "Got Dropped into a Ghost Story, Still Gotta Work",
    debut: "Debut or Die",
  };

  const snippetBookName = $derived(BOOK_NAMES[bookSlug] ?? bookSlug);
  const snippetChapterTitle = $derived.by(() => {
    const ch = chaptersForTL[currentIndex];
    if (!ch) return "";
    return ch.title === `Chapter ${ch.slug}` ? String(ch.slug) : `${ch.slug} - ${ch.title}`;
  });

  async function handleCapture() {
    const selection = window.getSelection();
    if (selection && !selection.isCollapsed && selection.rangeCount) {
      const range = selection.getRangeAt(0);
      const container = range.commonAncestorContainer;
      const el = container.nodeType === 1 ? container as HTMLElement : container.parentElement;
      const article = el?.closest("article");
      if (!article) return;

      const cloned = range.cloneContents();
      const wrapper = document.createElement("div");
      wrapper.appendChild(cloned);
      capturedHtml = wrapper.innerHTML;
      selection.removeAllRanges();
    } else if (cachedSelectionHtml) {
      capturedHtml = cachedSelectionHtml;
      cachedSelectionHtml = "";
      if (selectionCacheExpiry) { clearTimeout(selectionCacheExpiry); selectionCacheExpiry = null; }
    } else {
      snippetToast = true;
      if (snippetTimer) clearTimeout(snippetTimer);
      snippetTimer = setTimeout(() => { snippetToast = false; }, 2000);
      return;
    }

    snippetLoading = true;
    snippetImageUrl = "";
    snippetCopied = false;
    modals.snippet?.showModal();

    await tick();
    await applyReaderStyles();
    await renderSnippet();
  }

  async function applyReaderStyles() {
    if (!snippetPreviewEl) return;

    const readerBgEl = document.querySelector<HTMLElement>(".bg-base-100");
    if (readerBgEl) {
      const cs = getComputedStyle(readerBgEl);
      snippetPreviewEl.style.background = cs.backgroundColor;
    }
    const readerArticle = document.querySelector("article.reader-container") ?? document.querySelector("article.chapter-content");
    if (readerArticle) {
      const cs = getComputedStyle(readerArticle);
      snippetPreviewEl.style.fontFamily = cs.fontFamily;
      snippetPreviewEl.style.fontSize = cs.fontSize;
      snippetPreviewEl.style.fontWeight = cs.fontWeight;
      snippetPreviewEl.style.color = cs.color;
      snippetPreviewEl.style.lineHeight = cs.lineHeight;
      const chapterSize = cs.getPropertyValue("--chapter-size").trim();
      const chapterFont = cs.getPropertyValue("--chapter-font").trim();
      const chapterWeight = cs.getPropertyValue("--chapter-weight").trim();
      const chapterLh = cs.getPropertyValue("--chapter-lh").trim();
      if (chapterSize) snippetPreviewEl.style.setProperty("--chapter-size", chapterSize);
      if (chapterFont) snippetPreviewEl.style.setProperty("--chapter-font", chapterFont);
      if (chapterWeight) snippetPreviewEl.style.setProperty("--chapter-weight", chapterWeight);
      if (chapterLh) snippetPreviewEl.style.setProperty("--chapter-lh", chapterLh);

      snippetPreviewEl.style.paddingLeft = cs.paddingLeft;
      snippetPreviewEl.style.paddingRight = cs.paddingRight;
      const borderX = parseFloat(getComputedStyle(snippetPreviewEl).borderLeftWidth) + parseFloat(getComputedStyle(snippetPreviewEl).borderRightWidth);
      snippetPreviewEl.style.maxWidth = "none";
      snippetPreviewEl.style.width = `${Math.max(320, readerArticle.getBoundingClientRect().width + borderX)}px`;
      if (snippetOuterEl) {
        snippetOuterEl.style.width = `${parseFloat(getComputedStyle(snippetPreviewEl).width) + 40}px`;
      }
    }

    const primaryEl = document.querySelector<HTMLElement>(".text-primary");
    if (primaryEl) {
      snippetPrimaryColor = getComputedStyle(primaryEl).color;
    }

    let styleEl = snippetPreviewEl.querySelector("style#snippet-injected-css");
    if (!styleEl) {
      styleEl = document.createElement("style");
      styleEl.id = "snippet-injected-css";
      snippetPreviewEl.prepend(styleEl);
    }
    const winPins = ["bare-window", "wiki-window", "plain-window"]
      .map((sel) => {
        const w = readerArticle.querySelector(`.${sel}`);
        return w ? `.snippet-preview .${sel} { max-width: ${w.getBoundingClientRect().width}px !important; }` : "";
      })
      .filter(Boolean)
      .join("\n");
    styleEl.textContent = readerCss + "\n" + readerWindowsCss + "\n" + `
      .snippet-preview > :first-child { margin-top: 0 !important; padding-top: 0 !important; }
      .snippet-preview > :last-child { margin-bottom: 0 !important; padding-bottom: 0 !important; }
      ${winPins}
      /* html-to-image drops box-shadow on iOS: replace window shadows with filter drop-shadow */
      .snippet-preview .bare-window,
      .snippet-preview .plain-window,
      .snippet-preview .wiki-window {
        box-shadow: none !important;
        filter: drop-shadow(0 4px 24px oklch(0 0 0 / 0.4));
      }
    `;
  }

  async function renderSnippet() {
    if (!snippetOuterEl) return;
    snippetLoading = true;
    await tick();

    try {
      const readerBgEl = document.querySelector<HTMLElement>(".bg-base-100");
      const bg = readerBgEl ? getComputedStyle(readerBgEl).backgroundColor : "#0d0d0d";

      snippetImageUrl = await toPng(snippetOuterEl, {
        pixelRatio: 2,
        backgroundColor: bg,
        style: { borderRadius: "0" },
      });
    } catch (e) {
      console.error("Failed to render snippet:", e);
    } finally {
      snippetLoading = false;
    }
  }

  function onSnippetToggle() {
    snippetCopied = false;
    renderSnippet();
  }

  async function copySnippet() {
    if (!snippetImageUrl) return;
    try {
      const res = await fetch(snippetImageUrl);
      const blob = await res.blob();
      await navigator.clipboard.write([
        new ClipboardItem({ "image/png": blob }),
      ]);
      snippetCopied = true;
      setTimeout(() => { snippetCopied = false; }, 2000);
    } catch (e) {
      console.error("Failed to copy snippet:", e);
    }
  }

  function downloadSnippet() {
    if (!snippetImageUrl) return;
    const link = document.createElement("a");
    link.download = "snippet.png";
    link.href = snippetImageUrl;
    link.click();
  }

  // --- Constants: Themes ---
  const PRIORITY_THEMES = ["sunset", "light", "retro", "night", "business", "cupcake", "black"];
  const ALL_THEMES = [
    "sunset", "light", "dark", "cupcake", "bumblebee", "emerald", "corporate",
    "synthwave", "retro", "cyberpunk", "valentine", "halloween", "garden",
    "forest", "aqua", "lofi", "pastel", "fantasy", "wireframe", "black",
    "luxury", "dracula", "cmyk", "autumn", "business", "acid", "lemonade",
    "night", "coffee", "winter", "dim", "nord",
  ];
  const MISC_THEMES = ALL_THEMES.filter((t) => !PRIORITY_THEMES.includes(t));

  // --- Constants: Fonts ---
  const BOOK_FONTS = ["Alegreya", "Bookerly", "Roboto", "monospace", "Merriweather"];
  const SYSTEM_FONTS = [
    "EB Garamond", "Crimson Pro", "Georgia", "Verdana", "Arial", "sans-serif",
    "Times New Roman", "serif", "Helvetica", "Tahoma", "system-ui",
    "Trebuchet MS", "Courier New",
  ];

  // --- Logic: Derivations ---
  function tlDir(book: string, tl: string): string {
    if (book === "debut" && tl === "debutplaintxt") return "DebutPlainTxt";
    if (book === "debut" && tl === "debutformatted") return "DebutFormatted";
    return tl;
  }
  // Automatically updates the list whenever searchQuery or selectedTL changes
  const chapterList = $derived.by(() => {
    const chapters: Chapter[] = bookData[bookSlug]?.[navState.selectedTL] || [];
    const q = navState.searchQuery.toLowerCase();
    return chapters.filter(
      (ch) => ch.title.toLowerCase().includes(q) || ch.slug.toString().includes(q)
    );
  });

  const totalAllChapters = $derived(
    Object.values(bookData[bookSlug] || {}).reduce((sum: number, tl: any) => sum + tl.length, 0)
  );
  const totalCurrentTL = $derived(
    (bookData[bookSlug]?.[navState.selectedTL] || []).length
  );
  const isSearching = $derived(navState.searchQuery.trim().length > 0);

  let contentMatches = $state<Map<string, ContentMatch>>(new Map());
  let isSearchingContent = $state(false);
  let contentSearchAbort: AbortController | null = null;
  let contentSearchTimeout: ReturnType<typeof setTimeout> | null = null;

  const isTempBook = $derived(bookSlug === "temp" || bookSlug === "manwha");

  const displayList = $derived.by(() => {
    if (!isSearching) return chapterList;
    const seen = new Set(chapterList.map((c) => c.slug.toString()));
    const allChapters: Chapter[] = bookData[bookSlug]?.[navState.selectedTL] || [];
    const extra: Chapter[] = [];
    for (const slug of contentMatches.keys()) {
      if (!seen.has(slug)) {
        const ch = allChapters.find((c) => c.slug.toString() === slug);
        if (ch) extra.push(ch);
      }
    }
    return [...chapterList, ...extra];
  });

  $effect(() => {
    const q = navState.searchQuery;
    const chapters: Chapter[] = bookData[bookSlug]?.[navState.selectedTL] || [];
    const titleSlugMatches = chapters.filter(
      (ch) => ch.title.toLowerCase().includes(q.toLowerCase()) || ch.slug.toString().includes(q)
    );
    if (contentSearchAbort) contentSearchAbort.abort();
    if (contentSearchTimeout) clearTimeout(contentSearchTimeout);
    contentMatches = new Map();
    isSearchingContent = false;

    if (q.length >= 3 && titleSlugMatches.length < 3 && !isTempBook) {
      const timeout = setTimeout(() => {
        contentSearchAbort = new AbortController();
        isSearchingContent = true;
        searchChapterContent(
          q, chapters, titleSlugMatches, bookSlug, navState.selectedTL,
          (matches) => { contentMatches = matches; },
          () => { isSearchingContent = true; },
          () => { isSearchingContent = false; },
          contentSearchAbort.signal,
        );
      }, 500);
      contentSearchTimeout = timeout;
    }
    return () => {
      if (contentSearchAbort) contentSearchAbort.abort();
      if (contentSearchTimeout) clearTimeout(contentSearchTimeout);
    };
  });

  // --- UI Actions ---
  function toggleFullscreen() {
    if (!document.fullscreenElement) {
      // Close all modals before entering fullscreen for a cleaner transition
      modals.chapter?.close();
      modals.settings?.close();
      modals.edit?.close();
      document.documentElement.requestFullscreen().then(() => {
        screen.orientation?.lock?.("portrait").catch(() => {});
      }).catch(console.error);
    } else {
      document.exitFullscreen().then(() => {
        screen.orientation?.unlock?.();
      }).catch(console.error);
    }
  }

  // Note: In Svelte 5, prefer using props/callbacks for external control, 
  // but keeping these as internal functions for internal button triggers.
  const openTOC = () => {
    modals.chapter?.showModal();
    setTimeout(() => {
      modals.chapter
        ?.querySelector(".ch-active")
        ?.scrollIntoView({ block: "center" });
      (modals.chapter?.querySelector("input[type=search]") as HTMLInputElement)?.blur();
    }, 0);
  };
  
  const openSettings = () => modals.settings?.showModal();
  const openEdit = () => modals.edit?.showModal();
</script>

<!-- --- Navbar View --- -->
{#if prefs.config.navbarVisible}
  <nav
    class="w-full bg-base-100/80 backdrop-blur-md border-b border-base-content/5 z-50 relative {prefs.config.navbarSticky ? 'sticky top-0' : ''}"
  >
    <!-- Mobile: 3-column layout -->
    <div class="flex sm:hidden items-center justify-between px-1 h-12 gap-0.5 overflow-x-auto [&::-webkit-scrollbar]:hidden">
      <!-- Left: Navigation -->
      <div class="flex items-center gap-0.5 shrink-0">
        <a
          href="/book/{bookSlug}"
          class="btn btn-ghost btn-sm btn-square rounded-xl"
          aria-label="Home"
        >
          <Icon icon="material-symbols:home-outline-rounded" class="size-5" />
        </a>
        <a
          href={currentIndex > 0 ? `/read/${bookSlug}/${currentTL}/${chaptersForTL[currentIndex - 1].slug}` : `/book/${bookSlug}`}
          class="btn btn-ghost btn-sm btn-square rounded-xl {currentIndex <= 0 ? 'opacity-40' : ''}"
          aria-label={currentIndex > 0 ? "Previous Chapter" : "Home"}
        >
          <Icon icon="mage:previous" class="size-5" />
        </a>
        <button
          onclick={() => {
            if (currentIndex < totalChapters - 1) {
              goto(`/read/${bookSlug}/${currentTL}/${chaptersForTL[currentIndex + 1].slug}`);
            } else {
              nextInfoDialog?.showModal();
            }
          }}
          class="btn btn-ghost btn-sm btn-square rounded-xl"
          aria-label="Next Chapter"
        >
          <Icon icon="mage:next" class="size-5" />
        </button>
      </div>

      <!-- Center: Contents -->
      <button onclick={openTOC} class="btn btn-outline btn-sm rounded-xl gap-1 px-2 shrink-0">
        <Icon icon="lucide:table-of-contents" class="size-4" />
        <span class="text-[11px] font-semibold">Contents</span>
      </button>

      <!-- Right: Actions -->
      <div class="flex items-center gap-0.5 shrink-0">
        <button
          onclick={() => document.getElementById("comments")?.scrollIntoView({ behavior: "smooth" })}
          class="btn btn-ghost btn-sm btn-square rounded-xl"
          aria-label="Comments"
        >
          <Icon icon="iconamoon:comment" class="size-5" />
        </button>
        {#if bookSlug === "gsgw" || bookSlug === "debut"}
          <button onclick={handleCapture} class="btn btn-ghost btn-sm btn-square rounded-xl" aria-label="Capture snippet">
            <Icon icon="mdi:camera-outline" class="size-5" />
          </button>
        {/if}
        <button onclick={openEdit} class="btn btn-ghost btn-sm btn-square rounded-xl" aria-label="Edit">
          <Icon icon="material-symbols:edit-outline-rounded" class="size-5" />
        </button>
        <button onclick={openSettings} class="btn btn-ghost btn-sm btn-square rounded-xl" aria-label="Settings">
          <Icon icon="material-symbols:settings-outline-rounded" class="size-5" />
        </button>
      </div>
    </div>

    <!-- Desktop: centered row with tooltips (original feel) -->
    <div class="hidden sm:flex items-center justify-center gap-2 h-12">
      <div class="tooltip tooltip-bottom" data-tip="Home (H)">
        <a href="/book/{bookSlug}" class="btn btn-ghost btn-sm btn-square rounded-xl" aria-label="Home">
          <Icon icon="material-symbols:home-outline-rounded" class="size-6" />
        </a>
      </div>

      <div class="tooltip tooltip-bottom" data-tip="Previous (P)">
        <a
          href={currentIndex > 0 ? `/read/${bookSlug}/${currentTL}/${chaptersForTL[currentIndex - 1].slug}` : '#'}
          class="btn btn-ghost btn-sm btn-square rounded-xl {!currentIndex ? 'opacity-20 pointer-events-none' : ''}"
          aria-label="Previous Chapter"
        >
          <Icon icon="mage:previous" class="size-5" />
        </a>
      </div>

      <div class="tooltip tooltip-bottom" data-tip="Comments (C)">
        <button
          onclick={() => document.getElementById("comments")?.scrollIntoView({ behavior: "smooth" })}
          class="btn btn-ghost btn-sm btn-square rounded-xl"
          aria-label="Comments"
        >
          <Icon icon="iconamoon:comment" class="size-6" />
        </button>
      </div>

      <div class="tooltip tooltip-bottom" data-tip="Next (N)">
        <button
          onclick={() => {
            if (currentIndex < totalChapters - 1) {
              goto(`/read/${bookSlug}/${currentTL}/${chaptersForTL[currentIndex + 1].slug}`);
            } else {
              nextInfoDialog?.showModal();
            }
          }}
          class="btn btn-ghost btn-sm btn-square rounded-xl"
          aria-label="Next Chapter"
        >
          <Icon icon="mage:next" class="size-5" />
        </button>
      </div>

      <div class="w-px h-4 bg-base-content/10 mx-1"></div>

      <div class="tooltip tooltip-bottom" data-tip="Table of Contents (T)">
      <button onclick={openTOC} class="btn btn-outline btn-sm rounded-xl gap-1.5 px-3">
          <Icon icon="lucide:table-of-contents" class="size-5" />
          <span class="text-xs font-semibold">Contents</span>
        </button>
      </div>

      <div class="w-px h-4 bg-base-content/10 mx-1"></div>

      {#if bookSlug === "gsgw" || bookSlug === "debut"}
        <div class="tooltip tooltip-bottom" data-tip="Capture text snippet">
          <button onclick={handleCapture} class="btn btn-ghost btn-sm btn-square rounded-xl" aria-label="Capture snippet">
            <Icon icon="mdi:camera-outline" class="size-6" />
          </button>
        </div>
      {/if}

      <div class="tooltip tooltip-bottom" data-tip="Edit (E)">
        <button onclick={openEdit} class="btn btn-ghost btn-sm btn-square rounded-xl" aria-label="Edit">
          <Icon icon="material-symbols:edit-outline-rounded" class="size-6" />
        </button>
      </div>

      <div class="tooltip tooltip-bottom" data-tip="Settings (S)">
        <button onclick={openSettings} class="btn btn-ghost btn-sm btn-square rounded-xl" aria-label="Settings">
          <Icon icon="material-symbols:settings-outline-rounded" class="size-6" />
        </button>
      </div>
    </div>
  </nav>
{:else}
  <!-- Mini Fab button when navbar is hidden -->
  <button
    class="fixed top-4 right-4 z-50 btn btn-circle btn-ghost bg-base-100/80 backdrop-blur-md shadow-lg border border-base-content/10"
    onclick={() => (prefs.config.navbarVisible = true)}
  >
    <Icon icon="material-symbols:menu-rounded" class="size-6" />
  </button>
{/if}

<!-- --- World Setting Side Panel (GSGW only) --- -->
<ReferencePanel {currentChapter} />

<!-- --- Modal: Table of Contents --- -->
<dialog bind:this={modals.chapter} class="modal modal-bottom sm:modal-middle">
  <div class="modal-box bg-base-100 p-0 rounded-t-2xl sm:rounded-box max-h-[80vh] flex flex-col shadow-2xl overflow-hidden">
    <div class="relative">
      <div class="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-secondary/5"></div>
      <div class="relative sticky top-0 z-10 bg-base-100/95 backdrop-blur border-b border-base-content/10">
        <div class="flex items-center justify-between px-5 pt-4 pb-3">
          <span class="font-bold text-lg text-primary flex items-center gap-2"><Icon icon="lucide:table-of-contents" class="size-5" /> Contents</span>
          <span class="text-xs font-mono text-base-content/30">
            {#if isSearching}
              {displayList.length} found
            {:else}
              {totalCurrentTL}/{totalAllChapters} chapters
            {/if}
          </span>
        </div>
        <div class="flex gap-2 px-5 pb-4 flex-wrap">
          <input
            type="search"
            bind:value={navState.searchQuery}
            placeholder="Search..."
            class="input input-bordered input-sm shrink rounded-full focus:input-primary min-w-0 flex-[2]"
          />
          <select
            class="select select-bordered select-sm rounded-full focus:select-primary flex-1 min-w-[7rem]"
            bind:value={navState.selectedTL}
          >
            {#each Object.keys(bookData[bookSlug] || {}) as tl}
              <option value={tl}>{tl.toUpperCase()}</option>
            {/each}
          </select>
        </div>
      </div>
    </div>

    <div class="overflow-y-auto overscroll-contain p-2">
      {#if isSearchingContent}
        <div class="flex items-center gap-2 px-3 py-2 text-xs text-base-content/50">
          <span class="loading loading-spinner loading-xs"></span>
          Searching chapter content...
        </div>
      {/if}
      {#each displayList as ch, i}
        {@const isActive = readerState.ch_meta.slug == ch.slug}
        {@const contentMatch = contentMatches.get(ch.slug.toString())}
        <a
          href="/read/{bookSlug}/{navState.selectedTL}/{ch.slug}"
          class="flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-150 {isActive ? 'ch-active bg-primary/10 ring-1 ring-primary/20' : 'hover:bg-base-200/60'}"
          onclick={() => modals.chapter?.close()}
        >
          <span class="shrink-0 w-7 h-7 rounded-lg flex items-center justify-center text-xs font-mono font-bold {isActive ? 'bg-primary text-primary-content' : 'bg-base-200 text-base-content/40'}">
            {ch.slug}
          </span>
          <span class="truncate text-base {isActive ? 'text-primary' : 'text-base-content/70'}">{ch.title}</span>
          {#if isActive}
            <Icon icon="mdi:play-circle" class="size-4 shrink-0 text-primary/50" />
          {/if}
        </a>
        {#if contentMatch}
          <button
            type="button"
            class="ml-10 mr-2 mb-2 mt-0.5 px-3 py-2 rounded-lg bg-base-200/40 border border-base-content/5 block transition-colors text-left cursor-pointer hover:bg-base-200/60"
            onclick={(e) => {
              e.stopPropagation();
              storeSnippetTarget(contentMatch.snippet, navState.searchQuery);
              window.location.href = `/read/${bookSlug}/${navState.selectedTL}/${ch.slug}`;
            }}
          >
            <p class="text-[11px] leading-[1.7] text-base-content/50 whitespace-pre-line [&_strong]:text-base-content/65 [&_strong]:font-semibold [&_em]:italic [&_em]:text-base-content/50 [&_u]:decoration-base-content/25">{@html renderSearchSnippet(contentMatch.snippet, navState.searchQuery)}</p>
          </button>
        {/if}
      {/each}
      {#if displayList.length === 0}
        <div class="py-12 text-center">
          <Icon icon="mdi:magnify-close" class="size-8 mx-auto mb-2 text-base-content/20" />
          <p class="text-sm text-base-content/40">No chapters found</p>
        </div>
      {/if}
    </div>
  </div>
  <form method="dialog" class="modal-backdrop"><button>close</button></form>
</dialog>

<!-- --- Modal: Settings --- -->
<dialog bind:this={modals.settings} class="modal sm:modal-middle modal-bottom">
  <div class="modal-box bg-base-100 p-0 rounded-box shadow-2xl overflow-hidden">
    <div class="relative">
      <div class="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-secondary/5"></div>
      <div class="relative flex justify-between items-center px-6 py-4 border-b border-base-content/10">
        <span class="font-bold text-lg flex items-center gap-2 text-primary">
          <Icon icon="material-symbols:settings-outline-rounded" /> Settings
        </span>
        <div class="flex gap-2">
          <button class="btn btn-sm btn-ghost text-error rounded-full" onclick={() => prefs.reset()}>Reset</button>
          <form method="dialog">
            <button class="btn btn-sm btn-circle btn-ghost" aria-label="Close">
              <Icon icon="mdi:close" class="size-4" />
            </button>
          </form>
        </div>
      </div>
    </div>

    <div class="overflow-y-auto overscroll-contain max-h-[70vh]">
      <div class="p-5 space-y-6">
        <!-- Appearance -->
        <div class="rounded-2xl bg-base-200/40 border border-base-content/5 p-4 space-y-4">
          <div class="flex items-center gap-2">
            <Icon icon="mdi:palette-outline" class="size-4 text-primary/60" />
            <span class="text-xs font-bold uppercase tracking-widest text-base-content/40">Appearance</span>
          </div>

          <div class="form-control gap-1.5">
            <label class="label-text text-xs font-medium">Theme</label>
            <select class="select select-bordered select-sm w-full rounded-xl" bind:value={prefs.config.theme}>
              <optgroup label="Recommended">
                {#each PRIORITY_THEMES as t}
                  <option value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>
                {/each}
              </optgroup>
              <optgroup label="Other">
                {#each MISC_THEMES as t}
                  <option value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>
                {/each}
              </optgroup>
            </select>
          </div>

          <div class="form-control gap-1.5">
            <label class="label-text text-xs font-medium">Font</label>
            <select class="select select-bordered select-sm w-full rounded-xl" bind:value={prefs.config.font}>
              {#each [BOOK_FONTS, SYSTEM_FONTS] as group, i}
                <optgroup label={i === 0 ? "Book Fonts" : "System Fonts"}>
                  {#each group as f}
                    <option value={f} style="font-family: {f}">{f}</option>
                  {/each}
                </optgroup>
              {/each}
            </select>
          </div>

          <label class="flex items-center justify-between cursor-pointer">
            <span class="text-sm">Minimal embeds</span>
            <input type="checkbox" class="toggle toggle-primary toggle-sm" bind:checked={prefs.config.hideTweetMetadata} />
          </label>
        </div>

        <!-- Readability -->
        <div class="rounded-2xl bg-base-200/40 border border-base-content/5 p-4 space-y-4">
          <div class="flex items-center gap-2">
            <Icon icon="mdi:text-box-outline" class="size-4 text-primary/60" />
            <span class="text-xs font-bold uppercase tracking-widest text-base-content/40">Readability</span>
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div class="form-control gap-1.5">
              <label class="label-text text-xs font-medium flex justify-between">
                <span>Size</span>
                <span class="text-base-content/30 font-mono">{prefs.config.fontSize}px</span>
              </label>
              <input type="range" min="12" max="32" class="range range-xs range-primary" bind:value={prefs.config.fontSize} />
            </div>
            <div class="form-control gap-1.5">
              <label class="label-text text-xs font-medium flex justify-between">
                <span>Height</span>
                <span class="text-base-content/30 font-mono">{prefs.config.lineHeight}</span>
              </label>
              <input type="range" min="1.2" max="2.5" step="0.1" class="range range-xs range-secondary" bind:value={prefs.config.lineHeight} />
            </div>
          </div>

          <div class="form-control gap-1.5">
            <label class="label-text text-xs font-medium">Alignment</label>
            <div class="join w-full">
              {#each ["left", "center", "right", "justify"] as align}
                <button
                  class="join-item btn btn-xs grow rounded-xl {prefs.config.textAlign === align ? 'btn-primary' : 'btn-ghost bg-base-200'}"
                  onclick={() => (prefs.config.textAlign = align)}
                >
                  <Icon icon="material-symbols:format-align-{align}" />
                </button>
              {/each}
            </div>
          </div>
        </div>

        <!-- Display -->
        <div class="rounded-2xl bg-base-200/40 border border-base-content/5 p-4 space-y-3">
          <div class="flex items-center gap-2">
            <Icon icon="mdi:fullscreen-outline" class="size-4 text-primary/60" />
            <span class="text-xs font-bold uppercase tracking-widest text-base-content/40">Display</span>
          </div>
          <button class="btn btn-outline btn-primary btn-sm w-full rounded-xl gap-2" onclick={toggleFullscreen}>
            <Icon icon="material-symbols:fullscreen" class="size-4" /> Toggle Fullscreen
          </button>
          <div class="form-control gap-1.5">
            <label class="label-text text-xs font-medium">Scroll Gradient</label>
            <div class="join w-full">
              {#each ["none", "low", "medium", "high"] as level}
                <button
                  class="join-item btn btn-xs grow rounded-xl {prefs.config.scrollGradient === level ? 'btn-primary' : 'btn-ghost bg-base-200'}"
                  onclick={() => (prefs.config.scrollGradient = level)}
                >
                  {level.charAt(0).toUpperCase() + level.slice(1)}
                </button>
              {/each}
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
  <form method="dialog" class="modal-backdrop"><button>close</button></form>
</dialog>

<!-- --- Modal: Contribute --- -->
<dialog bind:this={modals.edit} class="modal modal-bottom sm:modal-middle">
  <div class="modal-box bg-base-100 p-0 rounded-box shadow-2xl overflow-hidden max-w-sm mx-auto">
    <div class="relative">
      <div class="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-secondary/5"></div>
      <div class="relative flex items-center justify-between px-6 py-4 border-b border-base-content/10">
        <span class="font-bold text-lg text-primary flex items-center gap-2">
          <Icon icon="material-symbols:edit-outline-rounded" class="size-5" /> Contribute
        </span>
        <form method="dialog">
          <button class="btn btn-sm btn-circle btn-ghost" aria-label="Close">
            <Icon icon="mdi:close" class="size-4" />
          </button>
        </form>
      </div>
    </div>
    <div class="p-5 space-y-3">
      <a href="https://github.com/EnderOksam/GSGW-Reader/blob/main/contributing.md" target="_blank" class="group flex items-center gap-4 p-4 rounded-2xl border border-base-content/5 bg-base-200/30 hover:bg-base-200/60 transition-colors">
        <div class="shrink-0 w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
          <Icon icon="mdi:book-open-page-variant" class="size-5 text-primary" />
        </div>
        <div class="min-w-0">
          <span class="block text-sm font-semibold">Read the Guide</span>
          <span class="block text-xs text-base-content/40 mt-0.5">Learn how to make edits to chapters</span>
        </div>

      </a>
      <a
        href="https://github.com/EnderOksam/GSGW-Reader/blob/main/chapters/{bookSlug}/{tlDir(bookSlug, navState.selectedTL)}/{(Number(readerState.ch_meta.slug) + (bookSlug === 'debut' ? 0 : 1)).toString().padStart(4, '0')}.md"
        target="_blank"
        class="group flex items-center gap-4 p-4 rounded-2xl border border-base-content/5 bg-base-200/30 hover:bg-base-200/60 transition-colors"
      >
        <div class="shrink-0 w-10 h-10 rounded-xl bg-secondary/10 flex items-center justify-center">
          <Icon icon="mdi:github" class="size-5 text-secondary" />
        </div>
        <div class="min-w-0">
          <span class="block text-sm font-semibold">Edit on GitHub</span>
          <span class="block text-xs text-base-content/40 mt-0.5">Make changes to this chapter</span>
        </div>

      </a>
    </div>
  </div>
  <form method="dialog" class="modal-backdrop"><button>close</button></form>
</dialog>

<!-- Hidden renderer (off-screen, used by html-to-image). Kept OUTSIDE the <dialog> so the modal-box scale/transform and 512px max-width don't shrink the card. -->
<div class="fixed left-[-9999px] top-0 pointer-events-none">
  <!-- Outer wrapper: controls padding + rounding of the final image -->
  <div
    bind:this={snippetOuterEl}
    style="padding: 20px; border-radius: 16px; width: 640px; position: relative;"
  >
    {#if snippetShowShadow}
      <!-- Gradient shadow layers (html-to-image drops box-shadow when rasterizing on iOS, gradients render) -->
      <div style="position: absolute; inset: 0; pointer-events: none;">
        <div style="position: absolute; left: 0; right: 0; bottom: 0; height: 20px; border-radius: 0 0 16px 16px; background: linear-gradient(to top, rgba(0,0,0,0.20), rgba(0,0,0,0.08) 55%, transparent);"></div>
        <div style="position: absolute; left: 0; right: 0; top: 0; height: 20px; border-radius: 16px 16px 0 0; background: linear-gradient(to bottom, rgba(0,0,0,0.10), transparent);"></div>
        <div style="position: absolute; top: 0; bottom: 0; right: 0; width: 20px; border-radius: 0 16px 16px 0; background: linear-gradient(to left, rgba(0,0,0,0.10), transparent);"></div>
        <div style="position: absolute; top: 0; bottom: 0; left: 0; width: 20px; border-radius: 16px 0 0 16px; background: linear-gradient(to right, rgba(0,0,0,0.10), transparent);"></div>
      </div>
    {/if}
    <!-- Inner card: the actual content card with shadow -->
    <div
      bind:this={snippetPreviewEl}
      class="reader-container snippet-preview"
      style="position: relative; z-index: 1; width: 600px; padding: 1.25em 2.25em 1.25em; border-radius: 12px; border: 1px solid color-mix(in oklch, currentColor 14%, transparent); --chapter-font: 'Alegreya', serif; --chapter-size: 18px; --chapter-weight: 450; --chapter-lh: 1.8; font-family: var(--chapter-font); font-size: var(--chapter-size); font-weight: var(--chapter-weight); line-height: var(--chapter-lh);"
    >
      {@html capturedHtml}

      {#if snippetShowDomain || snippetShowChapter}
        <div style="display: flex; justify-content: space-between; align-items: baseline; margin-top: 1.25em; padding-top: 0.75em; border-top: 1px solid currentColor; font-family: 'Inter', ui-sans-serif, system-ui, sans-serif; font-size: 11px; letter-spacing: 0.01em; line-height: 1.3;">
          {#if snippetShowDomain}
            <span style="text-decoration: underline; text-underline-offset: 2px; color: {snippetPrimaryColor}; font-weight: 700;">ireum.pages.dev</span>
          {:else}
            <span></span>
          {/if}
          {#if snippetShowChapter}
            <span style="text-align: right; font-weight: 700;">
              {#if snippetShowDomain}
                <span style="margin: 0 0.4em; opacity: 0.4;">/</span>
              {/if}
              {snippetBookName} &middot; {snippetChapterTitle}
            </span>
          {/if}
        </div>
      {/if}
    </div>
  </div>
</div>

<!-- --- Modal: Captured Snippet --- -->
<dialog bind:this={modals.snippet} class="modal modal-bottom sm:modal-middle">
  <div class="modal-box bg-base-100 rounded-box p-0 overflow-hidden shadow-2xl max-w-lg">

    <!-- Header -->
    <div class="relative overflow-hidden">
      <div class="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-secondary/5"></div>
      <div class="relative flex items-center justify-between px-6 py-4">
        <div>
          <span class="text-primary font-semibold" style="font-size: 1.15rem;">Snippet</span>
          {#if snippetChapterTitle}
            <p class="text-xs text-base-content/40 mt-0.5 max-w-[260px] truncate">{snippetChapterTitle}</p>
          {/if}
        </div>
        <form method="dialog">
          <button class="btn btn-sm btn-circle btn-ghost" aria-label="Close">
            <Icon icon="mdi:close" class="size-4" />
          </button>
        </form>
      </div>
    </div>

    <!-- Preview area -->
    <div class="px-5 pb-2 max-h-[55vh] overflow-y-auto overscroll-contain rounded-xl">
      {#if snippetLoading}
        <div class="flex flex-col items-center justify-center py-14 gap-3">
          <div class="relative">
            <Icon icon="mdi:loading" class="size-6 animate-spin text-primary/60" />
            <div class="absolute inset-0 size-6 animate-ping text-primary/20">
              <Icon icon="mdi:loading" class="size-6" />
            </div>
          </div>
          <span class="text-xs text-base-content/40 font-medium">Rendering preview...</span>
        </div>
      {:else if snippetImageUrl}
        <img src={snippetImageUrl} alt="Captured snippet" class="w-full rounded-xl" />
      {/if}
    </div>

    <!-- Toggle bar -->
    <!-- Toggle + action bar -->
    <div class="px-5 pt-3 pb-3 mt-1">
      <div class="flex flex-wrap items-center gap-2">
        <button
          onclick={() => { snippetShowDomain = !snippetShowDomain; onSnippetToggle(); }}
          class="btn btn-xs rounded-full gap-1.5 {snippetShowDomain ? 'btn-primary' : 'btn-ghost bg-base-200/80 text-base-content/60'}"
        >
          <Icon icon="mdi:web" class="size-3.5" />
          Domain
        </button>
        <button
          onclick={() => { snippetShowChapter = !snippetShowChapter; onSnippetToggle(); }}
          class="btn btn-xs rounded-full gap-1.5 {snippetShowChapter ? 'btn-primary' : 'btn-ghost bg-base-200/80 text-base-content/60'}"
        >
          <Icon icon="mdi:book-open-page-variant" class="size-3.5" />
          Chapter
        </button>
        <button
          onclick={() => { snippetShowShadow = !snippetShowShadow; onSnippetToggle(); }}
          class="btn btn-xs rounded-full gap-1.5 {snippetShowShadow ? 'btn-primary' : 'btn-ghost bg-base-200/80 text-base-content/60'}"
        >
          <Icon icon="material-symbols:shadow" class="size-3.5" />
          Shadow
        </button>
        <div class="flex-1"></div>
        <div class="flex items-center gap-2">
          <button
            onclick={copySnippet}
            class="btn btn-xs rounded-full gap-1.5 btn-ghost bg-base-200/80 text-base-content/60"
            disabled={!snippetImageUrl || snippetLoading}
          >
            <Icon icon={snippetCopied ? "mdi:check" : "mdi:content-copy"} class="size-3.5 {snippetCopied ? 'text-success' : ''}" />
            {snippetCopied ? "Copied" : "Copy"}
          </button>
          <button
            onclick={downloadSnippet}
            class="btn btn-xs rounded-full gap-1.5 btn-ghost bg-base-200/80 text-base-content/60"
            disabled={!snippetImageUrl || snippetLoading}
          >
            <Icon icon="mdi:download" class="size-3.5" />
            Save
          </button>
        </div>
      </div>
    </div>
  </div>
  <form method="dialog" class="modal-backdrop"><button>close</button></form>
</dialog>
{#if snippetToast}
  <div transition:fade={{ duration: 300 }} class="fixed top-14 left-1/2 -translate-x-1/2 z-50 flex items-center gap-3 bg-base-200/90 backdrop-blur-md border border-red-500/40 text-base-content/80 text-xs font-medium px-5 py-3 rounded-2xl shadow-xl shadow-red-500/10">
    <Icon icon="mdi:alert-circle-outline" class="size-4 text-red-400 shrink-0" />
    <span>Highlight text to take a snippet</span>
    <button onclick={() => { snippetToast = false; if (snippetTimer) clearTimeout(snippetTimer); }} class="btn btn-ghost btn-xs btn-square rounded-btn text-base-content/40 hover:text-base-content hover:bg-base-content/5 -mr-1">
      <Icon icon="mdi:close" class="size-3.5" />
    </button>
  </div>
{/if}
