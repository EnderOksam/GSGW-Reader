<script lang="ts">
  import { page } from "$app/state";
  import Giscus from "@giscus/svelte";

  let { children } = $props();
</script>

<div class="min-h-screen w-full bg-base-100 text-base-content relative">
  {@render children()}
</div>

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
      theme="preferred_color_scheme"
      lang="en"
      loading="eager"
    />
  {/key}
</div>
