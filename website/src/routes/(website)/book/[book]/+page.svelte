<script lang="ts">
  import { page } from "$app/state"; 
  import { onMount } from "svelte";
  import Icon from "@iconify/svelte";
  import imgLotmCover from "$lib/assets/web-lotm-cover.jpg";
  import imgtempCover from "$lib/assets/web-coi-cover.jpg";
  import book_meta from "$lib/meta.json";

  // --- Types ---

  interface Chapter {
    title: string;
    slug: string | number;
    category?: string;
  }

  interface BookConfig {
    title: string;
    author: string;
    synopsis: string;
    title_accent: string;
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

  // --- Data & State ---

  // Static info for book landing pages
  const bookConfigs: Record<string, BookConfig> = {
    gsgw: {
      title: "Got Dropped into a Ghost Story, Still Gotta Work",
      author: "Baek Deoksoo",
      synopsis: `placeholder`,
      title_accent: "text-default",
      button_primary: "btn-accent",
      button_secondary: "btn-info",
      cover: imgLotmCover,
      external_link: "https://page.kakao.com/content/65171279",
    },
    temp: {
      title: "Unofficial Dark Exploration Records",
      author: "Fanatics",
      synopsis: "A collection of fan-created records exploring the darkness that lies beyond.",
      title_accent: "text-primary",
      button_primary: "btn-secondary",
      button_secondary: "btn-primary",
      cover: imgtempCover,
      external_link: "",
    },
  };

  const meta = book_meta as BookMetadata;

  // Reactively track the current book based on URL
  const bookSlug = $derived(page.params.book || "gsgw");
  const book = $derived(bookConfigs[bookSlug] || bookConfigs["gsgw"]);

  // User interface state
  let searchQuery = $state("");
  let selectedTL = $state("fantl");
  let isReversed = $state(false);
  let continueData = $state<ReadingHistory | null>(null);

  // References for popup modals
  let synopsisModal: HTMLDialogElement;
  let tlSelectionModal: HTMLDialogElement;

  // Lists available translations and chapters for the current book
  const availableTLs = $derived(Object.keys(meta[bookSlug] || {}));
  const chapters = $derived(meta[bookSlug]?.[selectedTL] || []);

  // Returns chapters matching search query and chosen sort order
  const filteredChapters = $derived(() => {
    const list = chapters.filter(
      (ch: Chapter) =>
        ch.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        ch.slug.toString().includes(searchQuery),
    );
    return isReversed ? [...list].reverse() : list;
  });

  // Load bookmark from browser storage on page load
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

  // If no history exists, open translation choice modal before starting
  function handleReadClick(e: MouseEvent) {
    if (continueData) return;
    e.preventDefault();
    tlSelectionModal.showModal();
  }
</script>

<svelte:head>
  <title>{book.title}</title>
  <meta name="description" content={book.synopsis} />
</svelte:head>

<main class="flex md:flex-row flex-col min-h-screen">
  <!-- Left Side: Book Info & Actions -->
  <aside class="md:h-dvh md:w-[35vw] w-screen bg-base-200/50 md:sticky md:top-0 flex flex-col items-center border-b md:border-b-0 md:border-r border-base-300">
    <div class="w-full flex flex-col items-center p-6 md:p-8">
      <!-- Cover Image -->
      <div class="relative group mb-6">
        <div class="absolute -inset-1 bg-current opacity-10 blur-xl rounded-2xl transition-opacity group-hover:opacity-20"></div>
        <enhanced:img
          src={book.cover}
          alt="{book.title} cover"
          class="relative w-48 md:w-64 rounded-xl shadow-2xl transition-transform duration-300 group-hover:scale-[1.02]"
        />
      </div>

      <!-- Title & Author -->
      <div class="text-center space-y-1">
        <h1 class="text-2xl md:text-3xl font-black leading-tight {book.title_accent}">
          {book.title}
        </h1>
        <h2 class="text-sm font-bold opacity-70 uppercase tracking-widest">
          By: {book.author}
        </h2>
      </div>
    </div>

    <!-- Main Buttons: Continue/Start and Download -->
    <div class="w-full px-6 flex gap-2 mb-8">
      <a
        href={continueData
          ? `../../read/${continueData.book}/${continueData.tl}/${continueData.slug}`
          : "#"}
        onclick={handleReadClick}
        class="btn {book.button_primary} grow shadow-lg font-bold"
        data-sveltekit-preload-data
      >
        {#if continueData}
          <Icon icon="material-symbols:resume" class="size-5" />
          Continue Reading
        {:else}
          <Icon icon="material-symbols:menu-book-outline-rounded" class="size-5" />
          Start Reading
        {/if}
      </a>

      <a href="../../download" class="btn {book.button_secondary} btn-square shadow-lg" aria-label="Download">
        <Icon icon="material-symbols:download" class="size-6" />
      </a>
    </div>

    <!-- Description Area -->
    <div class="grow w-full px-6 md:px-8 pb-8 overflow-hidden">
      <!-- Scrollable text for Desktop -->
      <div class="hidden md:block h-full">
        <div class="h-full overflow-y-auto pr-2 custom-scrollbar">
          <p class="text-sm leading-relaxed text-justify opacity-80 whitespace-pre-line">
            {book.synopsis}
          </p>
        </div>
      </div>

      <!-- Compact button for Mobile (opens popup) -->
      <button
        class="md:hidden btn btn-ghost btn-sm w-full h-auto py-3 bg-base-300/30"
        onclick={() => synopsisModal.showModal()}
      >
        <p class="line-clamp-2 text-xs italic opacity-70">
          {book.synopsis}
        </p>
      </button>
    </div>
  </aside>

  <!-- Modal: Full Synopsis -->
  <dialog bind:this={synopsisModal} class="modal modal-bottom sm:modal-middle">
    <div class="modal-box bg-base-200">
      <form method="dialog"><button class="btn btn-sm btn-circle btn-ghost absolute right-2 top-2">✕</button></form>
      <h3 class="text-lg font-bold mb-4">Synopsis</h3>
      <div class="max-h-[60vh] overflow-y-auto">
        <p class="text-sm leading-relaxed whitespace-pre-line opacity-90">{book.synopsis}</p>
      </div>
    </div>
    <form method="dialog" class="modal-backdrop"><button>close</button></form>
  </dialog>

  <!-- Modal: Select Translation Source -->
  <dialog bind:this={tlSelectionModal} class="modal modal-bottom sm:modal-middle">
    <div class="modal-box bg-base-100">
      <div class="flex justify-between items-center mb-6">
        <h3 class="font-bold text-lg flex items-center gap-2">
          <Icon icon="material-symbols:translate-rounded" class="size-5" />
          Select Source
        </h3>
        <form method="dialog"><button class="btn btn-sm btn-circle btn-ghost">✕</button></form>
      </div>

      <!-- Static links for specific books (hardcoded logic) -->
      <div class="flex flex-col gap-3">
        {#if bookSlug === "lotm"}
          <a href="../../read/lotm/goblintl/1" class="btn btn-outline btn-lg justify-between h-auto py-4 group" onclick={() => tlSelectionModal.close()}>
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
            <a href="../../read/{bookSlug}/{tl}/0" class="btn btn-outline btn-lg justify-between h-auto py-4 group" onclick={() => tlSelectionModal.close()}>
              <div class="text-left">
                <div class="font-bold text-base flex items-center gap-2">
                  {tl.toUpperCase()} <span class="badge badge-secondary badge-sm">Recommended</span>
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

  <!-- Right Side: Search and Chapter Grid -->
  <div class="md:w-[65vw] w-screen min-h-dvh bg-base-100/50 backdrop-blur-sm">
    <!-- Filter Bar (Sticky) -->
    <div class="w-full flex flex-row items-center gap-2 p-4 sticky top-0 backdrop-blur-md z-10 bg-base-100/30 border-b border-white/5">
      <label class="input input-bordered flex items-center gap-2 grow">
        <Icon icon="material-symbols:search-rounded" class="size-6 opacity-50" />
        <input type="search" bind:value={searchQuery} placeholder="Search title or number..." class="grow" />
      </label>

      <!-- Toggle sort direction -->
      <button
        class="btn btn-square btn-bordered btn-soft {book.button_primary}"
        onclick={() => (isReversed = !isReversed)}
        aria-label="Reverse chapter order"
      >
        <Icon
          icon="material-symbols:sort-rounded"
          class="size-6 transition-transform duration-300 {isReversed ? 'rotate-180 text-accent' : ''}"
        />
      </button>

      <!-- Change Translation Source -->
      <select class="select select-bordered" bind:value={selectedTL}>
        {#each availableTLs as tl}
          <option value={tl}>{tl.toUpperCase()}</option>
        {/each}
      </select>
    </div>

    <!-- Grid of Chapter Buttons -->
    <div class="w-full grid grid-cols-1 gap-2 p-4">
      {#if filteredChapters().length > 0}
        {#each filteredChapters() as ch}
          <a
            href="../../read/{bookSlug}/{selectedTL}/{ch.slug}"
            class="btn {book.button_secondary} btn-soft justify-start h-auto py-4 text-left shadow-sm hover:scale-[1.01] transition-transform relative w-full overflow-hidden"
          >
            <div class="flex flex-col w-full min-w-0 pr-12">
              <span class="text-xs opacity-60 font-mono">CHAPTER {ch.slug}</span>
              <span class="sm:text-xl text-base font-bold truncate w-full block">{ch.title}</span>
              {#if ch.category}
                <span class="badge badge-sm badge-ghost text-[10px] font-mono uppercase tracking-widest opacity-60 absolute right-2 top-2">
                  {ch.category}
                </span>
              {/if}
            </div>
          </a>
        {/each}
      {:else}
        <!-- Empty search state -->
        <div class="flex flex-col items-center justify-center py-20 opacity-30">
          <Icon icon="tabler:ghost" class="size-20" />
          <p class="text-xl font-bold">No chapters found</p>
        </div>
      {/if}
    </div>
  </div>
</main>