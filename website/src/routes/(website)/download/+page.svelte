<script lang="ts">
  import Icon from "@iconify/svelte";
  import { fade, fly } from "svelte/transition";

  // --- Data Structure ---
  const archives = {
    gsgw: {
      title: "Got Dropped into a Ghost Story, Still Gotta Work",
      id: "gsgw",
      coverColor: "from-orange-900/40 to-black/60",
      tls: [
        {
          name: "Fan Translation",
          translator: "Salt Goblin & Fans",
          description:
            "Unofficial Fan Translation with edits and enhancements. Recommended for first time readers.",
          downloads: {
            standard: "PLACEHOLDER_LINK_GSGW_FAN_STD",
            legacy: "PLACEHOLDER_LINK_GSGW_FAN_LEGACY",
          },
        },
        {
          name: "Machine Translation (MTL)",
          translator: "translator TBD",
          description:
            "Raw machine translation for those who wish to read ahead. Expect lower grammatical accuracy.",
          downloads: {
            standard: "PLACEHOLDER_LINK_GSGW_MTL_STD",
            legacy: "PLACEHOLDER_LINK_GSGW_MTL_LEGACY",
          },
        },
      ],
    },
    uder: {
      title: "Unofficial Dark Exploration Records",
      id: "uder",
      coverColor: "from-blue-900/40 to-black/60",
      tls: [
        {
          name: "Unofficial Dark Exploration Records",
          translator: "Dedicated Fans",
          description: "Ongoing unofficial exploration records and classified data logs.",
          downloads: {
            standard: "PLACEHOLDER_LINK_UDER_STD",
            legacy: "PLACEHOLDER_LINK_UDER_LEGACY",
          },
        },
      ],
    },
  };

  // State
  let selectedBook: "gsgw" | "uder" = "gsgw";

  // Helper to get active book data
  $: activeData = archives[selectedBook];
</script>

<div class="flex flex-col items-center justify-center min-h-dvh p-4 md:p-8">
  <div class="max-w-4xl w-full flex flex-col items-center">
    
    <!-- STACKED & CENTERED HEADER -->
    <header class="mb-12 w-full flex flex-col items-center text-center">
      <h1 class="text-3xl md:text-5xl font-bold mb-3 tracking-tight text-white filter drop-shadow-[0_0_8px_rgba(255,255,255,0.3)]">
        Offline Archives
      </h1>
      <p class="text-base-content/60 max-w-lg">
        Download the complete records for offline access. Select a series to view available editions.
      </p>
    </header>

    <!-- Navigation Toggle -->
    <div class="flex justify-center mb-8 w-full">
      <div
        class="bg-base-300/50 p-1 rounded-xl inline-flex gap-1 border border-white/5 backdrop-blur-sm"
      >
        <button
          class="px-6 py-2.5 rounded-lg text-sm font-bold transition-all duration-200 flex items-center gap-2
          {selectedBook === 'gsgw'
            ? 'bg-primary text-primary-content shadow-md'
            : 'hover:bg-white/5 text-base-content/70'}"
          on:click={() => (selectedBook = "gsgw")}
        >
          <Icon icon="game-icons:ghost" class="size-5" />
          GSGW
        </button>
        <button
          class="px-6 py-2.5 rounded-lg text-sm font-bold transition-all duration-200 flex items-center gap-2
          {selectedBook === 'uder'
            ? 'bg-secondary text-secondary-content shadow-md'
            : 'hover:bg-white/5 text-base-content/70'}"
          on:click={() => (selectedBook = "uder")}
        >
          <Icon icon="game-icons:radar-sweep" class="size-5" />
          U-DER
        </button>
      </div>
    </div>

    {#key selectedBook}
      <div
        in:fly={{ y: 20, duration: 300, delay: 100 }}
        out:fade={{ duration: 150 }}
        class="grid gap-6 w-full"
      >
        {#each activeData.tls as tl}
          <div
            class="group relative overflow-hidden rounded-2xl border border-white/10 bg-base-200/40 shadow-xl transition-all hover:border-white/20 hover:shadow-2xl hover:bg-base-200/60"
          >
            <div
              class="absolute inset-0 bg-linear-to-br {activeData.coverColor} opacity-0 group-hover:opacity-10 transition-opacity duration-500"
            ></div>

            <div class="relative p-6 md:p-8 flex flex-col md:flex-row gap-8 items-start">
              <div class="flex-1 space-y-3">
                <div class="flex items-center gap-3">
                  <span class="badge badge-primary badge-outline font-mono text-xs font-bold tracking-widest">EPUB</span>
                  {#if tl.name.includes("Fan")}
                    <span class="badge badge-success badge-soft text-xs font-bold">RECOMMENDED</span>
                  {/if}
                </div>

                <h2 class="text-2xl font-bold text-white tracking-tight">{tl.name}</h2>
                <div class="flex items-center gap-2 text-xs font-mono opacity-50 uppercase tracking-wider">
                  <Icon icon="mdi:fountain-pen-tip" class="size-4" />
                  <span>Compiled by {tl.translator}</span>
                </div>
                <p class="text-base-content/70 leading-relaxed text-sm pt-2">
                  {tl.description}
                </p>
              </div>

              <div class="w-full md:w-80 flex flex-col gap-3 shrink-0">
                <a
                  href={tl.downloads.standard}
                  target="_blank"
                  rel="noopener noreferrer"
                  class="btn h-auto py-3 px-4 border-none bg-linear-to-r from-primary/90 to-primary text-white hover:brightness-110 shadow-lg shadow-primary/20 flex items-center justify-between group/btn"
                >
                  <div class="text-left">
                    <div class="font-bold flex items-center gap-2">
                      Standard Edition
                      <Icon icon="mdi:star-four-points" class="size-3 text-yellow-300" />
                    </div>
                    <div class="text-[10px] opacity-80 font-normal">
                      Full Formatting • Modern E-Readers
                    </div>
                  </div>
                  <Icon icon="mdi:download" class="size-6 opacity-70 group-hover/btn:translate-y-1 transition-transform" />
                </a>

                <a
                  href={tl.downloads.legacy}
                  target="_blank"
                  rel="noopener noreferrer"
                  class="btn h-auto py-3 px-4 btn-outline border-base-content/20 hover:bg-base-content/5 hover:border-base-content/30 text-base-content flex items-center justify-between group/btn"
                >
                  <div class="text-left">
                    <div class="font-bold flex items-center gap-2 text-base-content/90">
                      Legacy Edition
                      <Icon icon="mdi:history" class="size-4 opacity-50" />
                    </div>
                    <div class="text-[10px] opacity-60 font-normal">
                      Optimized for Old Devices • EPUB2
                    </div>
                  </div>
                  <Icon icon="mdi:download-outline" class="size-6 opacity-40 group-hover/btn:translate-y-1 transition-transform" />
                </a>
              </div>
            </div>
          </div>
        {/each}
      </div>
    {/key}

    <footer class="mt-16 text-center space-y-4 w-full">
      <p class="text-xs text-base-content/30 max-w-md mx-auto">
        Files are generated and hosted via GitHub. For a smooth experience on Kindle or older Kobo devices, the "Legacy" version is recommended.
      </p>
    </footer>
  </div>
</div>

<style>
  :global(.text-primary) {
    color: var(--p, #c47f0a) !important;
  }
</style>