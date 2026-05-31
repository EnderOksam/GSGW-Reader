<script lang="ts">
  import { page } from "$app/state";
  import JSZip from "jszip";
  import Icon from "@iconify/svelte";
  import book_meta from "$lib/meta.json";

  const REPO = "EnderOksam/GSGW-Reader";
  const BRANCH = "main";

  let tl = $derived(page.params.tl || "main");
  let slug = $derived(page.params.slug || "1");

  let images: string[] = [];
  let loaded = $state(false);
  let error = $state("");
  let showChapters = $state(false);

  interface Chapter { title: string; slug: string; index: number; }
  const meta = book_meta as Record<string, Record<string, Chapter[]>>;
  const chapters = $derived(meta["manwha"]?.[tl] || []);
  const currentIndex = $derived(chapters.findIndex(ch => ch.slug === slug));
  const prevChapter = $derived(currentIndex > 0 ? chapters[currentIndex - 1] : null);
  const nextChapter = $derived(currentIndex < chapters.length - 1 ? chapters[currentIndex + 1] : null);

  function padSlug(s: string) { return s.padStart(4, "0"); }

  $effect(() => {
    const s = slug;
    const t = tl;
    images = [];
    loaded = false;
    error = "";

    (async () => {
      try {
        const url = `https://raw.githubusercontent.com/${REPO}/${BRANCH}/chapters/manwha/${padSlug(s)}.cbz`;
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

<svelte:head>
  <title>Manwha Chapter {slug}</title>
</svelte:head>

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

<main class="mx-auto max-w-4xl w-full px-0 sm:px-6 md:px-12 z-0">
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

<style>
  :global(body) {
    margin: 0;
  }
</style>
