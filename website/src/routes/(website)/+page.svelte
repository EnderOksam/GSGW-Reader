<script lang="ts">
  import { onMount } from "svelte";
  import { fade } from "svelte/transition";
  import Icon from "@iconify/svelte";
  import StarField from "$lib/StarField.svelte";
  import imgGsgw from "$lib/assets/web-gsgw-cover.webp";
  import imgCoi from "$lib/assets/web-coi-cover.jpg";
  import imgManwha from "$lib/assets/webtoon-cover.webp";
  import imgDebut from "$lib/assets/debut.webp";
  import imgBanner from "$lib/assets/web-gsgw-banner.jpg";

  let showBanner = $state(false);
  let ackCount = $state(0);

  onMount(() => {
    const stored = localStorage.getItem("gsgw-ack");
    ackCount = stored ? parseInt(stored, 10) : 0;
    if (ackCount < 2) showBanner = true;
  });

  function handleAck() {
    ackCount++;
    localStorage.setItem("gsgw-ack", String(ackCount));
    showBanner = false;
  }

  function showBannerAgain() {
    localStorage.setItem("gsgw-ack", "0");
    showBanner = true;
  }

  let contributeModal: HTMLDialogElement;
  let currentIndex = $state(0);

  const books = [
    {
      href: "/book/gsgw",
      img: imgGsgw,
      title: "Got Dropped into a Ghost Story, Still Gotta Work",
      author: "Baek Deoksoo",
      tag: "Webnovel",
      tagClass: "text-primary",
    },
    {
      href: "/book/manwha",
      img: imgManwha,
      title: "Ghost Story, Gotta Work",
      author: "todac_s",
      tag: "Manwha",
      tagClass: "text-accent",
    },
    {
      href: "/book/debut",
      img: imgDebut,
      title: "Debut Or Die",
      author: "Baek Deoksoo",
      tag: "Webnovel",
      tagClass: "text-primary",
    },
    {
      href: "#",
      img: "",
      title: "",
      author: "",
      tag: "Coming Soon",
      tagClass: "text-base-content/30",
      blank: true,
    },
    {
      href: "/book/temp",
      img: imgCoi,
      title: "Dark Exploration Records",
      author: "Fanatics",
      tag: "Unofficial",
      tagClass: "text-warning",
    },
    {
      href: "#",
      img: "",
      title: "",
      author: "",
      tag: "Coming Soon",
      tagClass: "text-base-content/30",
      blank: true,
    },
  ];
</script>

<svelte:head>
  <title>GSGW-Reader</title>
  <meta
    name="description"
    content="A pop-up event for some 'modern fantasy' media… I loved so much that I even took a precious day off work to attend.

On that day, I ended up transmigrating as a character in that very fantasy world."
  />
  <meta property="og:type" content="website" />
  <meta property="og:title" content="GSGW-Reader" />
  <meta property="og:image" content={imgBanner} />
  <meta
    property="og:description"
    content="A pop-up event for some 'modern fantasy' media… I loved so much that I even took a precious day off work to attend.

On that day, I ended up transmigrating as a character in that very fantasy world."
  />
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:title" content="GSGW-Reader" />
  <meta name="twitter:image" content={imgBanner} />
  <meta
    name="twitter:description"
    content="A pop-up event for some 'modern fantasy' media… I loved so much that I even took a precious day off work to attend.

On that day, I ended up transmigrating as a character in that very fantasy world."
  />
</svelte:head>

<button onclick={() => showBannerAgain()} class="fixed top-4 left-4 z-50 text-white/5 hover:text-white/20 transition-colors text-sm font-mono" title="Show banner">
  #
</button>

{#if showBanner}
  <div class="fixed top-0 left-0 right-0 z-50 flex items-center justify-center gap-4 bg-[#0d0d0d]/95 backdrop-blur-sm border-b border-[#fb8462]/20 px-4 py-3 text-sm text-white/80">
    <span class="text-center">
      GSGW-Reader is a <strong class="text-[#fb8462] font-bold">non-profit</strong> passion project for hosting and reading gsgw translations.
    </span>
    <button
      onclick={handleAck}
      class="btn btn-soft btn-xs shrink-0 border border-[#fb8462]/30 text-[#fb8462] hover:bg-[#fb8462]/10"
    >
      Acknowledge
    </button>
  </div>
{/if}

<div class="relative h-dvh flex flex-col items-center justify-center p-6 md:p-12 overflow-hidden">
    <div class="flex flex-col items-center gap-4 md:gap-8 w-full max-w-7xl">
    <h1 class="crt-title text-4xl sm:text-5xl md:text-7xl lg:text-8xl font-bold leading-tight text-center whitespace-nowrap">
      GSGW-Reader
    </h1>

    <div class="hidden md:block relative w-full max-w-4xl">
      <span
        onclick={() => currentIndex = (currentIndex - 3 + books.length) % books.length}
        class="absolute -left-10 top-1/2 -translate-y-1/2 z-10 text-white/70 cursor-pointer select-none text-2xl p-2"
        aria-label="Previous books"
      >‹</span>

      {#key currentIndex}
        <div class="flex items-center justify-center gap-4" in:fade={{ duration: 180 }}>
        {#each books.slice(currentIndex, currentIndex + 3) as book}
          <a
            href={book.href}
            class="group relative w-56 md:w-72 aspect-[3/4] overflow-hidden rounded-2xl shadow-xl transition-all duration-500 hover:scale-[1.03] hover:shadow-2xl"
            data-sveltekit-preload-data
          >
            {#if book.blank}
              <div class="absolute inset-0 flex items-center justify-center bg-base-300/20">
                <div class="text-center">
                  <div class="text-3xl mb-2 opacity-30">+</div>
                  <span class="text-xs font-bold uppercase tracking-widest {book.tagClass}">{book.tag}</span>
                </div>
              </div>
            {:else}
              <div class="absolute inset-0 transition-all duration-700 group-hover:scale-110">
                <enhanced:img
                  src={book.img}
                  alt="{book.title} cover"
                  class="absolute inset-0 w-full h-full object-cover"
                />
                <div class="absolute inset-0 bg-gradient-to-t from-black/95 via-black/60 via-60% to-black/10 to-100%"></div>
              </div>

              <div class="absolute bottom-0 left-0 right-0 p-4 z-10 translate-y-1 group-hover:translate-y-0 transition-transform duration-500">
                <span class="inline-flex items-center gap-1.5 text-xs font-bold uppercase tracking-widest {book.tagClass} drop-shadow mb-1">
                  <span class="size-1.5 rounded-full bg-current"></span>
                  {book.tag}
                </span>
                <h2 class="text-sm font-black text-white drop-shadow leading-tight line-clamp-2">{book.title}</h2>
                <p class="text-[11px] text-white/70 font-mono mt-1">{book.author}</p>
              </div>
            {/if}

            <div class="absolute inset-0 ring-1 ring-inset ring-white/10 rounded-2xl pointer-events-none group-hover:ring-white/20 transition-all duration-500"></div>
          </a>
        {/each}
        </div>
      {/key}

      <span
        onclick={() => currentIndex = (currentIndex + 3) % books.length}
        class="absolute -right-3 md:-right-10 top-1/2 -translate-y-1/2 z-10 text-white/70 cursor-pointer select-none text-2xl p-2"
        aria-label="Next books"
      >›</span>
    </div>

    <div class="flex flex-col items-center gap-4 md:hidden">
      {#key currentIndex}
        <div class="flex items-center justify-center gap-4" in:fade={{ duration: 180 }}>
          {#each books.slice(currentIndex, currentIndex + 2) as book}
          <a
            href={book.href}
            class="group relative w-[42vw] max-w-44 aspect-[3/4] overflow-hidden rounded-2xl shadow-xl transition-all duration-500 hover:scale-[1.03] hover:shadow-2xl"
            data-sveltekit-preload-data
          >
            {#if book.blank}
              <div class="absolute inset-0 flex items-center justify-center bg-base-300/20">
                <div class="text-center">
                  <div class="text-2xl mb-2 opacity-30">+</div>
                  <span class="text-xs font-bold uppercase tracking-widest {book.tagClass}">{book.tag}</span>
                </div>
              </div>
            {:else}
              <div class="absolute inset-0 transition-all duration-700 group-hover:scale-110">
                <enhanced:img
                  src={book.img}
                  alt="{book.title} cover"
                  class="absolute inset-0 w-full h-full object-cover"
                />
                <div class="absolute inset-0 bg-gradient-to-t from-black/95 via-black/60 via-60% to-black/10 to-100%"></div>
              </div>
              <div class="absolute bottom-0 left-0 right-0 p-3 z-10 translate-y-1 group-hover:translate-y-0 transition-transform duration-500">
                <span class="inline-flex items-center gap-1 text-xs font-bold uppercase tracking-widest {book.tagClass} drop-shadow mb-1">
                  <span class="size-1.5 rounded-full bg-current"></span>
                  {book.tag}
                </span>
                <h2 class="text-xs font-black text-white drop-shadow leading-tight line-clamp-2">{book.title}</h2>
                <p class="text-[10px] text-white/70 font-mono mt-1">{book.author}</p>
              </div>
            {/if}
            <div class="absolute inset-0 ring-1 ring-inset ring-white/10 rounded-2xl pointer-events-none group-hover:ring-white/20 transition-all duration-500"></div>
          </a>
        {/each}
        </div>
      {/key}
      <div class="flex items-center justify-center gap-4">
        <span
          onclick={() => currentIndex = (currentIndex - 3 + books.length) % books.length}
          class="text-white/70 cursor-pointer select-none text-xl p-2"
          aria-label="Previous books"
        >‹</span>
        {#key currentIndex}
          {#each books.slice(currentIndex + 2, currentIndex + 3) as book}
            <a
              href={book.href}
              class="group relative w-[42vw] max-w-44 aspect-[3/4] overflow-hidden rounded-2xl shadow-xl transition-all duration-500 hover:scale-[1.03] hover:shadow-2xl"
              data-sveltekit-preload-data
              in:fade={{ duration: 180 }}
            >
              {#if book.blank}
                <div class="absolute inset-0 flex items-center justify-center bg-base-300/20">
                  <div class="text-center">
                  <div class="text-2xl mb-2 opacity-30">+</div>
                    <span class="text-xs font-bold uppercase tracking-widest {book.tagClass}">{book.tag}</span>
                  </div>
                </div>
              {:else}
                <div class="absolute inset-0 transition-all duration-700 group-hover:scale-110">
                  <enhanced:img
                    src={book.img}
                    alt="{book.title} cover"
                    class="absolute inset-0 w-full h-full object-cover"
                  />
                  <div class="absolute inset-0 bg-gradient-to-t from-black/95 via-black/60 via-60% to-black/10 to-100%"></div>
                </div>
                <div class="absolute bottom-0 left-0 right-0 p-3 z-10 translate-y-1 group-hover:translate-y-0 transition-transform duration-500">
                  <span class="inline-flex items-center gap-1 text-xs font-bold uppercase tracking-widest {book.tagClass} drop-shadow mb-1">
                    <span class="size-1.5 rounded-full bg-current"></span>
                    {book.tag}
                  </span>
                  <h2 class="text-xs font-black text-white drop-shadow leading-tight line-clamp-2">{book.title}</h2>
                  <p class="text-[10px] text-white/70 font-mono mt-1">{book.author}</p>
                </div>
              {/if}
              <div class="absolute inset-0 ring-1 ring-inset ring-white/10 rounded-2xl pointer-events-none group-hover:ring-white/20 transition-all duration-500"></div>
            </a>
          {/each}
        {/key}
        <span
          onclick={() => currentIndex = (currentIndex + 3) % books.length}
          class="text-white/70 cursor-pointer select-none text-xl p-2"
          aria-label="Next books"
        >›</span>
      </div>
    </div>

    <div class="flex flex-nowrap items-center justify-center gap-2 md:gap-4">
      <div class="tooltip" data-tip="Download">
        <a href="/download" class="btn btn-soft btn-square btn-lg md:btn-xl btn-secondary shadow-lg">
          <Icon icon="material-symbols:download" class="size-5 md:size-7" />
        </a>
      </div>
      <div class="tooltip" data-tip="Contribute">
        <button onclick={() => contributeModal.showModal()} class="btn btn-soft btn-square btn-lg md:btn-xl btn-warning shadow-lg">
          <Icon icon="ri:edit-line" class="size-5 md:size-7" />
        </button>
      </div>
      <div class="tooltip" data-tip="Discord">
        <a href="https://discord.gg/HHnSjeGN4d" target="_blank" rel="noopener noreferrer" class="btn btn-soft btn-square btn-lg md:btn-xl btn-accent shadow-lg">
          <Icon icon="mingcute:discord-line" class="size-5 md:size-7" />
        </a>
      </div>
      <div class="tooltip" data-tip="GitHub">
        <a href="https://github.com/EnderOksam/GSGW-Reader" target="_blank" rel="noopener noreferrer" class="btn btn-soft btn-square btn-lg md:btn-xl btn-info shadow-lg">
          <Icon icon="mdi:github" class="size-5 md:size-7" />
        </a>
      </div>
      <StarField>
        <div class="tooltip" data-tip="Info">
          <a href="/info" class="btn btn-soft btn-square btn-lg md:btn-xl btn-ghost shadow-lg info-glow">
            <Icon icon="mdi:information-outline" class="size-5 md:size-7" />
          </a>
        </div>
      </StarField>
    </div>
  </div>
</div>

<dialog bind:this={contributeModal} class="modal modal-bottom sm:modal-middle">
  <div class="modal-box bg-base-100 p-0 rounded-box shadow-2xl overflow-hidden max-w-sm mx-auto">
    <div class="relative">
      <div class="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-secondary/5"></div>
      <div class="relative flex items-center justify-between px-6 py-4 border-b border-base-content/10">
        <span class="font-bold text-lg text-primary flex items-center gap-2">
          <Icon icon="material-symbols:edit-outline-rounded" class="size-5" /> Contribute
        </span>
        <form method="dialog">
          <button class="btn btn-sm btn-circle btn-ghost" aria-label="Close">
            <Icon icon="mdi:close" class="size-4" />
          </button>
        </form>
      </div>
    </div>
    <div class="p-5 space-y-3">
      <a href="https://github.com/EnderOksam/GSGW-Reader/blob/main/contributing.md" target="_blank" class="group flex items-center gap-4 p-4 rounded-2xl border border-base-content/5 bg-base-200/30 hover:bg-base-200/60 transition-colors">
        <div class="shrink-0 w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
          <Icon icon="mdi:book-open-page-variant" class="size-5 text-primary" />
        </div>
        <div class="min-w-0">
          <span class="block text-sm font-semibold">Read the Guide</span>
          <span class="block text-xs text-base-content/40 mt-0.5">Learn how to make edits to chapters</span>
        </div>
      </a>
      <a href="/dev/editor" class="group flex items-center gap-4 p-4 rounded-2xl border border-base-content/5 bg-base-200/30 hover:bg-base-200/60 transition-colors">
        <div class="shrink-0 w-10 h-10 rounded-xl bg-secondary/10 flex items-center justify-center">
          <Icon icon="material-symbols:edit-note-rounded" class="size-5 text-secondary" />
        </div>
        <div class="min-w-0">
          <span class="block text-sm font-semibold">Open the Web Editor</span>
          <span class="block text-xs text-base-content/40 mt-0.5">Preview how your changes would look in the reader</span>
        </div>
      </a>
    </div>
  </div>
  <form method="dialog" class="modal-backdrop"><button>close</button></form>
</dialog>

<style>
  .crt-title {
    display: inline-block;
    font-weight: 800;
    background: linear-gradient(135deg, #ff2a00 0%, #ff7b00 15%, #ffcc00 30%, #ff2a6d 50%, #c213e0 70%, #ff2a00 100%);
    background-size: 200% 100%;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    animation: aurora-flow 8s linear infinite;
    filter: drop-shadow(0 0 10px rgba(255, 42, 0, 0.4)) drop-shadow(0 0 25px rgba(255, 42, 109, 0.3)) drop-shadow(0 0 50px rgba(194, 19, 224, 0.12));
    will-change: background-position;
  }

  @keyframes aurora-flow {
    0% { background-position: 0% 50%; }
    100% { background-position: 100% 50%; }
  }

  @keyframes crt-flicker {
    0%, 100% { opacity: 1; }
    92% { opacity: 1; }
    93% { opacity: 0.85; }
    94% { opacity: 1; }
    96% { opacity: 0.92; }
    97% { opacity: 1; }
  }
  .info-glow {
    position: relative;
    overflow: hidden;
    box-shadow: 0 0 15px 3px rgba(255, 224, 102, 0.25) !important;
    animation: info-shing 1.8s ease-out 1, info-pulse 3s ease-in-out infinite 2s;
  }
  .info-glow::after {
    content: "";
    position: absolute;
    inset: -60%;
    border-radius: inherit;
    background: linear-gradient(135deg, transparent 35%, rgba(255,224,102,0.25) 50%, transparent 65%);
    animation: info-sweep 2.5s ease-in-out infinite;
    pointer-events: none;
  }
  @keyframes info-sweep {
    0% { transform: translate(-70%, -70%); }
    35% { transform: translate(70%, 70%); }
    100% { transform: translate(70%, 70%); }
  }
  @keyframes info-pulse {
    0%, 100% { box-shadow: 0 0 15px 3px rgba(255, 224, 102, 0.25); }
    50% { box-shadow: 0 0 18px 5px rgba(255, 224, 102, 0.35); }
  }
  @keyframes info-shing {
    0% { box-shadow: 0 0 0 0 transparent, 0 0 15px 3px rgba(255, 224, 102, 0.25); }
    15% { box-shadow: 0 0 30px 10px rgba(255, 224, 102, 0.6), 0 0 15px 3px rgba(255, 224, 102, 0.25); }
    30% { box-shadow: 0 0 8px 2px rgba(255, 224, 102, 0.3), 0 0 15px 3px rgba(255, 224, 102, 0.25); }
    100% { box-shadow: 0 0 15px 3px rgba(255, 224, 102, 0.25); }
  }
</style>
