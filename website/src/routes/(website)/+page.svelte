<script lang="ts">
  import { onMount } from "svelte";
  import { fade } from "svelte/transition";
  import Icon from "@iconify/svelte";
  import StarField from "$lib/StarField.svelte";

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

  const tweetUrls = [
    "https://x.com/choilings/status/2042452514134774138?s=20",
    "https://x.com/choilings/status/2039191022065070498?s=20",
    "https://x.com/choilings/status/2037741469839118803?s=20",
    "https://x.com/choilings/status/2035929530217402438?s=20",
    "https://x.com/choilings/status/2035567141655875832?s=20",
    "https://x.com/choilings/status/2034479979355058326?s=20",
    "https://x.com/choilings/status/2034121032265830466/photo/2",
    "https://x.com/choilings/status/2033755205284859959?s=20",
    "https://x.com/choilings/status/2033392816257212692?s=20",
    "https://x.com/choilings/status/2033136861431099799?s=20",
  ];

  const TWITTER_RE = /https?:\/\/(?:x|twitter)\.com\/(\w+)\/status\/(\d+)(?:\/photo\/(\d+))?/;

  function parseUrl(url: string) {
    const m = url.match(TWITTER_RE);
    if (!m) return null;
    return { user: m[1], tweetId: m[2], photo: m[3] ? parseInt(m[3], 10) : undefined };
  }

  interface MediaItem {
    src: string;
    tweetUrl: string;
    name: string;
    user: string;
  }

  let mediaItems: MediaItem[] = [];
  let currentIndex = $state(0);
  let loaded = $state(false);

  const ROTATION_TIME = 10000;

  function preloadImage(src: string): Promise<void> {
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => resolve();
      img.onerror = () => reject();
      img.src = src;
    });
  }

  onMount(async () => {
    const results = await Promise.all(
      tweetUrls.map(async (url) => {
        const p = parseUrl(url);
        if (!p) return [];
        const { user, tweetId, photo } = p;
        try {
          const res = await fetch(`https://api.fxtwitter.com/${user}/status/${tweetId}`);
          const data = await res.json();
          if (!data?.tweet) return [];
          const t = data.tweet;
          const author = t.author || {};
          const name = author.name || user;
          const photos = t.media?.photos || [];
          const tweetUrl = `https://x.com/${user}/status/${tweetId}`;

          const item = (src: string) => ({ src, tweetUrl, name, user });

          if (photo !== undefined && photos.length) {
            const img = photos[photo - 1];
            return img ? [item(img.url)] : [];
          }

          if (photos.length > 1) return photos.map(p => item(p.url));
          if (photos.length === 1) return [item(photos[0].url)];
          return [];
        } catch {
          return [];
        }
      })
    );

    mediaItems = results.flat();
    loaded = true;

    if (mediaItems.length) {
      currentIndex = Math.floor(Math.random() * mediaItems.length);
    }
  });

  let preloading = false;
  let rotTimer: ReturnType<typeof setTimeout>;

  function scheduleNext() {
    rotTimer = setTimeout(advance, ROTATION_TIME);
  }

  async function advance() {
    if (preloading || !mediaItems.length) return;
    preloading = true;

    const nextIdx = (currentIndex + 1) % mediaItems.length;
    const next = mediaItems[nextIdx];

    try {
      await preloadImage(next.src);
      currentIndex = nextIdx;
    } catch {
      // image failed, stay on current and try again later
    }

    preloading = false;
    if (loaded) scheduleNext();
  }

  $effect(() => {
    if (loaded && mediaItems.length) {
      scheduleNext();
      return () => clearTimeout(rotTimer);
    }
  });
</script>

<a 
  href="/error-test-trigger" 
  class="fixed top-4 left-4 z-50 opacity-0 hover:opacity-20 transition-opacity text-white cursor-default"
>
  #
</a>

{#if showBanner}
  <div class="fixed top-0 left-0 right-0 z-50 flex items-center justify-center gap-4 bg-base-300/80 border-b border-white/10 px-4 py-3 text-sm text-white">
    <span class="text-center">
      GSGW-Reader is a <strong class="text-warning font-bold">non-profit</strong> passion project for hosting and reading gsgw translations.
    </span>
    <button
      onclick={handleAck}
      class="btn btn-soft btn-xs btn-primary shrink-0"
    >
      Acknowledge
    </button>
  </div>
{/if}

<main class="relative z-10 flex min-h-dvh flex-col items-center justify-center gap-10 p-8 md:flex-row md:justify-around text-white overflow-x-hidden">
  
  <div class="flex flex-col md:flex-row items-center gap-4 md:gap-8">
    <div class="flex flex-col items-center gap-4">
      <a href="/book" class="block">
        <div class="hover-3d relative">
          {#if loaded && mediaItems.length}
            <div class="bg-[#16181c] border border-white/[0.08] rounded-2xl shadow-[0_4px_24px_rgba(0,0,0,0.4)] overflow-hidden w-[30vh] md:w-[50vh] px-3 pb-2">
              <div class="flex items-baseline gap-1.5 py-3 pb-1">
                <span class="text-[#1d9bf0] text-[0.9375rem] font-bold truncate" style="text-shadow: 0 0 8px rgba(29,155,240,0.5)">{mediaItems[currentIndex].name}</span>
                <span class="text-[#71767b] text-[0.8125rem]">@{mediaItems[currentIndex].user}</span>
                <svg class="text-[#71767b] ml-auto shrink-0 opacity-60" viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>
              </div>
              <figure class="relative aspect-[2/3] overflow-hidden rounded-xl">
                {#key currentIndex}
                  <img
                    in:fade={{ duration: 1500 }}
                    out:fade={{ duration: 1500 }}
                    src={mediaItems[currentIndex].src}
                    alt="Chapter illustration"
                    class="absolute inset-0 h-full w-full object-cover"
                  />
                {/key}
              </figure>
            </div>
          {:else}
            <div class="bg-[#16181c] border border-white/[0.08] rounded-2xl shadow-[0_4px_24px_rgba(0,0,0,0.4)] overflow-hidden w-[30vh] md:w-[50vh] px-3 pb-2">
              <figure class="relative aspect-[2/3] overflow-hidden rounded-xl">
                <div class="absolute inset-0 flex items-center justify-center text-white/40 text-sm">
                  Loading…
                </div>
              </figure>
            </div>
          {/if}
          <div></div><div></div><div></div><div></div><div></div><div></div><div></div><div></div>
        </div>
      </a>
      <span class="hidden md:inline text-white/25 text-xs mt-1">(Interact with the card to access the books)</span>
    </div>

    <div class="hidden md:flex flex-col justify-center items-center gap-3">
      <div class="tooltip" data-tip="Download">
        <a href="/download" class="btn btn-soft btn-square btn-lg btn-secondary shadow-lg">
          <Icon icon="material-symbols:download" class="size-7" />
        </a>
      </div>
      <div class="tooltip" data-tip="Contribute">
        <a href="https://github.com/EnderOksam/GSGW-Reader/blob/main/contributing.md" target="_blank" rel="noopener noreferrer" class="btn btn-soft btn-square btn-lg btn-warning shadow-lg">
          <Icon icon="ri:edit-line" class="size-7" />
        </a>
      </div>
      <div class="tooltip" data-tip="Discord">
        <a href="https://discord.gg/HHnSjeGN4d" target="_blank" rel="noopener noreferrer" class="btn btn-soft btn-square btn-lg btn-accent shadow-lg">
          <Icon icon="mingcute:discord-line" class="size-7" />
        </a>
      </div>
      <div class="tooltip" data-tip="GitHub">
        <a href="https://github.com/EnderOksam/GSGW-Reader" target="_blank" rel="noopener noreferrer" class="btn btn-soft btn-square btn-lg btn-info shadow-lg">
          <Icon icon="mdi:github" class="size-7" />
        </a>
      </div>
      <StarField>
        <div class="tooltip" data-tip="Info">
          <a href="/info" class="btn btn-soft btn-square btn-lg btn-ghost shadow-lg info-glow">
            <Icon icon="mdi:information-outline" class="size-7" />
          </a>
        </div>
      </StarField>
    </div>

    <div class="flex flex-col items-center">
      <div class="max-w-md text-center md:text-left">
        <h1 class="lg:text-5xl text-3xl font-bold text-primary filter drop-shadow-[0_0_10px_#c47f0a] w-full block md:text-left">
          Got Dropped into a Ghost Story, Still Gotta Work
        </h1>
        <p class="py-6 lg:text-2xl text-sm md:text-lg lg:w-full md:w-4/5 w-full brightness-95 md:text-left">
          A pop-up event for some 'modern fantasy' media… I loved so much that I even took a precious day off work to attend. <br> <br> On that day, I ended up transmigrating as a character in that very fantasy world.
        </p>
      </div>

      <div class="block md:hidden text-white/25 text-xs text-center mb-1">(Interact with the card to access the books)</div>
      <div class="flex md:hidden flex-row items-center gap-3 mt-4">
        <div class="tooltip" data-tip="Download">
          <a href="/download" class="btn btn-soft btn-square btn-lg btn-secondary shadow-lg">
            <Icon icon="material-symbols:download" class="size-7" />
          </a>
        </div>
        <div class="tooltip" data-tip="Contribute">
          <a href="https://github.com/EnderOksam/GSGW-Reader/blob/main/contributing.md" target="_blank" rel="noopener noreferrer" class="btn btn-soft btn-square btn-lg btn-warning shadow-lg">
            <Icon icon="ri:edit-line" class="size-7" />
          </a>
        </div>
        <div class="tooltip" data-tip="Discord">
          <a href="https://discord.gg/HHnSjeGN4d" target="_blank" rel="noopener noreferrer" class="btn btn-soft btn-square btn-lg btn-accent shadow-lg">
            <Icon icon="mingcute:discord-line" class="size-7" />
          </a>
        </div>
        <div class="tooltip" data-tip="GitHub">
          <a href="https://github.com/EnderOksam/GSGW-Reader" target="_blank" rel="noopener noreferrer" class="btn btn-soft btn-square btn-lg btn-info shadow-lg">
            <Icon icon="mdi:github" class="size-7" />
          </a>
        </div>
        <StarField>
          <div class="tooltip" data-tip="Info">
            <a href="/info" class="btn btn-soft btn-square btn-lg btn-ghost shadow-lg info-glow">
              <Icon icon="mdi:information-outline" class="size-7" />
            </a>
          </div>
        </StarField>
      </div>

    </div>
  </div>
</main>

<style>
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
