<script lang="ts">
  import { page } from "$app/state";
  import Giscus from "@giscus/svelte";
  import Icon from "@iconify/svelte";
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

  <div id="comments" class="mx-auto max-w-4xl px-4 pb-4 pt-2">
    <div class="rounded-2xl border border-base-content/10 bg-base-200 shadow-xl shadow-base-content/5 overflow-hidden">
      <div class="px-4 sm:px-8 pt-6 pb-2">
        <div class="flex items-center gap-2">
          <Icon icon="lucide:message-square-text" class="size-4 text-base-content/30 shrink-0" />
          <span class="text-xs font-mono font-bold text-base-content/30 uppercase tracking-widest">Comments</span>
        </div>
      </div>
      <div class="px-4 sm:px-8 pb-8">
        {#key page.url.pathname}
          {#if currentChMeta.discussion}
            <Giscus
              id="manwha-comments"
              repo="EnderOksam/GSGW-Reader"
              repoId="R_kgDOSUYftA"
              category="General"
              categoryId="DIC_kwDOSUYftM4C9WvT"
              mapping="number"
              term={String(currentChMeta.discussion)}
              strict="1"
              reactionsEnabled="1"
              emitMetadata="0"
              inputPosition="top"
              theme="preferred_color_scheme"
              lang="en"
              loading="eager"
            />
          {:else}
            <Giscus
              id="manwha-comments"
              repo="EnderOksam/GSGW-Reader"
              repoId="R_kgDOSUYftA"
              category="General"
              categoryId="DIC_kwDOSUYftM4C9WvT"
              mapping="pathname"
              term=""
              strict="0"
              reactionsEnabled="1"
              emitMetadata="0"
              inputPosition="top"
              theme="preferred_color_scheme"
              lang="en"
              loading="eager"
            />
          {/if}
        {/key}
      </div>
    </div>
  </div>
</div>
