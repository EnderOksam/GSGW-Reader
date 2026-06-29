<script lang="ts">
  import { page } from "$app/state";
  import Giscus from "@giscus/svelte";
  import bookData from "$lib/meta.json";

  let { children } = $props();

  const currentTL = $derived(page.params.tl ?? "flame comics");
  const currentChapter = $derived(page.params.slug ?? "0");
  const chaptersForTL = $derived(
    (bookData as any)["manwha"]?.[currentTL] || []
  );
  const currentChMeta = $derived(
    chaptersForTL.find((ch: any) => ch.slug === currentChapter) ??
    { title: "", slug: "0" }
  );
</script>

<svelte:head>
  <title>GSGW Manwha - {currentChMeta.title}</title>
  <meta property="og:type" content="article" />
  <meta property="og:title" content="GSGW Manwha - {currentChMeta.title}" />
  <meta name="twitter:title" content="GSGW Manwha - {currentChMeta.title}" />
  {#if currentTL === "flame comics"}
    <meta property="og:description" content="Flame Comics" />
    <meta name="twitter:description" content="Flame Comics" />
  {:else}
    <meta property="og:description" content="" />
    <meta name="twitter:description" content="" />
  {/if}
</svelte:head>

<div class="min-h-screen w-full bg-base-100 text-base-content relative">
  {@render children()}

  <div id="comments" class="mx-auto max-w-4xl px-4 pb-16">
  {#key page.url.pathname}
    <Giscus
      repo="EnderOksam/GSGW-Reader"
      repoId="R_kgDOSUYftA"
      category="General"
      categoryId="DIC_kwDOSUYftM4C9WvT"
      mapping="pathname"
      strict="0"
      reactionsEnabled="1"
      emitMetadata="0"
      inputPosition="top"
      theme="dark"
      lang="en"
      loading="eager"
    />
  {/key}
</div>
</div>
