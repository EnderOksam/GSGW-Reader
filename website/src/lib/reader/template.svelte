<script>
  import css from "../../../../reader.css?url";
  import { readerState } from "$lib/reader.svelte";
  import { untrack } from 'svelte';

  // These variables are the targets for build_web.py's regex replacement.
  // DO NOT change the formatting of these two lines.
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

<article class="reader-container">
  {@html html_content}
</article>

<style>
  /* 1. Main Page Layout */
  .reader-container {
    text-align: center; /* General text is centered for the "novel" look */
    max-width: 800px;
    margin: 0 auto;
    padding: 2rem;
    line-height: 1.8;
    color: #1a1a1a;
    font-family: 'Inter', system-ui, sans-serif;
  }

  /* 2. Global styling for Markdown-injected paragraphs */
  .reader-container :global(p) {
    margin-bottom: 1.5rem;
  }

  /* 3. Global styling for default horizontal rules */
  .reader-container :global(hr) {
    margin: 2.5rem auto;
    width: 50%;
    border: 0;
    border-top: 1px solid rgba(0, 0, 0, 0.1);
    opacity: 0.6;
  }

  /* 4. THE WIKI/SYSTEM WINDOW 
     Triggered by ::: {.wiki-window} in Markdown */
  .reader-container :global(.wiki-window) {
    margin: 3rem auto;
    padding: 2rem;
    background-color: #ffffff; /* Contrast against page background */
    border: 1px solid #d1d5db;
    border-radius: 4px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
    text-align: left; /* Wikis and reports are easier to read left-aligned */
    max-width: 90%;
  }

  /* Resetting HRs inside the Wiki Window to be full-width and darker */
  .reader-container :global(.wiki-window hr) {
    width: 100%;
    margin: 1rem 0;
    border-top: 1px solid #e5e7eb;
    opacity: 1;
  }

  /* Styling bold titles inside the window */
  .reader-container :global(.wiki-window strong) {
    display: block;
    font-size: 1.15rem;
    color: #000;
    margin-bottom: 0.5rem;
  }

  /* Adjusting font for the Wiki Window to look more "official" */
  .reader-container :global(.wiki-window p) {
    font-size: 0.95rem;
    color: #374151;
    margin-bottom: 0.75rem;
  }
</style>