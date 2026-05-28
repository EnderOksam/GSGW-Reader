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



  $effect(() => {
    const embeds = document.querySelectorAll<HTMLElement>('.twitter-embed');
    if (!embeds.length) return;
    embeds.forEach(el => {
      const user = el.dataset.user;
      const tweetId = el.dataset.tweetId;
      if (!user || !tweetId) return;
      if (el.querySelector('.twitter-embed-inner')) return;
      hydrateEmbed(el, user, tweetId);
    });
  });

  async function hydrateEmbed(el: HTMLElement, user: string, tweetId: string) {
    try {
      const res = await fetch(`https://api.fxtwitter.com/${user}/status/${tweetId}`);
      const data = await res.json();
      if (!data?.tweet) throw new Error('no tweet data');

      const t = data.tweet;
      const author = t.author || {};
      const name = author.name || user;
      const tweetUrl = `https://x.com/${user}/status/${tweetId}`;
      const photos = t.media?.photos || [];
      const videos = t.media?.videos || [];
      const photoIdx = el.dataset.photo;

      let mediaHtml = '';
      if (photoIdx && photos.length) {
        const p = photos[parseInt(photoIdx, 10) - 1];
        if (p) mediaHtml = `<img class="twitter-embed-image" src="${esc(p.url)}" alt="" loading="lazy" />`;
      } else if (videos.length) {
        const v = videos[0];
        mediaHtml = `<video class="twitter-embed-video" src="${esc(v.url)}" controls playsinline preload="metadata"></video>`;
      } else if (photos.length === 1) {
        mediaHtml = `<img class="twitter-embed-image" src="${esc(photos[0].url)}" alt="" loading="lazy" />`;
      } else if (photos.length > 1) {
        mediaHtml = `<div class="twitter-embed-grid">${photos.map(p =>
          `<img src="${esc(p.url)}" alt="" loading="lazy" />`
        ).join('')}</div>`;
      }

      el.innerHTML = `
        <div class="twitter-embed-inner">
          <div class="twitter-embed-header">
            <a class="twitter-embed-name" href="${tweetUrl}" target="_blank" rel="noopener noreferrer">${esc(name)}</a>
            <span class="twitter-embed-user">@${user}</span>
            <svg class="twitter-embed-x-icon" viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>
        </div>
          ${mediaHtml}
        </div>
      `;
    } catch {
      el.innerHTML = '<div class="twitter-embed-error">Failed to load tweet</div>';
    }
  }

  function esc(str: string): string {
    const d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
  }

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

    --window-text: #ffffff !important;

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

    color: var(--window-text) !important;

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
    color: #ffffff !important;
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

    color: var(--window-text) !important;

  }

  @media (min-width: 640px) {
    .reader-container :global(.plain-window) {
      max-width: 88%;
    }
  }

  .reader-container :global(.plain-window p),
  .reader-container :global(.plain-window a),
  .reader-container :global(.plain-window strong),
  .reader-container :global(.plain-window b),
  .reader-container :global(.plain-window em),
  .reader-container :global(.plain-window i),
  .reader-container :global(.plain-window li),
  .reader-container :global(.plain-window h1),
  .reader-container :global(.plain-window h2),
  .reader-container :global(.plain-window h3),
  .reader-container :global(.plain-window h4),
  .reader-container :global(.plain-window h5),
  .reader-container :global(.plain-window h6),
  .reader-container :global(.plain-window code),
  .reader-container :global(.plain-window blockquote) {
    color: var(--window-text) !important;
  }

  .reader-container :global(.plain-window p) {
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
    color: #ffffff !important;
  }

  @media (min-width: 640px) {
    .reader-container :global(.followup-window) {
      max-width: 88%;
    }
  }

  .reader-container :global(.followup-window p),
  .reader-container :global(.followup-window a),
  .reader-container :global(.followup-window strong),
  .reader-container :global(.followup-window b),
  .reader-container :global(.followup-window em),
  .reader-container :global(.followup-window i),
  .reader-container :global(.followup-window li),
  .reader-container :global(.followup-window h1),
  .reader-container :global(.followup-window h2),
  .reader-container :global(.followup-window h3),
  .reader-container :global(.followup-window h4),
  .reader-container :global(.followup-window h5),
  .reader-container :global(.followup-window h6),
  .reader-container :global(.followup-window code),
  .reader-container :global(.followup-window blockquote) {
    color: #ffffff !important;
  }

  .reader-container :global(.followup-window p) {
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
    color: #000000 !important;
  }

  .reader-container :global(.sticky-window p),
  .reader-container :global(.sticky-window a),
  .reader-container :global(.sticky-window strong),
  .reader-container :global(.sticky-window b) {
    color: #000000 !important;
  }

  .reader-container :global(.sticky-window p) {
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
    font-size: 1.3em;
    color: #ffffff !important;
    /* glow-original: 0 0 7px rgba(255,255,255,0.4), 0 0 14px rgba(255,255,255,0.2) */
    text-shadow: 0 0 10px rgba(255,255,255,0.7), 0 0 20px rgba(255,255,255,0.4);
    transition: text-shadow 0.3s;
    background-image: repeating-linear-gradient(
      0deg,
      transparent,
      transparent 2px,
      rgba(255,255,255,0.03) 2px,
      rgba(255,255,255,0.03) 4px
    );
  }

  .reader-container :global(.black-window p) {
    color: #ffffff;
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

  .reader-container :global(.black-window):hover {
    animation: black-window-glow 1s ease-in-out infinite alternate;
  }

  .reader-container :global(.black-window p:empty) {
    display: none;
  }

  @keyframes black-window-glow {
    0% {
      text-shadow: 0 0 10px rgba(255,255,255,0.7), 0 0 20px rgba(255,255,255,0.4);
    }
    100% {
      text-shadow: 0 0 7px rgba(255,255,255,0.4), 0 0 14px rgba(255,255,255,0.2);
    }
  }



  /* --- BRAUN SCREEN (CRT monitor) --- */

  .reader-container :global(.braun-screen) {
    margin: 2.5rem auto;
    background:
      radial-gradient(ellipse at center, #050504 0%, #030302 60%, #020201 100%);
    border: 10px solid #4f4642;
    border-radius: 36px;
    max-width: 90%;
    position: relative;
    box-shadow:
      0 0 30px rgba(0,0,0,0.8),
      inset 0 0 60px rgba(0,0,0,0.3);
    padding: 6em 0.5em;
    text-align: center;
    font-family: 'Courier New', Courier, monospace;
    font-size: 2em;
    color: #ffffff !important;
    text-shadow:
      0 0 5px rgba(255, 255, 255, 0.4),
      0 0 15px rgba(255, 255, 255, 0.15);
    overflow: hidden;
    transition: text-shadow 0.2s;
    animation: braun-idle 0.08s infinite;
  }

  .reader-container :global(.braun-screen)::after {
    content: '';
    position: absolute;
    inset: 0;
    border-radius: 22px;
    background:
      repeating-linear-gradient(
        0deg,
        transparent,
        transparent 2px,
        rgba(255, 255, 255, 0.02) 2px,
        rgba(255, 255, 255, 0.02) 4px
      ),
      radial-gradient(
        ellipse at center,
        transparent 50%,
        rgba(0,0,0,0.5) 100%
      );
    pointer-events: none;
    z-index: 1;
  }

  .reader-container :global(.braun-screen)::before {
    content: '';
    position: absolute;
    inset: 0;
    border-radius: 22px;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='150' height='150'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='150' height='150' filter='url(%23n)' opacity='0.8'/%3E%3C/svg%3E");
    background-repeat: repeat;
    background-size: 150px 150px;
    opacity: 0.20;
    pointer-events: none;
    z-index: 2;
    mix-blend-mode: screen;
    animation: braun-static 0.12s infinite steps(3);
    transition: opacity 0.2s, animation-duration 0.2s;
  }

  @keyframes braun-static {
    0% { background-position: 0 0; }
    33% { background-position: -45px -25px; }
    66% { background-position: 25px -55px; }
    100% { background-position: -15px 35px; }
  }

  @keyframes braun-idle {
    0%, 100% { transform: translate(0, 0); }
    50% { transform: translate(0.1px, -0.1px); }
  }

  .reader-container :global(.braun-screen):hover {
    text-shadow:
      0 0 8px rgba(255, 255, 255, 0.6),
      0 0 20px rgba(255, 255, 255, 0.25);
    animation: braun-hover-shake 0.06s infinite;
  }

  .reader-container :global(.braun-screen):hover::before {
    opacity: 0.50;
    animation-duration: 0.04s;
    animation-timing-function: steps(6);
  }

  @keyframes braun-hover-shake {
    0%, 100% { transform: translate(0, 0); }
    25% { transform: translate(0.3px, -0.2px); }
    50% { transform: translate(-0.2px, 0.3px); }
    75% { transform: translate(0.2px, -0.3px); }
  }

  .reader-container :global(.braun-screen p) {
    color: #ffffff;
    margin: 0.8em 0;
    line-height: 1.6;
    text-align: center;
    position: relative;
    z-index: 3;
  }

  .reader-container :global(.braun-screen p:last-of-type) {
    margin-bottom: 0.5em;
  }

  .reader-container :global(.braun-screen p:empty) {
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
    color: #ffffff !important;
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

  .reader-container :global(.system-window p),
  .reader-container :global(.system-window a),
  .reader-container :global(.system-window strong),
  .reader-container :global(.system-window b),
  .reader-container :global(.system-window em),
  .reader-container :global(.system-window i),
  .reader-container :global(.system-window li),
  .reader-container :global(.system-window h1),
  .reader-container :global(.system-window h2),
  .reader-container :global(.system-window h3),
  .reader-container :global(.system-window h4),
  .reader-container :global(.system-window h5),
  .reader-container :global(.system-window h6),
  .reader-container :global(.system-window code),
  .reader-container :global(.system-window blockquote) {
    color: #ffffff !important;
  }

  .reader-container :global(.system-window p) {
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




  /* --- TWITTER EMBED --- */

  .reader-container :global(.twitter-embed) {
    margin: 2rem auto;
    max-width: 550px;
    transition: transform 0.15s;
  }

  .reader-container :global(.twitter-embed):hover {
    transform: translateY(-2px);
  }

  .reader-container :global(.twitter-embed-inner) {
    background: #16181c;
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 16px;
    overflow: hidden;
    padding: 0 0.75rem 0.75rem;
    box-shadow: 0 4px 24px rgba(0,0,0,0.4);
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
  }

  .reader-container :global(.twitter-embed-header) {
    display: flex;
    align-items: baseline;
    gap: 0.375rem;
    padding: 0.75rem 0 0.375rem;
  }

  .reader-container :global(.twitter-embed-name) {
    color: #1d9bf0;
    font-size: 0.9375rem;
    font-weight: 700;
    text-decoration: none;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    text-shadow: 0 0 8px rgba(29,155,240,0.5);
  }

  .reader-container :global(.twitter-embed-name:hover) {
    text-decoration: underline;
    text-shadow: 0 0 12px rgba(29,155,240,0.7);
  }

  .reader-container :global(.twitter-embed-user) {
    color: #71767b;
    font-size: 0.8125rem;
    font-weight: 400;
  }

  .reader-container :global(.twitter-embed-x-icon) {
    color: #71767b;
    margin-left: auto;
    flex-shrink: 0;
    opacity: 0.6;
  }

  .reader-container :global(.twitter-embed-image) {
    display: block;
    width: 100%;
    max-height: 85vh;
    object-fit: contain;
    margin: 0;
    border-radius: 12px;
  }

  .reader-container :global(.twitter-embed-grid) {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 2px;
    border-radius: 12px;
    overflow: hidden;
  }

  .reader-container :global(.twitter-embed-grid img) {
    display: block;
    width: 100%;
    height: 200px;
    object-fit: cover;
  }

  .reader-container :global(.twitter-embed-grid img:first-child:nth-last-child(3)) {
    height: 150px;
  }

  .reader-container :global(.twitter-embed-grid img:first-child:nth-last-child(3) ~ img) {
    height: 150px;
  }

  .reader-container :global(.twitter-embed-video) {
    display: block;
    width: 100%;
    max-height: 85vh;
    border-radius: 12px;
  }

  .reader-container :global(.twitter-embed-loading),
  .reader-container :global(.twitter-embed-error) {
    padding: 1.25rem;
    text-align: center;
    font-size: 0.8rem;
    color: #71767b;
    background: #16181c;
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 16px;
    box-shadow: 0 4px 24px rgba(0,0,0,0.4);
  }

</style>