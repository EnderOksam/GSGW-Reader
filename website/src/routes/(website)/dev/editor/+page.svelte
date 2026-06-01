<script lang="ts">
  import { onMount } from "svelte";
  import { browser } from "$app/environment";
  import { marked } from "marked";
  import Icon from "@iconify/svelte";
  import JSZip from "jszip";
  import readerCss from "../../../../routes/(reader)/reader.css?url";

  let theme = $state("sunset");
  let showThemeMenu = $state(false);
  let themeBtn: HTMLButtonElement;

  const THEMES = ["sunset", "light", "dark", "retro", "night", "business", "black", "dracula", "cyberpunk"];

  onMount(() => {
    const saved = localStorage.getItem("editor-theme");
    if (saved) theme = saved;
    document.documentElement.setAttribute("data-theme", theme);
  });

  $effect(() => {
    if (browser) {
      localStorage.setItem("editor-theme", theme);
      document.documentElement.setAttribute("data-theme", theme);
    }
  });

  const REPO = "EnderOksam/GSGW-Reader";
  const BRANCH = "main";
  const SOURCE_TRANSLATIONS = ["fantl", "MTL"];
  const CUSTOM_TRANSLATIONS_KEY = "editor-custom-translations";

  const TWITTER_EMBED_RE = /https?:\/\/(?:x|twitter)\.com\/(\w+)\/status\/(\d+)(?:\/photo\/(\d+))?[^\s<>"']*/g;

  function replaceTwitterUrls(text: string): string {
    return text.replace(TWITTER_EMBED_RE, (match, user: string, tweetId: string, photo: string | undefined) => {
      let attrs = `data-user="${user}" data-tweet-id="${tweetId}"`;
      if (photo) attrs += ` data-photo="${photo}"`;
      return `<div class="twitter-embed" ${attrs}><div class="twitter-embed-loading">Loading…</div></div>`;
    });
  }

  function fmtNum(n: string): string {
    const num = parseInt(n, 10);
    if (isNaN(num)) return n;
    if (num >= 1_000_000) return (num / 1_000_000).toFixed(num % 1_000_000 === 0 ? 0 : 1).replace(/\.0$/, '') + 'M';
    if (num >= 1_000) return (num / 1_000).toFixed(num % 1_000 === 0 ? 0 : 1).replace(/\.0$/, '') + 'k';
    return num.toLocaleString();
  }

  async function hydrateTwitterEmbeds() {
    const embeds = document.querySelectorAll<HTMLElement>('.twitter-embed');
    for (const el of embeds) {
      const user = el.dataset.user;
      const tweetId = el.dataset.tweetId;
      if (!user || !tweetId) continue;
      if (el.querySelector('.twitter-embed-inner')) continue;
      try {
        const res = await fetch(`https://api.fxtwitter.com/${user}/status/${tweetId}`);
        const data = await res.json();
        if (!data?.tweet) throw new Error('no tweet data');
        const t = data.tweet;
        const author = t.author || {};
        const name = author.name || user;
        const tweetUrl = `https://x.com/${user}/status/${tweetId}`;
        const photo = el.dataset.photo;
        const photos = t.media?.photos || [];
        const videos = t.media?.video || null;
        const text = t.text || '';
        const likes = t.likes !== undefined ? String(t.likes) : '';
        const retweets = t.retweets !== undefined ? String(t.retweets) : '';
        const replies = t.replies !== undefined ? String(t.replies) : '';
        const views = t.views !== undefined ? String(t.views) : '';
        let mediaHtml = '';
        if (photo) {
          const img = photos[parseInt(photo) - 1];
          if (img) mediaHtml = `<img class="twitter-embed-image" src="${img.url}" alt="" loading="lazy" />`;
        } else if (videos) {
          mediaHtml = `<video class="twitter-embed-video" src="${videos.url}" controls playsinline preload="metadata"></video>`;
        } else if (photos.length === 1) {
          mediaHtml = `<img class="twitter-embed-image" src="${photos[0].url}" alt="" loading="lazy" />`;
        } else if (photos.length > 1) {
          mediaHtml = `<div class="twitter-embed-grid">${photos.map((p: any) =>
            `<img class="twitter-embed-image" src="${p.url}" alt="" loading="lazy" />`
          ).join('')}</div>`;
        }
        el.innerHTML = `
          <div class="twitter-embed-inner">
            <div class="twitter-embed-header">
              <a class="twitter-embed-name" href="${tweetUrl}" target="_blank" rel="noopener noreferrer">${escHtml(name)}</a>
              <span class="twitter-embed-user">@${user}</span>
              <svg class="twitter-embed-x-icon" viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>
            </div>
            ${text ? `<p class="twitter-embed-text">${escHtml(text)}</p>` : ''}
            ${mediaHtml}
            <div class="twitter-embed-stats">
              <span class="twitter-embed-stat" title="Views">
                <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                ${fmtNum(views)}
              </span>
              <span class="twitter-embed-stat" title="Replies">
                <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
                ${fmtNum(replies)}
              </span>
              <span class="twitter-embed-stat" title="Reposts">
                <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M17 1l4 4-4 4"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/><path d="M7 23l-4-4 4-4"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/></svg>
                ${fmtNum(retweets)}
              </span>
              <span class="twitter-embed-stat" title="Likes">
                <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>
                ${fmtNum(likes)}
              </span>
            </div>
          </div>
        `;
      } catch {
        el.innerHTML = '<div class="twitter-embed-error">Failed to load tweet</div>';
      }
    }
  }

  function escHtml(s: string): string {
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  let customTranslations = $state<string[]>([]);

  function loadCustomTranslations() {
    try {
      const saved = localStorage.getItem(CUSTOM_TRANSLATIONS_KEY);
      if (saved) customTranslations = JSON.parse(saved);
    } catch {}
  }

  function saveCustomTranslations() {
    try { localStorage.setItem(CUSTOM_TRANSLATIONS_KEY, JSON.stringify(customTranslations)); } catch {}
  }

  function customStorageKey(tl: string) { return `editor-cache-custom-${tl}`; }

  function loadCustomChapterList(tl: string): string[] {
    try {
      const data = localStorage.getItem(customStorageKey(tl));
      if (!data) return [];
      return Object.keys(JSON.parse(data)).sort();
    } catch { return []; }
  }

  function loadCustomChapterContent(tl: string, file: string): string | null {
    try {
      const data = JSON.parse(localStorage.getItem(customStorageKey(tl)) || "{}");
      return data[file] ?? null;
    } catch { return null; }
  }

  function saveCustomChapter(tl: string, file: string, content: string) {
    try {
      const data = JSON.parse(localStorage.getItem(customStorageKey(tl)) || "{}");
      data[file] = content;
      localStorage.setItem(customStorageKey(tl), JSON.stringify(data));
    } catch {}
  }

  function deleteCustomChapter(tl: string, file: string) {
    try {
      const data = JSON.parse(localStorage.getItem(customStorageKey(tl)) || "{}");
      delete data[file];
      localStorage.setItem(customStorageKey(tl), JSON.stringify(data));
    } catch {}
  }

  let chapters = $state<string[]>([]);
  let filtered = $state<string[]>([]);
  let titles = $state<Map<string, string>>(new Map());
  let indices = $state<Map<string, string>>(new Map());
  let search = $state("");
  let showInfo = $state(false);
  let expandedVersion = $state<string | null>(null);

  let patchNotes = [
    {
      version: "v0.4",
      description: "- bug fixing\n- themes\n- changed mobile editing ui to fit the smaller screen"
    },
    {
      version: "v0.3",
      description: "- better ui (hopefully)\n- mobile editing\n- custom translations\n- adding/removing chapters"
    },
    {
      version: "v0.2",
      description: `- added caching chapter changes and scrolling positions\n- reverting to source\n- exporting single or bulk chapters`
    },
    {
      version: "v0.1",
      description: "initial release of the editor to see a live preview of how your changes would look in the reader"
    }
  ];

  function toggleVersion(v: string) {
    expandedVersion = expandedVersion === v ? null : v;
  }
  let translation = $state("fantl");
  let isSourceTranslation = $derived(SOURCE_TRANSLATIONS.includes(translation));
  let loading = $state(true);
  let refreshing = $state(false);
  let selected = $state<string | null>(null);
  let input = $state("");
  let error = $state("");
  let dirty = $state<Set<string>>(new Set());

  let cache = new Map<string, string>();
  let originalContent = new Map<string, string>();
  let importRef: HTMLInputElement | undefined = $state();

  function saveCache() {
    try {
      localStorage.setItem("editor-cache", JSON.stringify(Object.fromEntries(cache)));
    } catch {}
  }

  function loadCache() {
    try {
      const saved = localStorage.getItem("editor-cache");
      if (saved) {
        const parsed = JSON.parse(saved);
        cache = new Map(Object.entries(parsed));
        dirty = new Set(cache.keys());
      }
    } catch {}
  }

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

  $effect(() => {
    if (!isSourceTranslation && selected && input) {
      const { title, index } = extractMeta(input);
      if (titles.get(selected) !== title || indices.get(selected) !== index) {
        const nt = new Map(titles);
        const ni = new Map(indices);
        if (title) nt.set(selected, title); else nt.delete(selected);
        if (index) ni.set(selected, index); else ni.delete(selected);
        titles = nt;
        indices = ni;
      }
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
      const chars = inner.split(/(<[^>]+>)/).flatMap((part: string) => {
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
      const chars = inner.split(/(<[^>]+>)/).flatMap((part: string) => {
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

    s = replaceTwitterUrls(s);
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

  function loadCustomTitles(files: string[]) {
    const tmap = new Map<string, string>();
    const imap = new Map<string, string>();
    for (const f of files) {
      const content = loadCustomChapterContent(translation, f);
      if (!content) continue;
      const { title, index } = extractMeta(content);
      if (title) tmap.set(f, title);
      if (index) imap.set(f, index);
    }
    titles = tmap;
    indices = imap;
  }

  async function loadChapterList() {
    loading = true;
    error = "";
    try {
      if (isSourceTranslation) {
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
      } else {
        const files = loadCustomChapterList(translation);
        chapters = files;
        filtered = files;
        loadCustomTitles(files);
      }
    } catch (e: any) {
      error = e.message;
      chapters = [];
      filtered = [];
    } finally {
      loading = false;
    }
  }

  function loadSandbox() {
    saveCurrent();
    selected = "sandbox";
    input = "";
  }

  async function loadChapter(file: string) {
    saveCurrent();
    selected = file;
    if (!isSourceTranslation) {
      const content = loadCustomChapterContent(translation, file);
      if (content !== null) {
        originalContent.set(file, content);
        input = content;
        requestAnimationFrame(() => restoreScrollPositions(file));
        return;
      }
      input = `// error: chapter "${file}" not found`;
      return;
    }
    const cached = cache.get(file);
    if (cached !== undefined) {
      input = cached;
      requestAnimationFrame(() => restoreScrollPositions(file));
      return;
    }
    try {
      const url = `https://raw.githubusercontent.com/${REPO}/${BRANCH}/chapters/gsgw/${translation}/${file}`;
      const res = await fetch(url);
      if (!res.ok) throw new Error(`fetch: ${res.status}`);
      const text = await res.text();
      originalContent.set(file, text);
      input = text;
      requestAnimationFrame(() => restoreScrollPositions(file));
    } catch (e: any) {
      input = `// error loading ${file}: ${e.message}`;
    }
  }

  let leftTab = $state<'chapters' | 'formatting'>('chapters');
  let rightTab = $state<'editor' | 'reader'>('editor');
  let newTranslationName = $state("");
  let showManageTL = $state(false);
  let renameTL: string | null = $state(null);
  let renameTLValue = $state("");

  function handleTranslationChange() {
    saveCurrent();
    if (!isSourceTranslation && !customTranslations.includes(translation)) {
      customTranslations = [...customTranslations, translation];
      saveCustomTranslations();
    }
    loadChapterList();
  }

  function confirmNewTranslation() {
    const name = newTranslationName.trim();
    if (!name) return;
    showManageTL = false;
    translation = name;
    if (!customTranslations.includes(translation)) {
      customTranslations = [...customTranslations, translation];
      saveCustomTranslations();
    }
    loadChapterList();
  }

  function startRename(tl: string) {
    renameTL = tl;
    renameTLValue = tl;
  }

  function confirmRename() {
    const old = renameTL;
    const newName = renameTLValue.trim();
    if (!old || !newName || newName === old) { renameTL = null; return; }
    if (SOURCE_TRANSLATIONS.includes(newName) || customTranslations.includes(newName)) {
      renameTLValue = old;
      renameTL = null;
      return;
    }
    const data = localStorage.getItem(customStorageKey(old));
    if (data) localStorage.setItem(customStorageKey(newName), data);
    localStorage.removeItem(customStorageKey(old));
    customTranslations = customTranslations.map(t => t === old ? newName : t);
    saveCustomTranslations();
    if (translation === old) {
      translation = newName;
      loadChapterList();
    }
    renameTL = null;
  }

  function deleteTL(tl: string) {
    if (!confirm(`Delete "${tl}" and all its chapters?`)) return;
    try { localStorage.removeItem(customStorageKey(tl)); } catch {}
    customTranslations = customTranslations.filter(t => t !== tl);
    saveCustomTranslations();
    if (translation === tl) {
      translation = "fantl";
      loadChapterList();
    }
  }

  async function refreshChapters() {
    refreshing = true;
    loadCache();
    await loadChapterList();
    refreshing = false;
  }

  function triggerImport() {
    importRef?.click();
  }

  async function handleImportZip(e: Event) {
    const file = (e.target as HTMLInputElement).files?.[0];
    if (!file) return;
    try {
      const zip = await JSZip.loadAsync(file);
      const entries: { name: string; data: string }[] = [];
      const promises: Promise<void>[] = [];
      zip.forEach((path, entry) => {
        if (!entry.dir && path.endsWith(".md")) {
          promises.push(
            entry.async("string").then((data) => {
              entries.push({ name: path.split("/").pop() || path, data });
            })
          );
        }
      });
      await Promise.all(promises);
      if (!entries.length) { alert("No .md files found in zip."); return; }

      if (isSourceTranslation) {
        for (const e of entries) {
          cache.set(e.name, e.data);
          originalContent.set(e.name, e.data);
          dirty = new Set([...dirty, e.name]);
        }
        if (entries.some(e => !chapters.includes(e.name))) {
          const allFiles = new Set([...chapters, ...entries.map(e => e.name)]);
          chapters = [...allFiles].sort();
          filtered = [...allFiles].sort();
        }
      } else {
        const existing = loadCustomChapterList(translation);
        const allFiles = new Set([...existing, ...entries.map(e => e.name)]);
        for (const e of entries) {
          saveCustomChapter(translation, e.name, e.data);
        }
        chapters = [...allFiles].sort();
        filtered = [...allFiles].sort();
        if (entries.length === 1) {
          loadChapter(entries[0].name);
        }
      }
      saveCache();
    } catch (err) {
      alert("Failed to import zip: " + (err instanceof Error ? err.message : String(err)));
    }
    (e.target as HTMLInputElement).value = "";
  }

  function newChapter() {
    const nums = chapters.map(f => parseInt(f.match(/^(\d+)/)?.[1] ?? "0")).filter(n => !isNaN(n));
    const nextNum = nums.length ? Math.max(...nums) + 1 : 1;
    const name = String(nextNum).padStart(4, "0") + ".md";
    if (chapters.includes(name)) { alert(`"${name}" already exists.`); return; }
    const template = "---\ntitle: # chapter title\ncategory: # chapter number\ndiscussion: # same as chapter number\nindex: # same as chapter number\nsection: # part number\nslug: # same as chapter number\n---\n\n";
    if (isSourceTranslation) {
      cache.set(name, template);
      originalContent.set(name, template);
      dirty = new Set([...dirty, name]);
    } else {
      saveCustomChapter(translation, name, template);
    }
    chapters = [...chapters, name].sort();
    filtered = [...filtered, name].sort();
    input = template;
    selected = name;
  }

  async function deleteCurrentChapter() {
    if (!selected || selected === "sandbox") return;
    if (isSourceTranslation) { alert("Can only delete chapters from custom translations."); return; }
    if (!confirm(`Delete "${selected}" from "${translation}"?`)) return;
    deleteCustomChapter(translation, selected);
    cache.delete(selected);
    dirty = new Set([...dirty].filter(f => f !== selected));
    chapters = chapters.filter(f => f !== selected);
    filtered = filtered.filter(f => f !== selected);
    selected = null;
    input = "";
  }

  $effect(() => {
    const q = search.toLowerCase();
    filtered = chapters.filter((f) => f.toLowerCase().includes(q));
  });

  $effect(() => {
    if (previewHtml) {
      hydrateTwitterEmbeds();
    }
  });

  onMount(() => { loadCache(); loadCustomTranslations(); loadChapterList(); });

  let mdScroll: HTMLElement | null = $state(null);
  let readerScroll: HTMLElement | null = $state(null);
  let scrollPositions = new Map<string, { md: number; reader: number }>();
  let showExport = $state(false);
  let showRevert = $state(false);
  let showMobileMenu = $state(false);
  let exportBtn: HTMLElement | null = $state(null);
  let revertBtn: HTMLElement | null = $state(null);

  function toggleExport(e: MouseEvent) {
    showExport = !showExport;
    showRevert = false;
    if (showExport) {
      const handler = (ev: MouseEvent) => {
        if (!exportBtn?.contains(ev.target as Node) && !(ev.target as HTMLElement)?.closest?.('[data-export-dropdown]')) {
          showExport = false;
          document.removeEventListener("click", handler);
        }
      };
      requestAnimationFrame(() => document.addEventListener("click", handler));
    }
  }

  function toggleRevert(e: MouseEvent) {
    showRevert = !showRevert;
    showExport = false;
    if (showRevert) {
      const handler = (ev: MouseEvent) => {
        if (!revertBtn?.contains(ev.target as Node) && !(ev.target as HTMLElement)?.closest?.('[data-revert-dropdown]')) {
          showRevert = false;
          document.removeEventListener("click", handler);
        }
      };
      requestAnimationFrame(() => document.addEventListener("click", handler));
    }
  }

  function exportCurrentChapter() {
    if (!selected || selected === "sandbox" || !input) return;
    const blob = new Blob([input], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${translation}-${selected}`;
    a.click();
    URL.revokeObjectURL(url);
    showExport = false;
  }

  function exportAllEdited() {
    const entries: { name: string; data: string }[] = [];
    if (isSourceTranslation) {
      for (const file of dirty) {
        const content = cache.get(file);
        if (content) entries.push({ name: file, data: content });
      }
    } else {
      for (const file of chapters) {
        const content = loadCustomChapterContent(translation, file);
        if (content) entries.push({ name: file, data: content });
      }
    }
    if (!entries.length) return;
    const zip = createZip(entries);
    const blob = new Blob([zip as unknown as BlobPart], { type: "application/zip" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${translation}-chapters.zip`;
    a.click();
    URL.revokeObjectURL(url);
    showExport = false;
  }

  async function revertCurrentChapter() {
    if (!selected || selected === "sandbox") return;
    cache.delete(selected);
    dirty = new Set([...dirty].filter(f => f !== selected));
    scrollPositions.delete(selected);
    saveCache();
    const orig = originalContent.get(selected);
    if (orig !== undefined) {
      input = orig;
    } else {
      try {
        const url = `https://raw.githubusercontent.com/${REPO}/${BRANCH}/chapters/gsgw/${translation}/${selected}`;
        const res = await fetch(url);
        if (res.ok) {
          const text = await res.text();
          originalContent.set(selected, text);
          input = text;
        }
      } catch {}
    }
    showExport = false;
  }

  async function revertAllChapters() {
    const wasDirty = dirty.has(selected || "");
    cache.clear();
    dirty = new Set();
    scrollPositions.clear();
    saveCache();
    if (wasDirty && selected && selected !== "sandbox") {
      const orig = originalContent.get(selected);
      if (orig !== undefined) {
        input = orig;
      } else {
        try {
          const url = `https://raw.githubusercontent.com/${REPO}/${BRANCH}/chapters/gsgw/${translation}/${selected}`;
          const res = await fetch(url);
          if (res.ok) {
            const text = await res.text();
            originalContent.set(selected, text);
            input = text;
          }
        } catch {}
      }
    }
    showExport = false;
  }

  function crc32(data: Uint8Array): number {
    let crc = 0xffffffff;
    for (let i = 0; i < data.length; i++) {
      crc ^= data[i];
      for (let j = 0; j < 8; j++) crc = crc & 1 ? (crc >>> 1) ^ 0xedb88320 : crc >>> 1;
    }
    return (crc ^ 0xffffffff) >>> 0;
  }

  function createZip(entries: { name: string; data: string }[]): Uint8Array {
    const encoder = new TextEncoder();
    const localHeaders: Uint8Array[] = [];
    const centralEntries: Uint8Array[] = [];
    let offset = 0;

    for (const entry of entries) {
      const nameBytes = encoder.encode(entry.name);
      const dataBytes = encoder.encode(entry.data);
      const crc = crc32(dataBytes);

      const local = new Uint8Array(30 + nameBytes.length + dataBytes.length);
      const dv = new DataView(local.buffer);
      dv.setUint32(0, 0x04034b50, true); // local sig
      dv.setUint16(4, 20, true); // version
      dv.setUint16(6, 0, true); // flags
      dv.setUint16(8, 0, true); // compression (stored)
      dv.setUint16(10, 0, true); // mod time
      dv.setUint16(12, 0, true); // mod date
      dv.setUint32(14, crc, true);
      dv.setUint32(18, dataBytes.length, true); // compressed size
      dv.setUint32(22, dataBytes.length, true); // uncompressed size
      dv.setUint16(26, nameBytes.length, true);
      dv.setUint16(28, 0, true); // extra length
      local.set(nameBytes, 30);
      local.set(dataBytes, 30 + nameBytes.length);
      localHeaders.push(local);

      const central = new Uint8Array(46 + nameBytes.length);
      const cdv = new DataView(central.buffer);
      cdv.setUint32(0, 0x02014b50, true); // central sig
      cdv.setUint16(4, 20, true); // version made
      cdv.setUint16(6, 20, true); // version needed
      cdv.setUint16(8, 0, true); // flags
      cdv.setUint16(10, 0, true); // compression
      cdv.setUint16(12, 0, true); // mod time
      cdv.setUint16(14, 0, true); // mod date
      cdv.setUint32(16, crc, true);
      cdv.setUint32(20, dataBytes.length, true);
      cdv.setUint32(24, dataBytes.length, true);
      cdv.setUint16(28, nameBytes.length, true);
      cdv.setUint16(30, 0, true); // extra length
      cdv.setUint16(32, 0, true); // comment length
      cdv.setUint16(34, 0, true); // disk start
      cdv.setUint16(36, 0, true); // internal attrs
      cdv.setUint32(38, 0, true); // external attrs
      cdv.setUint32(42, offset, true); // local header offset
      central.set(nameBytes, 46);
      centralEntries.push(central);

      offset += local.length;
    }

    const centralSize = centralEntries.reduce((s, e) => s + e.length, 0);
    const centralOffset = offset;
    const eocd = new Uint8Array(22);
    const ecdv = new DataView(eocd.buffer);
    ecdv.setUint32(0, 0x06054b50, true); // eocd sig
    ecdv.setUint16(4, 0, true); // disk
    ecdv.setUint16(6, 0, true); // central disk
    ecdv.setUint16(8, entries.length, true); // entries on disk
    ecdv.setUint16(10, entries.length, true); // total entries
    ecdv.setUint32(12, centralSize, true);
    ecdv.setUint32(16, centralOffset, true);
    ecdv.setUint16(20, 0, true); // comment length

    const result = new Uint8Array(offset + centralSize + 22);
    let pos = 0;
    for (const h of localHeaders) { result.set(h, pos); pos += h.length; }
    for (const c of centralEntries) { result.set(c, pos); pos += c.length; }
    result.set(eocd, pos);
    return result;
  }

  function saveScrollPositions(file: string) {
    if (!mdScroll || !readerScroll) return;
    scrollPositions.set(file, { md: mdScroll.scrollTop, reader: readerScroll.scrollTop });
  }

  function restoreScrollPositions(file: string) {
    const pos = scrollPositions.get(file);
    if (mdScroll) mdScroll.scrollTop = pos?.md ?? 0;
    if (readerScroll) readerScroll.scrollTop = pos?.reader ?? 0;
  }

  function saveCurrent() {
    if (selected && selected !== "sandbox" && input) {
      saveScrollPositions(selected);
      if (!isSourceTranslation) {
        const orig = originalContent.get(selected);
        if (orig !== undefined && input !== orig) {
          dirty = new Set([...dirty, selected]);
        } else if (orig !== undefined && input === orig && dirty.has(selected)) {
          dirty = new Set([...dirty].filter(f => f !== selected));
        }
        saveCustomChapter(translation, selected, input);
        return;
      }
      const orig = originalContent.get(selected);
      if (orig !== undefined && input !== orig) {
        cache.set(selected, input);
        dirty = new Set([...dirty, selected]);
        saveCache();
      } else if (orig !== undefined && input === orig && cache.has(selected)) {
        cache.delete(selected);
        dirty = new Set([...dirty].filter(f => f !== selected));
        saveCache();
      }
    }
  }
</script>

<svelte:head>
  <link rel="stylesheet" href={readerCss}>
</svelte:head>

<div class="h-dvh bg-base-300 flex flex-col overflow-hidden selection:bg-primary/30">
  <div class="flex items-center justify-between px-3 py-1.5 border-b border-base-content/10 bg-base-300/50 backdrop-blur-sm shrink-0 relative z-10">
    <div class="flex items-center gap-0.5 relative">
      <button onclick={() => showMobileMenu = true} class="lg:hidden text-base-content/40 hover:text-base-content transition-colors p-1.5 rounded hover:bg-base-content/5" title="Menu"><Icon icon="mdi:menu" class="size-4" /></button>
      <a href="/" class="text-base-content/40 hover:text-base-content transition-colors p-1.5 rounded hover:bg-base-content/5" title="Home"><Icon icon="mdi:home-outline" class="size-4" /></a>
      <button bind:this={exportBtn} onclick={toggleExport} class="text-base-content/40 hover:text-base-content transition-colors p-1.5 rounded hover:bg-base-content/5" title="Export"><Icon icon="mdi:export-variant" class="size-4" /></button>
      <button onclick={triggerImport} class="text-base-content/40 hover:text-base-content transition-colors p-1.5 rounded hover:bg-base-content/5" title="Import zip"><Icon icon="mdi:file-import-outline" class="size-4" /></button>
      <input bind:this={importRef} onchange={handleImportZip} type="file" accept=".zip" class="hidden" />
      <button bind:this={revertBtn} onclick={toggleRevert} class="text-base-content/40 hover:text-base-content transition-colors p-1.5 rounded hover:bg-base-content/5" title="Revert"><Icon icon="mdi:undo-variant" class="size-4" /></button>
      <span class="mx-0.5 w-px h-4 bg-base-content/10"></span>
      <button onclick={newChapter} disabled={!translation} class="text-base-content/40 hover:text-base-content transition-colors p-1.5 rounded hover:bg-base-content/5 disabled:text-base-content/15 disabled:hover:bg-transparent disabled:cursor-not-allowed" title="New chapter"><Icon icon="mdi:plus" class="size-4" /></button>
      <button onclick={deleteCurrentChapter} disabled={!selected || selected === "sandbox" || isSourceTranslation} class="text-base-content/40 hover:text-base-content transition-colors p-1.5 rounded hover:bg-base-content/5 disabled:text-base-content/15 disabled:hover:bg-transparent disabled:cursor-not-allowed" title="Delete chapter"><Icon icon="mdi:delete-outline" class="size-4" /></button>
      <span class="mx-0.5 w-px h-4 bg-base-content/10"></span>
      <button onclick={() => { newTranslationName = ""; renameTL = null; showManageTL = true; }} class="text-base-content/40 hover:text-base-content transition-colors p-1.5 rounded hover:bg-base-content/5" title="Manage translations"><Icon icon="mdi:translate" class="size-4" /></button>
      <span class="mx-0.5 w-px h-4 bg-base-content/10"></span>
      {#if showExport}
        <div data-export-dropdown class="absolute top-full left-0 mt-1.5 bg-base-200/95 backdrop-blur-sm border border-base-content/10 rounded-xl shadow-2xl py-1 min-w-44 z-50 overflow-hidden">
          <button onclick={exportCurrentChapter} disabled={!selected || selected === "sandbox" || !input} class="block w-full text-left text-xs px-3 py-2 hover:bg-base-content/5 text-base-content/70 disabled:text-base-content/20 disabled:cursor-not-allowed transition-colors">Export current chapter</button>
          <button onclick={exportAllEdited} disabled={dirty.size === 0 && isSourceTranslation} class="block w-full text-left text-xs px-3 py-2 hover:bg-base-content/5 text-base-content/70 disabled:text-base-content/20 disabled:cursor-not-allowed transition-colors">Export all chapters</button>
        </div>
      {/if}
      {#if showRevert}
        <div data-revert-dropdown class="absolute top-full left-0 mt-1.5 bg-base-200/95 backdrop-blur-sm border border-base-content/10 rounded-xl shadow-2xl py-1 min-w-44 z-50 overflow-hidden">
          <button onclick={revertCurrentChapter} disabled={!selected || selected === "sandbox" || !dirty.has(selected)} class="block w-full text-left text-xs px-3 py-2 hover:bg-base-content/5 text-base-content/70 disabled:text-base-content/20 disabled:cursor-not-allowed transition-colors">Revert current chapter</button>
          <button onclick={revertAllChapters} disabled={dirty.size === 0} class="block w-full text-left text-xs px-3 py-2 hover:bg-base-content/5 text-base-content/70 disabled:text-base-content/20 disabled:cursor-not-allowed transition-colors">Revert all edited chapters</button>
        </div>
      {/if}
    </div>
    <div class="flex items-center gap-2">
      <div class="relative">
        <button bind:this={themeBtn} onclick={() => showThemeMenu = !showThemeMenu} class="text-base-content/40 hover:text-base-content transition-colors p-1.5 rounded hover:bg-base-content/5" title="Theme">
          <Icon icon="mdi:palette-outline" class="size-4" />
        </button>
        {#if showThemeMenu}
          <div class="absolute top-full right-0 mt-1.5 bg-base-200/95 backdrop-blur-sm border border-base-content/10 rounded-xl shadow-2xl py-1 min-w-36 z-50 overflow-hidden">
            {#each THEMES as t}
              <button onclick={() => { theme = t; showThemeMenu = false; }} class="block w-full text-left text-xs px-3 py-2 hover:bg-base-content/10 text-base-content/70 transition-colors {theme === t ? 'bg-primary/10 text-primary' : ''}">{t.charAt(0).toUpperCase() + t.slice(1)}</button>
            {/each}
          </div>
        {/if}
      </div>
      <button onclick={() => showInfo = true} class="version-btn text-xs font-mono px-2 py-1 rounded">v0.4</button>
    </div>
  </div>

  <div class="flex-1 flex p-2 lg:p-3 gap-2 lg:gap-3 min-h-0">
    <!-- ===== MOBILE LAYOUT (< lg) ===== -->
    <div class="flex flex-1 lg:hidden min-h-0">
      <!-- Full-width editor | reader -->
      <div class="flex-1 flex flex-col min-w-0">
        <div class="flex gap-0.5 mb-2 shrink-0">
          <button onclick={() => rightTab = 'editor'} class="flex-1 text-[10px] font-mono font-medium tracking-wider py-1.5 rounded-lg transition-colors {rightTab === 'editor' ? 'bg-base-content/10 text-base-content/70' : 'text-base-content/50 hover:text-base-content/70'}">Markdown</button>
          <button onclick={() => rightTab = 'reader'} class="flex-1 text-[10px] font-mono font-medium tracking-wider py-1.5 rounded-lg transition-colors {rightTab === 'reader' ? 'bg-base-content/10 text-base-content/70' : 'text-base-content/50 hover:text-base-content/70'}">Reader</button>
        </div>
        {#if rightTab === 'editor'}
          <div class="flex-1 flex flex-col min-h-0 min-w-0">
            <div class="flex items-center gap-2 px-3 py-1.5 border-b border-base-content/10 bg-base-200/40 backdrop-blur-sm rounded-t-xl shrink-0">
              <span class="text-[10px] font-mono text-base-content/30 font-medium uppercase tracking-wider">markdown</span>
              {#if selected}
                <span class="text-[10px] font-mono text-base-content/20">·</span>
                <span class="text-[10px] font-mono text-base-content/25 truncate">{selected}</span>
              {/if}
            </div>
            <textarea bind:value={input} bind:this={mdScroll} placeholder="select a chapter to start editing..." class="flex-1 font-mono text-sm leading-relaxed p-4 resize-none outline-none rounded-b-xl border-x border-b border-base-content/10 bg-base-300/60 text-base-content/80 placeholder:text-base-content/15 min-h-0 transition-colors focus:bg-base-300/80"></textarea>
          </div>
        {:else}
          <div class="flex-1 flex flex-col min-h-0 min-w-0">
            <div class="flex items-center gap-2 px-3 py-1.5 border-b border-base-content/10 bg-base-200/40 backdrop-blur-sm rounded-t-xl shrink-0">
              <span class="text-[10px] font-mono text-base-content/30 font-medium uppercase tracking-wider">reader</span>
              {#if selected}
                <span class="text-[10px] font-mono text-base-content/20">·</span>
                <span class="text-[10px] font-mono text-base-content/25">{selected}</span>
              {/if}
            </div>
            <div bind:this={readerScroll} class="flex-1 overflow-y-auto rounded-b-xl border-x border-b border-base-content/10 bg-base-300/60 scrollbar-thin">
              <article class="reader-container chapter-content prose prose-lg md:prose-xl max-w-none wrap-break-word" style="--chapter-font: 'Alegreya', serif; --chapter-size: 18px; --chapter-weight: 450; --chapter-lh: 1.8; --chapter-indent: 0; --chapter-align: left; --chapter-hyphens: none;">
                {#if previewHtml}{@html previewHtml}{/if}
              </article>
            </div>
          </div>
        {/if}
      </div>
    </div>

    <!-- ===== DESKTOP LAYOUT (lg+) ===== -->
    <div class="hidden lg:flex flex-1 gap-3">
      <div class="w-56 flex flex-col bg-base-200/80 backdrop-blur-sm rounded-xl border border-base-content/10 shrink-0 min-h-0 shadow-lg">
        <div class="flex gap-1 p-2 border-b border-base-content/10">
          <input type="text" bind:value={search} placeholder="search" class="flex-1 bg-base-300/60 text-base-content/70 text-xs px-2.5 py-1.5 rounded-lg outline-none border border-base-content/10 min-w-0 placeholder:text-base-content/20 transition-colors focus:border-primary/30 focus:text-base-content/80" />
          <select bind:value={translation} onchange={handleTranslationChange} class="bg-base-300/60 text-base-content/70 text-xs px-2 py-1.5 rounded-lg outline-none border border-base-content/10 w-22 transition-colors focus:border-primary/30 focus:text-base-content/80">
            <option value="fantl">fantl</option>
            <option value="MTL">MTL</option>
            {#each customTranslations as t}
              <option value={t}>{t}</option>
            {/each}
          </select>
          <button onclick={refreshChapters} disabled={refreshing} class="text-base-content/40 hover:text-base-content transition-colors p-1.5 rounded hover:bg-base-content/5 disabled:text-base-content/15 disabled:hover:bg-transparent disabled:cursor-not-allowed" title="Refresh chapters">
            <Icon icon={refreshing ? "mdi:loading" : "mdi:refresh"} class="size-3.5 {refreshing ? 'animate-spin' : ''}" />
          </button>
        </div>
        <div class="flex-1 overflow-y-auto p-1.5 min-h-0 space-y-0.5 scrollbar-thin">
          <button onclick={loadSandbox} class="block w-full text-left text-xs px-2.5 py-1.5 rounded-lg hover:bg-base-content/5 transition-colors {selected === 'sandbox' ? 'bg-primary/10 text-primary' : 'text-base-content/70'}">blank chapter</button>
          <div class="mx-1 my-1.5 border-t border-base-content/10"></div>
          {#if loading}
            <div class="flex items-center justify-center gap-2 py-6"><Icon icon="mdi:loading" class="size-4 text-base-content/50 animate-spin" /><span class="text-xs text-base-content/50">loading...</span></div>
          {:else if error}
            <p class="text-xs text-error/70 text-center py-6">{error}</p>
          {:else if filtered.length === 0}
            <p class="text-xs text-base-content/40 text-center py-6">none</p>
          {:else}
            {#each filtered as file}
              <button onclick={() => loadChapter(file)} title="{indices.has(file) ? 'ch' + indices.get(file) : file}{titles.has(file) ? ' - ' + titles.get(file) : ''}{dirty.has(file) ? ' (modified)' : ''}" class="block w-full text-left text-xs px-2.5 py-1.5 rounded-lg hover:bg-base-content/5 transition-colors whitespace-nowrap overflow-hidden text-ellipsis {selected === file ? 'bg-primary/10 text-base-content' : dirty.has(file) ? 'text-success' : 'text-base-content/70'}">
                {#if indices.has(file)}<span class="font-medium">ch{indices.get(file)}</span>{:else}<span class="font-medium">{file.replace('.md','')}</span>{/if}
                {#if titles.has(file)}<span class="text-base-content/50 ml-1">— {titles.get(file)}</span>{/if}
                {#if dirty.has(file)}<span class="text-success/60 ml-1">●</span>{/if}
              </button>
            {/each}
          {/if}
        </div>
      </div>
      <div class="flex-1 flex flex-col min-h-0 min-w-0">
        <div class="flex items-center gap-2 px-3 py-1.5 border-b border-base-content/10 bg-base-200/40 backdrop-blur-sm rounded-t-xl shrink-0">
          <span class="text-[10px] font-mono text-base-content/30 font-medium uppercase tracking-wider">markdown</span>
          {#if selected}
            <span class="text-[10px] font-mono text-base-content/20">·</span>
            <span class="text-[10px] font-mono text-base-content/25 truncate">{selected}</span>
          {/if}
        </div>
        <textarea bind:value={input} bind:this={mdScroll} placeholder="select a chapter to start editing..." class="flex-1 font-mono text-sm leading-relaxed p-4 resize-none outline-none rounded-b-xl border-x border-b border-base-content/10 bg-base-300/60 text-base-content/80 placeholder:text-base-content/15 min-h-0 transition-colors focus:bg-base-300/80"></textarea>
      </div>
      <div class="flex-1 flex flex-col min-h-0 min-w-0">
        <div class="flex items-center gap-2 px-3 py-1.5 border-b border-base-content/10 bg-base-200/40 backdrop-blur-sm rounded-t-xl shrink-0">
          <span class="text-[10px] font-mono text-base-content/30 font-medium uppercase tracking-wider">reader</span>
          {#if selected}
            <span class="text-[10px] font-mono text-base-content/20">·</span>
            <span class="text-[10px] font-mono text-base-content/25">{selected}</span>
          {/if}
        </div>
        <div bind:this={readerScroll} class="flex-1 overflow-y-auto rounded-b-xl border-x border-b border-base-content/10 bg-base-300/60 scrollbar-thin">
          <article class="reader-container chapter-content prose prose-lg md:prose-xl max-w-none wrap-break-word" style="--chapter-font: 'Alegreya', serif; --chapter-size: 18px; --chapter-weight: 450; --chapter-lh: 1.8; --chapter-indent: 0; --chapter-align: left; --chapter-hyphens: none;">
            {#if previewHtml}{@html previewHtml}{/if}
          </article>
        </div>
      </div>
      <div class="w-64 flex flex-col bg-base-200/40 rounded-xl border border-base-content/10 shrink-0 min-h-0">
        <div class="flex items-center gap-2 px-3 py-1.5 border-b border-base-content/10 bg-base-200/40 backdrop-blur-sm rounded-t-xl shrink-0">
          <span class="text-[10px] font-mono text-base-content/30 font-medium uppercase tracking-wider">formatting</span>
        </div>
        <div class="flex-1 overflow-y-auto overflow-x-hidden scrollbar-thin">
          <table class="w-full border-collapse">
            {#each [
              { syntax: "%%text%%", desc: "Shake effect (block)" }, { syntax: "%~text~%", desc: "Shake effect (per-char)" }, { syntax: "%^text^%", desc: "Wave up effect" }, { syntax: "@@text@@", desc: "Glitch text (heavy)" }, { syntax: "@_@text@_@", desc: "Glitch text (subtle)" }, { syntax: "#^#text#^#", desc: "Grow font size" }, { syntax: "#v#text#v#", desc: "Shrink font size" }, { syntax: "~~~", desc: "Visible horizontal rule" }, { syntax: "_text_", desc: "Underline" }, { syntax: "@ll@text@ll@", desc: "Mono left-aligned" }, { syntax: "@rr@text@rr@", desc: "Mono right-aligned" }, { syntax: "@l@text@l@", desc: "Left align" }, { syntax: "@r@text@r@", desc: "Right align" }, { syntax: "#*text*#", desc: "Large text" }, { syntax: "#><text><#", desc: "Large centered text" }, { syntax: "#rtextr#", desc: "Red text" }, { syntax: "#btextb#", desc: "Blue text" }, { syntax: "#ytexty#", desc: "Yellow text" }, { syntax: "#ptextp#", desc: "Magenta text" }, { syntax: "#gtextg#", desc: "Green text" }, { syntax: "#otexto#", desc: "Orange text" }, { syntax: "#f#text#f#", desc: "Fade out" }, { syntax: ";rtextr;", desc: "Red highlight" }, { syntax: ";btextb;", desc: "Blue highlight" }, { syntax: ";ytexty;", desc: "Yellow highlight" }, { syntax: ";ptextp;", desc: "Magenta highlight" }, { syntax: ";gtextg;", desc: "Green highlight" }, { syntax: ";otexto;", desc: "Orange highlight" }, { syntax: "+-text-+", desc: "Wiki window" }, { syntax: "+$text$+", desc: "Plain window" }, { syntax: "&$text$&", desc: "Followup window" }, { syntax: "&--text--&", desc: "Record window" }, { syntax: "+~text~+", desc: "System window" }, { syntax: "+=text=+", desc: "Black CRT window" }, { syntax: "!-text-!", desc: "Notepad window" }, { syntax: "!$text$!", desc: "Sticky note window" }, { syntax: "![text]!", desc: "Braun CRT monitor" },
            ] as opt}
              <tr class="border-b border-base-content/[3%] hover:bg-base-content/[4%] transition-colors">
                <td class="px-3 py-1.5 whitespace-nowrap text-base-content/70 text-[10px] font-mono">{opt.syntax}</td>
                <td class="px-3 py-1.5 text-base-content/30 text-[10px]">{opt.desc}</td>
              </tr>
            {/each}
          </table>
        </div>
      </div>
    </div>
  </div>

  <div class="flex items-center justify-between px-4 py-1.5 border-t border-base-content/10 bg-base-300/30 backdrop-blur-sm shrink-0">
    <span class="text-[10px] font-mono text-base-content/25">gsgw / {translation}{#if !isSourceTranslation} <span class="text-warning/40">(custom)</span>{/if}</span>
    <div class="flex items-center gap-3">
      {#if selected === "sandbox"}
        <span class="text-[10px] font-mono text-base-content/25">blank chapter</span>
      {:else if selected}
        {#if isSourceTranslation}
          <a
            href="https://github.com/{REPO}/edit/{BRANCH}/chapters/gsgw/{translation}/{selected}"
            target="_blank"
            class="text-[10px] font-mono text-base-content/30 hover:text-primary transition-colors"
          >↗ {selected}</a>
        {:else}
          <span class="text-[10px] font-mono text-warning/40">{selected}</span>
        {/if}
      {:else}
        <span class="text-[10px] font-mono text-base-content/20">no file</span>
      {/if}
    </div>
  </div>
</div>

{#if showMobileMenu}
  <div
    class="fixed inset-0 z-40 lg:hidden"
    onclick={() => showMobileMenu = false}
    role="dialog"
  >
    <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" onclick={() => showMobileMenu = false}></div>
    <div
      class="absolute left-0 top-0 bottom-0 w-72 max-w-[85vw] bg-base-300 border-r border-base-content/10 shadow-2xl flex flex-col animate-slide-in-left"
      onclick={(e) => e.stopPropagation()}
    >
      <div class="flex items-center justify-between px-3 py-2 border-b border-base-content/10 shrink-0">
        <span class="text-[10px] font-mono text-base-content/40 font-medium uppercase tracking-wider">Menu</span>
        <button onclick={() => showMobileMenu = false} class="text-base-content/40 hover:text-base-content transition-colors p-1 rounded hover:bg-base-content/5"><Icon icon="mdi:close" class="size-4" /></button>
      </div>
      <div class="flex gap-0.5 px-3 pt-2 shrink-0">
        <button onclick={() => leftTab = 'chapters'} class="flex-1 text-[10px] font-mono font-medium tracking-wider py-1.5 rounded-lg transition-colors {leftTab === 'chapters' ? 'bg-base-content/10 text-base-content/70' : 'text-base-content/50 hover:text-base-content/70'}">Chapters</button>
        <button onclick={() => leftTab = 'formatting'} class="flex-1 text-[10px] font-mono font-medium tracking-wider py-1.5 rounded-lg transition-colors {leftTab === 'formatting' ? 'bg-base-content/10 text-base-content/70' : 'text-base-content/50 hover:text-base-content/70'}">Formatting</button>
      </div>
      <div class="flex-1 min-h-0 px-3 pb-3 pt-1.5">
        {#if leftTab === 'chapters'}
          <div class="h-full flex flex-col bg-base-200/80 backdrop-blur-sm rounded-xl border border-base-content/10 shadow-lg">
            <div class="flex gap-1 p-2 border-b border-base-content/10">
              <input type="text" bind:value={search} placeholder="search" class="flex-1 bg-base-300/60 text-base-content/70 text-xs px-2.5 py-1.5 rounded-lg outline-none border border-base-content/10 min-w-0 placeholder:text-base-content/20 transition-colors focus:border-primary/30 focus:text-base-content/80" />
              <select bind:value={translation} onchange={handleTranslationChange} class="bg-base-300/60 text-base-content/70 text-xs px-2 py-1.5 rounded-lg outline-none border border-base-content/10 w-22 transition-colors focus:border-primary/30 focus:text-base-content/80">
                <option value="fantl">fantl</option>
                <option value="MTL">MTL</option>
                {#each customTranslations as t}
                  <option value={t}>{t}</option>
                {/each}
              </select>
              <button onclick={refreshChapters} disabled={refreshing} class="text-base-content/40 hover:text-base-content transition-colors p-1.5 rounded hover:bg-base-content/5 disabled:text-base-content/15 disabled:hover:bg-transparent disabled:cursor-not-allowed" title="Refresh chapters">
                <Icon icon={refreshing ? "mdi:loading" : "mdi:refresh"} class="size-3.5 {refreshing ? 'animate-spin' : ''}" />
              </button>
            </div>
            <div class="flex-1 overflow-y-auto p-1.5 min-h-0 space-y-0.5 scrollbar-thin">
              <button onclick={() => { loadSandbox(); showMobileMenu = false; }} class="block w-full text-left text-xs px-2.5 py-1.5 rounded-lg hover:bg-base-content/5 transition-colors {selected === 'sandbox' ? 'bg-primary/10 text-primary' : 'text-base-content/70'}">blank chapter</button>
              <div class="mx-1 my-1.5 border-t border-base-content/10"></div>
              {#if loading}
                <div class="flex items-center justify-center gap-2 py-6"><Icon icon="mdi:loading" class="size-4 text-base-content/50 animate-spin" /><span class="text-xs text-base-content/50">loading...</span></div>
              {:else if error}
                <p class="text-xs text-error/70 text-center py-6">{error}</p>
              {:else if filtered.length === 0}
                <p class="text-xs text-base-content/40 text-center py-6">none</p>
              {:else}
                {#each filtered as file}
                  <button onclick={() => { loadChapter(file); showMobileMenu = false; }} title="{indices.has(file) ? 'ch' + indices.get(file) : file}{titles.has(file) ? ' - ' + titles.get(file) : ''}{dirty.has(file) ? ' (modified)' : ''}" class="block w-full text-left text-xs px-2.5 py-1.5 rounded-lg hover:bg-base-content/5 transition-colors whitespace-nowrap overflow-hidden text-ellipsis {selected === file ? 'bg-primary/10 text-base-content' : dirty.has(file) ? 'text-success' : 'text-base-content/70'}">
                    {#if indices.has(file)}<span class="font-medium">ch{indices.get(file)}</span>{:else}<span class="font-medium">{file.replace('.md','')}</span>{/if}
                    {#if titles.has(file)}<span class="text-base-content/50 ml-1">— {titles.get(file)}</span>{/if}
                    {#if dirty.has(file)}<span class="text-success/60 ml-1">●</span>{/if}
                  </button>
                {/each}
              {/if}
            </div>
          </div>
        {:else}
          <div class="h-full flex flex-col bg-base-200/40 rounded-xl border border-base-content/10 overflow-y-auto scrollbar-thin">
            <table class="w-full border-collapse">
              {#each [
                { syntax: "%%text%%", desc: "Shake effect (block)" }, { syntax: "%~text~%", desc: "Shake effect (per-char)" }, { syntax: "%^text^%", desc: "Wave up effect" }, { syntax: "@@text@@", desc: "Glitch text (heavy)" }, { syntax: "@_@text@_@", desc: "Glitch text (subtle)" }, { syntax: "#^#text#^#", desc: "Grow font size" }, { syntax: "#v#text#v#", desc: "Shrink font size" }, { syntax: "~~~", desc: "Visible horizontal rule" }, { syntax: "_text_", desc: "Underline" }, { syntax: "@ll@text@ll@", desc: "Mono left-aligned" }, { syntax: "@rr@text@rr@", desc: "Mono right-aligned" }, { syntax: "@l@text@l@", desc: "Left align" }, { syntax: "@r@text@r@", desc: "Right align" }, { syntax: "#*text*#", desc: "Large text" }, { syntax: "#><text><#", desc: "Large centered text" }, { syntax: "#rtextr#", desc: "Red text" }, { syntax: "#btextb#", desc: "Blue text" }, { syntax: "#ytexty#", desc: "Yellow text" }, { syntax: "#ptextp#", desc: "Magenta text" }, { syntax: "#gtextg#", desc: "Green text" }, { syntax: "#otexto#", desc: "Orange text" }, { syntax: "#f#text#f#", desc: "Fade out" }, { syntax: ";rtextr;", desc: "Red highlight" }, { syntax: ";btextb;", desc: "Blue highlight" }, { syntax: ";ytexty;", desc: "Yellow highlight" }, { syntax: ";ptextp;", desc: "Magenta highlight" }, { syntax: ";gtextg;", desc: "Green highlight" }, { syntax: ";otexto;", desc: "Orange highlight" }, { syntax: "+-text-+", desc: "Wiki window" }, { syntax: "+$text$+", desc: "Plain window" }, { syntax: "&$text$&", desc: "Followup window" }, { syntax: "&--text--&", desc: "Record window" }, { syntax: "+~text~+", desc: "System window" }, { syntax: "+=text=+", desc: "Black CRT window" }, { syntax: "!-text-!", desc: "Notepad window" }, { syntax: "!$text$!", desc: "Sticky note window" }, { syntax: "![text]!", desc: "Braun CRT monitor" },
              ] as opt}
                <tr class="border-b border-base-content/[3%] hover:bg-base-content/[4%] transition-colors">
                  <td class="px-3 py-1.5 whitespace-nowrap text-base-content/70 text-[10px] font-mono">{opt.syntax}</td>
                  <td class="px-3 py-1.5 text-base-content/30 text-[10px]">{opt.desc}</td>
                </tr>
              {/each}
            </table>
          </div>
        {/if}
      </div>
    </div>
  </div>
{/if}

{#if showManageTL}
  <div
    class="fixed inset-0 z-50 flex items-start justify-center pt-24 bg-black/70 backdrop-blur-sm animate-in fade-in duration-150"
    onclick={() => showManageTL = false}
    role="dialog"
  >
    <div
      class="bg-base-200/80 border border-base-content/10 rounded-2xl p-5 w-96 shadow-2xl max-h-[65vh] flex flex-col"
      onclick={(e) => e.stopPropagation()}
    >
      <h2 class="text-sm font-bold text-base-content/70 font-mono mb-4 tracking-wide">Manage Translations</h2>
      <div class="flex gap-2 mb-4">
        <input
          bind:value={newTranslationName}
          onkeydown={(e) => { if (e.key === "Enter") confirmNewTranslation(); }}
          placeholder="new translation name"
          class="flex-1 bg-base-300/60 text-base-content/70 text-xs px-3 py-2 rounded-xl outline-none border border-base-content/10 transition-colors focus:border-primary/30 placeholder:text-base-content/20"
        />
        <button onclick={confirmNewTranslation} disabled={!newTranslationName.trim()} class="btn btn-soft btn-xs btn-primary rounded-xl px-3">Add</button>
      </div>
      <div class="flex-1 overflow-y-auto space-y-0.5 scrollbar-thin">
        {#each customTranslations as tl}
          <div class="flex items-center gap-2 group px-2 py-1 rounded-xl hover:bg-base-content/5 transition-colors">
            {#if renameTL === tl}
              <input
                bind:value={renameTLValue}
                onkeydown={(e) => { if (e.key === "Enter") confirmRename(); if (e.key === "Escape") renameTL = null; }}
                class="flex-1 bg-base-300/60 text-base-content/70 text-xs px-2 py-1.5 rounded-lg outline-none border border-primary/40 autofocus"
                autofocus
              />
              <button onclick={confirmRename} class="text-success/60 hover:text-success transition-colors p-1" title="Save"><Icon icon="mdi:check" class="size-4" /></button>
              <button onclick={() => renameTL = null} class="text-base-content/30 hover:text-base-content/60 transition-colors p-1" title="Cancel"><Icon icon="mdi:close" class="size-4" /></button>
            {:else}
              <span class="flex-1 text-xs text-base-content/60 font-mono truncate">{tl}</span>
              <button onclick={() => startRename(tl)} class="text-base-content/20 hover:text-base-content/60 transition-colors p-1 opacity-0 group-hover:opacity-100" title="Rename"><Icon icon="mdi:pencil-outline" class="size-3.5" /></button>
              <button onclick={() => deleteTL(tl)} class="text-error/30 hover:text-error transition-colors p-1 opacity-0 group-hover:opacity-100" title="Delete"><Icon icon="mdi:delete-outline" class="size-3.5" /></button>
            {/if}
          </div>
        {/each}
      </div>
    </div>
  </div>
{/if}

{#if showInfo}
  <div
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm animate-in fade-in duration-150"
    onclick={() => showInfo = false}
    role="dialog"
  >
    <div
      class="bg-base-200/80 border border-base-content/10 rounded-2xl p-6 w-96 shadow-2xl"
      onclick={(e) => e.stopPropagation()}
    >
      <h2 class="text-sm font-bold text-base-content/70 font-mono mb-5 tracking-wide">Patch Notes</h2>
      {#each patchNotes as note}
        <div class="mb-3 last:mb-0">
          <button
            onclick={() => toggleVersion(note.version)}
            class="flex items-center gap-2 text-xs font-mono text-base-content/60 hover:text-base-content transition-colors w-full text-left"
          >
            <span class="text-[10px] w-3 text-base-content/30">{expandedVersion === note.version ? "▼" : "▶"}</span>
            <span class="font-medium">{note.version}</span>
          </button>
          {#if expandedVersion === note.version}
            <p class="text-xs text-base-content/40 font-mono leading-relaxed mt-1.5 ml-5 whitespace-pre-line">{note.description}</p>
          {/if}
        </div>
      {/each}
    </div>
  </div>
{/if}

<style>
  @keyframes slide-in-left {
    from { transform: translateX(-100%); }
    to { transform: translateX(0); }
  }
  :global(.animate-slide-in-left) {
    animation: slide-in-left 0.2s ease-out;
  }

  @keyframes glow-pulse {
    0%, 100% { text-shadow: 0 0 10px oklch(var(--p)/0.3), 0 0 20px oklch(var(--p)/0.1); }
    50% { text-shadow: 0 0 18px oklch(var(--p)/0.55), 0 0 36px oklch(var(--p)/0.25); }
  }
  .version-btn {
    color: oklch(var(--bc)/0.55);
    transition: color 0.2s;
    animation: glow-pulse 2.5s ease-in-out infinite;
  }
  .version-btn:hover {
    color: oklch(var(--bc)/0.85);
    animation: glow-pulse 0.8s ease-in-out infinite;
  }
  :global(.scrollbar-thin) {
    scrollbar-width: thin;
    scrollbar-color: oklch(var(--bc)/0.08) transparent;
  }
  :global(.scrollbar-thin::-webkit-scrollbar) {
    width: 4px;
  }
  :global(.scrollbar-thin::-webkit-scrollbar-track) {
    background: transparent;
  }
  :global(.scrollbar-thin::-webkit-scrollbar-thumb) {
    background: oklch(var(--bc)/0.08);
    border-radius: 2px;
  }
  :global(.scrollbar-thin::-webkit-scrollbar-thumb:hover) {
    background: oklch(var(--bc)/0.15);
  }

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

  .reader-container :global(.twitter-embed-text) {
    color: #71767b;
    font-size: 0.85rem;
    line-height: 1.4;
    margin: 0.5rem 0;
  }

  .reader-container :global(.twitter-embed-stats) {
    display: flex;
    align-items: center;
    gap: 1rem;
    margin-top: 0.5rem;
    padding-top: 0.5rem;
    border-top: 1px solid rgba(255,255,255,0.1);
    color: #71767b;
    font-size: 0.75rem;
  }

  .reader-container :global(.twitter-embed-stat) {
    display: flex;
    align-items: center;
    gap: 0.25rem;
  }

  .reader-container :global(.twitter-embed-loading),
  .reader-container :global(.twitter-embed-error) {
    padding: 1.25rem;
    text-align: center;
    font-size: 0.8rem;
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
