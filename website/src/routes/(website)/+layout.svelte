<script lang="ts">
  import AnimatedInkTexture from "$lib/AnimatedInkTexture.svelte";
  import Icon from "@iconify/svelte";
  import "../../app.css";
  import { page } from "$app/state";
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

  $effect(() => {
    const _ = page.url.href;
    document.documentElement.setAttribute("data-theme", "sunset");
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

{#if !isEditorPage}
  <AnimatedInkTexture />
{/if}

{#if !isHomePage && !isEditorPage}
  <div class="fixed top-4 left-4 z-50">
    <button
      onclick={handleBack}
      class="btn btn-circle btn-ghost bg-base-300/70 hover:bg-base-300 transition-all shadow-lg"
      aria-label="Go back"
    >
      <Icon icon="material-symbols:arrow-back-rounded" class="size-6" />
    </button>
  </div>
{/if}

{@render children()}

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
</style>
