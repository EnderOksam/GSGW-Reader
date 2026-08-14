<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  import Icon from "@iconify/svelte";
  import "../../app.css";
  import { page } from "$app/state";
  import { browser, dev } from "$app/environment";
  import { goto } from "$app/navigation";
  import bgImage from "$lib/assets/background.jpg";
  import { BackgroundShader } from "$lib/bgShader";

  let { children } = $props();

  let path = $derived(page.url.pathname.replace(/\/$/, "") || "/");
  let isHomePage = $derived(path === "/");
  let isEditorPage = $derived(path === "/dev/editor" || path.startsWith("/dev/editor/"));

  let bgCanvas: HTMLCanvasElement;
  let bgShader: BackgroundShader | null = null;

  onMount(async () => {
    bgShader = new BackgroundShader(bgCanvas, bgImage);
    bgShader.start();
  });

  onDestroy(() => {
    bgShader?.dispose();
  });

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

<canvas
  bind:this={bgCanvas}
  class="bg"
  aria-hidden="true"
  style="background-image:url({bgImage});background-size:cover;background-position:center;"
></canvas>

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
    inset: 0;
    z-index: -1;
    display: block;
    width: 100%;
    height: 100%;
    background-color: #0d0d0d;
    filter: blur(5px);
  }

  .content {
    position: relative;
    z-index: 1;
    backdrop-filter: blur(0.8px);
  }
</style>
