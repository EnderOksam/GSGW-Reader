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
      scrollGradient: "low",
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
      scrollGradient: "low",
        };
      }
    }
  }



  // --- State ---
  const prefs = new UserPreferences();
  let mainContainer: HTMLDivElement;
  let navbarRef: any;
  let readProgress = $state(0);
  let mainEl: HTMLElement | undefined = $state();

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
  const currentChMeta = $derived(
    chaptersForTL.find((ch: any) => Number(ch.slug) === currentChapter) ??
    { section: "", title: "", slug: 0 }
  );



  let navState = $state({ searchQuery: "", selectedTL: "webnovel" });
  let nextInfoDialog: HTMLDialogElement | undefined = $state();

  const TL_INFO = [
    { name: "FanTL", desc: "This translation is the recommended one, has all the features made specifically for the site.", icon: "mdi:star-outline", color: "text-yellow-500" },
    { name: "UnfinishedTL", desc: "The base story with no special features — equivalent of reading an epub. Once chapters here get formatted they get put under FanTL.", icon: "mdi:book-outline", color: "text-blue-400" },
    { name: "MTL", desc: "Currently released part three chapters. Translated by ZestysDaddy on Discord, kept separate because they'd break the order of FanTL (jumping to part three since part two isn't fully formatted yet).", icon: "mdi:auto-fix", color: "text-purple-400" },
  ];

  // 4. Sync internal state with URL
  $effect(() => {
    navState.selectedTL = currentTL;
  });

  // --- Handlers ---

  afterNavigate(() => {
    nextInfoDialog?.close();
  });

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
    if (browser) {
      window.removeEventListener("scroll", handleScroll);
    }
  });

  function handleScroll() {
    const scrollTop = window.scrollY;
    if (mainEl) {
      const mainHeight = mainEl.offsetHeight;
      const mainOffsetTop = mainEl.offsetTop;
      const scrollable = mainHeight - window.innerHeight;
      readProgress = scrollable > 0 ? Math.min(Math.max(((scrollTop - mainOffsetTop) / scrollable) * 100, 0), 100) : 100;
    }
    localStorage.setItem(
      "lastRead",
      JSON.stringify({
        book: bookSlug,
        tl: currentTL,
        slug: currentChapter,
        scroll: scrollTop,
        timestamp: Date.now(),
      }),
    );
  }

  function toggleFullscreen() {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().then(() => {
        screen.orientation?.lock?.("portrait").catch(() => {});
      }).catch(console.error);
    } else {
      document.exitFullscreen().then(() => {
        screen.orientation?.unlock?.();
      }).catch(console.error);
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
  {#if bookSlug === "manwha"}
    <title>GSGW Manwha - {currentChMeta.title}</title>
    <meta property="og:type" content="article" />
    <meta property="og:title" content="GSGW Manwha - {currentChMeta.title}" />
    <meta name="twitter:title" content="GSGW Manwha - {currentChMeta.title}" />
    {#if currentTL === "flame comics"}
      <meta property="og:description" content="Flame Comics" />
      <meta name="twitter:description" content="Flame Comics" />
    {/if}
  {:else}
    <title>{currentChMeta.section} - {currentChMeta.title}</title>
    <meta property="og:type" content="article" />
    <meta property="og:title" content="{currentChMeta.section} - {currentChMeta.title}" />
    <meta name="twitter:title" content="{currentChMeta.section} - {currentChMeta.title}" />
    <meta property="og:description" content="" />
    <meta name="twitter:description" content="" />
  {/if}
</svelte:head>

<svelte:window onkeydown={handleKeydown} />

<!-- Reading progress bar -->
<div
  class="fixed top-0 z-[60] h-[3px] w-screen pointer-events-none"
  style="opacity: {readProgress > 0 ? 1 : 0}; transition: opacity 0.3s;"
>
  <div class="h-full rounded-full bg-gradient-to-r from-primary/60 to-accent/60 transition-all duration-150 ease-out" style="width: {readProgress}%"></div>
</div>

<div
  bind:this={mainContainer}
  data-hide-tweet-meta={prefs.config.hideTweetMetadata}
  class="min-h-screen w-full text-base-content relative transition-colors duration-200"
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
  <div class="fixed inset-0 -z-10 bg-[oklch(var(--b1))]"></div>
  <!-- Scroll gradient -->
  <div
    class="scroll-gradient fixed inset-0 pointer-events-none hidden sm:block"
    style="opacity: {Math.min(Math.max(readProgress - 35, 0) / 35, { none: 0, low: 0.035, medium: 0.07, high: 0.15 }[prefs.config.scrollGradient] ?? 0.035)}; transition: opacity 0.8s ease-out;"
  ></div>
  <Navbar bind:this={navbarRef} {prefs} {bookSlug} {bookData} bind:navState {currentChapter} {chaptersForTL} {currentIndex} {currentTL} {nextInfoDialog} />

  <main bind:this={mainEl} class="mx-auto my-0 sm:my-6 max-w-4xl w-full z-0 relative transition-transform duration-300 ease-out ref-shift" style="transform: translateX({readerState.refPanelOpen ? '-72px' : '0px'})">
    <div class="relative rounded-2xl border-0 sm:border border-base-content/10 bg-base-200 shadow-none sm:shadow-xl sm:shadow-base-content/5 overflow-hidden">
      <div
        class="absolute inset-0 bg-base-300 -z-10 transition-opacity duration-300"
        style="opacity: var(--card-bg-opacity);"
      ></div>

      <div class="px-5 py-8 sm:px-8 sm:py-10 md:px-12 md:py-12">
        <article
          class="chapter-content prose prose-lg md:prose-xl max-w-none wrap-break-word"
        >
          {@render children()}
        </article>
      </div>

      <div class="border-t border-base-content/5 px-5 sm:px-8 md:px-12 py-5 flex items-center justify-between bg-base-200/40">
        <a
          href={currentIndex <= 0 
              ? `/book/${bookSlug}` 
              : `/read/${bookSlug}/${currentTL}/${chaptersForTL[currentIndex - 1].slug}`}
          class="btn btn-ghost btn-sm gap-2 hover:bg-base-content/5"
          aria-label={currentIndex <= 0 ? "Go Home" : "Previous Chapter"}
        >
          <Icon icon={currentIndex <= 0 ? "iconamoon:home-light" : "mage:previous"} class="size-5" />
          <span class="hidden sm:inline">{currentIndex <= 0 ? "Home" : "Prev"}</span>
        </a>

        <span class="text-xs font-mono font-bold text-base-content/40 tracking-wider">
          CH. {currentChMeta.slug}
        </span>

        <div class="relative">
          <button
            onclick={() => {
              if (currentIndex >= totalChapters - 1) {
                nextInfoDialog?.showModal();
              } else {
                goto(`/read/${bookSlug}/${currentTL}/${chaptersForTL[currentIndex + 1].slug}`);
              }
            }}
            class="btn btn-ghost btn-sm gap-2 hover:bg-base-content/5"
            aria-label={currentIndex >= totalChapters - 1 ? "No Next Chapter" : "Next Chapter"}
          >
            <span class="hidden sm:inline">Next</span>
            <Icon icon="mage:next" class="size-5" />
          </button>
        </div>
      </div>
    </div>
  </main>

  {#if readerState.footnotes}
    <div class="mx-auto mt-8 mb-0 sm:mb-8 max-w-4xl transition-transform duration-300 ease-out ref-shift" style="transform: translateX({readerState.refPanelOpen ? '-72px' : '0px'})">
      <div class="rounded-2xl border-0 sm:border border-base-content/10 bg-base-200 shadow-none sm:shadow-xl sm:shadow-base-content/5 overflow-hidden">
        <div class="px-4 sm:px-8 pt-6 pb-2">
          <div class="flex items-center gap-2">
            <Icon icon="lucide:book-open-text" class="size-4 text-base-content/30 shrink-0" />
            <span class="text-xs font-mono font-bold text-base-content/30 uppercase tracking-widest">Footnotes</span>
          </div>
        </div>
        <div class="px-4 sm:px-8 pb-8">
          {@html readerState.footnotes}
        </div>
      </div>
    </div>
  {/if}

  {#if bookSlug === "gsgw"}
    <button
      onclick={() => readerState.refPanelOpen = !readerState.refPanelOpen}
      class="group fixed right-0 top-1/2 -translate-y-1/2 z-40 flex items-center justify-center size-9 rounded-l-xl bg-base-100/90 backdrop-blur-md shadow-lg shadow-base-content/10 border border-base-content/15 border-r-0 cursor-pointer hover:bg-base-100 hover:shadow-xl hover:border-primary/30 transition-all duration-200"
      aria-label="Toggle Reference Panel"
    >
      <Icon icon={readerState.refPanelOpen ? "material-symbols:chevron-right-rounded" : "material-symbols:chevron-left-rounded"} class="size-5 text-base-content/40 group-hover:text-primary transition-colors" />
    </button>
  {/if}

  <div id="comments" class="mx-auto mt-8 mb-0 sm:mb-8 max-w-4xl transition-transform duration-300 ease-out ref-shift" style="transform: translateX({readerState.refPanelOpen ? '-72px' : '0px'})">
    <div class="rounded-2xl border-0 sm:border border-base-content/10 bg-base-200 shadow-none sm:shadow-xl sm:shadow-base-content/5 overflow-hidden">
      <div class="px-4 sm:px-8 pt-6 pb-2">
        <div class="flex items-center gap-2">
          <Icon icon="lucide:message-square-text" class="size-4 text-base-content/30 shrink-0" />
          <span class="text-xs font-mono font-bold text-base-content/30 uppercase tracking-widest">Comments</span>
        </div>
      </div>
      <div class="px-4 sm:px-8 pb-8">
    {#key page.url.pathname}
      {#if readerState.ch_meta.discussion}
        <Giscus
          repo="EnderOksam/GSGW-Reader"
          repoId="R_kgDOSUYftA"
          category="General"
          categoryId="DIC_kwDOSUYftM4C9WvT"
          mapping="number"
          term={String(readerState.ch_meta.discussion)}
          strict="1"
          reactionsEnabled="1"
          emitMetadata="0"
          inputPosition="top"
          theme="preferred_color_scheme"
          lang="en"
          loading="eager"
        />
      {:else}
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
      {/if}
    {/key}
    </div>
  </div>
  </div>

</div>

<!-- --- Modal: No Next Chapter --- -->
<dialog bind:this={nextInfoDialog} class="modal modal-bottom sm:modal-middle">
  <div class="modal-box bg-base-100 p-0 rounded-t-2xl sm:rounded-box shadow-2xl overflow-hidden max-h-[85vh]">
    <div class="relative">
      <div class="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-secondary/5"></div>
      <div class="relative flex items-center justify-between px-6 py-4 border-b border-base-content/10">
        <span class="font-bold text-lg flex items-center gap-2 text-primary">
          <Icon icon="material-symbols:info-outline" class="size-5" />
          No next chapter found
        </span>
        <form method="dialog">
          <button class="btn btn-sm btn-circle btn-ghost" aria-label="Close">
            <Icon icon="mdi:close" class="size-4" />
          </button>
        </form>
      </div>
    </div>

    <div class="overflow-y-auto overscroll-contain max-h-[70vh]">
      <div class="p-5 space-y-4">
        <p class="text-sm text-base-content/60 leading-relaxed">
          There is no next chapter here, but it probably is on the site under a different translation folder.
        </p>

        <div class="space-y-2.5">
          {#each TL_INFO as item}
            <div class="flex gap-3 p-3 rounded-xl bg-base-200/50 border border-base-content/5">
              <Icon icon={item.icon} class="size-5 shrink-0 mt-0.5 {item.color}" />
              <div class="space-y-0.5 min-w-0">
                <div class="text-xs font-bold tracking-wide">{item.name}</div>
                <p class="text-[11px] text-base-content/50 leading-relaxed">{item.desc}</p>
              </div>
            </div>
          {/each}
        </div>

        <a
          href="https://discord.gg/HHnSjeGN4d"
          target="_blank"
          class="btn btn-primary btn-sm w-full rounded-xl gap-2"
        >
          <Icon icon="mdi:discord" class="size-4" />
          <span class="text-xs">Chapters are still releasing — join the Discord</span>
        </a>
      </div>
    </div>
  </div>
  <form method="dialog" class="modal-backdrop"><button>close</button></form>
</dialog>

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

  .chapter-content :global(h1),
  .chapter-content :global(h2),
  .chapter-content :global(h3) {
    text-wrap: balance;
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

  :global(html) {
    overflow-y: overlay;
  }
  :global(.scroll-gradient) {
    --grad-top: color-mix(in oklch, var(--color-primary) 100%, transparent);
    --grad-mid: color-mix(in oklch, var(--color-accent) 100%, transparent);
    background: linear-gradient(180deg, var(--color-base-100) 0%, var(--grad-mid) 50%, var(--grad-top) 100%);
  }
  :global(.giscus-frame-wrapper) {
    width: 100%;
  }
  :global(.giscus) {
    width: 100%;
  }
</style>