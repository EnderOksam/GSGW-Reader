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



  /* --- BLACK WINDOW (CRT) --- */

  .reader-container :global(.black-window) {
    margin: 2.5rem auto;
    background: #000000;
    border: 1px solid #333;
    border-radius: 4px;
    max-width: 88%;
    position: relative;
    box-shadow: 0 0 20px rgba(0,0,0,0.6);
    padding: 1.5rem 2rem 1rem;
    text-align: center;
    font-weight: 700;
    background-image: repeating-linear-gradient(
      0deg,
      transparent,
      transparent 2px,
      rgba(255,255,255,0.03) 2px,
      rgba(255,255,255,0.03) 4px
    );
  }

  .reader-container :global(.black-window p) {
    color: #e0e0e0 !important;
    margin: 0.8rem 0;
    font-size: 1rem;
    line-height: 1.6;
    text-align: center;
  }

  .reader-container :global(.black-window p strong:only-child),
  .reader-container :global(.black-window p strong:first-child) {
    display: block;
    font-size: 1.25rem;
    margin: 1rem 0 0.8rem;
  }

  .reader-container :global(.black-window p:last-of-type) {
    margin-bottom: 0.5rem;
  }

  .reader-container :global(.black-window p:empty) {
    display: none;
  }



  /* --- SYSTEM WINDOW (double-line) --- */

  .reader-container :global(.system-window) {
    margin: 2.5rem auto;
    background: #1a1a1a;
    border: 1px solid #444;
    border-radius: 4px;
    max-width: 88%;
    position: relative;
    box-shadow: 0 0 20px rgba(0,0,0,0.6);
    padding: 1.5rem 2rem 1rem;
    text-align: center;
    font-weight: 700;
    transition: box-shadow 0.3s;
  }

  .reader-container :global(.system-window):hover {
    box-shadow: 0 0 20px rgba(0,0,0,0.6), 0 0 15px rgba(100, 100, 100, 0.3);
  }

  .reader-container :global(.system-window)::before {
    content: '';
    position: absolute;
    inset: 8px;
    box-shadow:
      inset 0 0 0 1px #888,
      inset 0 0 0 5px #888;
    pointer-events: none;
    transition: box-shadow 0.3s;
  }

  .reader-container :global(.system-window):hover::before {
    box-shadow:
      inset 0 0 0 1px #aaa,
      inset 0 0 0 5px #aaa;
  }

  .reader-container :global(.system-window)::after {
    content: '';
    position: absolute;
    inset: 17px;
    pointer-events: none;
    background:
      linear-gradient(to right, #888, transparent) 0 0 / 20px 1px no-repeat,
      linear-gradient(to bottom, #888, transparent) 0 0 / 1px 20px no-repeat,
      linear-gradient(to left, #888, transparent) 100% 0 / 20px 1px no-repeat,
      linear-gradient(to bottom, #888, transparent) 100% 0 / 1px 20px no-repeat,
      linear-gradient(to left, #888, transparent) 100% 100% / 20px 1px no-repeat,
      linear-gradient(to top, #888, transparent) 100% 100% / 1px 20px no-repeat,
      linear-gradient(to right, #888, transparent) 0 100% / 20px 1px no-repeat,
      linear-gradient(to top, #888, transparent) 0 100% / 1px 20px no-repeat;
  }

  .reader-container :global(.system-window):hover::after {
    background:
      linear-gradient(to right, #aaa, transparent) 0 0 / 20px 1px no-repeat,
      linear-gradient(to bottom, #aaa, transparent) 0 0 / 1px 20px no-repeat,
      linear-gradient(to left, #aaa, transparent) 100% 0 / 20px 1px no-repeat,
      linear-gradient(to bottom, #aaa, transparent) 100% 0 / 1px 20px no-repeat,
      linear-gradient(to left, #aaa, transparent) 100% 100% / 20px 1px no-repeat,
      linear-gradient(to top, #aaa, transparent) 100% 100% / 1px 20px no-repeat,
      linear-gradient(to right, #aaa, transparent) 0 100% / 20px 1px no-repeat,
      linear-gradient(to top, #aaa, transparent) 0 100% / 1px 20px no-repeat;
  }

  .reader-container :global(.system-window p) {
    color: #e0e0e0 !important;
    margin: 0.8rem 0;
    font-size: 1rem;
    line-height: 1.6;
    text-align: center;
  }

  .reader-container :global(.system-window:not(.no-fl-dividers) > p:first-of-type) {
    padding: 0.75rem 0;
    font-size: 1.25rem;
    background-image:
      linear-gradient(90deg, transparent, #888, transparent),
      linear-gradient(90deg, transparent, #888, transparent);
    background-repeat: no-repeat;
    background-size: 80% 1px;
    background-position: center top, center bottom;
  }

  .reader-container :global(.system-window p:last-of-type) {
    margin-bottom: 0.5rem;
  }

  .reader-container :global(.system-window p:empty) {
    display: none;
  }



</style>