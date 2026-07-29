<script lang="ts">
  import { page } from "$app/state";
  import { onMount } from "svelte";
  import { dev } from "$app/environment";
  import Icon from "@iconify/svelte";
  import imgGsgwCover from "$lib/assets/web-gsgw-cover.webp";
  import imgtempCover from "$lib/assets/web-coi-cover.jpg";
  import imgManwhaCover from "$lib/assets/webtoon-cover.webp";
  import imgDebutCover from "$lib/assets/debut.webp";
  import imgDebutBanner from "$lib/assets/debut-banner.png";
  import book_meta from "$lib/meta.json";
  import { searchChapterContent, renderSnippet, storeSnippetTarget } from "$lib/content-search";
  import type { Chapter, ContentMatch } from "$lib/content-search";

  interface BookConfig {
    title: string;
    author: string;
    synopsis: string;
    title_accent: string;
    accent_color: string;
    button_primary: string;
    button_secondary: string;
    cover: string;
    external_link: string;
  }

  interface ReadingHistory {
    book: string;
    tl: string;
    slug: string | number;
  }

  interface BookMetadata {
    [bookKey: string]: {
      [translationKey: string]: Chapter[];
    };
  }

  const bookConfigs: Record<string, BookConfig> = {
    gsgw: {
      title: "Got Dropped into a Ghost Story, Still Gotta Work",
      author: "Baek Deoksoo",
      synopsis: [
        "A pop-up event for some 'modern fantasy' media… I loved so much that I even took a precious day off work to attend.",
        "On that day, I ended up transmigrating as a character in that very fantasy world.",
        "As none other than a newly hired employee at a famous large corporation!",
        "A dream job with great benefits, an excellent salary, and even kind and competent bosses.",
        "I'm using the information I know about the world to rise through the ranks at lightning speed!",
        "Am I happy, you ask?",
        "Please, just let me go home. I'm begging you.",
      ].join("\n\n"),
      title_accent: "text-default",
      accent_color: "accent",
      button_primary: "btn-accent",
      button_secondary: "btn-info",
      cover: imgGsgwCover,
      external_link: "https://page.kakao.com/content/65171279",
    },
    temp: {
      title: "Unofficial Dark Exploration Records",
      author: "Fanatics",
      synopsis: "A collection of fan-created records exploring the darkness that lies beyond.",
      title_accent: "text-primary",
      accent_color: "primary",
      button_primary: "btn-secondary",
      button_secondary: "btn-primary",
      cover: imgtempCover,
      external_link: "",
    },
    debut: {
      title: "Debut Or Die",
      author: "Baek Deoksoo",
      synopsis: [
        "A student who had been preparing for the Civil Service examination for 4 years suddenly found himself in an unfamiliar body, 3 years in the past.",
        "Along with it came a status window displaying a threat right before his eyes!",
        "",
        "[Outbreak!]",
        "[Status Abnormality: \u2018Debut or Die\u2019 occurs!]",
        "",
        "A diary about the transformation of the main character, who was suddenly challenged to be an idol even though he had never been in the industry before, due to the sudden threat of death.",
        "",
        "\u203bSpeciality: Before regressing and possessing his new body, he used to collect and sell idol\u2019s data.",
      ].join("\n\n"),
      title_accent: "text-primary",
      accent_color: "secondary",
      button_primary: "btn-secondary",
      button_secondary: "btn-info",
      cover: imgDebutCover,
      external_link: "",
    },
    manwha: {
      title: "Ghost Story, Gotta Work",
      author: "todac_s",
      synopsis: [
        "A pop-up event for some 'modern fantasy' media… I loved so much that I even took a precious day off work to attend.",
        "On that day, I ended up transmigrating as a character in that very fantasy world.",
        "As none other than a newly hired employee at a famous large corporation!",
        "A dream job with great benefits, an excellent salary, and even kind and competent bosses.",
        "I'm using the information I know about the world to rise through the ranks at lightning speed!",
        "Am I happy, you ask?",
        "Please, just let me go home. I'm begging you.",
      ].join("\n\n"),
      title_accent: "text-accent",
      accent_color: "accent",
      button_primary: "btn-accent",
      button_secondary: "btn-primary",
      cover: imgManwhaCover,
      external_link: "https://page.kakao.com/content/69229506",
    },
  };

  const meta = book_meta as BookMetadata;

  const bookSlug = $derived(page.params.book || "gsgw");
  const book = $derived(bookConfigs[bookSlug] || bookConfigs["gsgw"]);
  const isTemp = $derived(bookSlug === "temp");
  const isManwha = $derived(bookSlug === "manwha");
  const embedImage = $derived(bookSlug === "debut" ? imgDebutBanner : book.cover);
  const embedTitle = $derived(bookSlug === "debut" ? "Debut or Die" : book.title);
  const embedDescription = $derived(bookSlug === "debut"
    ? "An aspiring civil servant passes out and awakens three years in the past in the body of a young man.\nBefore he can even assess the situation, he's given a mission: Debut or Die!"
    : "A pop-up event for some 'modern fantasy' media… I loved so much that I even took a precious day off work to attend.\nOn that day, I ended up transmigrating as a character in that very fantasy world.");

  let searchQuery = $state("");
  let selectedTags = $state<string[]>([]);
  let isReversed = $state(false);

  const allTags = ["Daydream Inc.", "Disaster Management Bureau", "Church of the Luminous Unknown", "Exploration Record"];

  const tagColors: Record<string, string> = {
    "Daydream Inc.": "text-red-400 border-red-400/30 bg-red-400/10",
    "Disaster Management Bureau": "text-blue-400 border-blue-400/30 bg-blue-400/10",
    "Church of the Luminous Unknown": "text-yellow-400 border-yellow-400/30 bg-yellow-400/10",
    "Exploration Record": "text-base-content/60 border-base-content/20 bg-base-content/5",
  };

  const tagColorsSolid: Record<string, string> = {
    "Daydream Inc.": "bg-red-500/20 text-red-300 border-red-500/30",
    "Disaster Management Bureau": "bg-blue-500/20 text-blue-300 border-blue-500/30",
    "Church of the Luminous Unknown": "bg-yellow-500/20 text-yellow-300 border-yellow-500/30",
    "Exploration Record": "bg-base-content/10 text-base-content/60 border-base-content/20",
  };

  function toggleTag(tag: string) {
    if (selectedTags.includes(tag)) {
      selectedTags = selectedTags.filter((t) => t !== tag);
    } else {
      selectedTags = [...selectedTags, tag];
    }
  }
  let selectedTL = $state("");

  let isSearchingContent = $state(false);
  let contentMatches = $state<Map<string, ContentMatch>>(new Map());
  let contentSearchAbort: AbortController | null = null;
  let contentSearchTimeout: ReturnType<typeof setTimeout> | null = null;

  $effect(() => {
    const tls = Object.keys(meta[bookSlug] || {});
    if (!selectedTL || !tls.includes(selectedTL)) {
      selectedTL = tls.includes("fantl") ? "fantl" : tls.includes("mtl") ? "mtl" : tls[0] || "";
    }
  });
  let continueData = $state<ReadingHistory | null>(null);

  let synopsisModal: HTMLDialogElement;
  let tlSelectionModal: HTMLDialogElement;

  const availableTLs = $derived(Object.keys(meta[bookSlug] || {}));
  const chapters = $derived(meta[bookSlug]?.[selectedTL] || []);

  const titleSlugMatches = $derived(
    chapters.filter(
      (ch: Chapter) =>
        ch.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        ch.slug.toString().includes(searchQuery),
    ),
  );

  const filteredChapters = $derived(() => {
    const titleSlugSet = new Set(titleSlugMatches.map((c: Chapter) => c.slug.toString()));
    const contentOnly = [...contentMatches.values()]
      .map((m) => m.chapter)
      .filter((c: Chapter) => !titleSlugSet.has(c.slug.toString()));
    const combined = [...titleSlugMatches, ...contentOnly];
    return isReversed ? [...combined].reverse() : combined;
  });

  $effect(() => {
    const q = searchQuery;
    const tls = titleSlugMatches;
    const tl = selectedTL;
    if (contentSearchAbort) contentSearchAbort.abort();
    if (contentSearchTimeout) clearTimeout(contentSearchTimeout);
    contentMatches = new Map();
    isSearchingContent = false;

    if (q.length >= 3 && tls.length < 3 && !isTemp && !isManwha) {
      const timeout = setTimeout(() => {
        contentSearchAbort = new AbortController();
        isSearchingContent = true;
        searchChapterContent(
          q, chapters, titleSlugMatches, bookSlug, tl,
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

  const isContinueChapter = (ch: Chapter) =>
    continueData?.slug === ch.slug && continueData?.tl === selectedTL;

  const records = [
    { title: "TITLE", excerpt: "short description", tags: ["Exploration Record"], img: true },
    { title: "TITLE", excerpt: "short description", tags: ["Exploration Record"], img: true },
    { title: "TITLE", excerpt: "short description", tags: ["Disaster Management Bureau"], img: true },
    { title: "TITLE", excerpt: "short description", tags: ["Exploration Record"], img: true },
    { title: "TITLE", excerpt: "short description", tags: ["Daydream Inc."], img: true },
    { title: "TITLE", excerpt: "short description", tags: ["Church of the Luminous Unknown"], img: true },
    { title: "TITLE", excerpt: "short description", tags: ["Exploration Record"], img: true },
    { title: "TITLE", excerpt: "short description", tags: ["Disaster Management Bureau"], img: true },
  ];

  const filteredRecords = $derived(
    records.filter((r) => {
      const matchesSearch = !searchQuery || r.title.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesTags = selectedTags.length === 0 || selectedTags.some((t) => r.tags.includes(t));
      return matchesSearch && matchesTags;
    }),
  );

  onMount(() => {
    const stored = localStorage.getItem("lastRead");
    if (stored) {
      try {
        const data = JSON.parse(stored);
        if (data.book === bookSlug) {
          continueData = data;
        }
      } catch (e) {
        console.error("Failed to parse reading history", e);
      }
    }
  });

  function handleReadClick(e: MouseEvent) {
    if (continueData) return;
    e.preventDefault();
    tlSelectionModal.showModal();
  }
</script>

<svelte:head>
  <title>{book.title}</title>
  <meta name="description" content={book.synopsis} />
  <meta property="og:type" content="website" />
  <meta property="og:title" content={embedTitle} />
  <meta property="og:description" content={embedDescription} />
  <meta property="og:image" content={embedImage} />
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:title" content={embedTitle} />
  <meta name="twitter:description" content={embedDescription} />
  <meta name="twitter:image" content={embedImage} />
</svelte:head>

<main class="flex flex-col md:flex-row min-h-dvh">
  <!-- Left: Book Info -->
  <aside class="relative md:h-dvh md:w-[35vw] w-full bg-base-200/70 md:sticky md:top-0 flex flex-col items-center border-b md:border-b-0 md:border-r border-base-content/10 overflow-hidden">
    <div class="absolute inset-0 bg-[radial-gradient(ellipse_at_top,var(--color-base-content)/3,transparent_70%)] pointer-events-none"></div>
    <div class="relative w-full flex flex-col items-center p-8 md:p-12">
      <div class="relative group mb-8">
        <div class="absolute -inset-4 rounded-3xl blur-2xl opacity-60 group-hover:opacity-100 transition-opacity duration-700"
          style="background: linear-gradient(135deg, color-mix(in srgb, var(--color-{book.accent_color}) 20%, transparent), transparent)"
        ></div>
        <div class="absolute -inset-2 bg-base-content/5 rounded-3xl opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
        <enhanced:img
          src={book.cover}
          alt="{book.title} cover"
          class="relative w-44 md:w-56 rounded-2xl shadow-2xl ring-1 ring-base-content/10 transition-transform duration-500 group-hover:scale-[1.02]"
        />
      </div>

      <div class="text-center space-y-3 max-w-sm">
        <h1 class="text-xl md:text-2xl font-black leading-tight {book.title_accent}">
          {book.title}
        </h1>
        <p class="text-xs font-bold opacity-50 uppercase tracking-[0.2em]">
          {book.author}
        </p>
      </div>

      <div class="flex items-center gap-4 mt-6 text-xs font-mono opacity-40">
        {#if isTemp}
          <span class="flex items-center gap-1.5">
            <Icon icon="material-symbols:auto-stories" class="size-3.5" />
            {records.length} {records.length === 1 ? "record" : "records"}
          </span>
        {:else}
          <span class="flex items-center gap-1.5">
            <Icon icon="material-symbols:auto-stories" class="size-3.5" />
            {chapters.length} {chapters.length === 1 ? "chapter" : "chapters"}
          </span>
          {#if availableTLs.length > 1}
            <span class="w-px h-3 bg-base-content/20"></span>
            <span class="flex items-center gap-1.5">
              <Icon icon="material-symbols:translate" class="size-3.5" />
              {availableTLs.length} {availableTLs.length === 1 ? "translation" : "translations"}
            </span>
          {/if}
        {/if}
      </div>
    </div>

    <div class="relative w-full px-6 md:px-8 flex gap-2 mb-5">
      {#if isTemp}
        <a
          href="#"
          onclick={(e) => e.preventDefault()}
          class="btn {book.button_primary} grow shadow-lg font-bold gap-2 h-auto min-h-[2.75rem] py-2.5"
        >
          <Icon icon="material-symbols:menu-book-outline-rounded" class="size-5 shrink-0" />
          <span class="flex flex-col items-start leading-tight">
            <span>Read a Record</span>
          </span>
        </a>
        <button
          disabled
          class="btn btn-ghost grow shadow-lg font-bold gap-2 h-auto min-h-[2.75rem] py-2.5 opacity-30 cursor-not-allowed"
        >
          <Icon icon="material-symbols:resume" class="size-5 shrink-0" />
          <span class="flex flex-col items-start leading-tight">
            <span>Continue Reading</span>
          </span>
        </button>
      {:else}
        <a
          href={continueData
            ? `../../read/${continueData.book}/${continueData.tl}/${continueData.slug}`
            : "#"}
          onclick={handleReadClick}
          class="btn {book.button_primary} grow shadow-lg font-bold gap-2 h-auto min-h-[2.75rem] py-2.5"
          data-sveltekit-preload-data
        >
          <Icon icon={continueData ? "material-symbols:resume" : "material-symbols:menu-book-outline-rounded"} class="size-5 shrink-0" />
          <span class="flex flex-col items-start leading-tight">
            <span>{continueData ? "Continue" : "Start Reading"}</span>
            {#if continueData}
              <span class="text-[10px] font-normal opacity-70">Chapter {continueData.slug}</span>
            {/if}
          </span>
        </a>
        {#if book.external_link}
          <a href={book.external_link} target="_blank" rel="noopener noreferrer" class="btn {book.button_secondary} shadow-lg shrink-0 h-auto min-h-[2.75rem] py-2.5 aspect-square" aria-label="Official source">
            <Icon icon="material-symbols:open-in-new" class="size-5" />
          </a>
        {/if}
      {/if}
    </div>

    <div class="relative grow w-full px-6 md:px-8 pb-6 overflow-hidden">
      <div class="hidden md:block h-full">
        <div class="h-full overflow-y-auto pr-2 custom-scrollbar">
          <p class="text-sm leading-relaxed text-center opacity-60 whitespace-pre-line">
            {book.synopsis}
          </p>
        </div>
      </div>

      <button
        class="md:hidden btn btn-ghost btn-sm w-full h-auto py-3.5 bg-base-300/20 hover:bg-base-300/40 rounded-xl"
        onclick={() => synopsisModal.showModal()}
      >
        <p class="line-clamp-2 text-xs italic opacity-50 text-center leading-relaxed">
          {book.synopsis}
        </p>
      </button>
    </div>
  </aside>

  <!-- Modal: Synopsis -->
  <dialog bind:this={synopsisModal} class="modal modal-bottom sm:modal-middle">
    <div class="modal-box bg-base-200 rounded-2xl p-6">
      <form method="dialog"><button class="btn btn-sm btn-circle btn-ghost absolute right-3 top-3">✕</button></form>
      <h3 class="text-lg font-bold mb-4">Synopsis</h3>
      <div class="max-h-[60vh] overflow-y-auto custom-scrollbar pr-1">
        <p class="text-sm leading-relaxed whitespace-pre-line opacity-75 text-center">{book.synopsis}</p>
      </div>
    </div>
    <form method="dialog" class="modal-backdrop"><button>close</button></form>
  </dialog>

  <!-- Modal: TL Selection -->
  <dialog bind:this={tlSelectionModal} class="modal modal-bottom sm:modal-middle">
    <div class="modal-box bg-base-100 rounded-2xl p-6">
      <div class="flex justify-between items-center mb-6">
        <h3 class="font-bold text-lg flex items-center gap-2">
          <Icon icon="material-symbols:translate-rounded" class="size-5" />
          Select Translation
        </h3>
        <form method="dialog"><button class="btn btn-sm btn-circle btn-ghost">✕</button></form>
      </div>
      <div class="flex flex-col gap-3">
        {#if bookSlug === "lotm"}
          <a href="../../read/lotm/goblintl/1" class="btn btn-outline btn-lg justify-between h-auto py-4 group rounded-xl" onclick={() => tlSelectionModal.close()}>
            <div class="text-left">
              <div class="font-bold text-base flex items-center gap-2">
                goblintl <span class="badge badge-primary badge-sm">Recommended</span>
              </div>
              <div class="text-xs opacity-60 font-normal mt-1 flex items-center gap-1">
                <Icon icon="material-symbols:imagesmode-outline" class="size-3" /> With Illustrations & Notes
              </div>
            </div>
            <Icon icon="material-symbols:arrow-forward-rounded" class="size-6 group-hover:translate-x-1 transition-transform" />
          </a>
        {:else}
          {#each availableTLs as tl}
            {@const isRecommended = (bookSlug === "gsgw" && tl === "fantl") || (bookSlug === "manwha" && tl === "flame comics")}
            {@const firstSlug = meta[bookSlug]?.[tl]?.[0]?.slug ?? "1"}
            <a href="../../read/{bookSlug}/{tl}/{firstSlug}" class="btn btn-outline btn-lg justify-between h-auto py-4 group rounded-xl" onclick={() => tlSelectionModal.close()}>
              <div class="text-left">
                <div class="font-bold text-base flex items-center gap-2">
                  {tl.toUpperCase()} {#if isRecommended}<span class="badge badge-primary badge-sm">Recommended</span>{/if}
                </div>
              </div>
              <Icon icon="material-symbols:arrow-forward-rounded" class="size-6 group-hover:translate-x-1 transition-transform" />
            </a>
          {/each}
        {/if}
      </div>
    </div>
    <form method="dialog" class="modal-backdrop"><button>close</button></form>
  </dialog>

  <!-- Right: Record List -->
  <div class="md:w-[65vw] w-full min-h-dvh bg-base-100/50">
    {#if isTemp}
      <div class="p-3 md:p-4">
        <div class="flex items-center gap-2 mb-4">
          <div class="relative grow">
            <Icon icon="material-symbols:search-rounded" class="absolute left-3 top-1/2 -translate-y-1/2 size-4 opacity-30" />
            <input
              type="search"
              bind:value={searchQuery}
              placeholder="Search by name..."
              class="input input-sm input-bordered w-full pl-9 rounded-xl bg-base-200/50 focus:bg-base-200 transition-colors"
            />
          </div>
        </div>
        <div class="flex flex-wrap gap-1.5 mb-4">
          {#each allTags as tag}
            <button
              class="badge badge-sm gap-1 cursor-pointer transition-all border {selectedTags.includes(tag) ? tagColorsSolid[tag] : tagColors[tag]}"
              onclick={() => toggleTag(tag)}
            >
              {#if selectedTags.includes(tag)}
                <Icon icon="material-symbols:close-rounded" class="size-3" />
              {/if}
              {tag}
            </button>
          {/each}
          {#if selectedTags.length > 0}
            <button class="badge badge-sm cursor-pointer transition-all border text-base-content/40 border-base-content/20 hover:text-base-content/70" onclick={() => (selectedTags = [])}>
              Clear
            </button>
          {/if}
        </div>
        <h2 class="text-sm font-bold opacity-60 uppercase tracking-widest mb-4">Records</h2>
        {#if filteredRecords.length > 0}
          <div class="gallery-grid">
            {#each filteredRecords as entry}
            <a
              href="#"
              onclick={(e) => e.preventDefault()}
              class="gallery-card group relative flex flex-col rounded-xl bg-base-200/40 border border-base-content/10 overflow-hidden hover:border-base-content/30 hover:shadow-lg transition-all duration-300"
            >
              <div class="aspect-[16/9] w-full bg-base-300/50 flex items-center justify-center shrink-0">
                <Icon icon="material-symbols:image-outline-rounded" class="size-8 opacity-20" />
              </div>
              <div class="flex flex-col gap-2 p-4 grow">
                <h3 class="text-sm font-bold leading-snug group-hover:text-primary transition-colors">{entry.title}</h3>
                <p class="text-xs opacity-50 leading-relaxed line-clamp-3">{entry.excerpt}</p>
                <div class="flex flex-wrap gap-1.5 mt-auto pt-2">
                  {#each entry.tags as tag}
                    <span class="badge badge-xs border font-mono tracking-wider {tagColorsSolid[tag]}">{tag}</span>
                  {/each}
                </div>
              </div>
            </a>
          {/each}
          </div>
        {:else}
          <div class="flex flex-col items-center justify-center py-28 opacity-25 gap-4">
            <Icon icon="tabler:ghost" class="size-14" />
            <div class="text-center">
              <p class="text-lg font-bold">No records found</p>
              <p class="text-sm opacity-60 mt-1">Try a different tag</p>
            </div>
          </div>
        {/if}
      </div>
    {:else if isManwha}
      <div class="sticky top-0 z-10 bg-base-100/80 backdrop-blur-lg border-b border-base-content/5">
        <div class="flex items-center gap-2 p-3 md:p-4">
          <div class="relative grow">
            <Icon icon="material-symbols:search-rounded" class="absolute left-3 top-1/2 -translate-y-1/2 size-4 opacity-30" />
            <input
              type="search"
              bind:value={searchQuery}
              placeholder="Search chapters..."
              class="input input-sm input-bordered w-full pl-9 rounded-xl bg-base-200/50 focus:bg-base-200 transition-colors"
            />
          </div>

          <div class="flex items-center gap-1.5">
            <button
              class="btn btn-sm btn-square rounded-xl {isReversed ? 'btn-ghost text-accent' : 'bg-base-200/70'}"
              onclick={() => (isReversed = !isReversed)}
              aria-label="Toggle order"
            >
              <Icon
                icon="material-symbols:sort-rounded"
                class="size-5 transition-transform duration-300 {isReversed ? 'rotate-180' : ''}"
              />
            </button>
            <select class="select select-sm select-bordered rounded-xl bg-base-200/50 min-w-[5rem]" bind:value={selectedTL}>
              {#each availableTLs as tl}
                <option value={tl}>{tl.toUpperCase()}</option>
              {/each}
            </select>
          </div>
        </div>
      </div>

      <div class="p-3 md:p-4">
        {#if filteredChapters().length > 0}
          <div class="flex flex-col gap-1">
            {#each filteredChapters() as ch}
              {@const isCurr = isContinueChapter(ch)}
              <a
                href="../../read/{bookSlug}/{selectedTL}/{ch.slug}"
                class="chapter-row group flex items-center gap-4 p-3 rounded-xl bg-base-200/30 border transition-all duration-200 relative overflow-hidden {isCurr ? 'border-accent/20 bg-accent/5 hover:bg-accent/10' : 'border-transparent hover:border-base-content/10 hover:bg-base-200/60'}"
              >
                {#if isCurr}
                  <div class="absolute left-0 top-0 bottom-0 w-0.5 bg-accent rounded-full"></div>
                {/if}
                <div class="relative w-32 h-24 shrink-0 rounded-lg overflow-hidden bg-base-300/60">
                  {#if ch.thumb}
                    <img
                      src={ch.thumb}
                      alt=""
                      class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-200"
                      loading="lazy"
                    />
                  {:else}
                    <div class="w-full h-full flex items-center justify-center">
                      <Icon icon="material-symbols:image-outline-rounded" class="size-6 opacity-20" />
                    </div>
                  {/if}
                </div>
                <div class="flex flex-col min-w-0">
                  <span class="text-2xl font-bold group-hover:text-accent transition-colors truncate {isCurr ? 'text-accent' : ''}">
                    {ch.title}
                  </span>
                  {#if isCurr}
                    <div class="flex items-center gap-2 mt-1">
                      <span class="inline-flex items-center gap-1 text-[10px] font-mono text-accent">
                        <Icon icon="material-symbols:resume" class="size-3" />
                        In progress
                      </span>
                    </div>
                  {/if}
                </div>
                <Icon icon="material-symbols:chevron-right-rounded" class="size-5 opacity-0 -translate-x-2 group-hover:opacity-30 group-hover:translate-x-0 transition-all duration-200 shrink-0 {isCurr ? 'opacity-30' : ''}" />
              </a>
            {/each}
          </div>
        {:else}
          <div class="flex flex-col items-center justify-center py-28 opacity-25 gap-4">
            <Icon icon="tabler:ghost" class="size-14" />
            <div class="text-center">
              <p class="text-lg font-bold">No chapters found</p>
              <p class="text-sm opacity-60 mt-1">Try adjusting your search</p>
            </div>
          </div>
        {/if}
      </div>
    {:else}
      <div class="sticky top-0 z-10 bg-base-100/80 backdrop-blur-lg border-b border-base-content/5">
        <div class="flex items-center gap-2 p-3 md:p-4">
          <div class="relative grow">
            <Icon icon="material-symbols:search-rounded" class="absolute left-3 top-1/2 -translate-y-1/2 size-4 opacity-30" />
            <input
              type="search"
              bind:value={searchQuery}
              placeholder="Search chapters..."
              class="input input-sm input-bordered w-full pl-9 rounded-xl bg-base-200/50 focus:bg-base-200 transition-colors"
            />
          </div>

          <div class="flex items-center gap-1.5">
            <button
              class="btn btn-sm btn-square rounded-xl {isReversed ? `btn-ghost text-${book.accent_color}` : 'bg-base-200/70'}"
              onclick={() => (isReversed = !isReversed)}
              aria-label="Toggle order"
            >
              <Icon
                icon="material-symbols:sort-rounded"
                class="size-5 transition-transform duration-300 {isReversed ? 'rotate-180' : ''}"
              />
            </button>
            <select class="select select-sm select-bordered rounded-xl bg-base-200/50 min-w-[5rem]" bind:value={selectedTL}>
              {#each availableTLs as tl}
                <option value={tl}>{tl.toUpperCase()}</option>
              {/each}
            </select>
          </div>
        </div>
      </div>

      <div class="p-3 md:p-4 space-y-1.5">
        {#if isSearchingContent}
          <div class="flex items-center gap-2 px-3 py-2 text-xs text-base-content/50">
            <span class="loading loading-spinner loading-xs"></span>
            Searching chapter content...
          </div>
        {/if}
        {#if filteredChapters().length > 0}
          {#each filteredChapters() as ch}
            {@const isCurr = isContinueChapter(ch)}
            {@const contentMatch = contentMatches.get(ch.slug.toString())}
            <div class="rounded-xl {isCurr ? 'ring-1 ring-accent/20 bg-accent/5' : ''}">
              <a
                href="../../read/{bookSlug}/{selectedTL}/{ch.slug}"
                class="flex items-center gap-3 md:gap-4 p-3 md:p-4 rounded-xl bg-base-200/30 hover:bg-base-200/70 transition-all duration-200 relative {isCurr ? 'hover:bg-accent/10' : ''}"
              >
                {#if isCurr}
                  <div class="absolute left-0 top-0 bottom-0 w-0.5 bg-accent rounded-full"></div>
                {/if}
                <span class="text-xs md:text-sm font-mono opacity-40 tabular-nums shrink-0 leading-none w-24 text-right mr-2 whitespace-nowrap">
                  Chapter {ch.slug}
                </span>
                <div class="flex flex-col min-w-0 grow">
                  <span class="text-sm md:text-base font-bold truncate transition-colors {isCurr ? 'text-accent' : ''} group-hover/card:text-accent flex items-center gap-2">
                    {ch.title}
                    {#if ch.category}
                      <span class="ml-auto badge badge-xs badge-ghost font-mono tracking-wider opacity-70">
                        {ch.category}
                      </span>
                    {/if}
                  </span>
                  {#if !contentMatch && isCurr}
                    <span class="inline-flex items-center gap-1 text-[10px] font-mono text-accent mt-1">
                      <Icon icon="material-symbols:resume" class="size-3" />
                      In progress
                    </span>
                  {/if}
                </div>
                {#if !contentMatch}
                  <Icon icon="material-symbols:chevron-right-rounded" class="size-5 opacity-0 -translate-x-2 group-hover/card:opacity-30 group-hover/card:translate-x-0 transition-all duration-200 shrink-0" />
                {/if}
              </a>
              {#if contentMatch}
                <button
                  type="button"
                  class="ml-5 md:ml-8 mr-2 mt-1 mb-1 px-3 py-2.5 rounded-lg bg-base-200/30 border border-accent/15 block transition-colors text-left cursor-pointer hover:bg-base-200/50"
                  onclick={(e) => {
                    e.stopPropagation();
                    storeSnippetTarget(contentMatch.snippet, searchQuery);
                    window.location.href = `../../read/${bookSlug}/${selectedTL}/${ch.slug}`;
                  }}
                >
                  <p class="text-[11px] leading-[1.7] text-base-content/50 whitespace-pre-line [&_strong]:text-base-content/65 [&_strong]:font-semibold [&_em]:italic [&_em]:text-base-content/50 [&_u]:decoration-base-content/25">{@html renderSnippet(contentMatch.snippet, searchQuery)}</p>
                </button>
              {/if}
            </div>
          {/each}
        {:else}
          <div class="flex flex-col items-center justify-center py-28 opacity-25 gap-4">
            <Icon icon="tabler:ghost" class="size-14" />
            <div class="text-center">
              <p class="text-lg font-bold">No chapters found</p>
              <p class="text-sm opacity-60 mt-1">Try adjusting your search</p>
            </div>
          </div>
        {/if}
      </div>
    {/if}
  </div>
</main>

<style>
  .gallery-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
    gap: 0.75rem;
  }
  .chapter-row img {
    display: block;
  }
</style>
