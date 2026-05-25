<script lang="ts">
  import { onMount } from "svelte";
  import { marked } from "marked";
  import Icon from "@iconify/svelte";
  import readerCss from "../../../../routes/(reader)/reader.css?url";

  const REPO = "EnderOksam/GSGW-Reader";
  const BRANCH = "main";
  const TRANSLATIONS = ["fantl", "MTL"];

  let chapters = $state<string[]>([]);
  let filtered = $state<string[]>([]);
  let titles = $state<Map<string, string>>(new Map());
  let indices = $state<Map<string, string>>(new Map());
  let search = $state("");
  let showInfo = $state(false);
  let translation = $state("fantl");
  let loading = $state(true);
  let selected = $state<string | null>(null);
  let input = $state("");
  let error = $state("");
  let body = $derived(preprocessMarkdown(input.replace(/^---[\s\S]*?---\n*/, "")));
  let previewHtml = $derived.by(() => {
    if (!body) return "";
    try {
      const renderer = new marked.Renderer();
      renderer.image = ({ href, title, text }) => {
        const src = href.startsWith("http") || href.startsWith("/")
          ? href
          : `https://raw.githubusercontent.com/${REPO}/${BRANCH}/images/gsgw/illustrations/${href}`;
        return `<img src="${src}" alt="${text}"${title ? ` title="${title}"` : ""}>`;
      };
      return marked.parse(body, { renderer });
    } catch {
      return body;
    }
  });

  function preprocessMarkdown(text: string): string {
    let s = text.replace(/\r\n/g, "\n");

    s = s.replace(/%%(.*?)%%/gs, '<span class="shake">$1</span>');

    s = s.replace(/%~(.*?)~%/gs, (_, inner) => {
      return [...inner].map((c, i) =>
        c === " " ? " " : `<span class="shake" style="animation-delay:-${(i * 0.05) % 0.5}s">${c}</span>`
      ).join("");
    });

    s = s.replace(/%\^(.*?)\^%/gs, (_, inner) => {
      const len = inner.length;
      return [...inner].map((c, i) => {
        if (c === " ") return " ";
        const delay = ((len - 1 - i) * 0.05) % 0.5;
        return `<span class="wave-up" style="animation-delay:-${delay}s">${c}</span>`;
      }).join("");
    });

    s = s.replace(/^~~~\s*$/gm, '<hr class="visible-hr">');

    s = s.replace(/@_@(.+?)@_@/gs, (_, inner) => {
      inner = inner.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
      const chars = inner.split(/(<[^>]+>)/).flatMap(part => {
        if (part.startsWith("<") && part.endsWith(">")) return [part];
        return [...part].map(c => c === " " ? " " : `<span class="char">${c}</span>`);
      });
      return `<span class="glitch-subtle">${chars.join("")}</span>`;
    });

    s = s.replace(/#\^#(.+?)#\^#/gs, (_, inner) => {
      const len = inner.length;
      const chars = [...inner].map((c, i) => {
        if (c === " ") return " ";
        const scale = 1 + (i / Math.max(len - 1, 1)) * 0.6;
        return `<span class="grow-char" style="font-size:${scale.toFixed(2)}em">${c}</span>`;
      });
      return `<span class="text-grow">${chars.join("")}</span>`;
    });

    s = s.replace(/#v#(.+?)#v#/gs, (_, inner) => {
      const len = inner.length;
      const chars = [...inner].map((c, i) => {
        if (c === " ") return " ";
        const scale = 1.4 - (i / Math.max(len - 1, 1)) * 0.4;
        return `<span class="grow-char" style="font-size:${scale.toFixed(2)}em">${c}</span>`;
      });
      return `<span class="text-grow">${chars.join("")}</span>`;
    });

    const placeholders = new Map<string, string>();
    let pid = 0;
    s = s.replace(/!\[.*?\]\(.*?\)/g, (m) => { const k = `\x00IMG${pid++}\x00`; placeholders.set(k, m); return k; });
    s = s.replace(/~~[^~]+?~~/g, (m) => { const k = `\x00IMG${pid++}\x00`; placeholders.set(k, m); return k; });

    const simple: [RegExp, string][] = [
      [/(?<!\\)_(.*?)(?<!\\)_/gs, '<span class="underline">$1</span>'],
      [/(?<!\\)(?<!~)~(?!~)(.+?)(?<!\\)~/gs, '~~$1~~'],
      [/@ll@(.*?)@ll@/gs, '<span class="mono mono-left">$1</span>'],
      [/@rr@(.*?)@rr@/gs, '<span class="mono mono-right">$1</span>'],
      [/@l@(.*?)@l@/gs, '<span class="align-left">$1</span>'],
      [/@r@(.*?)@r@/gs, '<span class="align-right">$1</span>'],
      [/#\*(.*?)\*#/gs, '<span class="text-large">$1</span>'],
      [/#><(.*?)><#/gs, '<span class="text-large-centered">$1</span>'],
      [/#r(.*?)r#/gs, '<span class="text-red">$1</span>'],
      [/#b(.*?)b#/gs, '<span class="text-blue">$1</span>'],
      [/#y(.*?)y#/gs, '<span class="text-yellow">$1</span>'],
      [/#p(.*?)p#/gs, '<span class="text-magenta">$1</span>'],
      [/#g(.*?)g#/gs, '<span class="text-green">$1</span>'],
      [/#o(.*?)o#/gs, '<span class="text-orange">$1</span>'],
      [/#f#(.*?)#f#/gs, '<span class="text-faded">$1</span>'],
      [/#f>#(.*?)#f>#/gs, '<span class="text-fade-right">$1</span>'],
      [/#f<#(.*?)#f<#/gs, '<span class="text-fade-left">$1</span>'],
      [/;r(.*?)r;/gs, '<span class="hl-red">$1</span>'],
      [/;b(.*?)b;/gs, '<span class="hl-blue">$1</span>'],
      [/;y(.*?)y;/gs, '<span class="hl-yellow">$1</span>'],
      [/;p(.*?)p;/gs, '<span class="hl-magenta">$1</span>'],
      [/;g(.*?)g;/gs, '<span class="hl-green">$1</span>'],
      [/;o(.*?)o;/gs, '<span class="hl-orange">$1</span>'],
    ];
    for (const [re, repl] of simple) {
      s = s.replace(re, repl);
    }

    for (const [key, val] of placeholders) {
      s = s.replace(key, val);
    }

    s = s.replace(/@@([^@]+)@@/gs, (_, inner) => {
      inner = inner.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
      const chars = inner.split(/(<[^>]+>)/).flatMap(part => {
        if (part.startsWith("<") && part.endsWith(">")) return [part];
        return [...part].map(c => c === " " ? " " : `<span class="char">${c}</span>`);
      });
      return `<span class="glitch-text">${chars.join("")}</span>`;
    });

    function makeWindow(cls: string, inner: string, extra?: string): string {
      const cl = extra ? `${cls} ${extra}` : cls;
      return `\n<div class="${cl}">\n\n${inner}\n\n</div>\n`;
    }

    s = s.replace(/\+[-+]+\n(.*?)\n[-+]+\+/gs, (_, inner) => {
      const noMeta = inner.trimStart().startsWith("\\");
      if (noMeta) inner = inner.replace("\\", "");
      return makeWindow("wiki-window", inner, noMeta ? "no-meta" : undefined);
    });

    s = s.replace(/\+[=]+\n(.*?)\n[=]+\+/gs, (_, inner) => makeWindow("black-window", inner));

    s = s.replace(/\+[~]+\n(.*?)\n[~]+\+/gs, (_, inner) => {
      const noFl = inner.trimStart().startsWith("\\");
      if (noFl) inner = inner.replace("\\", "");
      return makeWindow("system-window", inner, noFl ? "no-fl-dividers" : undefined);
    });

    s = s.replace(/\+\$\n(.*?)\n\$\+/gs, (_, inner) => makeWindow("plain-window", inner));

    s = s.replace(/&[-]+\n(.*?)\n[-]+&/gs, (_, inner) => {
      const noMeta = inner.trimStart().startsWith("\\");
      if (noMeta) inner = inner.replace("\\", "");
      return makeWindow("record-window", inner, noMeta ? "no-meta" : undefined);
    });

    s = s.replace(/&\$\n(.*?)\n\$&/gs, (_, inner) => makeWindow("followup-window", inner));

    s = s.replace(/![-]+\n(.*?)\n[-]+!/gs, (_, inner) => {
      const noMeta = inner.trimStart().startsWith("\\");
      if (noMeta) inner = inner.replace("\\", "");
      return makeWindow("note-window", inner, noMeta ? "no-meta" : undefined);
    });

    s = s.replace(/!\$\n(.*?)\n\$!/gs, (_, inner) => makeWindow("sticky-window", inner));

    s = s.replace(/!\[\n(.*?)\n\]!/gs, (_, inner) => makeWindow("braun-screen", inner));

    return s;
  }

  function extractMeta(text: string): { title: string; index: string } {
    const lines = text.split("\n");
    let title = "";
    let index = "";
    for (const line of lines) {
      const tm = line.match(/^title:\s*(.+)/i);
      if (tm) title = tm[1].trim().replace(/^["']|["']$/g, "");
      const im = line.match(/^index:\s*(.+)/i);
      if (im) index = im[1].trim();
    }
    return { title, index };
  }

  async function fetchTitles(files: string[]) {
    const tmap = new Map<string, string>();
    const imap = new Map<string, string>();
    await Promise.allSettled(files.map(async (f) => {
      try {
        const url = `https://raw.githubusercontent.com/${REPO}/${BRANCH}/chapters/gsgw/${translation}/${f}`;
        const res = await fetch(url);
        if (!res.ok) return;
        const reader = res.body?.getReader();
        if (!reader) return;
        const decoder = new TextDecoder();
        let buf = "";
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buf += decoder.decode(value, { stream: true });
          if (buf.length > 2048) break;
        }
        reader.cancel();
        const { title, index } = extractMeta(buf);
        if (title) tmap.set(f, title);
        if (index) imap.set(f, index);
      } catch { /* skip */ }
    }));
    titles = tmap;
    indices = imap;
  }

  async function loadChapterList() {
    loading = true;
    error = "";
    try {
      const url = `https://api.github.com/repos/${REPO}/contents/chapters/gsgw/${translation}`;
      const res = await fetch(url);
      if (!res.ok) throw new Error(`GitHub API: ${res.status}`);
      const data = await res.json();
      const files: string[] = data
        .filter((f: any) => f.name.endsWith(".md") && f.name !== "0000.md")
        .map((f: any) => f.name)
        .sort();
      chapters = files;
      filtered = files;
      fetchTitles(files);
    } catch (e: any) {
      error = e.message;
      chapters = [];
      filtered = [];
    } finally {
      loading = false;
    }
  }

  function loadSandbox() {
    selected = "sandbox";
    input = "";
  }

  async function loadChapter(file: string) {
    selected = file;
    try {
      const url = `https://raw.githubusercontent.com/${REPO}/${BRANCH}/chapters/gsgw/${translation}/${file}`;
      const res = await fetch(url);
      if (!res.ok) throw new Error(`fetch: ${res.status}`);
      input = await res.text();
    } catch (e: any) {
      input = `// error loading ${file}: ${e.message}`;
    }
  }

  $effect(() => {
    const q = search.toLowerCase();
    filtered = chapters.filter((f) => f.toLowerCase().includes(q));
  });

  onMount(loadChapterList);
</script>

<svelte:head>
  <link rel="stylesheet" href={readerCss}>
</svelte:head>

<div class="h-dvh bg-neutral-800 flex flex-col overflow-hidden">
  <div class="flex items-center justify-between px-4 py-2 border-b border-white/10 bg-neutral-900 shrink-0">
    <a href="/" class="text-white/50 hover:text-white transition-colors"><Icon icon="mdi:home-outline" class="size-5" /></a>
    <button
      onclick={() => showInfo = true}
      class="text-sm font-mono text-white/80 animate-pulse drop-shadow-[0_0_8px_rgba(255,255,255,0.5)] hover:drop-shadow-[0_0_12px_rgba(255,255,255,0.8)] transition-all cursor-pointer"
    >editor v0.1</button>
  </div>

  <div class="flex-1 flex p-4 gap-4 min-h-0">
    <div class="w-56 flex flex-col bg-neutral-900 rounded-lg border border-white/10 shrink-0 min-h-0">
      <div class="flex gap-1 p-2 border-b border-white/10">
        <input
          type="text"
          bind:value={search}
          placeholder="search"
          class="flex-1 bg-neutral-800 text-white/60 text-xs px-2 py-1 rounded outline-none border border-white/5 min-w-0"
        />
        <select
          bind:value={translation}
          onchange={loadChapterList}
          class="bg-neutral-800 text-white/60 text-xs px-2 py-1 rounded outline-none border border-white/5"
        >
          {#each TRANSLATIONS as t}
            <option value={t}>{t}</option>
          {/each}
        </select>
      </div>

      <div class="flex-1 overflow-y-auto p-1 min-h-0">
        <button
          onclick={loadSandbox}
          class="block w-full text-left text-xs px-2 py-1 rounded hover:bg-white/5 transition-colors {selected === 'sandbox' ? 'bg-white/10 text-white' : 'text-white/50'}"
        >blank chapter</button>
        <div class="mx-2 my-1 border-t border-white/10"></div>
        {#if loading}
          <p class="text-xs text-white/40 text-center py-4">loading...</p>
        {:else if error}
          <p class="text-xs text-red-400 text-center py-4">{error}</p>
        {:else if filtered.length === 0}
          <p class="text-xs text-white/40 text-center py-4">none</p>
        {:else}
          {#each filtered as file}
            <button
              onclick={() => loadChapter(file)}
              title="{indices.has(file) ? 'ch' + indices.get(file) : file}{titles.has(file) ? ' - ' + titles.get(file) : ''}"
              class="block w-full text-left text-xs px-2 py-1 rounded hover:bg-white/5 transition-colors whitespace-nowrap overflow-hidden text-ellipsis {selected === file ? 'bg-white/10 text-white' : 'text-white/50'}"
            >
              {#if indices.has(file)}
                ch{indices.get(file)}
              {:else}
                {file}
              {/if}
              {#if titles.has(file)}
                <span class="text-white/40"> - {titles.get(file)}</span>
              {/if}
            </button>
          {/each}
        {/if}
      </div>
    </div>

    <div class="flex-1 flex flex-col min-h-0 min-w-0">
      <div class="flex items-center px-3 py-1.5 border-b border-white/10 bg-neutral-900/50 rounded-t-lg">
        <span class="text-xs text-white/40 font-mono">markdown</span>
      </div>
      <textarea
        bind:value={input}
        placeholder="select a chapter to start editing..."
        class="flex-1 font-mono text-sm p-4 resize-none outline-none rounded-b-lg border-x border-b border-white/10 bg-neutral-900 text-white/90 min-h-0"
      ></textarea>
    </div>

    <div class="flex-1 flex flex-col min-h-0 min-w-0">
      <div class="flex items-center px-3 py-1.5 border-b border-white/10 bg-neutral-900/50 rounded-t-lg">
        <span class="text-xs text-white/40 font-mono">reader</span>
      </div>
      <div class="flex-1 overflow-y-auto rounded-b-lg border-x border-b border-white/10 bg-neutral-900">
        <article
          class="reader-container chapter-content prose prose-lg md:prose-xl max-w-none wrap-break-word"
          style="
            --chapter-font: 'Alegreya', serif;
            --chapter-size: 18px;
            --chapter-weight: 450;
            --chapter-lh: 1.8;
            --chapter-indent: 0;
            --chapter-align: left;
            --chapter-hyphens: none;
          "
        >
          {#if previewHtml}
            {@html previewHtml}
          {/if}
        </article>
      </div>
    </div>

    <div class="w-64 flex flex-col min-h-0 shrink-0">
      <div class="flex items-center px-3 py-1.5 border-b border-white/10 bg-neutral-900/50 rounded-t-lg">
        <span class="text-xs text-white/40 font-mono">formatting options</span>
      </div>
      <div class="flex-1 overflow-y-auto rounded-b-lg border-x border-b border-white/10 bg-neutral-900/80 text-xs text-white/50 font-mono leading-relaxed">
        <table class="w-full border-collapse">
          {#each [
            { syntax: "%%text%%", desc: "Shake effect (block)" },
            { syntax: "%~text~%", desc: "Shake effect (per-char)" },
            { syntax: "%^text^%", desc: "Wave up effect" },
            { syntax: "@@text@@", desc: "Glitch text (heavy)" },
            { syntax: "@_@text@_@", desc: "Glitch text (subtle)" },
            { syntax: "#^#text#^#", desc: "Grow font size" },
            { syntax: "#v#text#v#", desc: "Shrink font size" },
            { syntax: "~~~", desc: "Visible horizontal rule" },
            { syntax: "_text_", desc: "Underline" },
            { syntax: "@ll@text@ll@", desc: "Mono left-aligned" },
            { syntax: "@rr@text@rr@", desc: "Mono right-aligned" },
            { syntax: "@l@text@l@", desc: "Left align" },
            { syntax: "@r@text@r@", desc: "Right align" },
            { syntax: "#*text*#", desc: "Large text" },
            { syntax: "#><text><#", desc: "Large centered text" },
            { syntax: "#rtextr#", desc: "Red text" },
            { syntax: "#btextb#", desc: "Blue text" },
            { syntax: "#ytexty#", desc: "Yellow text" },
            { syntax: "#ptextp#", desc: "Magenta text" },
            { syntax: "#gtextg#", desc: "Green text" },
            { syntax: "#otexto#", desc: "Orange text" },
            { syntax: "#f#text#f#", desc: "Fade out" },
            { syntax: ";rtextr;", desc: "Red highlight" },
            { syntax: ";btextb;", desc: "Blue highlight" },
            { syntax: ";ytexty;", desc: "Yellow highlight" },
            { syntax: ";ptextp;", desc: "Magenta highlight" },
            { syntax: ";gtextg;", desc: "Green highlight" },
            { syntax: ";otexto;", desc: "Orange highlight" },
            { syntax: "+-text-+", desc: "Wiki window" },
            { syntax: "+$text$+", desc: "Plain window" },
            { syntax: "&$text$&", desc: "Followup window" },
            { syntax: "&--text--&", desc: "Record window" },
            { syntax: "+~text~+", desc: "System window" },
            { syntax: "+=text=+", desc: "Black CRT window" },
            { syntax: "!-text-!", desc: "Notepad window" },
            { syntax: "!$text$!", desc: "Sticky note window" },
            { syntax: "![text]!", desc: "Braun CRT monitor" },
          ] as opt}
            <tr
              class="border-b border-white/5 hover:bg-white/5"
            >
              <td class="px-2 py-1.5 whitespace-nowrap text-white/80 text-[10px]">{opt.syntax}</td>
              <td class="px-2 py-1.5 text-white/40">{opt.desc}</td>
            </tr>
          {/each}
        </table>
      </div>
    </div>
  </div>

  <div class="flex items-center justify-between px-4 py-1.5 border-t border-white/10 bg-neutral-900 shrink-0">
    <span class="text-xs text-white/40 font-mono">gsgw / {translation}</span>
    {#if selected === "sandbox"}
      <span class="text-xs text-white/40 font-mono">blank chapter</span>
    {:else if selected}
      <a
        href="https://github.com/{REPO}/edit/{BRANCH}/chapters/gsgw/{translation}/{selected}"
        target="_blank"
        class="text-xs text-white/40 hover:text-white font-mono transition-colors"
      >{selected}</a>
    {:else}
      <span class="text-xs text-white/40 font-mono">no file</span>
    {/if}
  </div>
</div>

{#if showInfo}
  <div
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
    onclick={() => showInfo = false}
    role="dialog"
  >
    <div
      class="bg-neutral-800 border border-white/10 rounded-lg p-6 w-96 shadow-2xl"
      onclick={(e) => e.stopPropagation()}
    >
      <p class="text-xs text-white/60 font-mono leading-relaxed">initial release of the editor to see a live preview of how your changes would look in the reader</p>
      <p class="text-xs text-white/40 font-mono leading-relaxed mt-3">clicking on the filename on the bottom right should redirect to the corresponding file on github, just paste over your changes and request a push</p>
    </div>
  </div>
{/if}

<style>
  .chapter-content {
    font-family: var(--chapter-font);
    font-size: var(--chapter-size);
    line-height: var(--chapter-lh);
    text-align: var(--chapter-align);
    hyphens: var(--chapter-hyphens);
    font-weight: var(--chapter-weight, 400);
  }

  .chapter-content :global(p) {
    text-indent: var(--chapter-indent);
  }

  :root {
    --window-bg: #1e1e2e;
    --window-border: #3a3a5c;
    --window-text: #ffffff !important;
    --window-accent: #ff4d00;
  }

  .reader-container {
    padding: 1.25rem;
    line-height: 1.6;
  }
  @media (min-width: 640px) {
    .reader-container {
      padding: 2rem;
    }
  }

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
</style>
