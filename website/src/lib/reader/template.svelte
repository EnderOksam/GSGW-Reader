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

  style="text-align: {(readerState as any).textAlign || 'left'}"

>

  {@html html_content}

</article>



<style>

  :root {

    --reader-text: #e0e0e0;

    --window-bg: #2d2d2d;

    --window-bar-bg: #4a4a4a;

    --window-border: #1a1a1a;

    --window-text: #f8f9fa;

  }



  .reader-container {

    max-width: 800px;

    margin: 0 auto;

    padding: 2rem;

    line-height: 1.6;

    color: var(--reader-text);

    font-family: 'Inter', system-ui, sans-serif;

  }



  /* --- THE COMPUTER WINDOW --- */

  .reader-container :global(.wiki-window) {

    margin: 3rem auto;

    background-color: var(--window-bg);

    border: 2px solid var(--window-border);

    border-radius: 6px;

    overflow: hidden;

    max-width: 90%;

    position: relative;

    box-shadow: 0 15px 40px rgba(0,0,0,0.6);

    display: flex;

    flex-direction: column;

    padding: 0;

    text-align: center;

  }



  /* Title Bar: Icons only, pinned far right */

  .reader-container :global(.wiki-window::before) {

    content: "_ □ X";

    display: flex;

    justify-content: flex-end;

    background: var(--window-bar-bg);

    color: #ffffff;

    padding: 8px 16px;

    font-family: monospace;

    font-size: 18px;

    letter-spacing: 8px;

    border-bottom: 2px solid var(--window-border);

  }



  /* Standard window text */

  .reader-container :global(.wiki-window p) {

    color: var(--window-text) !important;

    font-family: 'Courier New', Courier, monospace;

    margin: 1.2rem 2rem;

    font-size: 1.3rem;

    line-height: 1.5;

    text-align: center;

  }



  /* Bolded text inside the window is now Red */

  .reader-container :global(.wiki-window strong),

  .reader-container :global(.wiki-window b) {

    color: #ff4d4d !important; /* Vibrant Red */

    font-family: 'Courier New', Courier, monospace;

    font-weight: 700;

    font-size: 1.4rem; /* Slightly larger to emphasize bold */

  }



  /* Title highlights (specifically for bracketed headers) */

  .reader-container :global(.wiki-window p strong:first-child) {

    display: block;

    margin-top: 1rem;

    margin-bottom: 1rem;

  }



  .reader-container :global(.wiki-window p:last-child) {

    margin-bottom: 2rem;

  }



  .reader-container :global(.wiki-window hr) {

    width: 60%;

    margin: 1.5rem auto;

    border: 0;

    border-top: 2px solid #555;

  }

</style>