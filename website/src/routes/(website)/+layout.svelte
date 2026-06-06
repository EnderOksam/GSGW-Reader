<script lang="ts">
  import Icon from "@iconify/svelte";
  import "../../app.css";
  import { page } from "$app/state";
  import { browser, dev } from "$app/environment";
  import { goto } from "$app/navigation";

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
  <meta
    property="og:description"
    content="A pop-up event for some 'modern fantasy' media… I loved so much that I even took a precious day off work to attend.

On that day, I ended up transmigrating as a character in that very fantasy world."
  />
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:title" content="GSGW-Reader" />
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
    background: #0d0d0d;
  }

  :global(body)::before {
    content: "";
    position: fixed;
    inset: 0;
    pointer-events: none;
    z-index: 0;
    background: repeating-linear-gradient(
      0deg,
      transparent 0px,
      transparent 2px,
      rgba(255, 255, 255, 0.035) 2px,
      rgba(255, 255, 255, 0.035) 4px
    );
    filter: blur(0.5px);
  }

  :global(body)::after {
    content: "";
    position: fixed;
    inset: 0;
    pointer-events: none;
    z-index: 0;
    opacity: 0.025;
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
    background-repeat: repeat;
    background-size: 256px 256px;
    animation: crt-shift 8s steps(4) infinite;
  }

  :global {
    @keyframes crt-shift {
      0% { background-position: 0 0; }
      25% { background-position: 5px 3px; }
      50% { background-position: -3px 7px; }
      75% { background-position: 2px -4px; }
      100% { background-position: 0 0; }
    }
  }

  .content {
    position: relative;
    z-index: 1;
    backdrop-filter: blur(0.8px);
  }
</style>
