<script lang="ts">
  import { onMount } from "svelte";
  import Icon from "@iconify/svelte";
  import StarField from "$lib/StarField.svelte";
  import imgLotm from "$lib/assets/web-lotm-cover.jpg";
  import imgCoi from "$lib/assets/web-coi-cover.jpg";
  import imgManwha from "$lib/assets/webtoon-cover.webp";

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

  const books = [
    {
      href: "/book/gsgw",
      img: imgLotm,
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
      href: "/book/temp",
      img: imgCoi,
      title: "Dark Exploration Records",
      author: "Fanatics",
      tag: "Unofficial",
      tagClass: "text-warning",
    },
  ];
</script>

<svelte:head>
  <title>GSGW-Reader</title>
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

<div class="relative min-h-dvh flex flex-col items-center justify-center p-6 md:p-12">
  <div class="flex flex-col items-center gap-6 md:gap-14 w-full max-w-7xl">
    <h1 class="crt-title text-6xl md:text-7xl font-bold leading-tight text-center filter drop-shadow-[0_0_10px_#fb8462]" style="color:#fb8462">
      GSGW-Reader
    </h1>

    <div class="hidden md:flex flex-wrap items-center justify-center gap-4">
      {#each books as book}
        <a
          href={book.href}
          class="group relative w-72 aspect-[3/4] overflow-hidden rounded-2xl shadow-xl transition-all duration-500 hover:scale-[1.03] hover:shadow-2xl"
          data-sveltekit-preload-data
        >
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
            <h2 class="text-sm font-black text-white drop-shadow leading-tight line-clamp-2">
              {book.title}
            </h2>
            <p class="text-[11px] text-white/70 font-mono mt-1">
              {book.author}
            </p>
          </div>

          <div class="absolute inset-0 ring-1 ring-inset ring-white/10 rounded-2xl pointer-events-none group-hover:ring-white/20 transition-all duration-500"></div>
        </a>
      {/each}
    </div>

    <div class="flex md:hidden flex-col items-center gap-4">
      <div class="flex items-center justify-center gap-4">
        {#each books.slice(0, 2) as book}
          <a
            href={book.href}
            class="group relative w-[42vw] max-w-56 aspect-[3/4] overflow-hidden rounded-2xl shadow-xl transition-all duration-500 hover:scale-[1.03] hover:shadow-2xl"
            data-sveltekit-preload-data
          >
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
            <div class="absolute inset-0 ring-1 ring-inset ring-white/10 rounded-2xl pointer-events-none group-hover:ring-white/20 transition-all duration-500"></div>
          </a>
        {/each}
      </div>
      {#each books.slice(2) as book}
        <a
          href={book.href}
          class="group relative w-[42vw] max-w-56 aspect-[3/4] overflow-hidden rounded-2xl shadow-xl transition-all duration-500 hover:scale-[1.03] hover:shadow-2xl"
          data-sveltekit-preload-data
        >
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
          <div class="absolute inset-0 ring-1 ring-inset ring-white/10 rounded-2xl pointer-events-none group-hover:ring-white/20 transition-all duration-500"></div>
        </a>
      {/each}
    </div>

    <div class="flex flex-wrap items-center justify-center gap-4">
      <div class="tooltip" data-tip="Download">
        <a href="/download" class="btn btn-soft btn-square btn-xl btn-secondary shadow-lg">
          <Icon icon="material-symbols:download" class="size-7" />
        </a>
      </div>
      <div class="tooltip" data-tip="Contribute">
        <button onclick={() => contributeModal.showModal()} class="btn btn-soft btn-square btn-xl btn-warning shadow-lg">
          <Icon icon="ri:edit-line" class="size-7" />
        </button>
      </div>
      <div class="tooltip" data-tip="Discord">
        <a href="https://discord.gg/HHnSjeGN4d" target="_blank" rel="noopener noreferrer" class="btn btn-soft btn-square btn-xl btn-accent shadow-lg">
          <Icon icon="mingcute:discord-line" class="size-7" />
        </a>
      </div>
      <div class="tooltip" data-tip="GitHub">
        <a href="https://github.com/EnderOksam/GSGW-Reader" target="_blank" rel="noopener noreferrer" class="btn btn-soft btn-square btn-xl btn-info shadow-lg">
          <Icon icon="mdi:github" class="size-7" />
        </a>
      </div>
      <StarField>
        <div class="tooltip" data-tip="Info">
          <a href="/info" class="btn btn-soft btn-square btn-xl btn-ghost shadow-lg info-glow">
            <Icon icon="mdi:information-outline" class="size-7" />
          </a>
        </div>
      </StarField>
    </div>
  </div>
</div>

<dialog bind:this={contributeModal} class="modal modal-bottom sm:modal-middle">
  <div class="modal-box bg-base-100 rounded-box">
    <form method="dialog">
      <button class="btn btn-sm btn-circle btn-ghost absolute right-2 top-2">✕</button>
    </form>
    <h3 class="font-bold text-lg mb-4" style="color:#fb8462">Contribute</h3>
    <div class="flex flex-col gap-3">
      <a href="https://github.com/EnderOksam/GSGW-Reader/blob/main/contributing.md" target="_blank" rel="noopener noreferrer" class="btn btn-outline w-full rounded-btn gap-2" style="border-color:#fb8462; color:#fb8462; hover:background:#fb8462/10">
        <Icon icon="mdi:book-open-page-variant" class="size-5" /> Read Guide
      </a>
      <a href="/dev/editor" class="btn btn-outline w-full rounded-btn gap-2" style="border-color:#fb8462; color:#fb8462;">
        <Icon icon="material-symbols:edit-note-rounded" class="size-5" /> Editor
      </a>
    </div>
  </div>
  <form method="dialog" class="modal-backdrop"><button>close</button></form>
</dialog>

<style>
  .crt-title {
    text-shadow:
      0 0 3px rgba(251, 132, 98, 0.3),
      0 0 8px rgba(251, 132, 98, 0.1),
      -0.5px 0 rgba(255, 0, 0, 0.1),
      0.5px 0 rgba(0, 0, 255, 0.1);
    animation: crt-flicker 4s infinite;
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
