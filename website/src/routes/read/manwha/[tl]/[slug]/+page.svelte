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
  let showChapters = $state(false);
  let showSettings = $state(false);
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

  interface Chapter { title: string; slug: string; index: number; }
  const meta = book_meta as Record<string, Record<string, Chapter[]>>;
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



<nav class="sticky top-0 z-50 flex w-full items-center justify-center gap-2 sm:gap-5 bg-base-100 border-b border-base-content/10 p-3">
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
    <button onclick={() => showChapters = !showChapters} class="btn btn-outline btn-sm rounded-btn">
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
      <button onclick={() => showSettings = !showSettings} class="btn btn-ghost btn-sm btn-square rounded-btn relative z-[60]">
        <Icon icon="material-symbols:settings-outline-rounded" class="size-5" />
      </button>
    </div>
    {#if showSettings}
      <div class="fixed inset-0 z-40" onclick={() => showSettings = false}></div>
      <div class="absolute top-full right-0 mt-2 z-50 bg-base-100 border border-base-content/10 rounded-box shadow-2xl p-4 min-w-48" onclick={(e) => e.stopPropagation()}>
        <div class="flex flex-col gap-3">
          <div class="max-md:hidden">
            <span class="text-xs font-medium">Size: {Math.round(imageScale * 100)}%</span>
            <input type="range" min="0.5" max="1.5" step="0.05" bind:value={imageScale} class="range range-sm" />
            <div class="flex justify-between text-[10px] opacity-40 px-0.5">
              <span>50%</span>
              <span>70%</span>
              <span>150%</span>
            </div>
            <div class="border-t border-base-content/10 my-1"></div>
          </div>
          <span class="text-xs font-medium">Theme</span>
          <select class="select select-bordered select-sm w-full rounded-btn" bind:value={theme}>
            <optgroup label="Recommended">
              {#each PRIORITY_THEMES as t}
                <option value={t}>{t}</option>
              {/each}
            </optgroup>
            <optgroup label="Other">
              {#each MISC_THEMES as t}
                <option value={t}>{t}</option>
              {/each}
            </optgroup>
          </select>
        </div>
      </div>
    {/if}
  </div>



  <div class="tooltip tooltip-bottom" data-tip="Comments (C)">
    <button onclick={() => document.getElementById("comments")?.scrollIntoView({ behavior: "smooth" })} class="btn btn-ghost btn-sm btn-square rounded-btn">
      <Icon icon="iconamoon:comment" class="size-6" />
    </button>
  </div>
</nav>

{#if showChapters}
  <div class="fixed inset-0 z-40 bg-black/30" onclick={() => showChapters = false}></div>
  <aside class="fixed top-16 right-4 z-50 w-72 max-w-[85vw] max-h-[70vh] bg-base-100 border border-base-content/10 rounded-box shadow-2xl overflow-y-auto p-3">
    <div class="flex items-center justify-between mb-3 px-1">
      <h3 class="text-sm font-bold text-base-content/60 uppercase tracking-wider">Chapters</h3>
      <button onclick={() => showChapters = false} class="btn btn-ghost btn-xs btn-square">✕</button>
    </div>
    <div class="flex flex-col gap-0.5">
      {#each chapters as ch}
        <a
          href="/read/manwha/{tl}/{ch.slug}"
          class="btn btn-sm justify-start w-full font-normal border-none rounded-btn {ch.slug === slug ? 'btn-primary btn-soft' : 'btn-ghost'}"
          onclick={() => showChapters = false}
        >
          <span class="w-10 font-mono text-xs opacity-50">#{ch.slug}</span>
          <span class="truncate">{ch.title}</span>
        </a>
      {/each}
    </div>
  </aside>
{/if}

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

<footer class="mx-auto w-full px-0 sm:px-6 md:px-12 pb-8 pt-12" style="max-width: {56 * imageScale}rem">
  <div class="mt-16 flex items-center justify-between border-t border-base-content/10 pt-8">
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
