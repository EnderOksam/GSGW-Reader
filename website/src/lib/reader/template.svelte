<script lang="ts">

  import css from "../../../../reader.css?url";
  import "$lib/reader/reader-windows.css";

  import { readerState } from "$lib/reader.svelte";
  import { hydrateTwitterEmbeds } from "$lib/reader/twitter-embeds";

  import { untrack } from 'svelte';



  let ch_meta = null;

  let html_content = "";



  $effect(() => {

    if (ch_meta) {

      untrack(() => {

        readerState.ch_meta = ch_meta;

      });

    }

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

