<script lang="ts">
  import { onMount } from "svelte";
  import { fade, fly } from "svelte/transition";
  import Icon from "@iconify/svelte";

  interface Part {
    id: string;
    label: string;
    range?: string;
    status: string;
  }

  interface Variant {
    id: string;
    label: string;
    description: string;
    parts: Part[];
  }

  interface Story {
    id: string;
    title: string;
    short: string;
    badgeClass: string;
    variants: Variant[];
  }

  const variantDefs = [
    { id: "plaintext", label: "Plain Text", badge: "css", description: "All formatting is done through text — the best attempt to use CSS to make it look like the website." },
    { id: "default", label: "Default", description: "Coming Soon — standard EPUBs with no special windows, support for legacy devices." },
  ];

  const defaultStories: Story[] = [
    {
      id: "gsgw", title: "Got Dropped into a Ghost Story, Still Gotta Work", short: "GSGW", badgeClass: "badge-primary",
      variants: [
        { id: "plaintext", label: "Plain Text", description: variantDefs[0].description, parts: [
          { id: "part1", label: "Part 1", range: "Chapters 0–208", status: "Formatted" },
          { id: "part2", label: "Part 2", range: "Chapters 209–371", status: "WIP" },
          { id: "part3", label: "Part 3", range: "Chapter 372 – Current", status: "Ongoing" },
        ] },
        { id: "default", label: "Default", description: variantDefs[1].description, parts: [
          { id: "part1", label: "Part 1", range: "Chapters 0–208", status: "Formatted" },
          { id: "part2", label: "Part 2", range: "Chapters 209–371", status: "WIP" },
          { id: "part3", label: "Part 3", range: "Chapter 372 – Current", status: "Ongoing" },
        ] },
      ],
    },
    {
      id: "debut", title: "Debut or Die", short: "Debut", badgeClass: "badge-secondary",
      variants: [
        { id: "plaintext", label: "Plain Text", description: variantDefs[0].description, parts: [
          { id: "part1", label: "Part 1", range: "Chapters 1–147", status: "Formatted" },
          { id: "part2", label: "Part 2", range: "Chapters 148–364", status: "WIP" },
          { id: "part3", label: "Part 3", range: "Chapters 365–451", status: "Unformatted" },
          { id: "part4", label: "Part 4", range: "Chapters 452–644", status: "Unformatted" },
        ] },
        { id: "default", label: "Default", description: variantDefs[1].description, parts: [
          { id: "part1", label: "Part 1", range: "Chapters 1–147", status: "Formatted" },
          { id: "part2", label: "Part 2", range: "Chapters 148–364", status: "WIP" },
          { id: "part3", label: "Part 3", range: "Chapters 365–451", status: "Unformatted" },
          { id: "part4", label: "Part 4", range: "Chapters 452–644", status: "Unformatted" },
        ] },
      ],
    },
  ];

  let stories = $state<Story[]>(defaultStories);
  let selectedStory = $state("gsgw");
  let selectedVariant = $state("plaintext");
  let selectedPart = $state("part1");
  let downloadUrl = $state("");
  let epubName = $state("");
  let releaseDate = $state("");
  let downloading = $state(false);
  let storyAssets = $state<Record<string, { url: string; name: string; count: number }>>({});

  function releaseFilename(story: string, variant: string, part: string) {
    return `${story} - Part ${part} [PlainText]`.replace(/[[\],]/g, '').replace(/ /g, '.').replace(/\.+/g, '.') + '.epub';
  }

  function makeAssetUrl(tag: string, story: string, variant: string, part: string) {
    const name = releaseFilename(story, variant, part);
    return { url: `https://github.com/EnderOksam/GSGW-Reader/releases/download/${tag}/${name}`, name };
  }

  function updateDownload() {
    const key = `${selectedStory}/${selectedVariant}/${selectedPart}`;
    const asset = storyAssets[key];
    downloadUrl = asset?.url || "";
    epubName = asset?.name || "";
  }

  onMount(async () => {
    try {
      const res = await fetch("https://api.github.com/repos/EnderOksam/GSGW-Reader/releases");
      if (!res.ok) throw new Error("API error");
      const releases = await res.json();
      if (!releases.length) throw new Error("No releases");

      const tag = releases[0].tag_name;
      releaseDate = releases[0].published_at?.slice(0, 10) || "";

      const assets: Record<string, { url: string; name: string; count: number }> = {};

      for (const def of defaultStories) {
        for (const v of def.variants) {
          for (const p of v.parts) {
            const num = p.id.replace("part", "");
            const targetName = releaseFilename(def.title, v.id, num);
            const releaseAsset = releases[0].assets?.find((a: any) => a.name === targetName);
            if (releaseAsset) {
              assets[`${def.id}/${v.id}/${p.id}`] = { url: releaseAsset.browser_download_url, name: releaseAsset.name, count: releaseAsset.download_count || 0 };
            } else {
              const a = makeAssetUrl(tag, def.title, v.id, num);
              assets[`${def.id}/${v.id}/${p.id}`] = { url: a.url, name: a.name, count: 0 };
            }
          }
        }
      }

      storyAssets = assets;

      if (!storyAssets[`${selectedStory}/${selectedVariant}/${selectedPart}`]?.url) {
        selectedStory = defaultStories[0].id;
        selectedVariant = defaultStories[0].variants[0].id;
        selectedPart = defaultStories[0].variants[0].parts[0].id;
      }
      updateDownload();
    } catch {
      for (const def of defaultStories) {
        for (const v of def.variants) {
          for (const p of v.parts) {
            const num = p.id.replace("part", "");
            const a = makeAssetUrl("latest", def.title, v.id, num);
            storyAssets[`${def.id}/${v.id}/${p.id}`] = { url: a.url, name: a.name, count: 0 };
          }
        }
      }
      stories = defaultStories;
      selectedStory = "gsgw";
      selectedVariant = "plaintext";
      selectedPart = "part1";
      updateDownload();
    }
  });

  function selectStory(id: string) {
    selectedStory = id;
    const story = stories.find((s) => s.id === id);
    if (story) {
      selectedVariant = story.variants[0].id;
      selectedPart = story.variants[0].parts[0].id;
    }
    updateDownload();
  }

  function selectVariant(id: string) {
    selectedVariant = id;
    const story = stories.find((s) => s.id === selectedStory)!;
    const variant = story.variants.find((v) => v.id === id)!;
    selectedPart = variant.parts[0].id;
    updateDownload();
  }

  function selectPart(id: string) {
    selectedPart = id;
    updateDownload();
  }

  async function handleDownload() {
    if (!downloadUrl || downloading) return;
    downloading = true;
    try {
      const res = await fetch(downloadUrl);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = epubName || "epub.epub";
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      window.open(downloadUrl, "_blank");
    } finally {
      downloading = false;
    }
  }

  let recommendModal: HTMLDialogElement;
  const openRecommended = () => recommendModal?.showModal();

  const currentStory = $derived(stories.find((s) => s.id === selectedStory)!);
  const currentVariant = $derived(currentStory?.variants.find((v) => v.id === selectedVariant)!);
  const currentPart = $derived(currentVariant?.parts.find((p) => p.id === selectedPart)!);
  const currentAsset = $derived(storyAssets[`${selectedStory}/${selectedVariant}/${selectedPart}`]);
  const currentDownloadCount = $derived(currentAsset?.count ?? 0);
</script>

<div class="relative min-h-dvh overflow-x-hidden">
  
  <div class="relative flex flex-col items-center justify-center min-h-dvh p-4 md:p-8">
    <div class="max-w-4xl w-full">
      <header class="text-center mb-14">
        <h1 class="crt-title text-4xl md:text-6xl font-black mb-3 tracking-tight">
          Offline Archives
        </h1>
        <p class="text-base-content/50 max-w-lg mx-auto text-sm md:text-base leading-relaxed">
          Download the complete fan translation for offline reading on your e-reader, tablet, or phone.
        </p>
      </header>

      <div
        in:fly={{ y: 20, duration: 400 }}
        class="relative overflow-hidden rounded-2xl bg-[#0d0d0d]/80 border border-primary/15 shadow-2xl"
      >
        <div class="relative p-8 md:p-10 space-y-8">
          <div class="flex items-center justify-center gap-4">
            <div class="h-px flex-1 bg-linear-to-r from-transparent via-white/5 to-transparent"></div>
            <div class="inline-flex p-1 rounded-2xl bg-white/5 border border-white/10 shadow-inner shadow-black/20">
              {#each stories as story}
                <button
                  onclick={() => selectStory(story.id)}
                  class="relative px-5 py-2.5 rounded-xl text-sm font-bold tracking-wide transition-all duration-300
                    {selectedStory === story.id
                      ? 'text-white'
                      : 'text-base-content/40 hover:text-base-content/70'}"
                >
                  {#if selectedStory === story.id}
                    <div class="absolute inset-0 rounded-xl bg-linear-to-br from-primary/20 via-primary/10 to-primary/5 shadow-lg shadow-black/10 border border-primary/20"></div>
                  {/if}
                  <span class="relative z-10">{story.short}</span>
                </button>
              {/each}
            </div>
            <div class="h-px flex-1 bg-linear-to-r from-transparent via-white/5 to-transparent"></div>
          </div>

          {#if currentStory}
            <div class="flex justify-center gap-3 flex-wrap">
              {#each variantDefs as def}
                {@const supported = currentStory.variants.some((v) => v.id === def.id)}
                {@const isDefault = def.id === 'default'}
                <button
                  onclick={() => !isDefault && supported && selectVariant(def.id)}
                  disabled={!supported || isDefault}
                  class="relative flex items-center gap-2.5 px-4 py-2 rounded-xl text-sm font-bold transition-all duration-300
                    {selectedVariant === def.id && supported
                      ? 'text-white shadow-lg shadow-primary/15'
                      : isDefault
                        ? 'text-base-content/25 line-through cursor-not-allowed border border-white/[0.03] bg-white/[0.01]'
                        : 'text-base-content/50 hover:text-base-content/70 border border-white/5 hover:border-white/10 bg-white/[0.02]'}"
                >
                  {#if selectedVariant === def.id && supported}
                    <div class="absolute inset-0 rounded-xl bg-linear-to-br from-primary/25 to-primary/10 border border-primary/30 shadow-inner shadow-white/5"></div>
                  {/if}
                  <span class="relative z-10">{def.label}</span>
                  {#if def.badge}
                    <span class="relative z-10 text-[10px] font-mono font-medium px-1.5 py-0.5 rounded-md text-green-300 bg-green-500/10 border border-green-500/20">{def.badge}</span>
                  {/if}
                </button>
              {/each}
            </div>
          {/if}

          {#if currentVariant && currentVariant.parts.length > 1}
            <div class="flex flex-col md:flex-row gap-6 md:gap-10 items-start">
              <div class="grid grid-cols-2 gap-2">
                {#each currentVariant.parts as part}
                  <button
                    onclick={() => selectPart(part.id)}
                    class="relative px-4 py-3 rounded-xl text-sm font-bold transition-all duration-300 text-left
                      {selectedPart === part.id
                        ? 'text-white shadow-md shadow-primary/10'
                        : 'text-base-content/40 hover:text-base-content/70 border border-white/[0.04] hover:border-white/10 bg-white/[0.01]'}"
                  >
                    {#if selectedPart === part.id}
                      <div class="absolute inset-0 rounded-xl bg-linear-to-br from-primary/25 to-primary/10 border border-primary/25 shadow-inner shadow-white/5"></div>
                    {/if}
                    <span class="relative z-10">{part.label}</span>
                    {#if part.range}
                      <span class="relative z-10 block text-[10px] font-normal opacity-50 mt-0.5">{part.range}</span>
                    {/if}
                  </button>
                {/each}
              </div>
              <div class="flex-1 min-w-0 space-y-4">
                {#each variantDefs as def}
                  {@const variant = currentStory?.variants.find((v) => v.id === def.id)}
                  {@const isDefault = def.id === 'default'}
                  {#if !isDefault}
                    <div class="text-sm leading-relaxed pl-3 border-l-2 {variant ? 'border-green-500/40' : 'border-white/5'}">
                      <span class="font-semibold text-white/80">{def.label}</span>
                      <span class="text-base-content/50"> — {variant?.description || def.description}</span>
                    </div>
                  {/if}
                {/each}
                {#each variantDefs as def}
                  {@const variant = currentStory?.variants.find((v) => v.id === def.id)}
                  {@const isDefault = def.id === 'default'}
                  {#if isDefault}
                    <div class="text-xs leading-relaxed pl-3 border-l border-white/5 opacity-30 mt-3">
                      <span class="font-semibold text-white/40">{def.label}</span>
                      <span class="text-base-content/30"> — {variant?.description || def.description}</span>
                    </div>
                  {/if}
                {/each}
              </div>
            </div>
          {:else}
            <div class="h-10"></div>
          {/if}

          <hr class="border-white/[0.06]" />

          <div class="flex flex-col md:flex-row gap-8 md:gap-12 items-center">
            <div class="flex-1 space-y-4">
              <div class="flex items-center gap-3">
                <span class="badge {currentStory?.badgeClass ?? 'badge-primary'} badge-outline font-mono text-xs font-bold tracking-widest px-3 py-2">EPUB</span>
                <span class="badge badge-ghost font-mono text-xs tracking-wider px-3 py-2 bg-white/5">
                  {currentVariant?.label || ''}
                </span>
                {#if currentPart?.status}
                  <span class="badge badge-outline font-mono text-xs font-semibold tracking-wider px-3 py-2 text-yellow-300 border-yellow-500/30 bg-yellow-500/10">
                    {currentPart.status}
                  </span>
                {/if}
              </div>

              <div>
                <h2 class="text-2xl md:text-3xl font-bold text-white leading-tight">{currentStory?.title ?? ''} - {currentPart?.label ?? ''}</h2>
              {#if currentPart?.range}
                <p class="text-xs font-mono opacity-40 uppercase tracking-widest mt-1">{currentPart.range}</p>
              {/if}
              </div>

              <div class="flex items-center gap-2 text-xs font-mono opacity-40 uppercase tracking-widest">
                <Icon icon="mdi:translate" class="size-3.5" />
                <span>Fan Translation</span>
              </div>

              <div class="flex items-center gap-4">
                {#if releaseDate}
                  <span class="inline-flex items-center gap-1.5 text-xs font-mono text-base-content/40">
                    <Icon icon="mdi:calendar-outline" class="size-3.5" />
                    Updated {releaseDate}
                  </span>
                {/if}
                {#if currentDownloadCount > 0}
                  <span class="inline-flex items-center gap-1.5 text-xs font-mono text-base-content/40">
                    <Icon icon="mdi:download-outline" class="size-3.5" />
                    {currentDownloadCount.toLocaleString()} downloads
                  </span>
                {/if}
              </div>
            </div>

            <div class="w-full md:w-72 flex flex-col gap-3 shrink-0">
              <button
                onclick={handleDownload}
                disabled={downloading || !downloadUrl}
                class="btn h-auto py-5 px-6 border-none bg-linear-to-br from-primary via-primary/90 to-primary/80 text-white hover:brightness-110 hover:scale-[1.02] active:scale-[0.98] shadow-xl shadow-primary/25 hover:shadow-2xl hover:shadow-primary/30 flex items-center justify-between group/btn text-base rounded-2xl transition-all duration-300"
              >
                <div class="text-left">
                  <div class="font-bold flex items-center gap-2 text-lg">
                    {downloading ? "Downloading…" : "Download EPUB"}
                    <Icon icon="mdi:star-four-points" class="size-4 text-yellow-300" />
                  </div>
                  <div class="text-xs opacity-70 font-normal mt-0.5">
                    {currentPart?.label || "Full Story"} • Modern Format
                  </div>
                </div>
                <Icon icon="mdi:download" class="size-7 opacity-60 group-hover/btn:translate-y-0.5 transition-transform duration-300" />
              </button>
              <button onclick={openRecommended} class="btn h-auto py-4 px-6 border border-accent/30 bg-accent/10 text-accent hover:bg-accent/20 hover:border-accent/50 flex items-center justify-between group/btn text-sm rounded-2xl transition-all duration-300">
                <div class="text-left">
                  <div class="font-semibold flex items-center gap-2">
                    Recommended EPUB Readers
                  </div>
                  <div class="text-[11px] opacity-70 font-normal mt-0.5">
                    Best apps for any device
                  </div>
                </div>
                <Icon icon="mdi:book-open-outline" class="size-5 opacity-60 group-hover/btn:scale-110 transition-transform duration-300" />
              </button>
            </div>
          </div>
        </div>
      </div>

    </div>
  </div>
</div>

<dialog bind:this={recommendModal} class="modal backdrop:!bg-black/60 backdrop:!backdrop-blur-sm">
  <div class="modal-box max-w-md bg-[#0d0d0d]/95 border border-primary/15 p-0 rounded-2xl shadow-2xl max-h-[85dvh] flex flex-col">
    <div class="p-6 border-b border-white/5 flex items-center justify-between shrink-0">
      <div>
        <h3 class="text-lg font-bold text-white flex items-center gap-2">
          <Icon icon="mdi:bookmark" class="size-5 text-accent" />
          Recommended EPUB Readers
        </h3>
        <p class="text-xs text-base-content/50 mt-0.5">Best apps for EPUB reading on any device</p>
      </div>
      <button onclick={() => recommendModal?.close()} class="btn btn-ghost btn-xs btn-circle text-base-content/50 hover:text-white">
        <Icon icon="mdi:close" class="size-4" />
      </button>
    </div>
    <div class="p-6 space-y-3 text-sm text-base-content/80 leading-relaxed overflow-y-auto">
      <p>Hey hey 👋, Ender here. A lot of people have issues with the story not looking how it should depending on their device.</p>
      <p>I try to fix as much as I can with the epub but most of the fault lies in their epub reader so here are some recommended ones:</p>

      <div class="space-y-2">
        <div class="p-3 rounded-xl bg-white/[0.02] border border-white/5">
          <div class="flex items-center gap-2 text-sm font-semibold text-white mb-2">
            <Icon icon="mdi:apple" class="size-5 text-accent/70" /> iOS
          </div>
          <div class="space-y-2">
            <div>
              <span class="font-semibold text-white">PocketBook / BookFusion</span>
              <p class="text-xs text-base-content/60">I don't personally use these on iOS, but both are solid EPUB reader options. PocketBook has been recommended by Lei and Destiny from the Discord, while BookFusion is considered the better option overall, though the free version is limited to a maximum of 10 books.</p>
            </div>
            <div>
              <span class="font-semibold text-white">Suwatte</span>
              <p class="text-xs text-base-content/60">Lei really likes this one. It's a comic reader app for iOS that now also supports EPUB/PDF files. Since it's available through TestFlight, you'll need to opt in to access it.</p>
            </div>
            <div class="opacity-50">
              <span class="font-semibold text-white">Apple Books</span>
              <p class="text-xs text-base-content/60">Apple Books works as well, but enabling Dark Mode may interfere with the EPUB's CSS styling, which can affect the intended text formatting and overall appearance.</p>
            </div>
          </div>
        </div>

        <div class="p-3 rounded-xl bg-white/[0.02] border border-white/5">
          <div class="flex items-center gap-2 text-sm font-semibold text-white mb-2">
            <Icon icon="mdi:android" class="size-5 text-accent/70" /> Android
          </div>
          <div class="space-y-2">
            <div>
              <span class="font-semibold text-white">Episteme</span>
              <p class="text-xs text-base-content/60">I've discovered Episteme recently and it's been my favorite epub reader so far. Haven't had any issues people report on other epub readers.</p>
            </div>
            <div class="opacity-50">
              <span class="font-semibold text-white">Lithium</span>
              <p class="text-xs text-base-content/60">Good alternative, it works but it's not perfect.</p>
            </div>
          </div>
        </div>

        <div class="p-3 rounded-xl bg-white/[0.02] border border-white/5">
          <div class="flex items-center gap-2 text-sm font-semibold text-white mb-2">
            <Icon icon="mdi:laptop" class="size-5 text-accent/70" /> PC / Desktop
          </div>
          <div class="space-y-2">
            <div>
              <span class="font-semibold text-white">Calibre</span>
              <p class="text-xs text-base-content/60">I don't personally use epub readers on my pc but Calibre has worked best from my tests.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</dialog>

<style>
  .crt-title {
    font-weight: 800;
    background: linear-gradient(135deg, #ff3a1a 0%, #ff8c3a 20%, #ffd644 40%, #ff3a7a 60%, #c820e0 80%, #ff3a1a 100%);
    background-size: 250% 100%;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    animation: aurora-flow 12s linear infinite alternate;
    filter: drop-shadow(0 0 8px rgba(255, 58, 26, 0.3)) drop-shadow(0 0 20px rgba(255, 58, 122, 0.18)) drop-shadow(0 0 40px rgba(200, 32, 224, 0.08));
  }

  @keyframes aurora-flow {
    0% { background-position: 0% 50%; }
    100% { background-position: 100% 50%; }
  }
</style>
