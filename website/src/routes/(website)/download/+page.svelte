<script lang="ts">
  import { onMount } from "svelte";
  import { fade, fly } from "svelte/transition";
  import Icon from "@iconify/svelte";

  const releaseApiUrl = "https://api.github.com/repos/EnderOksam/GSGW-Reader/releases/tags/latest";

  interface Part {
    id: string;
    label: string;
    range: string;
    assetMatch: (name: string) => boolean;
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
    supportedVariants: string[];
    variants: Variant[];
  }

  const allVariantDefs: { id: string; label: string; badge: string; description: string }[] = [
    { id: "windows", label: "Windows", badge: "experimental", description: "Experimental — uses a html-to-image library to render windows inside the EPUB just as they appear on the website." },
    { id: "plaintext", label: "Plain Text", badge: "css", description: "All formatting is done through text — the best attempt to use CSS to make it look like the website." },
  ];

  const gsgwVariant = (v: string, p: string) => (n: string) => n.startsWith(`Ghost.Story - Part ${p} [${v}]`);
  const debutVariant = (p: string) => (n: string) => n.startsWith(`Debut.or.Die - Part ${p} [Windows]`);

  const stories: Story[] = [
    {
      id: "gsgw",
      title: "Got Dropped into a Ghost Story, Still Gotta Work",
      short: "GSGW",
      badgeClass: "badge-primary",
      supportedVariants: ["windows", "plaintext"],
      variants: [
        {
          id: "windows",
          label: "Windows",
          description: "Experimental — uses a html-to-image library to render windows inside the EPUB just as they appear on the website.",
          parts: [
            { id: "part1", label: "Part 1", range: "Chapters 0–208", assetMatch: gsgwVariant("Windows", "1") },
            { id: "part2", label: "Part 2", range: "Chapters 209–371", assetMatch: gsgwVariant("Windows", "2") },
            { id: "part3", label: "Part 3", range: "Chapter 372 – Current", assetMatch: gsgwVariant("Windows", "3") },
          ],
        },
        {
          id: "plaintext",
          label: "Plain Text",
          description: "All formatting is done through text — the best attempt to use CSS to make it look like the website.",
          parts: [
            { id: "part1", label: "Part 1", range: "Chapters 0–208", assetMatch: gsgwVariant("PlainText", "1") },
            { id: "part2", label: "Part 2", range: "Chapters 209–371", assetMatch: gsgwVariant("PlainText", "2") },
            { id: "part3", label: "Part 3", range: "Chapter 372 – Current", assetMatch: gsgwVariant("PlainText", "3") },
          ],
        },
      ],
    },
    {
      id: "debut",
      title: "Debut or Die",
      short: "Debut",
      badgeClass: "badge-secondary",
      supportedVariants: ["windows"],
      variants: [
        {
          id: "windows",
          label: "Windows",
          description: "Experimental — uses a html-to-image library to render windows inside the EPUB just as they appear on the website.",
          parts: [
            { id: "part1", label: "Part 1", range: "Chapters 1–147", assetMatch: debutVariant("1") },
            { id: "part2", label: "Part 2", range: "Chapters 148–364", assetMatch: debutVariant("2") },
            { id: "part3", label: "Part 3", range: "Chapters 365–451", assetMatch: debutVariant("3") },
            { id: "part4", label: "Part 4", range: "Chapters 452–644", assetMatch: debutVariant("4") },
          ],
        },
      ],
    },
  ];

  let selectedStory = $state("gsgw");
  let selectedVariant = $state("windows");
  let selectedPart = $state("part1");
  let downloadUrl = $state("");
  let epubName = $state("");
  let releaseDate = $state("");
  let downloading = $state(false);
  let storyAssets = $state<Record<string, { url: string; name: string; count: number }>>({});

  onMount(async () => {
    try {
      const res = await fetch(releaseApiUrl);
      if (!res.ok) return;
      const data = await res.json();
      releaseDate = data.published_at?.slice(0, 10) || "";

      const assets: Record<string, { url: string; name: string; count: number }> = {};
      for (const story of stories) {
        for (const variant of story.variants) {
          for (const part of variant.parts) {
            const key = `${story.id}/${variant.id}/${part.id}`;
            const asset = (data.assets || []).find((a: any) => part.assetMatch(a.name));
            if (asset) assets[key] = { url: asset.browser_download_url, name: asset.name, count: asset.download_count || 0 };
          }
        }
      }
      storyAssets = assets;
      updateDownload();
    } catch {}
  });

  function updateDownload() {
    const key = `${selectedStory}/${selectedVariant}/${selectedPart}`;
    const asset = storyAssets[key];
    downloadUrl = asset?.url || "";
    epubName = asset?.name || "";
  }

  function selectStory(id: string) {
    selectedStory = id;
    const story = stories.find((s) => s.id === id);
    if (story) {
      if (!story.supportedVariants.includes(selectedVariant)) {
        selectedVariant = story.supportedVariants[0];
      }
      const variant = story.variants.find((v) => v.id === selectedVariant);
      if (variant) selectedPart = variant.parts[0].id;
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
  const partAvailable = $derived(!!currentAsset);
  const currentDownloadCount = $derived(currentAsset?.count ?? 0);
</script>

<div class="relative min-h-dvh overflow-hidden">
  
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
              {#each allVariantDefs as def}
                {@const supported = currentStory.supportedVariants.includes(def.id)}
                <button
                  onclick={() => supported && selectVariant(def.id)}
                  disabled={!supported}
                  class="relative flex items-center gap-2.5 px-4 py-2 rounded-xl text-sm font-bold transition-all duration-300
                    {selectedVariant === def.id && supported
                      ? 'text-white shadow-lg shadow-primary/15'
                      : 'text-base-content/50 hover:text-base-content/70 border border-white/5 hover:border-white/10 bg-white/[0.02]'}"
                >
                  {#if selectedVariant === def.id && supported}
                    <div class="absolute inset-0 rounded-xl bg-linear-to-br from-primary/25 to-primary/10 border border-primary/30 shadow-inner shadow-white/5"></div>
                  {/if}
                  <span class="relative z-10 {!supported ? 'line-through opacity-50' : ''}">{def.label}</span>
                  <span class="relative z-10 text-[10px] font-mono font-medium px-1.5 py-0.5 rounded-md {def.id === 'windows' ? 'text-purple-300 bg-purple-500/10 border border-purple-500/20' : 'text-green-300 bg-green-500/10 border border-green-500/20'}">{def.badge}</span>
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
                {#each allVariantDefs as def}
                  {@const variant = currentStory.variants.find((v) => v.id === def.id)}
                  <div class="text-sm leading-relaxed pl-3 border-l-2 {variant ? (def.id === 'windows' ? 'border-purple-500/40' : 'border-green-500/40') : 'border-white/5'} {!variant ? 'opacity-25' : ''}">
                    <span class="font-semibold {variant ? 'text-white/80' : 'text-white/40'}">{def.label}</span>
                    <span class="{variant ? 'text-base-content/50' : 'text-base-content/30'}"> — {variant?.description || def.description}</span>
                  </div>
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
                <span class="badge {currentStory.badgeClass} badge-outline font-mono text-xs font-bold tracking-widest px-3 py-2">EPUB</span>
                <span class="badge badge-ghost font-mono text-xs tracking-wider px-3 py-2 bg-white/5">
                  {currentVariant?.label || ''}
                </span>
                {#if !partAvailable}
                  <span class="badge badge-ghost font-mono text-xs tracking-wider px-3 py-2 bg-white/5 border border-dashed border-white/10">Coming Soon</span>
                {/if}
              </div>

              <div>
                <h2 class="text-2xl md:text-3xl font-bold text-white leading-tight">{currentStory.title}</h2>
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
                    {downloading
                      ? "Downloading…"
                      : partAvailable
                        ? "Download EPUB"
                        : "Unavailable"}
                    <Icon icon="mdi:star-four-points" class="size-4 text-yellow-300" />
                  </div>
                  <div class="text-xs opacity-70 font-normal mt-0.5">
                    {currentPart?.label || "Full Story"} • Modern Format
                  </div>
                </div>
                <Icon icon="mdi:download" class="size-7 opacity-60 group-hover/btn:translate-y-0.5 transition-transform duration-300" />
              </button>
              <button onclick={openRecommended} class="btn h-auto py-4 px-6 border border-white/10 bg-white/[0.03] text-base-content/70 hover:text-white hover:bg-white/10 hover:border-white/20 flex items-center justify-between group/btn text-sm rounded-2xl transition-all duration-300">
                <div class="text-left">
                  <div class="font-semibold flex items-center gap-2">
                    Recommended Readers
                  </div>
                  <div class="text-[11px] opacity-50 font-normal mt-0.5">
                    Best apps for any device
                  </div>
                </div>
                <Icon icon="mdi:book-open-outline" class="size-5 opacity-50 group-hover/btn:scale-110 transition-transform duration-300" />
              </button>
            </div>
          </div>
        </div>
      </div>

    </div>
  </div>
</div>

<dialog bind:this={recommendModal} class="modal backdrop:!bg-black/60 backdrop:!backdrop-blur-sm">
  <div class="modal-box max-w-md bg-base-200/95 border border-white/10 p-0 overflow-hidden rounded-2xl shadow-2xl">
    <div class="p-6 border-b border-white/5 flex items-center justify-between">
      <div>
        <h3 class="text-lg font-bold text-white">Recommended Readers</h3>
        <p class="text-xs text-base-content/50 mt-0.5">Best apps for EPUB reading on any device</p>
      </div>
      <button onclick={() => recommendModal?.close()} class="btn btn-ghost btn-xs btn-circle text-base-content/50 hover:text-white">
        <Icon icon="mdi:close" class="size-4" />
      </button>
    </div>
    <div class="p-6 space-y-3">
      {#each [
        { name: "Google Play Books", desc: "Cross-platform, syncs progress, great for Android & web.", icon: "mdi:google-play" },
        { name: "Apple Books", desc: "Built into iOS/macOS, clean interface with iCloud sync.", icon: "mdi:apple" },
        { name: "FBReader", desc: "Lightweight, customizable, supports many formats.", icon: "mdi:book-open-variant" },
        { name: "Calibre", desc: "Desktop power-user tool for managing & converting libraries.", icon: "mdi:desktop-classic" },
        { name: "Lithium", desc: "Minimalist Android reader with a focus on typography.", icon: "mdi:book-open-blank-variant" },
      ] as reader}
        <div class="flex items-center gap-4 p-3 rounded-xl bg-white/[0.02] border border-white/5 hover:bg-white/5 transition-colors">
          <div class="size-9 rounded-lg bg-linear-to-br from-primary/20 to-accent/20 flex items-center justify-center shrink-0">
            <Icon icon={reader.icon} class="size-4 text-primary" />
          </div>
          <div class="flex-1 min-w-0">
            <div class="text-sm font-semibold text-white">{reader.name}</div>
            <div class="text-xs text-base-content/50 truncate">{reader.desc}</div>
          </div>
        </div>
      {/each}
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