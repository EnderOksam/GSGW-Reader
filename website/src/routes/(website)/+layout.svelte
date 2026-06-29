<script lang="ts">
  import Icon from "@iconify/svelte";
  import "../../app.css";
  import { page } from "$app/state";
  import { browser, dev } from "$app/environment";
  import { goto } from "$app/navigation";
  import bgImage from "$lib/assets/background.jpg";
  import imgLotmCover from "$lib/assets/web-lotm-cover.jpg";

  let { children } = $props();

  let path = $derived(page.url.pathname.replace(/\/$/, "") || "/");
  let isHomePage = $derived(path === "/");
  let isEditorPage = $derived(path === "/dev/editor" || path.startsWith("/dev/editor/"));

  function handleBack() {
    if (typeof window !== "undefined" && window.history.length > 1) {
      goto("../");
    } else {
      goto("/");
    }
  }

  function getCachedTheme(): string {
    if (!browser) return "sunset";
    try {
      const saved = localStorage.getItem("readerSettings");
      if (saved) {
        const parsed = JSON.parse(saved);
        if (parsed.theme) return parsed.theme;
      }
    } catch {}
    return "sunset";
  }

  $effect(() => {
    const _ = page.url.href;
    document.documentElement.setAttribute("data-theme", getCachedTheme());
    document.documentElement.style.setProperty("--bg-image", `url(${bgImage})`);
  });
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
  <meta property="og:image" content={imgLotmCover} />
  <meta
    property="og:description"
    content="A pop-up event for some 'modern fantasy' media… I loved so much that I even took a precious day off work to attend.

On that day, I ended up transmigrating as a character in that very fantasy world."
  />
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:title" content="GSGW-Reader" />
  <meta name="twitter:image" content={imgLotmCover} />
  <meta
    name="twitter:description"
    content="A pop-up event for some 'modern fantasy' media… I loved so much that I even took a precious day off work to attend.

On that day, I ended up transmigrating as a character in that very fantasy world."
  />
</svelte:head>

{#if !isHomePage && !isEditorPage}
  <div class="fixed top-4 left-4 z-50 flex gap-2">
    <button
      onclick={handleBack}
      class="btn btn-circle btn-ghost bg-base-300/70 hover:bg-base-300 transition-all shadow-lg"
      aria-label="Go back"
    >
      <Icon icon="material-symbols:arrow-back-rounded" class="size-6" />
    </button>
  </div>
{/if}

<div class="bg"></div>

<div class="content">
  {@render children()}
</div>

<style>
  :global(:root) {
    --c1: #1C3760;
    --c2: #4682B4;
    --c3: #FF69B4;
    --c4: #FF4500;
    --c5: #4B0082;
    --c6: #C0C0C0;
    --c7: #FFFF00;
    --c8: #3A2E3B;
    --c9: #E0115F;
  }

  :global(body) {
    background: transparent;
  }



  .bg {
    position: fixed;
    inset: -10%;
    z-index: -1;
    background-color: #0d0d0d;
    background-image: var(--bg-image);
    background-size: cover;
    background-position: center;
    background-repeat: no-repeat;
    filter: blur(12px);
    animation: swirl 30s ease-in-out infinite alternate;
    transform-origin: center;
  }

  @keyframes swirl {
    0% {
      transform: rotate(-0.5deg) scale(1);
    }
    50% {
      transform: rotate(0.5deg) scale(1.02);
    }
    100% {
      transform: rotate(-0.25deg) scale(1.03);
    }
  }

  .content {
    position: relative;
    z-index: 1;
    backdrop-filter: blur(0.8px);
  }
</style>
