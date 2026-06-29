<script lang="ts">
  import { fade, fly } from "svelte/transition";
  import Icon from "@iconify/svelte";

  const standardUrl = "https://raw.githubusercontent.com/EnderOksam/GSGW-Reader/main/scripts/epub/Got%20Dropped%20into%20a%20Ghost%20Story%2C%20Still%20Gotta%20Work%20-%20fantl%20%5BDefault%5D.epub";

  let recommendModal: HTMLDialogElement;
  const openRecommended = () => recommendModal?.showModal();
</script>

<div class="flex flex-col items-center justify-center min-h-dvh p-4 md:p-8">
  <div class="max-w-4xl w-full">
    <header class="text-center mb-12">
      <h1 class="text-3xl md:text-5xl font-bold mb-3 tracking-tight text-white drop-shadow-[0_0_8px_rgba(255,255,255,0.3)]">
        Offline Archives
      </h1>
      <p class="text-base-content/60 max-w-lg mx-auto">
        Download the complete fan translation for offline reading on your e-reader, tablet, or phone.
      </p>
    </header>

    <div
      in:fly={{ y: 20, duration: 300 }}
      class="group relative overflow-hidden rounded-2xl border border-white/10 bg-base-200/40 shadow-xl transition-all hover:border-white/20 hover:shadow-2xl hover:bg-base-200/60"
    >
      <div
        class="absolute inset-0 bg-linear-to-br from-blue-900/40 to-black/60 opacity-0 group-hover:opacity-10 transition-opacity duration-500"
      ></div>

      <div class="relative p-6 md:p-8 flex flex-col md:flex-row gap-8 items-center">
        <div class="flex-1 space-y-3">
          <div class="flex items-center gap-3">
            <span class="badge badge-primary badge-outline font-mono text-xs font-bold tracking-widest">EPUB</span>
          </div>

          <h2 class="text-2xl font-bold text-white">Got Dropped into a Ghost Story, Still Gotta Work</h2>
          <div class="flex items-center gap-2 text-xs font-mono opacity-50 uppercase tracking-wider">
            <Icon icon="mdi:translate" class="size-4" />
            <span>Fan Translation</span>
          </div>
          <p class="text-base-content/70 leading-relaxed text-sm pt-2">
            Built EPUB based on the markdown files in the GitHub. Up to date with edits.
          </p>
          <p class="text-base-content/50 leading-relaxed text-xs">
            It gets automatically updated on the 1st and 15th of every month.
          </p>
        </div>

        <div class="w-full md:w-80 flex flex-col gap-3 shrink-0">
          <a
            href={standardUrl}
            class="btn h-auto py-4 px-5 border-none bg-linear-to-r from-primary/90 to-primary text-white hover:brightness-110 shadow-lg shadow-primary/20 flex items-center justify-between group/btn text-base"
          >
            <div class="text-left">
              <div class="font-bold flex items-center gap-2 text-lg">
                Download EPUB
                <Icon icon="mdi:star-four-points" class="size-4 text-yellow-300" />
              </div>
              <div class="text-xs opacity-80 font-normal">
                Full Color • Modern Format
              </div>
            </div>
            <Icon icon="mdi:download" class="size-7 opacity-70 group-hover/btn:translate-y-1 transition-transform" />
          </a>
          <button onclick={openRecommended} class="btn h-auto py-4 px-5 border-none bg-linear-to-r from-violet-600/90 to-purple-600 text-white hover:brightness-110 shadow-lg shadow-violet-600/20 flex items-center justify-between group/btn text-base">
            <div class="text-left">
              <div class="font-bold flex items-center gap-2 text-lg">
                Recommended EPub Readers
              </div>
              <div class="text-xs opacity-80 font-normal">
                Best apps for reading on any device
              </div>
            </div>
            <Icon icon="mdi:book-open-outline" class="size-7 opacity-70 group-hover/btn:scale-110 transition-transform" />
          </button>
        </div>
      </div>
    </div>

  </div>
</div>

<dialog bind:this={recommendModal} class="modal modal-bottom sm:modal-middle">
  <div class="modal-box bg-base-100 rounded-t-2xl sm:rounded-box max-w-lg p-5">
    <form method="dialog">
      <button class="btn btn-sm btn-circle btn-ghost absolute right-3 top-3">✕</button>
    </form>
    <h3 class="text-xl font-bold mb-4 flex items-center gap-2">
      <Icon icon="mdi:bookmark" class="size-5 text-primary" />
      Recommended EPub Readers
    </h3>
    <div class="space-y-3 text-sm text-base-content/80 leading-relaxed">
      <p>Hey hey 👋, Ender here. A lot of people have issues with the story not looking how it should depending on their device.</p>
      <p>I try to fix as much as I can with the epub but most of the fault lies in their epub reader so here are some reccomended ones:</p>

      <div class="space-y-2">
        <div class="p-3 rounded-xl bg-base-300/40">
          <div class="flex items-center gap-2 text-sm font-semibold text-white mb-2">
            <Icon icon="mdi:apple" class="size-5" /> iOS
          </div>
          <div class="space-y-2">
            <div>
              <span class="font-semibold text-white">PocketBook</span>
              <p class="text-xs text-base-content/60">I don't personally use iOS, but Lei and Destiny on the discord have said PocketBook is the best.</p>
            </div>
            <div class="opacity-50">
              <span class="font-semibold text-white">Apple Books</span>
              <p class="text-xs text-base-content/60">Apple Books works too but if you change the theme to dark mode it will mess up the css rules (what makes text look pretty).</p>
            </div>
          </div>
        </div>

        <div class="p-3 rounded-xl bg-base-300/40">
          <div class="flex items-center gap-2 text-sm font-semibold text-white mb-2">
            <Icon icon="mdi:android" class="size-5" /> Android
          </div>
          <div class="space-y-2">
            <div>
              <span class="font-semibold text-white">Episteme</span>
              <p class="text-xs text-base-content/60">I've discovered Episteme recently and it's been my favorite epub reader so far. Haven't had any issues people report on other epub readers.</p>
            </div>
            <div class="opacity-50">
              <span class="font-semibold text-white">Moon Reader</span>
              <p class="text-xs text-base-content/60">Good alternative, it works but it's not perfect.</p>
            </div>
          </div>
        </div>

        <div class="p-3 rounded-xl bg-base-300/40">
          <div class="flex items-center gap-2 text-sm font-semibold text-white mb-2">
            <Icon icon="mdi:laptop" class="size-5" /> PC / Desktop
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
  <form method="dialog" class="modal-backdrop"><button>close</button></form>
</dialog>