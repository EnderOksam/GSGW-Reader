<script lang="ts">

  import css from "../../../../reader.css?url";

  import { readerState } from "$lib/reader.svelte";

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

</script>



<svelte:head>

  <link rel="stylesheet" href={css}>

</svelte:head>



<article

  class="reader-container"

>

  {@html html_content}

</article>



<style>

  :root {

    --reader-text: #e0e0e0;

    --window-bg: #1e1e2e;

    --window-border: #3a3a5c;

    --window-text: #f8f9fa;

    --window-accent: #ff4d00;

  }



  .reader-container {

    max-width: 800px;

    margin: 0 auto;

    padding: 2rem;

    line-height: 1.6;

    color: var(--reader-text);

    font-family: var(--chapter-font, 'Inter', system-ui, sans-serif);

  }



  /* --- RECORD WINDOW --- */

  .reader-container :global(.wiki-window) {

    margin: 2.5rem auto;

    background: var(--window-bg);

    border: 1px solid var(--window-border);

    border-radius: 8px;

    max-width: 88%;

    position: relative;

    box-shadow: 0 4px 24px rgba(0,0,0,0.4);

    padding: 1.5rem 2rem 1rem;

    text-align: left;

  }



  .reader-container :global(.wiki-window)::before {
    content: "_ □ X";
    display: flex;
    justify-content: flex-end;
    background: var(--window-border);
    color: #ffffff;
    padding: 6px 14px;
    font-family: monospace;
    font-size: 16px;
    letter-spacing: 6px;
    margin: -1.5rem -2rem 1rem;
    border-bottom: 1px solid var(--window-border);
    border-radius: 8px 8px 0 0;
  }



  .reader-container :global(.wiki-window p) {

    color: var(--window-text) !important;

    margin: 0.8rem 0;

    font-size: 1rem;

    line-height: 1.6;

    text-align: left;

  }

  .reader-container :global(.wiki-window:not(.no-meta) p:first-of-type) {

    font-size: 0.8rem;

    opacity: 0.6;

    text-align: right;

    margin-bottom: 0.3rem;

  }



  .reader-container :global(.wiki-window strong),

  .reader-container :global(.wiki-window b) {

    color: inherit;

    font-weight: 700;

    font-size: 1rem;

  }



  .reader-container :global(.wiki-window p strong:only-child),

  .reader-container :global(.wiki-window p strong:first-child):not(b strong) {

    display: block;

    font-size: 1.25rem;

    margin: 1rem 0 0.8rem;

  }



  .reader-container :global(.wiki-window p:last-of-type) {

    margin-bottom: 0.5rem;

  }

  .reader-container :global(.wiki-window p:empty) {

    display: none;

  }





</style>