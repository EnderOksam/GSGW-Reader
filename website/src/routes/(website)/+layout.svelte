<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  import Icon from "@iconify/svelte";
  import "../../app.css";
  import { page } from "$app/state";
  import { browser, dev } from "$app/environment";
  import { goto } from "$app/navigation";
  import bgImage from "$lib/assets/background.jpg";
  import { BackgroundShader } from "$lib/bgShader";
  import { uderTransition } from "$lib/uder-transition";

  let { children } = $props();

  let path = $derived(page.url.pathname.replace(/\/$/, "") || "/");
  let isHomePage = $derived(path === "/");
  let isEditorPage = $derived(path === "/dev/editor" || path.startsWith("/dev/editor/"));

  let bgCanvas: HTMLCanvasElement;
  let bgShader: BackgroundShader | null = null;

  let uderPhase = $state<"idle" | "fade-in" | "hold" | "fade-out" | "back-fade" | "back-hold">("idle");

  $effect(() => {
    const unsub = uderTransition.subscribe((v) => (uderPhase = v));
    return unsub;
  });

  $effect(() => {
    if (uderPhase === "fade-in" && path === "/book/temp") {
      const t = setTimeout(() => {
        uderTransition.set("hold");
        const t2 = setTimeout(() => {
          uderTransition.set("fade-out");
          const t3 = setTimeout(() => uderTransition.set("idle"), 600);
        }, 2000);
      }, 100);
      return () => { clearTimeout(t); };
    }
  });

  $effect(() => {
    if (uderPhase === "back-fade" && path === "/book/temp") {
      const t = setTimeout(() => {
        uderTransition.set("back-hold");
        const t2 = setTimeout(() => {
          navigateBack();
        }, 80);
      }, 80);
      return () => { clearTimeout(t); };
    }
  });

  onMount(async () => {
    bgShader = new BackgroundShader(bgCanvas, bgImage);
    bgShader.start();
  });

  onDestroy(() => {
    bgShader?.dispose();
  });

  function navigateBack() {
    if (typeof window !== "undefined" && window.history.length > 1) {
      goto("../");
    } else {
      goto("/");
    }
  }

  function handleBack() {
    if (path === "/book/temp") {
      uderTransition.set("back-fade");
      return;
    }
    navigateBack();
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

  $effect(() => {
    if (bgShader) {
      bgShader.setTextureStrength(path === "/book/temp" ? 0 : 1);
    }
  });

  $effect(() => {
    if (path !== "/book/temp" && (uderPhase === "back-fade" || uderPhase === "back-hold")) {
      const t = setTimeout(() => uderTransition.set("idle"), 150);
      return () => clearTimeout(t);
    }
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

<div
  class="fixed inset-0 z-[100] bg-black pointer-events-none transition-opacity"
  class:duration-500={uderPhase !== 'back-fade' && uderPhase !== 'back-hold'}
  class:duration-100={uderPhase === 'back-fade' || uderPhase === 'back-hold'}
  style="opacity: {uderPhase === 'idle' ? 0 : 1}"
  class:pointer-events-auto={uderPhase !== 'idle'}
>
  {#if uderPhase === 'hold' || uderPhase === 'fade-out'}
    <div class="absolute inset-0 flex flex-col items-center justify-center gap-6 {uderPhase === 'fade-out' ? 'transition-opacity duration-500 opacity-0' : 'transition-opacity duration-500 opacity-100'}">
      <img src="/assets/ghost.webp" alt="" class="w-32 h-32 md:w-48 md:h-48 object-contain" />
      <p class="text-white/60 text-xs md:text-sm font-mono uppercase tracking-[0.25em] text-center max-w-md px-4">Prophecy of the Apocalypse: Darkness Exploration Records</p>
    </div>
  {/if}
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
    filter: blur(6px);
  }

  .content {
    position: relative;
    z-index: 1;
    backdrop-filter: blur(0.8px);
  }
</style>
