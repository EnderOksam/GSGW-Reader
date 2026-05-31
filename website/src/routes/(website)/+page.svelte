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
    "https://x.com/uoongpig/status/1917150679854149695?s=20",
    "https://x.com/uoongpig/status/1872288337043828780?s=20",
    "https://x.com/uoongpig/status/1852241314630549886?s=20",
    "https://x.com/uoongpig/status/1909183405956420090?s=20",
  ];

  const TWITTER_RE = /https?:\/\/(?:x|twitter)\.com\/(\w+)\/status\/(\d+)(?:\/photo\/(\d+))?/;

  function fmt(n: string): string {
    const num = parseInt(n, 10);
    if (isNaN(num)) return n;
    if (num >= 1_000_000) return (num / 1_000_000).toFixed(num % 1_000_000 === 0 ? 0 : 1).replace(/\.0$/, '') + 'M';
    if (num >= 1_000) return (num / 1_000).toFixed(num % 1_000 === 0 ? 0 : 1).replace(/\.0$/, '') + 'k';
    return num.toLocaleString();
  }

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
    text: string;
    likes: string;
    retweets: string;
    replies: string;
    views: string;
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
          const text = t.text || '';
          const likes = t.likes !== undefined ? String(t.likes) : '';
          const retweets = t.retweets !== undefined ? String(t.retweets) : '';
          const replies = t.replies !== undefined ? String(t.replies) : '';
          const views = t.views !== undefined ? String(t.views) : '';

          const item = (src: string) => ({ src, tweetUrl, name, user, text, likes, retweets, replies, views });

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

<svelte:head>
  <title>GSGW-Reader</title>
</svelte:head>

<a 
  href="/error-test-trigger" 
  class="fixed top-4 left-4 z-50 opacity-0 hover:opacity-20 transition-opacity text-white cursor-default"
>
  #
</a>

{#if showBanner}
  <div class="fixed top-0 left-0 right-0 z-50 flex items-center justify-center gap-4 bg-base-300/90 backdrop-blur-sm border-b border-white/5 px-4 py-3 text-sm text-white/90">
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

<div class="relative min-h-dvh flex flex-col items-center justify-center p-6 md:p-12">
  <div class="flex flex-col md:flex-row items-center justify-center gap-10 md:gap-16 w-full max-w-6xl">
    <!-- Card + side buttons -->
    <div class="flex items-center gap-4">
      <a href="/book" class="block">
        <div class="hover-3d relative">
          {#if loaded && mediaItems.length}
            <div class="bg-[#16181c] border border-white/[0.08] rounded-2xl shadow-[0_4px_24px_rgba(0,0,0,0.4)] overflow-hidden w-[75vw] max-w-[40vh] md:w-[48vh] px-4 pb-3">
              <div class="flex items-baseline gap-1.5 py-3 pb-1">
                <span class="text-[#1d9bf0] text-[0.9375rem] font-bold truncate" style="text-shadow: 0 0 8px rgba(29,155,240,0.5)">{mediaItems[currentIndex].name}</span>
                <span class="text-[#71767b] text-[0.8125rem]">@{mediaItems[currentIndex].user}</span>
                <svg class="text-[#71767b] ml-auto shrink-0 opacity-60" viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>
              </div>
              {#if mediaItems[currentIndex].text}
                <p class="text-[#71767b] text-[0.85rem] leading-[1.4] mt-2 mb-2 line-clamp-3">
                  {mediaItems[currentIndex].text}
                </p>
              {/if}
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
              <div class="flex items-center gap-3 mt-2 pt-2 text-[#71767b] text-[0.75rem] border-t border-white/10">
                <span class="flex items-center gap-1" title="Views">
                  <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                  {fmt(mediaItems[currentIndex].views)}
                </span>
                <span class="flex items-center gap-1" title="Replies">
                  <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
                  {fmt(mediaItems[currentIndex].replies)}
                </span>
                <span class="flex items-center gap-1" title="Reposts">
                  <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M17 1l4 4-4 4"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/><path d="M7 23l-4-4 4-4"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/></svg>
                  {fmt(mediaItems[currentIndex].retweets)}
                </span>
                <span class="flex items-center gap-1" title="Likes">
                  <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>
                  {fmt(mediaItems[currentIndex].likes)}
                </span>
              </div>
            </div>
          {:else}
            <div class="bg-[#16181c] border border-white/[0.08] rounded-2xl shadow-[0_4px_24px_rgba(0,0,0,0.4)] overflow-hidden w-[75vw] max-w-[40vh] md:w-[48vh] px-4 pb-3">
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

      <div class="hidden md:flex flex-col items-center gap-3">
        <div class="tooltip" data-tip="Download">
          <a href="/download" class="btn btn-soft btn-square btn-lg btn-secondary shadow-lg">
            <Icon icon="material-symbols:download" class="size-6" />
          </a>
        </div>
        <div class="tooltip" data-tip="Contribute">
          <a href="https://github.com/EnderOksam/GSGW-Reader/blob/main/contributing.md" target="_blank" rel="noopener noreferrer" class="btn btn-soft btn-square btn-lg btn-warning shadow-lg">
            <Icon icon="ri:edit-line" class="size-6" />
          </a>
        </div>
        <div class="tooltip" data-tip="Discord">
          <a href="https://discord.gg/HHnSjeGN4d" target="_blank" rel="noopener noreferrer" class="btn btn-soft btn-square btn-lg btn-accent shadow-lg">
            <Icon icon="mingcute:discord-line" class="size-6" />
          </a>
        </div>
        <div class="tooltip" data-tip="GitHub">
          <a href="https://github.com/EnderOksam/GSGW-Reader" target="_blank" rel="noopener noreferrer" class="btn btn-soft btn-square btn-lg btn-info shadow-lg">
            <Icon icon="mdi:github" class="size-6" />
          </a>
        </div>
        <StarField>
          <div class="tooltip" data-tip="Info">
            <a href="/info" class="btn btn-soft btn-square btn-lg btn-ghost shadow-lg info-glow">
              <Icon icon="mdi:information-outline" class="size-6" />
            </a>
          </div>
        </StarField>
      </div>
    </div>

    <!-- Title + Description -->
    <div class="flex flex-col items-center md:items-start gap-5 max-w-lg">
      <h1 class="text-3xl md:text-5xl font-bold leading-tight text-primary text-center md:text-left filter drop-shadow-[0_0_10px_#c47f0a]">
        Got Dropped into a Ghost Story, Still Gotta Work
      </h1>
      <p class="text-sm md:text-base text-white/60 leading-relaxed text-center md:text-left">
        A pop-up event for some 'modern fantasy' media… I loved so much that I even took a precious day off work to attend.
      </p>
      <p class="text-sm md:text-base text-white/60 leading-relaxed text-center md:text-left">
        On that day, I ended up transmigrating as a character in that very fantasy world.
      </p>
    </div>
  </div>

  <div class="flex md:hidden items-center justify-center gap-3 mt-10">
    <div class="tooltip" data-tip="Download">
      <a href="/download" class="btn btn-soft btn-square btn-lg btn-secondary shadow-lg">
        <Icon icon="material-symbols:download" class="size-6" />
      </a>
    </div>
    <div class="tooltip" data-tip="Contribute">
      <a href="https://github.com/EnderOksam/GSGW-Reader/blob/main/contributing.md" target="_blank" rel="noopener noreferrer" class="btn btn-soft btn-square btn-lg btn-warning shadow-lg">
        <Icon icon="ri:edit-line" class="size-6" />
      </a>
    </div>
    <div class="tooltip" data-tip="Discord">
      <a href="https://discord.gg/HHnSjeGN4d" target="_blank" rel="noopener noreferrer" class="btn btn-soft btn-square btn-lg btn-accent shadow-lg">
        <Icon icon="mingcute:discord-line" class="size-6" />
      </a>
    </div>
    <div class="tooltip" data-tip="GitHub">
      <a href="https://github.com/EnderOksam/GSGW-Reader" target="_blank" rel="noopener noreferrer" class="btn btn-soft btn-square btn-lg btn-info shadow-lg">
        <Icon icon="mdi:github" class="size-6" />
      </a>
    </div>
    <StarField>
      <div class="tooltip" data-tip="Info">
        <a href="/info" class="btn btn-soft btn-square btn-lg btn-ghost shadow-lg info-glow">
          <Icon icon="mdi:information-outline" class="size-6" />
        </a>
      </div>
    </StarField>
  </div>
</div>

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
