<script lang="ts">
  import { onMount } from "svelte";
  import { fly } from "svelte/transition";
  import Icon from "@iconify/svelte";
  import coverGsgw from "$lib/assets/web-gsgw-cover.webp";
  import coverDebut from "$lib/assets/debut.webp";

  interface Part {
    id: string;
    label: string;
    range?: string;
    status?: string;
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
    cover: string;
    variants: Variant[];
  }

  const variantDefs: { id: string; label: string; badge?: string; description: string }[] = [
    {
      id: "styled",
      label: "Styled",
      badge: "Recommended",
      description:
        "Full window styling with images in their original format. Best for modern e-readers.",
    },
    {
      id: "legacy",
      label: "Legacy",
      description:
        "Plain-text windows and JPEG images for maximum compatibility with older or limited e-readers that struggle with heavy CSS.",
    },
  ];

  const gsgwParts: Part[] = [
    { id: "part1", label: "Part 1", range: "Chapters 0–208", status: "Formatted" },
    { id: "part2", label: "Part 2", range: "Chapters 209–371", status: "Formatted" },
    { id: "part3", label: "Part 3", range: "Chapter 372 – Current", status: "Ongoing" },
    { id: "complete", label: "Complete", range: "All 408 chapters", status: "Ongoing" },
  ];

  const debutParts: Part[] = [
    { id: "part1", label: "Part 1", range: "Chapters 1–147", status: "Formatted" },
    { id: "part2", label: "Part 2", range: "Chapters 148–364", status: "Formatted" },
    { id: "part3", label: "Part 3", range: "Chapters 365–451", status: "WIP" },
    { id: "part4", label: "Part 4", range: "Chapters 452–644", status: "Unformatted" },
    { id: "complete", label: "Complete", range: "All 644 chapters", status: "Semi Formatted" },
  ];

  function buildVariants(parts: Part[]): Variant[] {
    return variantDefs.map((v) => ({ id: v.id, label: v.label, description: v.description, parts }));
  }

  const defaultStories: Story[] = [
    {
      id: "gsgw",
      title: "Got Dropped into a Ghost Story, Still Gotta Work",
      short: "GSGW",
      badgeClass: "badge-primary",
      cover: coverGsgw,
      variants: buildVariants(gsgwParts),
    },
    {
      id: "debut",
      title: "Debut or Die",
      short: "DoD",
      badgeClass: "badge-secondary",
      cover: coverDebut,
      variants: buildVariants(debutParts),
    },
  ];

  let stories = $state<Story[]>(defaultStories);
  let selectedStory = $state("gsgw");
  let selectedVariant = $state("styled");
  let selectedPart = $state("part1");
  let downloadUrl = $state("");
  let epubName = $state("");
  let releaseDate = $state("");
  let downloading = $state(false);
  let storyAssets = $state<Record<string, { url: string; name: string; count: number; size?: number }>>({});

  function formatFileSize(bytes?: number) {
    if (!bytes || !Number.isFinite(bytes) || bytes < 0) return "67 MB";
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  function releaseFilename(storyTitle: string, variantLabel: string, partId: string) {
    const edition = partId === "complete" ? "Complete" : `Part ${partId.replace("part", "")}`;
    return (
      `${storyTitle} - ${edition} [${variantLabel}]`.replace(/[[\],]/g, "").replace(/ /g, ".").replace(/\.+/g, ".") + ".epub"
    );
  }

  function makeAssetUrl(tag: string, storyTitle: string, variantLabel: string, partId: string) {
    const name = releaseFilename(storyTitle, variantLabel, partId);
    return { url: `https://github.com/EnderOksam/GSGW-Reader/releases/download/${tag}/${name}`, name };
  }

  function updateDownload() {
    const key = `${selectedStory}/${selectedVariant}/${selectedPart}`;
    const asset = storyAssets[key];
    downloadUrl = asset?.url || "";
    epubName = asset?.name || "";
  }

  function statusClass(status?: string) {
    if (status === "Formatted") return "text-green-300";
    if (status === "Ongoing") return "text-yellow-300";
    if (status === "Semi Formatted") return "text-amber-300";
    if (status === "Unformatted" || status === "WIP") return "text-orange-300";
    return "text-base-content/40";
  }

  onMount(async () => {
    try {
      const res = await fetch("https://api.github.com/repos/EnderOksam/GSGW-Reader/releases");
      if (!res.ok) throw new Error("API error");
      const releases = await res.json();
      if (!releases.length) throw new Error("No releases");

      const tag = releases[0].tag_name;
      releaseDate = releases[0].published_at?.slice(0, 10) || "";

      const assets: Record<string, { url: string; name: string; count: number; size?: number }> = {};

      for (const def of defaultStories) {
        for (const v of def.variants) {
          for (const p of v.parts) {
            const targetName = releaseFilename(def.title, v.label, p.id);
            const releaseAsset = releases[0].assets?.find((a: any) => a.name === targetName);
            if (releaseAsset) {
              assets[`${def.id}/${v.id}/${p.id}`] = {
                url: releaseAsset.browser_download_url,
                name: releaseAsset.name,
                count: releaseAsset.download_count || 0,
                size: releaseAsset.size,
              };
            } else {
              const a = makeAssetUrl(tag, def.title, v.label, p.id);
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
            const a = makeAssetUrl("latest", def.title, v.label, p.id);
            storyAssets[`${def.id}/${v.id}/${p.id}`] = { url: a.url, name: a.name, count: 0 };
          }
        }
      }
      stories = defaultStories;
      selectedStory = "gsgw";
      selectedVariant = "styled";
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
  const currentDownloadSize = $derived(formatFileSize(currentAsset?.size));
</script>

<div class="relative min-h-dvh overflow-x-hidden">
  <div class="relative flex flex-col items-center justify-center min-h-dvh p-4 md:p-8">
    <div class="max-w-4xl w-full">
      <div
        in:fly={{ y: 20, duration: 400 }}
        class="relative overflow-hidden rounded-2xl bg-[#0d0d0d]/80 border border-primary/15 shadow-2xl"
      >
        <div class="relative p-6 md:p-10 space-y-8">
          <header class="text-center relative z-10">
            <h1 class="crt-title text-4xl md:text-6xl font-black mb-3 tracking-tight">
              Epub Downloads
            </h1>
            <p class="text-base-content/50 max-w-lg mx-auto text-sm md:text-base leading-relaxed">
              Download the complete fan translation for offline reading on your e-reader, tablet, or phone. updated automatically every two weeks
            </p>
          </header>

          <div class="space-y-2.5">
            <div class="grid grid-cols-2 gap-3">
              {#each stories as story}
                {@const bookActive = selectedStory === story.id}
                <button
                  onclick={() => selectStory(story.id)}
                  class="group relative flex flex-col items-center justify-center gap-1 overflow-hidden rounded-2xl border px-4 py-3.5 text-center transition-all duration-300
                    {bookActive
                      ? 'border-primary/30 bg-primary/10 ring-1 ring-primary/20'
                      : 'border-white/[0.06] bg-white/[0.015] hover:border-white/10 hover:bg-white/[0.03]'}"
                >
                  <span class="text-sm font-black {bookActive ? 'text-white' : 'text-base-content/60 group-hover:text-base-content/90'}">{story.short}</span>
                  <span class="hidden text-[11px] leading-tight opacity-45 line-clamp-2 sm:block">{story.title}</span>
                  {#if bookActive}
                    <Icon icon="mdi:check-circle" class="absolute right-2 top-2 size-4 text-primary" />
                  {/if}
                </button>
              {/each}
            </div>
          </div>

          {#if currentStory}
            <div class="grid gap-6 md:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)] md:items-start">
              <div class="space-y-2">
                {#each currentVariant?.parts ?? [] as part}
                  {@const isComplete = part.id === "complete"}
                  {@const active = selectedPart === part.id}
                  <button
                    onclick={() => selectPart(part.id)}
                    class="group relative flex w-full items-center gap-3.5 rounded-2xl px-4 py-3.5 text-left transition-all duration-300
                      {active
                        ? 'text-white'
                        : isComplete
                          ? 'border border-accent/15 bg-accent/[0.03] text-base-content/60 hover:bg-accent/[0.06] hover:text-base-content/90'
                          : 'border border-white/[0.05] bg-white/[0.015] text-base-content/60 hover:border-white/10 hover:bg-white/[0.03] hover:text-base-content/90'}"
                  >
                    {#if active}
                      <div class="absolute inset-0 rounded-2xl border shadow-inner shadow-white/5 {isComplete ? 'border-accent/30 bg-linear-to-br from-accent/25 via-accent/10 to-transparent' : 'border-primary/30 bg-linear-to-br from-primary/25 via-primary/10 to-transparent'}"></div>
                    {/if}

                    <span
                      class="relative z-10 flex size-10 shrink-0 items-center justify-center rounded-xl font-mono text-xs font-bold transition-colors duration-300
                        {active
                          ? isComplete
                            ? 'bg-accent/20 text-accent'
                            : 'bg-primary/20 text-primary'
                          : 'bg-white/5 text-base-content/40 group-hover:text-base-content/70'}"
                    >
                      {#if isComplete}
                        <Icon icon="mdi:bookshelf" class="size-5" />
                      {:else}
                        {part.id.replace("part", "").padStart(2, "0")}
                      {/if}
                    </span>

                    <span class="relative z-10 min-w-0 flex-1">
                      <span class="flex items-center gap-2">
                        <span class="text-sm font-bold">{part.label}</span>
                        {#if isComplete}
                          <span class="rounded-md border border-accent/20 bg-accent/10 px-1.5 py-0.5 text-[10px] font-mono font-medium text-accent">Single file</span>
                        {/if}
                      </span>
                      {#if part.range}
                        <span class="mt-0.5 block truncate text-[11px] opacity-50">{part.range}</span>
                      {/if}
                    </span>

                    {#if part.status}
                      <span class="relative z-10 inline-flex shrink-0 items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider {statusClass(part.status)}">
                        <span class="size-1.5 rounded-full bg-current"></span>
                        <span class="hidden sm:inline">{part.status}</span>
                      </span>
                    {/if}

                    <span class="relative z-10 shrink-0 transition-opacity duration-300 {active ? 'opacity-100' : 'opacity-0 group-hover:opacity-40'}">
                      <Icon icon="mdi:check-circle" class="size-5 {isComplete ? 'text-accent' : 'text-primary'}" />
                    </span>
                  </button>
                {/each}
              </div>

              <div class="space-y-2.5">
                <div class="flex justify-center">
                  <div class="flex w-full rounded-2xl border border-white/10 bg-white/5 p-1 shadow-inner shadow-black/20">
                    {#each currentStory.variants as v}
                      <button
                        onclick={() => selectVariant(v.id)}
                        class="relative flex flex-1 items-center justify-center gap-2 rounded-xl px-3 py-2.5 text-sm font-bold transition-all duration-300
                          {selectedVariant === v.id ? 'text-white' : 'text-base-content/40 hover:text-base-content/70'}"
                      >
                        {#if selectedVariant === v.id}
                          <div class="absolute inset-0 rounded-xl bg-linear-to-br from-primary/25 to-primary/10 border border-primary/25 shadow-inner shadow-white/5"></div>
                        {/if}
                        <span class="relative z-10">{v.label}</span>
                        {#if variantDefs.find((d) => d.id === v.id)?.badge}
                          <span class="relative z-10 hidden text-[10px] font-mono font-medium px-1.5 py-0.5 rounded-md text-green-300 bg-green-500/10 border border-green-500/20 lg:inline">
                            {variantDefs.find((d) => d.id === v.id)?.badge}
                          </span>
                        {/if}
                      </button>
                    {/each}
                  </div>
                </div>
                <p class="text-center text-xs text-base-content/50 leading-relaxed">
                  {currentVariant?.description}
                </p>
                <div
                  class="mx-auto w-full max-w-sm rounded-xl border border-white/[0.07] bg-white/[0.02] p-3 sm:p-4"
                  aria-label={selectedStory === "debut" ? "Debut system window preview" : "Wiki window preview"}
                >
                  {#if selectedStory === "debut"}
                    {#if selectedVariant === "legacy"}
                      <div class="debut-preview-plaintext">
                        <p><strong>[Name: Park Moondae (Ryu Gunwoo)]</strong></p>
                        <p><strong>Level: 0</strong></p>
                        <p><strong>Title: None</strong></p>
                        <p><strong>Vocal: C</strong></p>
                        <p><strong>Dance: -</strong></p>
                        <p><strong>Visual: C</strong></p>
                        <p><strong>Talent: -</strong></p>
                        <p><strong>Characteristics: Infinite potential</strong></p>
                      </div>
                    {:else}
                      <div class="debut-preview-window">
                        <div class="debut-preview-title">[Name: Park Moondae (Ryu Gunwoo)]</div>
                        <div class="debut-preview-body">
                          <p>Level: 0</p>
                          <p>Title: None</p>
                          <p>Vocal: C</p>
                          <p>Dance: -</p>
                          <p>Visual: C</p>
                          <p>Talent: -</p>
                          <p>Characteristics: Infinite potential</p>
                        </div>
                      </div>
                    {/if}
                  {:else if selectedVariant === "legacy"}
                    <div class="wiki-preview-plaintext">
                      <p class="wiki-preview-rule">======================</p>
                      <p class="wiki-preview-meta">Darkness Exploration Records</p>
                      <p>[Memorial Popsocket]</p>
                      <p>: C-Class item featured in &lt;Darkness Exploration Records&gt;.</p>
                      <p>When attached to a smartphone, it renders the text you remember into a clear, organized page for easy viewing.</p>
                      <p>A standard issue item for ninth-level employees at the Supernatural Disaster Management Bureau under the Ministry of Environment.</p>
                      <p class="wiki-preview-rule">======================</p>
                    </div>
                  {:else}
                    <div class="wiki-preview-default">
                      <div class="wiki-preview-titlebar">— ▢ ×</div>
                      <div class="wiki-preview-body">
                        <p class="wiki-preview-meta">Darkness Exploration Records</p>
                        <p>[Memorial Popsocket]</p>
                        <p>: C-Class item featured in &lt;Darkness Exploration Records&gt;.</p>
                        <p>When attached to a smartphone, it renders the text you remember into a clear, organized page for easy viewing.</p>
                        <p>A standard issue item for ninth-level employees at the Supernatural Disaster Management Bureau under the Ministry of Environment.</p>
                      </div>
                    </div>
                  {/if}
                </div>
                <div class="flex justify-center">
                  <button
                    onclick={openRecommended}
                    class="inline-flex items-center gap-1.5 text-xs font-semibold text-accent/80 underline decoration-accent/40 underline-offset-4 transition-colors hover:text-accent hover:decoration-accent"
                  >
                    <Icon icon="mdi:book-open-outline" class="size-4" />
                    Recommended EPUB readers
                  </button>
                </div>
              </div>
            </div>
          {/if}

          <hr class="border-white/[0.06]" />

          <div class="space-y-6">
            <div class="flex flex-col md:flex-row gap-6 md:gap-10 items-center">
              {#if currentStory}
                <img
                  src={currentStory.cover}
                  alt="{currentStory.title} cover"
                  class="w-28 md:w-36 rounded-xl shadow-2xl ring-1 ring-white/10 shrink-0 object-cover"
                />
              {/if}

              <div class="flex-1 space-y-4 min-w-0 text-center md:text-left">
                <div class="flex items-center justify-center md:justify-start gap-3 flex-wrap">
                  <span class="badge badge-ghost font-mono text-xs tracking-wider px-3 py-2 bg-white/5">
                    {currentVariant?.label || ''}
                  </span>
                  {#if currentPart?.status}
                    <span class="badge badge-outline font-mono text-xs font-semibold tracking-wider px-3 py-2 {statusClass(currentPart.status)} border-white/15 bg-white/5">
                      {currentPart.status}
                    </span>
                  {/if}
                </div>

                <div>
                  <h2 class="text-2xl md:text-3xl font-bold text-white leading-tight">
                    {currentStory?.title ?? ''} - {currentPart?.id === 'complete' ? 'Complete' : currentPart?.label ?? ''}
                  </h2>
                  {#if currentPart?.range}
                    <p class="text-xs font-mono opacity-40 uppercase tracking-widest mt-1">{currentPart.range}</p>
                  {/if}
                </div>

                <div class="flex items-center justify-center md:justify-start gap-4 flex-wrap">
                  <span class="inline-flex items-center gap-1.5 text-xs font-mono text-base-content/40">
                    <Icon icon="mdi:translate" class="size-3.5" />
                    Fan Translation
                  </span>
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

              <div class="w-full md:w-72 shrink-0 space-y-3">
                <button
                  onclick={handleDownload}
                  disabled={downloading || !downloadUrl}
                  class="btn h-auto w-full py-5 px-6 border-none bg-linear-to-br from-primary via-primary/90 to-primary/80 text-white hover:brightness-110 hover:scale-[1.02] active:scale-[0.98] shadow-xl shadow-primary/25 hover:shadow-2xl hover:shadow-primary/30 flex items-center justify-between group/btn text-base rounded-2xl transition-all duration-300"
                >
                  <div class="text-left">
                    <div class="font-bold flex items-center gap-2 text-lg">
                      {downloading ? "Downloading…" : "Download EPUB"}
                      <Icon icon="mdi:star-four-points" class="size-4 text-yellow-300" />
                    </div>
                    <div class="text-xs opacity-70 font-normal mt-0.5">
                      {currentVariant?.label || ''} • {currentPart?.id === 'complete' ? 'Single file' : currentPart?.label || 'Full story'} • {currentDownloadSize}
                    </div>
                  </div>
                  <Icon icon="mdi:download" class="size-7 opacity-60 group-hover/btn:translate-y-0.5 transition-transform duration-300" />
                </button>

              </div>
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
              <span class="font-semibold text-white">Apple Books</span>
              <p class="text-xs text-base-content/60">Works well. Dark Mode has minor issues that we've fixed to the best of our ability, but overall, it's a solid choice.</p>
            </div>
            <div>
              <span class="font-semibold text-white">Suwatte</span>
              <p class="text-xs text-base-content/60">Lei really likes this one. It’s an iOS reader for manga, comics, and novels, with EPUB/PDF support. Available on the App Store in the US and Canada, or worldwide via TestFlight. For access, visit https://www.suwatte.app/</p>
            </div>
            <div>
              <span class="font-semibold text-white">PocketBook / BookFusion</span>
              <p class="text-xs text-base-content/60">PocketBook has been recommended by Lei and Destiny on Discord, while BookFusion is considered the better option overall, though the free version is limited to a maximum of 10 books.</p>
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
  .wiki-preview-default {
    overflow: hidden;
    border: 1px solid rgba(160, 150, 190, 0.18);
    border-radius: 7px;
    background: linear-gradient(145deg, #17151d, #201e27);
    color: #c3bfd0;
    font-size: 12px;
    line-height: 1.5;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
  }

  .wiki-preview-titlebar {
    margin-bottom: 7px;
    border-bottom: 1px solid rgba(160, 150, 190, 0.16);
    background: rgba(255, 255, 255, 0.035);
    padding: 3px 7px;
    color: #e8e5ef;
    text-align: right;
    font-family: ui-monospace, monospace;
    letter-spacing: 0.08em;
  }

  .wiki-preview-body {
    padding: 0 7px 6px;
  }

  .wiki-preview-body p,
  .wiki-preview-plaintext p {
    margin: 0;
  }

  .wiki-preview-body p + p,
  .wiki-preview-plaintext p + p {
    margin-top: 0.65em;
  }

  .wiki-preview-meta {
    margin-bottom: 4px !important;
    color: #9d9ab0;
    font-size: 10px;
    letter-spacing: 0.035em;
    text-align: right;
  }

  .wiki-preview-plaintext {
    color: currentColor;
    font-size: 11px;
    line-height: 1.5;
    overflow-wrap: anywhere;
  }

  .wiki-preview-plaintext .wiki-preview-rule {
    color: currentColor;
    font-family: ui-monospace, monospace;
    font-size: 10px;
    letter-spacing: -0.04em;
    opacity: 0.55;
    white-space: nowrap;
  }

  .wiki-preview-plaintext .wiki-preview-meta {
    margin: 4px 0 !important;
    color: inherit;
    font-size: 10px;
    opacity: 0.6;
    text-align: right;
  }

  .debut-preview-window {
    position: relative;
    width: 100%;
    margin: 1rem auto;
    border: 2px solid rgba(255, 255, 255, 0.85);
    background: #28272d;
    padding: 1.5rem 1rem 1rem;
    color: #f2f2f2;
    text-align: center;
    box-shadow: 0 0 10px rgba(255, 255, 255, 0.3), inset 0 0 20px rgba(255, 255, 255, 0.07);
  }

  .debut-preview-window::before {
    position: absolute;
    inset: 6px;
    border: 1px solid rgba(255, 255, 255, 0.45);
    content: "";
    pointer-events: none;
  }

  .debut-preview-title {
    position: absolute;
    top: -0.55rem;
    left: 50%;
    max-width: calc(100% - 1rem);
    transform: translateX(-50%);
    overflow: hidden;
    border: 1px solid rgba(255, 255, 255, 0.8);
    background: #28272d;
    padding: 0.05rem 0.55rem;
    color: #f2f2f2;
    font-size: 8px;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-overflow: ellipsis;
    text-transform: uppercase;
    white-space: nowrap;
  }

  .debut-preview-body {
    font-size: 11px;
    line-height: 1.45;
  }

  .debut-preview-body p {
    margin: 0.55em 0;
    color: inherit;
  }

  .debut-preview-body p:last-child {
    margin-bottom: 0.25em;
  }

  .debut-preview-plaintext {
    font-size: 11px;
    font-weight: 700;
    line-height: 1.5;
    overflow-wrap: anywhere;
  }

  .debut-preview-plaintext p {
    margin: 0.45em 0;
  }

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
