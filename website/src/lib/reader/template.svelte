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

    --window-bg: #1e1e2e;

    --window-border: #3a3a5c;

    --window-text: #ffffff;

    --window-accent: #ff4d00;

  }



  .reader-container {

    max-width: 800px;

    margin: 0 auto;

    padding: 1.25rem;

    line-height: 1.6;

    color: oklch(from var(--bc) l 0 h);

    font-family: var(--chapter-font, 'Inter', system-ui, sans-serif);

  }

  @media (min-width: 640px) {
    .reader-container {
      padding: 2rem;
    }
  }



  /* --- RECORD WINDOW --- */

  .reader-container :global(.wiki-window) {

    margin: 2.5rem auto;

    background: var(--window-bg);

    border: 1px solid var(--window-border);

    border-radius: 8px;

    max-width: 98%;

    position: relative;

    box-shadow: 0 4px 24px rgba(0,0,0,0.4);

    padding: 1em 1em 0.75em;

    text-align: left;

  }

  @media (min-width: 640px) {
    .reader-container :global(.wiki-window) {
      max-width: 88%;
      padding: 1.5em 2em 1em;
    }
  }



  .reader-container :global(.wiki-window)::before {
    content: "— ▢ X";
    display: flex;
    justify-content: flex-end;
    background: var(--window-border);
    color: #ffffff;
    padding: 0.375em 0.875em;
    font-family: monospace;
    font-size: 1em;
    letter-spacing: 0.375em;
    margin: -1em -1em 0.75em;
    border-bottom: 1px solid var(--window-border);
    border-radius: 8px 8px 0 0;
  }

  @media (min-width: 640px) {
    .reader-container :global(.wiki-window)::before {
      margin: -1.5em -2em 1em;
    }
  }



  .reader-container :global(.wiki-window p) {

    color: var(--window-text) !important;

    margin: 0.8em 0;

    line-height: 1.6;

    text-align: left;

  }

  .reader-container :global(.wiki-window:not(.no-meta) p:first-of-type) {

    font-size: 0.8em;

    opacity: 0.6;

    text-align: right;

    margin-bottom: 0.3em;

  }



  .reader-container :global(.wiki-window strong),

  .reader-container :global(.wiki-window b) {

    color: inherit;

    font-weight: 700;

  }



  .reader-container :global(.wiki-window p strong:only-child),

  .reader-container :global(.wiki-window p strong:first-child):not(b strong) {

    display: block;

    font-size: 1.25em;

    margin: 1em 0 0.8em;

  }



  .reader-container :global(.wiki-window p:last-of-type) {

    margin-bottom: 0.5em;

  }

  .reader-container :global(.wiki-window p:empty) {
    display: none;
  }



  /* --- RECORD WINDOW (greyish-blue) --- */

  .reader-container :global(.record-window) {
    margin: 2.5rem auto;
    background: #1d2350;
    border: 1px solid rgba(255,255,255,0.15);
    border-radius: 8px;
    max-width: 98%;
    position: relative;
    box-shadow: 0 4px 24px rgba(0,0,0,0.4);
    padding: 1em 1em 0.75em;
    text-align: left;
  }

  @media (min-width: 640px) {
    .reader-container :global(.record-window) {
      max-width: 88%;
      padding: 1.5em 2em 1em;
    }
  }

  .reader-container :global(.record-window)::before {
    content: "— ▢ X";
    display: flex;
    justify-content: flex-end;
    background: rgba(0,0,0,0.25);
    color: #ffffff;
    padding: 0.375em 0.875em;
    font-family: monospace;
    font-size: 1em;
    letter-spacing: 0.375em;
    margin: -1em -1em 0.75em;
    border-bottom: 1px solid rgba(255,255,255,0.1);
    border-radius: 8px 8px 0 0;
  }

  @media (min-width: 640px) {
    .reader-container :global(.record-window)::before {
      margin: -1.5em -2em 1em;
    }
  }

  .reader-container :global(.record-window p) {
    color: #ffffff !important;
    margin: 0.8em 0;
    line-height: 1.6;
    text-align: left;
  }

  .reader-container :global(.record-window:not(.no-meta) p:first-of-type) {
    font-size: 0.8em;
    opacity: 0.6;
    text-align: right;
    margin-bottom: 0.3em;
  }

  .reader-container :global(.record-window strong),
  .reader-container :global(.record-window b) {
    color: inherit;
    font-weight: 700;
  }

  .reader-container :global(.record-window p strong:only-child),
  .reader-container :global(.record-window p strong:first-child):not(b strong) {
    display: block;
    font-size: 1.25em;
    margin: 1em 0 0.8em;
  }

  .reader-container :global(.record-window p:last-of-type) {
    margin-bottom: 0.5em;
  }

  .reader-container :global(.record-window p:empty) {
    display: none;
  }



  /* --- PLAIN WINDOW (no titlebar) --- */

  .reader-container :global(.plain-window) {

    margin: 2.5rem auto;

    background: var(--window-bg);

    border: 1px solid var(--window-border);

    border-radius: 8px;

    max-width: 98%;

    position: relative;

    box-shadow: 0 4px 24px rgba(0,0,0,0.4);

    padding: 1.5em 2em 1em;

    text-align: left;

  }

  @media (min-width: 640px) {
    .reader-container :global(.plain-window) {
      max-width: 88%;
    }
  }

  .reader-container :global(.plain-window p) {

    color: var(--window-text) !important;

    margin: 0.8em 0;

    line-height: 1.6;

    text-align: left;

  }

  .reader-container :global(.plain-window p:last-of-type) {

    margin-bottom: 0.5em;

  }

  .reader-container :global(.plain-window p:empty) {
    display: none;
  }



  /* --- &$ WINDOW (greyish-blue, no titlebar) --- */

  .reader-container :global(.followup-window) {
    margin: 2.5rem auto;
    background: #1d2350;
    border: 1px solid rgba(255,255,255,0.15);
    border-radius: 8px;
    max-width: 98%;
    position: relative;
    box-shadow: 0 4px 24px rgba(0,0,0,0.4);
    padding: 1.5em 2em 1em;
    text-align: left;
  }

  @media (min-width: 640px) {
    .reader-container :global(.followup-window) {
      max-width: 88%;
    }
  }

  .reader-container :global(.followup-window p) {
    color: #ffffff !important;
    margin: 0.8em 0;
    line-height: 1.6;
    text-align: left;
  }

  .reader-container :global(.followup-window p:last-of-type) {
    margin-bottom: 0.5em;
  }

  .reader-container :global(.followup-window p:empty) {
    display: none;
  }



  /* --- NOTE WINDOW (pale yellow notepad) --- */

  .reader-container :global(.note-window) {
    margin: 2.5rem auto;
    background: #fefce8;
    border: 1px solid #e6dec0;
    border-radius: 4px;
    max-width: 98%;
    position: relative;
    box-shadow:
      -4px 4px 0 #d4c060,
      0 4px 24px rgba(0,0,0,0.12);
    padding: 1em 1.25em 0.75em;
    text-align: left;
    overflow: hidden;
  }

  @media (min-width: 640px) {
    .reader-container :global(.note-window) {
      max-width: 88%;
      padding: 1.25em 1.75em 1em;
    }
  }

  .reader-container :global(.note-window)::before {
    content: "";
    display: block;
    background: #edd44d;
    height: 0.875em;
    margin: -1em -1.25em 0.75em;
    border-radius: 4px 4px 0 0;
    position: relative;
    z-index: 1;
  }

  @media (min-width: 640px) {
    .reader-container :global(.note-window)::before {
      margin: -1.25em -1.75em 0.75em;
    }
  }

  .reader-container :global(.note-window)::after {
    content: '';
    position: absolute;
    inset: 0;
    border-radius: 4px;
    background-image: repeating-linear-gradient(
      transparent,
      transparent 1.6em,
      rgba(160,160,160,0.35) 1.6em,
      rgba(160,160,160,0.35) 1.65em
    );
    filter: blur(0.05em);
    pointer-events: none;
    z-index: 0;
  }

  .reader-container :global(.note-window p) {
    color: #000000;
    margin: 0.8em 0;
    line-height: 1.7;
    text-align: left;
    position: relative;
    z-index: 1;
  }

  .reader-container :global(.note-window:not(.no-meta) p:first-of-type) {
    color: #4a6fa5;
    font-size: 1.35em;
    font-weight: 600;
    text-align: left;
    margin-bottom: 0.3em;
  }

  .reader-container :global(.note-window strong),
  .reader-container :global(.note-window b) {
    color: inherit;
    font-weight: 700;
  }

  .reader-container :global(.note-window p:last-of-type) {
    margin-bottom: 0.5em;
  }

  .reader-container :global(.note-window p:empty) {
    display: none;
  }



  /* --- STICKY NOTE (folded corner) --- */

  .reader-container :global(.sticky-window) {
    margin: 2.5rem auto;
    background: #fefce8;
    border: 1px solid #e6dec0;
    border-radius: 2px;
    max-width: 25em;
    min-height: 15.625em;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    position: relative;
    box-shadow:
      -3px 3px 0 #d4c060,
      0 4px 24px rgba(0,0,0,0.12);
    padding: 1.5em;
    text-align: center;
  }



  .reader-container :global(.sticky-window p) {
    color: #000000;
    margin: 0.3em 0;
    line-height: 1.7;
    text-align: center;
    position: relative;
    z-index: 1;
  }

  .reader-container :global(.sticky-window p:last-of-type) {
    margin-bottom: 0;
  }

  .reader-container :global(.sticky-window p:empty) {
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
    padding: 1.5em 2em 1em;
    text-align: center;
    font-weight: 700;
    color: #ffffff;
    background-image: repeating-linear-gradient(
      0deg,
      transparent,
      transparent 2px,
      rgba(255,255,255,0.03) 2px,
      rgba(255,255,255,0.03) 4px
    );
  }

  .reader-container :global(.black-window *),
  .reader-container :global(.black-window p) {
    color: #ffffff !important;
    margin: 0.8em 0;
    line-height: 1.6;
    text-align: center;
  }

  .reader-container :global(.black-window p strong:only-child),
  .reader-container :global(.black-window p strong:first-child) {
    display: block;
    font-size: 1.25em;
    margin: 1em 0 0.8em;
  }

  .reader-container :global(.black-window p:last-of-type) {
    margin-bottom: 0.5em;
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
    padding: 1.5em 2em 1em;
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
    color: #ffffff !important;
    margin: 0.8em 0;
    line-height: 1.6;
    text-align: center;
  }

  .reader-container :global(.system-window:not(.no-fl-dividers) > p:first-of-type) {
    padding: 0.75em 0;
    font-size: 1.25em;
    background-image:
      linear-gradient(90deg, transparent, #888, transparent),
      linear-gradient(90deg, transparent, #888, transparent);
    background-repeat: no-repeat;
    background-size: 80% 1px;
    background-position: center top, center bottom;
  }

  .reader-container :global(.system-window p:last-of-type) {
    margin-bottom: 0.5em;
  }

  .reader-container :global(.system-window p:empty) {
    display: none;
  }





</style>