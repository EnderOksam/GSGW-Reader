<script lang="ts">
  import Icon from "@iconify/svelte";
  import { fade } from "svelte/transition";
  import { tick } from "svelte";
  import { toPng } from "html-to-image";
  import { readerState } from "$lib/reader.svelte";
  import ReferencePanel from "./ReferencePanel.svelte";
  import readerCss from "../../routes/(reader)/reader.css?inline";
  import readerWindowsCss from "./reader-windows.css?inline";

  // --- Types ---
  interface Chapter {
    title: string;
    slug: string | number;
  }

  // --- Props ---
  // Using Svelte 5 $props for reactive input
  let { prefs, bookSlug, bookData, navState = $bindable(), currentChapter = 0, chaptersForTL = [], currentIndex = 0, currentTL = "" } = $props();
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
  let snippetShowDomain = $state(true);
  let snippetShowChapter = $state(true);
  let snippetCopied = $state(false);
  let snippetPrimaryColor = $state("oklch(var(--p))");

  // --- Selection cache (iOS coyote time) ---
  let cachedSelectionHtml = $state("");
  let selectionCacheExpiry: ReturnType<typeof setTimeout> | null = null;

  $effect(() => {
    function onSelectionChange() {
      const selection = window.getSelection();
      if (!selection || selection.isCollapsed || !selection.rangeCount) return;

      const range = selection.getRangeAt(0);
      const container = range.commonAncestorContainer;
      const el = container.nodeType === 1 ? container as HTMLElement : container.parentElement;
      if (!el?.closest("article")) return;

      const cloned = range.cloneContents();
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
    snippetShowDomain = true;
    snippetShowChapter = true;
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
    const readerArticle = document.querySelector("article.chapter-content");
    if (readerArticle) {
      const cs = getComputedStyle(readerArticle);
      snippetPreviewEl.style.fontFamily = cs.fontFamily;
      snippetPreviewEl.style.fontSize = cs.fontSize;
      snippetPreviewEl.style.fontWeight = cs.fontWeight;
      snippetPreviewEl.style.color = cs.color;
    }

    const primaryEl = document.querySelector<HTMLElement>(".text-primary");
    if (primaryEl) {
      snippetPrimaryColor = getComputedStyle(primaryEl).color;
    }

    let styleEl = snippetPreviewEl.querySelector("style#snippet-injected-css");
    if (!styleEl) {
      styleEl = document.createElement("style");
      styleEl.id = "snippet-injected-css";
      styleEl.textContent = readerCss + "\n" + readerWindowsCss;
      snippetPreviewEl.prepend(styleEl);
    }
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
        skipAutoScale: true,
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

  // --- UI Actions ---
  function toggleFullscreen() {
    if (!document.fullscreenElement) {
      // Close all modals before entering fullscreen for a cleaner transition
      modals.chapter?.close();
      modals.settings?.close();
      modals.edit?.close();
      document.documentElement.requestFullscreen().catch(console.error);
    } else {
      document.exitFullscreen();
    }
  }

  // Note: In Svelte 5, prefer using props/callbacks for external control, 
  // but keeping these as internal functions for internal button triggers.
  const openTOC = () => {
    modals.chapter?.showModal();
    // Scroll the currently active chapter into view within the modal
    setTimeout(() => {
      modals.chapter
        ?.querySelector(".btn-primary")
        ?.scrollIntoView({ block: "center" });
    }, 0);
  };
  
  const openSettings = () => modals.settings?.showModal();
  const openEdit = () => modals.edit?.showModal();
</script>

<!-- --- Navbar View --- -->
{#if prefs.config.navbarVisible}
  <nav
    class="flex w-full items-center justify-center gap-2 sm:gap-5 bg-base-100 border-b border-base-content/10 p-3 z-50 relative {prefs.config.navbarSticky ? 'sticky top-0' : ''}"
  >
    <div class="flex items-center justify-center gap-2 sm:gap-5">
      <!-- Home Link -->
      <div class="tooltip tooltip-bottom" data-tip="Home (H)">
        <a href="/book/{bookSlug}" class="btn btn-ghost btn-sm btn-square rounded-btn" aria-label="Home">
          <Icon icon="material-symbols:home-outline-rounded" class="size-6" />
        </a>
      </div>

      <!-- Previous Chapter -->
      <div class="tooltip tooltip-bottom" data-tip="Previous (P)">
        {#if currentIndex > 0}
          <a
            href="/read/{bookSlug}/{currentTL}/{chaptersForTL[currentIndex - 1].slug}"
            class="btn btn-ghost btn-sm btn-square rounded-btn"
            aria-label="Previous Chapter"
          >
            <Icon icon="mage:previous" class="size-5" />
          </a>
        {:else}
          <button class="btn btn-ghost btn-sm btn-square rounded-btn opacity-30" disabled aria-label="No previous chapter">
            <Icon icon="mage:previous" class="size-5" />
          </button>
        {/if}
      </div>

      <!-- Scroll to Comments -->
      <div class="tooltip tooltip-bottom" data-tip="Comments (C)">
        <button
          onclick={() => document.getElementById("comments")?.scrollIntoView({ behavior: "smooth" })}
          class="btn btn-ghost btn-sm btn-square rounded-btn"
          aria-label="Comments"
        >
          <Icon icon="iconamoon:comment" class="size-6" />
        </button>
      </div>

      <!-- Next Chapter -->
      <div class="tooltip tooltip-bottom" data-tip="Next (N)">
        {#if currentIndex < totalChapters - 1}
          <a
            href="/read/{bookSlug}/{currentTL}/{chaptersForTL[currentIndex + 1].slug}"
            class="btn btn-ghost btn-sm btn-square rounded-btn"
            aria-label="Next Chapter"
            data-sveltekit-preload-data="viewport"
          >
            <Icon icon="mage:next" class="size-5" />
          </a>
        {:else}
          <button class="btn btn-ghost btn-sm btn-square rounded-btn opacity-30" disabled aria-label="No next chapter">
            <Icon icon="mage:next" class="size-5" />
          </button>
        {/if}
      </div>

      <!-- Table of Contents Toggle -->
      <div class="tooltip tooltip-bottom" data-tip="Table of Contents (T)">
        <button onclick={openTOC} class="btn btn-outline btn-sm rounded-btn">
          <Icon icon="lucide:table-of-contents" class="size-5" />
          <span class="hidden sm:inline">Contents</span>
        </button>
      </div>

      {#if bookSlug === "gsgw" || bookSlug === "debut"}
        <!-- Camera -->
        <div class="tooltip tooltip-bottom" data-tip="Capture text snippet">
          <button onclick={handleCapture} class="btn btn-ghost btn-sm btn-square rounded-btn" aria-label="Camera">
            <Icon icon="mdi:camera-outline" class="size-6" />
          </button>
        </div>
      {/if}

      <!-- Edit/Contribute Toggle -->
      <div class="tooltip tooltip-bottom" data-tip="Edit (E)">
        <button onclick={openEdit} class="btn btn-ghost btn-sm btn-square rounded-btn" aria-label="Edit">
          <Icon icon="material-symbols:edit-outline-rounded" class="size-6" />
        </button>
      </div>

      <!-- Settings Toggle -->
      <div class="tooltip tooltip-bottom" data-tip="Settings (S)">
        <button onclick={openSettings} class="btn btn-ghost btn-sm btn-square rounded-btn" aria-label="Settings">
          <Icon icon="material-symbols:settings-outline-rounded" class="size-6" />
        </button>
      </div>
    </div>

  </nav>
{:else}
  <!-- Mini Fab button when navbar is hidden -->
  <button
    class="fixed top-4 right-4 z-50 btn btn-circle btn-ghost bg-base-100 shadow-md"
    onclick={() => (prefs.config.navbarVisible = true)}
  >
    <Icon icon="material-symbols:menu-rounded" class="size-6" />
  </button>
{/if}

<!-- --- World Setting Side Panel (GSGW only) --- -->
<ReferencePanel {currentChapter} />

<!-- --- Modal: Table of Contents --- -->
<dialog bind:this={modals.chapter} class="modal modal-bottom sm:modal-middle">
  <div class="modal-box bg-base-100 p-0 rounded-t-2xl sm:rounded-box max-h-[80vh] flex flex-col">
    <div class="sticky top-0 z-10 bg-base-100/95 backdrop-blur border-b border-base-content/10 p-4 space-y-3">
      <div class="flex justify-between items-center">
        <h3 class="font-bold text-lg text-primary">Contents</h3>
        <form method="dialog">
          <button class="btn btn-sm btn-circle btn-ghost">✕</button>
        </form>
      </div>
      <div class="flex gap-2">
        <input
          type="search"
          bind:value={navState.searchQuery}
          placeholder="Search chapters..."
          class="input input-bordered input-sm grow rounded-btn focus:input-primary"
        />
        <select
          class="select select-bordered select-sm rounded-btn focus:select-primary"
          bind:value={navState.selectedTL}
        >
          {#each Object.keys(bookData[bookSlug] || {}) as tl}
            <option value={tl}>{tl.toUpperCase()}</option>
          {/each}
        </select>
      </div>
    </div>

    <div class="overflow-y-auto p-2">
      {#each chapterList as ch}
        <a
          href="/read/{bookSlug}/{navState.selectedTL}/{ch.slug}"
          class="btn btn-sm justify-start w-full font-normal border-none mb-1 rounded-btn {readerState.ch_meta.slug == ch.slug ? 'btn-primary btn-soft' : 'btn-ghost'}"
          onclick={() => modals.chapter?.close()}
        >
          <span class="w-10 font-mono text-xs opacity-50">#{ch.slug}</span>
          <span class="truncate">{ch.title}</span>
        </a>
      {/each}
    </div>
  </div>
  <form method="dialog" class="modal-backdrop"><button>close</button></form>
</dialog>

<!-- --- Modal: Settings --- -->
<dialog bind:this={modals.settings} class="modal sm:modal-middle modal-bottom">
  <div class="modal-box bg-base-100 rounded-box">
    <div class="flex justify-between items-center mb-6 border-b border-base-content/10 pb-4">
      <h3 class="font-bold text-lg flex items-center gap-2 text-primary pt-0.5">
        <Icon icon="material-symbols:settings-outline-rounded" /> Settings
      </h3>
      <div class="flex gap-2">
        <button class="btn btn-sm btn-ghost text-error rounded-btn" onclick={() => prefs.reset()}>Reset</button>
        <form method="dialog">
          <button class="btn btn-sm btn-circle btn-ghost">✕</button>
        </form>
      </div>
    </div>

    <div class="grid md:grid-cols-2 gap-8">
      <!-- Left Column: Visuals -->
      <div class="space-y-4">
        <h4 class="text-xs font-bold opacity-50 uppercase tracking-widest">Appearance</h4>
        <div class="form-control">
          <label class="label"><span class="label-text">Theme</span></label>
          <select class="select select-bordered select-sm w-full rounded-btn focus:select-primary" bind:value={prefs.config.theme}>
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

        <div class="form-control">
          <label class="label"><span class="label-text">Font</span></label>
          <select class="select select-bordered select-sm w-full rounded-btn focus:select-primary" bind:value={prefs.config.font}>
            {#each [BOOK_FONTS, SYSTEM_FONTS] as group, i}
              <optgroup label={i === 0 ? "Book Fonts" : "System Fonts"}>
                {#each group as f}
                  <option value={f} style="font-family: {f}">{f}</option>
                {/each}
              </optgroup>
            {/each}
          </select>
        </div>
        <div class="form-control">
          <label class="label cursor-pointer gap-3">
            <span class="label-text text-xs">Minimal embeds</span>
            <input type="checkbox" class="toggle toggle-primary toggle-xs" bind:checked={prefs.config.hideTweetMetadata} />
          </label>
        </div>
      </div>

      <!-- Right Column: Text Formatting -->
      <div class="space-y-4">
        <h4 class="text-xs font-bold opacity-50 uppercase tracking-widest">Readability</h4>
        <div class="grid grid-cols-2 gap-4">
          <div class="form-control">
            <label class="label text-xs">Size ({prefs.config.fontSize}px)</label>
            <input type="range" min="12" max="32" class="range range-xs range-primary" bind:value={prefs.config.fontSize} />
          </div>
          <div class="form-control">
            <label class="label text-xs">Height ({prefs.config.lineHeight})</label>
            <input type="range" min="1.2" max="2.5" step="0.1" class="range range-xs range-secondary" bind:value={prefs.config.lineHeight} />
          </div>
        </div>
        
        <div class="join w-full">
          {#each ["left", "center", "right", "justify"] as align}
            <button
              class="join-item btn btn-xs grow {prefs.config.textAlign === align ? 'btn-primary' : 'btn-ghost bg-base-200'}"
              onclick={() => (prefs.config.textAlign = align)}
            >
              <Icon icon="material-symbols:format-align-{align}" />
            </button>
          {/each}
        </div>

        <div class="divider my-2"></div>
        <button class="btn btn-outline btn-primary btn-sm w-full rounded-btn" onclick={toggleFullscreen}>
          <Icon icon="material-symbols:fullscreen" class="size-5" /> Fullscreen
        </button>
      </div>
    </div>
  </div>
  <form method="dialog" class="modal-backdrop"><button>close</button></form>
</dialog>

<!-- --- Modal: Contribute --- -->
<dialog bind:this={modals.edit} class="modal modal-bottom sm:modal-middle">
  <div class="modal-box bg-base-100 rounded-box">
    <form method="dialog">
      <button class="btn btn-sm btn-circle btn-ghost absolute right-2 top-2">✕</button>
    </form>
    <h3 class="font-bold text-lg mb-4 text-primary">Contribute</h3>
    <div class="flex flex-col gap-3">
      <a href="https://github.com/EnderOksam/GSGW-Reader/blob/main/contributing.md" target="_blank" class="btn btn-outline btn-primary w-full rounded-btn">
        <Icon icon="mdi:book-open-page-variant" class="size-5 mr-2" /> Read Guide
      </a>
      <a
        href="https://github.com/EnderOksam/GSGW-Reader/blob/main/chapters/{bookSlug}/{tlDir(bookSlug, navState.selectedTL)}/{(Number(readerState.ch_meta.slug) + 1).toString().padStart(4, '0')}.md"
        target="_blank"
        class="btn btn-secondary w-full rounded-btn"
      >
        <Icon icon="mdi:github" class="size-5 mr-2" /> Edit on GitHub
      </a>
    </div>
  </div>
  <form method="dialog" class="modal-backdrop"><button>close</button></form>
</dialog>

<!-- --- Modal: Captured Snippet --- -->
<dialog bind:this={modals.snippet} class="modal modal-bottom sm:modal-middle">
  <div class="modal-box bg-base-100 rounded-box p-0 overflow-hidden shadow-2xl max-w-lg snippet-reset">

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

    <!-- Hidden renderer (off-screen, used by html-to-image) -->
    <div class="fixed left-[-9999px] top-0 pointer-events-none">
      <!-- Outer wrapper: controls padding + rounding of the final image -->
      <div
        bind:this={snippetOuterEl}
        style="padding: 20px; border-radius: 16px; width: 640px;"
      >
        <!-- Inner card: the actual content card with shadow -->
        <div
          bind:this={snippetPreviewEl}
          class="reader-container"
          style="width: 600px; padding: 2em 2.25em 1.25em; border-radius: 12px; box-shadow: 0 8px 32px rgba(0,0,0,0.35), 0 2px 8px rgba(0,0,0,0.2); --chapter-font: 'Alegreya', serif; --chapter-size: 18px; --chapter-weight: 450; --chapter-lh: 2.2; font-family: var(--chapter-font); font-size: var(--chapter-size); font-weight: var(--chapter-weight); line-height: var(--chapter-lh);"
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
      <div class="flex items-center gap-2">
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
        <div class="flex-1"></div>
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

<style>
  :global(dialog.snippet-reset) h1,
  :global(dialog.snippet-reset) h2,
  :global(dialog.snippet-reset) h3 {
    text-align: left;
    position: static;
    padding-bottom: 0;
    margin-bottom: 0;
    font-variant: normal;
  }
  :global(dialog.snippet-reset) h1::after,
  :global(dialog.snippet-reset) h2::after,
  :global(dialog.snippet-reset) h3::after {
    display: none;
  }
</style>