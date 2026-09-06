<script lang="ts">
  import { page } from "$app/state";
  import { onMount, onDestroy } from "svelte";
  import { browser, dev } from "$app/environment";
  import JSZip from "jszip";
  import Icon from "@iconify/svelte";
  import book_meta from "$lib/meta.json";

  let tl = $derived(page.params.tl || "main");
  let slug = $derived(page.params.slug || "1");

  let images = $state<string[]>([]);
  let loaded = $state(false);
  let error = $state("");
  let chaptersDialog: HTMLDialogElement | undefined = $state();
  let settingsDialog: HTMLDialogElement | undefined = $state();
  let imageScale = $state(browser ? parseFloat(localStorage.getItem("manwha-scale") ?? "0.7") : 0.7);

  const PRIORITY_THEMES = ["sunset", "light", "retro", "night", "business", "cupcake", "black"];
  const ALL_THEMES = ["sunset","light","dark","cupcake","bumblebee","emerald","corporate","synthwave","retro","cyberpunk","valentine","halloween","garden","forest","aqua","lofi","pastel","fantasy","wireframe","black","luxury","dracula","cmyk","autumn","business","acid","lemonade","night","coffee","winter","dim","nord","sunset"];
  const MISC_THEMES = ALL_THEMES.filter((t) => !PRIORITY_THEMES.includes(t));
  let theme = $state(browser ? (() => { try { const s = localStorage.getItem("readerSettings"); if (s) { const p = JSON.parse(s); if (p.theme) return p.theme; } } catch {} return "sunset"; })() : "sunset");

  $effect(() => {
    localStorage.setItem("manwha-scale", String(imageScale));
  });

  $effect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    if (browser) {
      try {
        const saved = localStorage.getItem("readerSettings");
        const config = saved ? JSON.parse(saved) : {};
        config.theme = theme;
        localStorage.setItem("readerSettings", JSON.stringify(config));
      } catch {}
    }
  });

  function resetSettings() {
    if (confirm("Reset manwha settings?")) {
      imageScale = 0.7;
      theme = "sunset";
    }
  }

  interface Chapter { title: string; slug: string; index: number; thumb?: string; }
  const meta = book_meta as unknown as Record<string, Record<string, Chapter[]>>;
  const chapters = $derived(meta["manwha"]?.[tl] || []);
  const currentIndex = $derived(chapters.findIndex(ch => ch.slug === slug));
  const prevChapter = $derived(currentIndex > 0 ? chapters[currentIndex - 1] : null);
  const nextChapter = $derived(currentIndex < chapters.length - 1 ? chapters[currentIndex + 1] : null);

  function padSlug(s: string) { return s.padStart(4, "0"); }

  function saveLastRead() {
    localStorage.setItem(
      "lastRead",
      JSON.stringify({
        book: "manwha",
        tl,
        slug,
        timestamp: Date.now(),
      }),
    );
  }

  $effect(() => {
    const s = slug;
    const t = tl;
    images = [];
    loaded = false;
    error = "";
    saveLastRead();

    (async () => {
      try {
        const repoBase = "https://raw.githubusercontent.com/EnderOksam/GSGW-Reader/main";
        const url = dev
          ? `/chapters/manwha/${encodeURIComponent(t)}/${padSlug(s)}.cbz`
          : `${repoBase}/chapters/manwha/${encodeURIComponent(t)}/${padSlug(s)}.cbz`;
        const res = await fetch(url);
        if (!res.ok) throw new Error();
        const blob = await res.blob();
        const zip = await JSZip.loadAsync(blob);
        const names: string[] = [];
        zip.forEach((name, file) => {
          if (!file.dir && /\.(png|jpg|jpeg|webp|gif)$/i.test(name)) names.push(name);
        });
        names.sort((a, b) => a.localeCompare(b, undefined, { numeric: true }));
        const urls: string[] = [];
        for (const name of names) {
          const file = zip.file(name);
          if (file) urls.push(URL.createObjectURL(await file.async("blob")));
        }
        images = urls;
        loaded = true;
        window.scrollTo(0, 0);
      } catch {
        error = "Chapter not found";
      }
    })();
  });


</script>



<nav class="sticky top-0 z-50 flex w-full items-center justify-center gap-2 sm:gap-5 bg-base-100/80 backdrop-blur-md border-b border-base-content/5 p-3">
  <div class="tooltip tooltip-bottom" data-tip="Home (H)">
    <a href="/book/manwha" class="btn btn-ghost btn-sm btn-square rounded-btn">
      <Icon icon="material-symbols:home-outline-rounded" class="size-6" />
    </a>
  </div>

  <div class="tooltip tooltip-bottom" data-tip="Previous (P)">
    {#if prevChapter}
      <a href="/read/manwha/{tl}/{prevChapter.slug}" class="btn btn-ghost btn-sm btn-square rounded-btn">
        <Icon icon="mage:previous" class="size-5" />
      </a>
    {:else}
      <button class="btn btn-ghost btn-sm btn-square rounded-btn opacity-30" disabled>
        <Icon icon="mage:previous" class="size-5" />
      </button>
    {/if}
  </div>

  <div class="tooltip tooltip-bottom" data-tip="Chapters (T)">
    <button onclick={() => chaptersDialog?.showModal()} class="btn btn-outline btn-sm rounded-btn">
      <Icon icon="lucide:table-of-contents" class="size-5" />
      <span class="hidden sm:inline">Chapters</span>
    </button>
  </div>

  <div class="tooltip tooltip-bottom" data-tip="Next (N)">
    {#if nextChapter}
      <a href="/read/manwha/{tl}/{nextChapter.slug}" class="btn btn-ghost btn-sm btn-square rounded-btn">
        <Icon icon="mage:next" class="size-5" />
      </a>
    {:else}
      <button class="btn btn-ghost btn-sm btn-square rounded-btn opacity-30" disabled>
        <Icon icon="mage:next" class="size-5" />
      </button>
    {/if}
  </div>

  <div class="relative">
    <div class="tooltip tooltip-bottom" data-tip="Settings">
      <button onclick={() => settingsDialog?.showModal()} class="btn btn-ghost btn-sm btn-square rounded-btn relative z-[60]">
        <Icon icon="material-symbols:settings-outline-rounded" class="size-5" />
      </button>
    </div>
  </div>



  <div class="tooltip tooltip-bottom" data-tip="Comments (C)">
    <button onclick={() => document.getElementById("comments")?.scrollIntoView({ behavior: "smooth" })} class="btn btn-ghost btn-sm btn-square rounded-btn">
      <Icon icon="iconamoon:comment" class="size-6" />
    </button>
  </div>
</nav>


<dialog bind:this={chaptersDialog} class="modal modal-bottom sm:modal-middle">
  <div class="modal-box bg-base-100 p-0 rounded-t-2xl sm:rounded-box max-h-[85vh] flex flex-col shadow-2xl overflow-hidden">
    <div class="relative">
      <div class="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-secondary/5"></div>
      <div class="relative flex items-center justify-between px-5 pt-4 pb-3 border-b border-base-content/10">
        <span class="font-bold text-lg text-primary flex items-center gap-2"><Icon icon="lucide:table-of-contents" class="size-5" /> Chapters</span>
        <div class="flex items-center gap-2">
          <span class="text-xs font-mono text-base-content/30">{chapters.length} chapters</span>
          <form method="dialog">
            <button class="btn btn-sm btn-circle btn-ghost" aria-label="Close">
              <Icon icon="mdi:close" class="size-4" />
            </button>
          </form>
        </div>
      </div>
    </div>
    <div class="overflow-y-auto overscroll-contain p-2">
      <div class="flex flex-col gap-1">
        {#each chapters as ch}
          {@const isActive = ch.slug === slug}
          <a
            href="/read/manwha/{tl}/{ch.slug}"
            class="flex items-center gap-3 px-2.5 py-2 rounded-xl transition-all duration-150 {isActive ? 'bg-primary/10 ring-1 ring-primary/20' : 'hover:bg-base-200/60'}"
            onclick={() => chaptersDialog?.close()}
          >
            <div class="relative w-28 h-[84px] shrink-0 rounded-lg overflow-hidden bg-base-300/60 border border-base-content/10">
              {#if ch.thumb}
                <img src={ch.thumb} alt={ch.title} class="w-full h-full object-cover" loading="lazy" />
              {:else}
                <div class="w-full h-full flex items-center justify-center">
                  <Icon icon="material-symbols:image-outline-rounded" class="size-6 opacity-20" />
                </div>
              {/if}
            </div>
            <span class="text-base font-bold tabular-nums {isActive ? 'text-primary' : 'text-base-content/80'}">
              Chapter {ch.slug}
            </span>
            {#if isActive}
              <Icon icon="mdi:play-circle" class="ml-auto size-4 shrink-0 text-primary/50" />
            {/if}
          </a>
        {/each}
      </div>
    </div>
  </div>
  <form method="dialog" class="modal-backdrop"><button>close</button></form>
</dialog>


<dialog bind:this={settingsDialog} class="modal modal-bottom sm:modal-middle">
  <div class="modal-box bg-base-100 p-0 rounded-box shadow-2xl overflow-hidden">
    <div class="relative">
      <div class="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-secondary/5"></div>
      <div class="relative flex justify-between items-center px-6 py-4 border-b border-base-content/10">
        <span class="font-bold text-lg flex items-center gap-2 text-primary">
          <Icon icon="material-symbols:settings-outline-rounded" class="size-5" /> Settings
        </span>
        <div class="flex gap-2">
          <button class="btn btn-sm btn-ghost text-error rounded-full" onclick={resetSettings}>Reset</button>
          <form method="dialog">
            <button class="btn btn-sm btn-circle btn-ghost" aria-label="Close">
              <Icon icon="mdi:close" class="size-4" />
            </button>
          </form>
        </div>
      </div>
    </div>

    <div class="overflow-y-auto overscroll-contain max-h-[70vh]">
      <div class="p-5 space-y-4">
        <div class="rounded-2xl bg-base-200/40 border border-base-content/5 p-4 space-y-4">
          <div class="flex items-center gap-2">
            <Icon icon="mdi:palette-outline" class="size-4 text-primary/60" />
            <span class="text-xs font-bold uppercase tracking-widest text-base-content/40">Appearance</span>
          </div>
          <div class="form-control gap-1.5">
            <label class="label-text text-xs font-medium flex justify-between">
              <span>Size</span>
              <span class="text-base-content/30 font-mono">{Math.round(imageScale * 100)}%</span>
            </label>
            <input type="range" min="0.5" max="1.5" step="0.05" bind:value={imageScale} class="range range-xs range-primary" />
          </div>
          <div class="form-control gap-1.5">
            <label class="label-text text-xs font-medium">Theme</label>
            <select class="select select-bordered select-sm w-full rounded-xl" bind:value={theme}>
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
        </div>
      </div>
    </div>
  </div>
  <form method="dialog" class="modal-backdrop"><button>close</button></form>
</dialog>

<main class="mx-auto w-full px-0 sm:px-6 md:px-12 z-0" style="max-width: {56 * imageScale}rem">
  {#if error}
    <div class="flex items-center justify-center h-[60dvh] text-base-content/50 text-sm">{error}</div>
  {:else if !loaded}
    <div class="flex flex-col items-center justify-center h-[60dvh] gap-3 text-base-content/50">
      <Icon icon="svg-spinners:180-ring" class="size-8" />
      <span class="text-sm">Loading chapter...</span>
    </div>
  {:else if images.length === 0}
    <div class="flex items-center justify-center h-[60dvh] text-base-content/50 text-sm">No images found</div>
  {:else}
    <div class="flex flex-col items-center w-full">
      {#each images as src, i}
        <img {src} alt="Page {i + 1}" class="w-full block" loading="lazy" />
      {/each}
    </div>
  {/if}
</main>

<footer class="mx-auto w-full px-3 sm:px-6 md:px-12 pb-8 pt-6" style="max-width: {56 * imageScale}rem">
  <div class="mt-6 flex items-center justify-between border-t border-base-content/10 pt-6">
    <a
      href={prevChapter ? `/read/manwha/${tl}/${prevChapter.slug}` : `/book/manwha`}
      class="btn btn-soft btn-sm gap-2"
      aria-label={prevChapter ? "Previous Chapter" : "Go Home"}
    >
      <Icon icon={prevChapter ? "mage:previous" : "iconamoon:home-light"} class="size-5" />
      <span class="hidden sm:inline">{prevChapter ? "Prev" : "Home"}</span>
    </a>

    <span class="text-xs font-mono font-bold opacity-50 tracking-wider">
      CH. {slug}
    </span>

    <a
      href={nextChapter ? `/read/manwha/${tl}/${nextChapter.slug}` : `/book/manwha`}
      class="btn btn-soft btn-sm gap-2"
      aria-label={nextChapter ? "Next Chapter" : "Go Home"}
    >
      <span class="hidden sm:inline">{nextChapter ? "Next" : "Home"}</span>
      <Icon icon={nextChapter ? "mage:next" : "iconamoon:home-light"} class="size-5" />
    </a>
  </div>
</footer>

<style>
  :global(body) {
    margin: 0;
  }
  main {
    transition: max-width 0.15s ease-out;
  }
</style>
