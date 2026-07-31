<script lang="ts">

  import css from "../../../../reader.css?url";
  import "$lib/reader/reader-windows.css";

  import { readerState } from "$lib/reader.svelte";
  import { hydrateTwitterEmbeds } from "$lib/reader/twitter-embeds";
  import { consumeSnippetTarget } from "$lib/content-search";

  import { untrack, onMount } from 'svelte';



  let ch_meta = null;

  let html_content = "";

  let footnotes = "";



  $effect(() => {

    if (ch_meta) {

      untrack(() => {

        readerState.ch_meta = ch_meta;

      });

    }

  });

  $effect(() => {
    readerState.footnotes = footnotes;
  });

  onMount(() => {
    const target = consumeSnippetTarget();
    if (!target) return;
    const { query } = target;
    setTimeout(() => {
      const article = document.querySelector("article.reader-container");
      if (!article) return;
      const q = query.toLowerCase();
      const all = article.querySelectorAll("p, span, div, h1, h2, h3, h4, strong, em");
      for (const el of all) {
        const text = el.textContent?.toLowerCase() || "";
        if (text.includes(q)) {
          el.scrollIntoView({ behavior: "smooth", block: "center" });
          el.classList.add("search-highlight");
          setTimeout(() => el.classList.remove("search-highlight"), 2500);
          return;
        }
      }
    }, 300);
  });



  $effect(() => {
    hydrateTwitterEmbeds();
  });

</script>



<svelte:head>

  <link rel="stylesheet" href={css}>

</svelte:head>



<article

  class="reader-container"

>

  {@html html_content}

</article>

