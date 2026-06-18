<script lang="ts">
  import "../../app.css";
  import { onMount, onDestroy } from "svelte";
  import { browser } from "$app/environment";
  import { page } from "$app/state";
  import { goto, afterNavigate } from "$app/navigation";
  import Icon from "@iconify/svelte";
  import Giscus from "@giscus/svelte";


  // Components
  import Navbar from "$lib/reader/Navbar.svelte";

  // Data
  import { readerState } from "$lib/reader.svelte";
  import bookData from "$lib/meta.json";

  let { children } = $props();

  // --- Logic: User Preferences ---
  class UserPreferences {
    config = $state({
      theme: "sunset",
      font: "Alegreya",
      fontSize: 25,
      fontWeight: 450,
      lineHeight: 1.8,
          textAlign: "left",
      hyphens: false,
      indent: false,
      navbarVisible: true,
      navbarSticky: true,
      solidBackground: true,
      hideTweetMetadata: false,
    });

    constructor() {
      if (browser) {
        this.load();
        $effect(() => {
          localStorage.setItem("readerSettings", JSON.stringify(this.config));
          document.documentElement.setAttribute(
            "data-theme",
            this.config.theme,
          );
        });
      }
    }

    load() {
      const saved = localStorage.getItem("readerSettings");
      if (saved) this.config = { ...this.config, ...JSON.parse(saved) };
      document.documentElement.setAttribute("data-theme", this.config.theme);
    }

    reset() {
      if (confirm("Reset settings?")) {
        this.config = {
          theme: "sunset",
          font: "Alegreya",
          fontSize: 25,
          fontWeight: 450,
          lineHeight: 1.8,
      textAlign: "left",
          hyphens: false,
          indent: false,
          navbarVisible: true,
      navbarSticky: true,
      solidBackground: true,
      hideTweetMetadata: false,
        };
      }
    }
  }



  // --- State ---
  const prefs = new UserPreferences();
  let mainContainer: HTMLDivElement;
  let navbarRef: any;

  // 1. Parse URL manually (since page.params is empty)
  // Split path, filter out empty strings to handle trailing slashes
  // URL: /read/coi/webnovel/1 -> ["read", "coi", "webnovel", "1"]
  const pathSegments = $derived(page.url.pathname.split("/").filter(Boolean));

  // 2. Derive values from URL position
  const bookSlug = $derived(pathSegments[1] ?? "lotm");
  const currentTL = $derived(pathSegments[2] ?? "webnovel");
  const currentChapter = $derived(
    pathSegments[3] !== undefined ? Number(pathSegments[3]) : 1
  );


  // 3. Get chapters list and current index for the current TL
  const chaptersForTL = $derived(
    (bookData as any)[bookSlug]?.[currentTL] || []
  );
  const currentIndex = $derived(
    chaptersForTL.findIndex((ch: any) => Number(ch.slug) === currentChapter)
  );
  const totalChapters = $derived(chaptersForTL.length);


  let navState = $state({ searchQuery: "", selectedTL: "webnovel" });

  // 4. Sync internal state with URL
  $effect(() => {
    navState.selectedTL = currentTL;
  });

  // --- Handlers ---

  afterNavigate(async () => {
    const { littlefoot } = await import("littlefoot");
    littlefoot({
      activateOnHover: true,
      hoverDelay: 50,
      dismissOnUnhover: true,
      buttonTemplate: `<button aria-label="Footnote <% number %>" class="relative btn btn-xs btn-info px-3 py-2 h-3 text-sm mx-1 font-mono"><% number %></button>`,
    });
  });
  onMount(async () => {
    if (browser) {
      const lastRead = JSON.parse(localStorage.getItem("lastRead") || "{} ");
      // Check if saved position matches current URL
      if (lastRead.slug == currentChapter && lastRead.book === bookSlug) {
        window.scrollTo({ top: lastRead.scroll, behavior: "instant" });
      }
      window.addEventListener("scroll", handleScroll);
    }
  });

  onDestroy(() => {
    if (browser) window.removeEventListener("scroll", handleScroll);
  });

  function handleScroll() {
    localStorage.setItem(
      "lastRead",
      JSON.stringify({
        book: bookSlug,
        tl: currentTL,
        slug: currentChapter,
        scroll: window.scrollY,
        timestamp: Date.now(),
      }),
    );
  }

  function toggleFullscreen() {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().catch(console.error);
    } else {
      document.exitFullscreen();
    }
  }

  function handleKeydown(event: KeyboardEvent) {
    if (["INPUT", "TEXTAREA"].includes((event.target as HTMLElement).tagName))
      return;

    const key = event.key.toLowerCase();

    switch (key) {
      case "h":
        goto(`/book/${bookSlug}`);
        break;
      case "e":
        navbarRef?.openEdit();
        break;
      case "t":
        navbarRef?.openTOC();
        break;
      case "s":
        navbarRef?.openSettings();
        break;
      case "c":
        document
          .getElementById("comments")
          ?.scrollIntoView({ behavior: "smooth" });
        break;
      case "f":
        toggleFullscreen();
        break;
       case "n":
       case "arrowright":
           // Check if it's the last chapter before navigating
           if (currentIndex < totalChapters - 1) {
              goto(`/read/${bookSlug}/${currentTL}/${chaptersForTL[currentIndex + 1].slug}`);
           }
          break;
       case "p":
       case "arrowleft":
          if (currentIndex > 0) {
              goto(`/read/${bookSlug}/${currentTL}/${chaptersForTL[currentIndex - 1].slug}`);
          }
         break;
    }
  }
</script>

<svelte:head>
  <title>{bookSlug.toUpperCase()} {readerState.ch_meta.slug} — {readerState.ch_meta.title}</title>
  <meta property="og:type" content="article" />
  <meta property="og:title" content="{bookSlug.toUpperCase()} {readerState.ch_meta.slug} — {readerState.ch_meta.title}" />
  <meta name="twitter:title" content="{bookSlug.toUpperCase()} {readerState.ch_meta.slug} — {readerState.ch_meta.title}" />
</svelte:head>

<svelte:window onkeydown={handleKeydown} />

<div
  bind:this={mainContainer}
  data-hide-tweet-meta={prefs.config.hideTweetMetadata}
  class="min-h-screen w-full bg-base-100 text-base-content relative transition-colors duration-200"
  style="
    --chapter-font: {prefs.config.font}, serif; 
    --chapter-size: {prefs.config.fontSize}px; 
    --chapter-weight: {prefs.config.fontWeight};
    --chapter-lh: {prefs.config.lineHeight};
    --chapter-indent: {prefs.config.indent ? '1.5em' : '0'};
    --chapter-align: {prefs.config.textAlign};
    --chapter-hyphens: {prefs.config.hyphens ? 'auto' : 'none'};
    --card-bg-opacity: {prefs.config.solidBackground ? 1 : 0};
  "
>
  <Navbar bind:this={navbarRef} {prefs} {bookSlug} {bookData} bind:navState {currentChapter} {chaptersForTL} {currentIndex} />

  <main class="mx-auto my-3 max-w-4xl w-full px-4 py-8 sm:px-6 md:px-12 sm:py-12 z-0 relative transition-transform duration-300 ease-out ref-shift" style="transform: translateX({readerState.refPanelOpen ? '-72px' : '0px'})">
    <div
      class="absolute inset-0 bg-base-200 -z-10 rounded-box transition-opacity duration-300"
      style="opacity: var(--card-bg-opacity);"
    ></div>

    <article
      class="chapter-content prose prose-lg md:prose-xl max-w-none wrap-break-word"
    >
      {@render children()}
    </article>

    <div class="mt-16 flex items-center justify-between border-t border-base-content/10 pt-8">
      <a
        href={currentIndex <= 0 
            ? `/book/${bookSlug}` 
            : `/read/${bookSlug}/${navState.selectedTL}/${chaptersForTL[currentIndex - 1].slug}`}
        class="btn btn-soft btn-sm gap-2"
        aria-label={currentIndex <= 0 ? "Go Home" : "Previous Chapter"}

      >
        <Icon icon={currentIndex <= 0 ? "iconamoon:home-light" : "mage:previous"} class="size-5" />
        <span class="hidden sm:inline">{currentIndex <= 0 ? "Home" : "Prev"}</span>
      </a>

      <span class="text-xs font-mono font-bold opacity-50 tracking-wider">
        CH. {readerState.ch_meta.slug}
      </span>

      <a
        href={currentIndex >= totalChapters - 1
            ? `/book/${bookSlug}`
            : `/read/${bookSlug}/${navState.selectedTL}/${chaptersForTL[currentIndex + 1].slug}`}
        class="btn btn-soft btn-sm gap-2"
        aria-label={currentIndex >= totalChapters - 1 ? "Go Home" : "Next Chapter"}
        data-sveltekit-preload-data="viewport"
      >
        <span class="hidden sm:inline">{currentIndex >= totalChapters - 1 ? "Home" : "Next"}</span>
        <Icon icon={currentIndex >= totalChapters - 1 ? "iconamoon:home-light" : "mage:next"} class="size-5" />
      </a>
    </div>
  </main>

  {#if bookSlug === "gsgw"}
    <button
      onclick={() => readerState.refPanelOpen = !readerState.refPanelOpen}
      class="fixed right-0 top-1/2 -translate-y-1/2 z-40 btn btn-ghost btn-square btn-sm rounded-l-full bg-base-100/80 shadow-md hover:bg-base-100 border border-base-content/20 border-r-0"
      aria-label="Toggle Reference Panel"
    >
      <Icon icon={readerState.refPanelOpen ? "material-symbols:chevron-right-rounded" : "material-symbols:chevron-left-rounded"} class="size-5" />
    </button>
  {/if}

  <div id="comments" class="mx-auto max-w-4xl px-4 pb-16 transition-transform duration-300 ease-out ref-shift" style="transform: translateX({readerState.refPanelOpen ? '-72px' : '0px'})">
    {#key page.url.pathname}
      <Giscus
        repo="EnderOksam/GSGW-Reader"
        repoId="R_kgDOSUYftA"
        category="General"
        categoryId="DIC_kwDOSUYftM4C9WvT"
        mapping="pathname"
        strict="0"
        reactionsEnabled="1"
        emitMetadata="0"
        inputPosition="top"
        theme="preferred_color_scheme"
        lang="en"
        loading="eager"
      />
    {/key}
  </div>

</div>

<style>
  @media (max-width: 639px) {
    .ref-shift {
      transform: none !important;
    }
  }
  .chapter-content {
    font-family: var(--chapter-font);
    font-size: var(--chapter-size);
    line-height: var(--chapter-lh);
    text-align: var(--chapter-align);
    hyphens: var(--chapter-hyphens);
    font-weight: var(--chapter-weight, 400);
    overflow-wrap: break-word;
    word-break: break-word;
  }

  .chapter-content :global(p) {
    text-indent: var(--chapter-indent);
  }

  :global(:fullscreen) {
    width: 100vw;
    height: 100vh;
    overflow-y: auto;
    overflow-x: hidden;
    background-color: var(--fallback-b1, oklch(var(--b1) / 1));
  }
</style>