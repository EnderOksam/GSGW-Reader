<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  import { marked } from "marked";
  import Icon from "@iconify/svelte";
  import { slide } from "svelte/transition";
  import { tick } from "svelte";
  import { preprocessMarkdown } from "./lib/editor-markdown";
  import { REPO, BRANCH, BOOKS, tlDir, fetchChapterList, fetchChapterFile, fetchChapterPreview, extractMeta } from "./lib/github-api";
  import { loadCache as loadChapterCache, saveCache as saveChapterCache, saveChapterEdit } from "./lib/chapter-cache";
  import { hydrateTwitterEmbeds } from "$lib/reader/twitter-embeds";
  import { loadCustomTranslations, saveCustomTranslations, loadCustomChapterList, loadCustomChapterContent, saveCustomChapter, deleteCustomChapter, renameCustomTranslation, deleteCustomTranslation } from "./lib/custom-translations";
  import { importZip, createZip, downloadBlob } from "./lib/zip-tools";

  let {
    showMobileMenu = $bindable(false),
    currentBook = $bindable("gsgw"),
    selected = $bindable<string | null>(null),
    translation = $bindable("fantl"),
    dirty = $bindable<Set<string>>(new Set()),
    input = $bindable(""),
    isSourceTranslation = $bindable(true),
  } = $props();

  let customTranslations = $state<string[]>([]);
  let chapters = $state<string[]>([]);
  let filtered = $state<string[]>([]);
  let titles = $state<Map<string, string>>(new Map());
  let indices = $state<Map<string, string>>(new Map());
  let search = $state("");
  let loading = $state(true);
  let refreshing = $state(false);
  let error = $state("");
  let cache = $state<Map<string, string>>(new Map());
  let originalContent = $state<Map<string, string>>(new Map());
  let leftTab = $state<'chapters' | 'formatting'>('chapters');
  let rightTab = $state<'editor' | 'reader'>('editor');
  let formatSections = $state<Record<string, boolean>>({ 'Colors & Markdown': true, 'Changing Text': true, 'windows': true });
  let expandedSyntax = $state<Record<string, boolean>>({});
  let windowViewMode = $state<Record<string, 'code' | 'preview'>>({});

  let activeTextarea: HTMLTextAreaElement | null = null;

  async function insertFormatting(syntax: string) {
    if (!activeTextarea) return;
    const el = activeTextarea;
    const start = el.selectionStart;
    const end = el.selectionEnd;
    const current = input;
    const selected = current.slice(start, end);
    const hasPlaceholder = syntax.includes("text");
    const replacement = hasPlaceholder ? syntax.replace("text", selected || "text") : syntax;
    const before = current.slice(0, start);
    const after = current.slice(end);
    const readerTop = readerScroll?.scrollTop ?? 0;
    input = before + replacement + after;
    await tick();
    el.focus();
    const pos = start + replacement.length;
    el.setSelectionRange(pos, pos);
    if (readerScroll) readerScroll.scrollTop = readerTop;
  }
  let newTranslationName = $state("");
  let showManageTL = $state(false);
  let renameTL: string | null = $state(null);
  let renameTLValue = $state("");
  let mdScroll: HTMLElement | null = $state(null);
  let readerScroll: HTMLElement | null = $state(null);
  let scrollPositions = new Map<string, { md: number; reader: number }>();

  $effect(() => {
    isSourceTranslation = (BOOKS.find(b => b.slug === currentBook)?.translations ?? []).includes(translation);
  });

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
      return marked.parse(body, { renderer, html: true });
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

  async function loadChapterList() {
    loading = true;
    error = "";
    try {
      if (isSourceTranslation) {
        const files = await fetchChapterList(currentBook, translation);
        chapters = files;
        filtered = files;
        const tmap = new Map<string, string>();
        const imap = new Map<string, string>();
        await Promise.allSettled(files.map(async (f) => {
          const meta = await fetchChapterPreview(currentBook, translation, f);
          if (meta.title) tmap.set(f, meta.title);
          if (meta.index) imap.set(f, meta.index);
        }));
        titles = tmap;
        indices = imap;
      } else {
        const files = loadCustomChapterList(translation);
        chapters = files;
        filtered = files;
        const tmap = new Map<string, string>();
        const imap = new Map<string, string>();
        for (const f of files) {
          const content = loadCustomChapterContent(translation, f);
          if (!content) continue;
          const meta = extractMeta(content);
          if (meta.title) tmap.set(f, meta.title);
          if (meta.index) imap.set(f, meta.index);
        }
        titles = tmap;
        indices = imap;
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
      const text = await fetchChapterFile(currentBook, translation, file);
      originalContent.set(file, text);
      input = text;
      requestAnimationFrame(() => restoreScrollPositions(file));
    } catch (e: any) {
      input = `// error loading ${file}: ${e.message}`;
    }
  }

  let prevBook = currentBook;

  $effect(() => {
    if (currentBook !== prevBook) {
      saveCurrent();
      prevBook = currentBook;
      const tls = BOOKS.find(b => b.slug === currentBook)?.translations ?? [];
      if (!tls.includes(translation)) {
        translation = tls[0] ?? "fantl";
      }
      refreshChapters();
    }
  });

  function handleTranslationChange() {
    saveCurrent();
    if (!isSourceTranslation && !customTranslations.includes(translation)) {
      customTranslations = [...customTranslations, translation];
      saveCustomTranslations(customTranslations);
    }
    refreshChapters();
  }

  function confirmNewTranslation() {
    const name = newTranslationName.trim();
    if (!name) return;
    showManageTL = false;
    translation = name;
    if (!customTranslations.includes(translation)) {
      customTranslations = [...customTranslations, translation];
      saveCustomTranslations(customTranslations);
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
    if ((BOOKS.find(b => b.slug === currentBook)?.translations ?? []).includes(newName) || customTranslations.includes(newName)) {
      renameTLValue = old;
      renameTL = null;
      return;
    }
    renameCustomTranslation(old, newName);
    customTranslations = customTranslations.map(t => t === old ? newName : t);
    saveCustomTranslations(customTranslations);
    if (translation === old) {
      translation = newName;
      loadChapterList();
    }
    renameTL = null;
  }

  function deleteTL(tl: string) {
    if (!confirm(`Delete "${tl}" and all its chapters?`)) return;
    deleteCustomTranslation(tl);
    customTranslations = customTranslations.filter(t => t !== tl);
    saveCustomTranslations(customTranslations);
    if (translation === tl) {
      translation = "fantl";
      loadChapterList();
    }
  }

  async function refreshChapters() {
    refreshing = true;
    const cached = loadChapterCache();
    cache = cached.cache;
    originalContent = cached.originalContent;
    dirty = cached.dirty;
    await loadChapterList();
    refreshing = false;
  }

  export function handleImportZip(e: Event) {
    const file = (e.target as HTMLInputElement).files?.[0];
    if (!file) return;
    importZip(file).then(async (entries) => {
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
      saveChapterCache(cache, originalContent);
    }).catch((err) => {
      alert("Failed to import zip: " + (err instanceof Error ? err.message : String(err)));
    });
    (e.target as HTMLInputElement).value = "";
  }

  export function newChapter() {
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

  export function deleteCurrentChapter() {
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
    filtered = chapters.filter((f) => {
      const title = titles.get(f)?.toLowerCase() || '';
      if (title.includes(q)) return true;
      const index = indices.get(f);
      if (index) {
        const chapterNum = currentBook === "debut" ? String(Number(index) + 1) : index;
        if (chapterNum.includes(q)) return true;
      }
      return false;
    });
  });

  $effect(() => {
    if (previewHtml) {
      hydrateTwitterEmbeds();
    }
  });

  $effect(() => {
    if (window.innerWidth >= 768) return;
    if (rightTab === 'reader' && previewHtml) {
      hydrateTwitterEmbeds();
    }
  });

  onMount(() => {
    const cached = loadChapterCache();
    cache = cached.cache;
    originalContent = cached.originalContent;
    dirty = cached.dirty;
    customTranslations = loadCustomTranslations();
    loadChapterList();
  });

  onDestroy(() => { saveCurrent(); });

  function saveScrollPositions(file: string) {
    if (!mdScroll || !readerScroll) return;
    scrollPositions.set(file, { md: mdScroll.scrollTop, reader: readerScroll.scrollTop });
  }

  function restoreScrollPositions(file: string) {
    const pos = scrollPositions.get(file);
    if (mdScroll) mdScroll.scrollTop = pos?.md ?? 0;
    if (readerScroll) readerScroll.scrollTop = pos?.reader ?? 0;
  }

  export function saveCurrent() {
    if (selected && selected !== "sandbox" && input) {
      saveScrollPositions(selected);
      if (!isSourceTranslation) {
        const result = saveChapterEdit(cache, originalContent, dirty, selected, input, false);
        dirty = result.dirty;
        saveCustomChapter(translation, selected, input);
        return;
      }
      const result = saveChapterEdit(cache, originalContent, dirty, selected, input, true);
      cache = result.cache;
      dirty = result.dirty;
      saveChapterCache(cache, originalContent);
    }
  }

  export function exportCurrentChapter() {
    if (!selected || selected === "sandbox" || !input) return;
    downloadBlob(new Blob([input]), `${translation}-${selected}`, "text/markdown");
  }

  export function exportAllEdited() {
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
    downloadBlob(zip as BlobPart, `${translation}-chapters.zip`, "application/zip");
  }

  export async function revertCurrentChapter() {
    if (!selected || selected === "sandbox") return;
    cache.delete(selected);
    dirty = new Set([...dirty].filter(f => f !== selected));
    scrollPositions.delete(selected);
    saveChapterCache(cache, originalContent);
    const orig = originalContent.get(selected);
    if (orig !== undefined) {
      input = orig;
    } else {
      try {
        const text = await fetchChapterFile(currentBook, translation, selected);
        originalContent.set(selected, text);
        input = text;
      } catch {}
    }
  }

  export async function revertAllChapters() {
    const wasDirty = dirty.has(selected || "");
    cache.clear();
    dirty = new Set();
    scrollPositions.clear();
    saveChapterCache(cache, originalContent);
    if (wasDirty && selected && selected !== "sandbox") {
      const orig = originalContent.get(selected);
      if (orig !== undefined) {
        input = orig;
      } else {
        try {
          const text = await fetchChapterFile(currentBook, translation, selected);
          originalContent.set(selected, text);
          input = text;
        } catch {}
      }
    }
  }

  export function openManageTL() {
    newTranslationName = "";
    renameTL = null;
    showManageTL = true;
  }

  function growPreview(): string {
    const t = "growing text";
    const len = t.length;
    return [...t].map((c, i) => {
      if (c === " ") return " ";
      const scale = 1 + (i / Math.max(len - 1, 1)) * 0.6;
      return `<span style="font-size:${scale.toFixed(2)}em">${c}</span>`;
    }).join("");
  }

  function shrinkPreview(): string {
    const t = "shrinking text";
    const len = t.length;
    return [...t].map((c, i) => {
      if (c === " ") return " ";
      const scale = 1.4 - (i / Math.max(len - 1, 1)) * 0.4;
      return `<span style="font-size:${scale.toFixed(2)}em">${c}</span>`;
    }).join("");
  }

  function wavePreview(): string {
    const t = "wave text";
    const len = t.length;
    return [...t].map((c, i) => {
      if (c === " ") return " ";
      const delay = ((len - 1 - i) * 0.05) % 0.5;
      return `<span class="wave-up" style="animation-delay:-${delay}s">${c}</span>`;
    }).join("");
  }

  function shakePerCharPreview(): string {
    const t = "shake text";
    return [...t].map((c, i) => {
      if (c === " ") return " ";
      return `<span class="shake" style="animation-delay:-${(i * 0.05) % 0.5}s">${c}</span>`;
    }).join("");
  }

  const colorsItems = [
    { syntax: "$$text$$", text: "handwritten text", cls: "handwritten", expandable: true },
    { syntax: "#rtextr#", text: "red text", cls: "text-red" },
    { syntax: "#otexto#", text: "orange text", cls: "text-orange" },
    { syntax: "#ytexty#", text: "yellow text", cls: "text-yellow" },
    { syntax: "#gtextg#", text: "green text", cls: "text-green" },
    { syntax: "#cytextcy#", text: "cyan text", cls: "text-cyan" },
    { syntax: "#btextb#", text: "blue text", cls: "text-blue" },
    { syntax: "#lptextlp#", text: "purple text", cls: "text-light-purple" },
    { syntax: "#ptextp#", text: "magenta text", cls: "text-magenta" },
    { syntax: ";rtextr;", text: "red highlight", cls: "hl-red" },
    { syntax: ";otexto;", text: "orange highlight", cls: "hl-orange" },
    { syntax: ";ytexty;", text: "yellow highlight", cls: "hl-yellow" },
    { syntax: ";gtextg;", text: "green highlight", cls: "hl-green" },
    { syntax: ";btextb;", text: "blue highlight", cls: "hl-blue" },
    { syntax: ";ptextp;", text: "magenta highlight", cls: "hl-magenta" },
    { syntax: "**text**", text: "bold text", cls: "font-bold" },
    { syntax: "*text*", text: "italic text", cls: "italic" },
    { syntax: "_text_", text: "underline text", cls: "underline" },
    { syntax: "~~text~~", text: "strikethrough text", cls: "line-through text-base-content/50" },
    { syntax: "$agtextag$", text: "silver text", cls: "silver-text", expandable: true },
    { syntax: "$stexts$", text: "smoke text", cls: "smoke-text", expandable: true },
    { syntax: "$atexta$", text: "aurora text", cls: "aurora-text", expandable: true },
    { syntax: "$gtextg$", text: "gold text", cls: "gold-text", expandable: true },
    { syntax: "$*text*$", text: "sparkle text", cls: "sparkle-text", expandable: true },
    { syntax: "$(text)$", text: "moon text", cls: "moon-text", expandable: true },
  ];

  const changingItems = [
    { syntax: "#*text*#", text: "large text", cls: "text-large", expandable: true },
    { syntax: "#><text><#", text: "large centered", cls: "text-large-centered", expandable: true },
    { syntax: "-# text #-", text: "small text", cls: "text-sub", expandable: true },
    { syntax: "#^#text#^#", text: "grow text", cls: "text-base-content/70", expandable: true, previewHtml: growPreview() },
    { syntax: "#v#text#v#", text: "shrink text", cls: "text-base-content/70", expandable: true, previewHtml: shrinkPreview() },
    { syntax: "#f#text#f#", text: "fade out", cls: "text-faded", expandable: true },
    { syntax: "#f>#text#f>#", text: "fade right", cls: "text-fade-right", expandable: true },
    { syntax: "#f<#text#f<#", text: "fade left", cls: "text-fade-left", expandable: true },
    { syntax: "@l@text@l@", text: "left align", cls: "text-left", expandable: true },
    { syntax: "@c@text@c@", text: "center align", cls: "text-center", expandable: true },
    { syntax: "@r@text@r@", text: "right align", cls: "text-right", expandable: true },
    { syntax: "@ll@text@ll@", text: "mono left", cls: "mono mono-left", expandable: true },
    { syntax: "@cc@text@cc@", text: "mono center", cls: "mono mono-center", expandable: true },
    { syntax: "@rr@text@rr@", text: "mono right", cls: "mono mono-right", expandable: true },
    { syntax: "%%text%%", text: "shake block", cls: "shake", expandable: true },
    { syntax: "%~text~%", text: "shake per-char", cls: "shake", expandable: true, previewHtml: shakePerCharPreview() },
    { syntax: "%^text^%", text: "wave up", cls: "wave-up", expandable: true, previewHtml: wavePreview() },
    { syntax: "@@text@@", text: "glitch heavy", cls: "glitch-text", expandable: true },
    { syntax: "@_@text@_@", text: "glitch subtle", cls: "glitch-subtle", expandable: true },
  ];

  const windowsItems = [
    { syntax: "~~~", name: "horizontal rule", cls: "", code: "~~~", html: '<hr class="visible-hr">', expandable: true },
    { syntax: "~^~", name: "section break", cls: "", code: "~^~", html: '<hr class="invisible-hr">', expandable: true },
    { syntax: "+-...-+", name: "wiki window", cls: "wiki-window", code: "+-\\nDark exploration records\\n\\nwindow example\\n-+", html: '<p><strong>Dark exploration records</strong></p>\n<p>window example</p>', expandable: true, meta: "the first line is metadata and can be canceled out if you put a \\ before it" },
    { syntax: "+=...=+", name: "crt window", cls: "black-window", code: "+=\\ncrt window example\\n=+", html: '<p>crt window example</p>', expandable: true },
    { syntax: "+~...~+", name: "gsgw system window", cls: "system-window", code: "+~\\nTitle\\nBody text\\n~+", html: '<p>Title</p><p>Body text</p>', expandable: true, meta: "the first line becomes a styled title with divider lines, use \\ to suppress" },
    { syntax: "+$...$+", name: "plain window", cls: "plain-window", code: "+$\\nplain window example\\n$+", html: '<p>plain window example</p>', expandable: true },
    { syntax: "&-...-&", name: "record window", cls: "record-window", code: "&-\\ndisaster management bureau\\n\\ndmb window example\\n-&", html: '<p><strong>disaster management bureau</strong></p>\n<p>dmb window example</p>', expandable: true, meta: "the first line is metadata and can be canceled out if you put a \\ before it" },
    { syntax: "&$...$&", name: "followup window", cls: "followup-window", code: "&$\\nfollowup window example\\n$&", html: '<p>followup window example</p>', expandable: true },
    { syntax: "!-...-!", name: "note window", cls: "note-window", code: "!-\\nheader\\n\\nnote window example\\n-!", html: '<p><strong>header</strong></p>\n<p>note window example</p>', expandable: true, meta: "the first line is metadata and can be canceled out if you put a \\ before it" },
    { syntax: "!$...$!", name: "sticky window", cls: "sticky-window", code: "!$\\nsticky window example\\n$!", html: '<p>sticky window example</p>', expandable: true },
    { syntax: "![...]!", name: "braun screen", cls: "braun-screen", code: "![\\nbraun screen example\\n]!", html: '<p>braun screen example</p>', expandable: true },
    { syntax: "★!...!★", name: "debut alert", cls: "debut-alert", code: "★!\\ndebut alert example\\n!★", html: '<p>debut alert example</p>', expandable: true },
    { syntax: "★:...:★", name: "sms window", cls: "sms-window", code: "★:\\n- PMD: left message\\nright message -\\ncentered message\\n:★", html: '<div class="sms-bubble sms-left" style="background:#FFF8D9;color:#222;">left message</div>\n<div class="sms-bubble sms-right" style="background:#FFF0E1;color:#222;">right message</div>\n<div class="sms-bubble sms-center">centered message</div>', expandable: true, meta: "Prefix with speaker code for colors: PMD (yellow), SAH (orange), BSJ (blue), LSJ (purple), KRB (pink), CE (red), RCW (green). - prefix = left, suffix - = right, no dash = centered" },
    { syntax: "★$...$★", name: "comment window", cls: "alert-window", code: "★$\\n[Title]\\n: Sub-Title\\nDescription\\n-Comment\\n└ reply\\n└└reply reply\\n$★", html: '<div class="comment-post-header"><div class="comment-post-title">Title</div><div class="comment-post-desc"><p>: Sub-Title</p><p>Description</p></div></div><div class="comment-section"><div class="comment">Comment</div><div class="comment-reply depth-1"><span class="reply-icon">└</span><span class="reply-body">reply</span></div><div class="comment-reply depth-2"><span class="reply-icon">└└</span><span class="reply-body">reply reply</span></div></div>', expandable: true, meta: "[title] = title, : desc = description, - comment = top-level comment, └ = reply (each └ adds a depth level, max 2)" },
    { syntax: "★=...=★", name: "debut achievement", cls: "debut-achievement", code: "★=\\n[Achievement]\\n[\\nitem one\\nitem two\\n]\\n=★", html: '<div class="debut-achievement-list"><div class="debut-achievement-list-item">item one</div><div class="debut-achievement-list-divider"></div><div class="debut-achievement-list-item">item two</div></div>', expandable: true, meta: "first line = title, [\\n lines \\n] = list, }text{ = sub-left, {text{ = sub-right, }[!]text} = alert-sub-left, {[!]text{ = alert-sub-right" },
    { syntax: "★-...-★", name: "debut window", cls: "debut-window", code: "★-\\nTitle\\n[label text]\\ncontent\\n-★", html: '<div class="debut-window-title">Title</div><div class="debut-window-label">label text</div><p>content</p>', expandable: true, meta: "first line = title (\\ to suppress), [text] on its own line = label div, use \\ before line to keep raw text" },
    { syntax: "}text}", name: "sub left", cls: "", code: "}left label}", html: '<span class="debut-achievement-sub debut-achievement-sub-left">left label</span>', expandable: true },
    { syntax: "{text{", name: "sub right", cls: "", code: "{right label{", html: '<span class="debut-achievement-sub debut-achievement-sub-right">right label</span>', expandable: true },
    { syntax: "}[!]text}", name: "alert sub left", cls: "", code: "}[!]alert label}", html: '<span class="alert-sub alert-sub-left">alert label</span>', expandable: true },
    { syntax: "{[!]text{", name: "alert sub right", cls: "", code: "{[!]alert label{", html: '<span class="alert-sub alert-sub-right">alert label</span>', expandable: true },
  ];
</script>

<div class="flex-1 flex flex-col min-h-0 min-w-0">
{#snippet section(title, items)}
  {@const sectionId = title}
  {@const expandable = items.filter(i => i.expandable)}
  {@const regular = items.filter(i => !i.expandable)}
  <div class="bg-base-300/40 rounded-xl border border-base-content/10 overflow-hidden">
    <button onclick={() => formatSections[sectionId] = !formatSections[sectionId]} class="flex items-center gap-2 w-full px-3 py-2 text-left hover:bg-base-content/[3%] transition-colors">
      <Icon icon={formatSections[sectionId] ? "mdi:chevron-down" : "mdi:chevron-right"} class="size-3.5 text-base-content/30 shrink-0 transition-transform" />
      <span class="text-[10px] font-mono font-medium text-base-content/50 uppercase tracking-wider">{title}</span>
    </button>
    {#if !formatSections[sectionId]}
      <div class="px-2 pb-2 space-y-0.5">
        {#each regular as item}
          <button onclick={() => insertFormatting(item.syntax)} class="w-full flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-base-content/[3%] transition-colors cursor-pointer text-left">
            <span class="text-[10px] font-mono text-base-content/70 whitespace-nowrap shrink-0">{item.syntax}</span>
            <span class="text-[10px] text-base-content/15 shrink-0">→</span>
            <span class="text-[11px] {item.cls} truncate">{item.text}</span>
          </button>
        {/each}
        {#each expandable as item}
          <div class="rounded-lg overflow-hidden border border-base-content/5">
            <div class="flex items-center">
              <button onclick={() => insertFormatting(item.syntax)} class="flex-1 flex items-center gap-2 px-2 py-1.5 text-left hover:bg-base-content/[3%] transition-colors cursor-pointer">
                <span class="text-[10px] font-mono text-base-content/70 whitespace-nowrap shrink-0">{item.syntax}</span>
                <span class="text-[10px] text-base-content/15 shrink-0">→</span>
                <span class="text-[11px] text-base-content/50 truncate">{item.text}</span>
              </button>
              <button onclick={() => expandedSyntax[item.syntax] = !expandedSyntax[item.syntax]} class="p-2 text-base-content/20 hover:text-base-content/40 transition-colors shrink-0" title="Preview">
                <Icon icon={expandedSyntax[item.syntax] ? "mdi:eye" : "mdi:eye-outline"} class="size-3.5" />
              </button>
            </div>
            {#if expandedSyntax[item.syntax]}
              <div class="px-3 py-3 bg-base-200/40 border-t border-base-content/5 {item.cls === 'text-left' ? 'text-left' : item.cls === 'text-right' ? 'text-right' : 'text-center'}">
                {#if item.previewHtml}
                  <span class="text-base">{@html item.previewHtml}</span>
                {:else}
                  <span class="text-base {item.cls}">{item.text} preview</span>
                {/if}
              </div>
            {/if}
          </div>
        {/each}
      </div>
    {/if}
  </div>
{/snippet}

<!-- ===== MOBILE LAYOUT (< lg) ===== -->
<div class="flex flex-1 lg:hidden min-h-0 p-2 gap-2">
  <div class="flex-1 flex flex-col min-w-0">
    <div class="flex gap-1 mb-2 shrink-0">
      <button onclick={() => rightTab = 'editor'} class="flex-1 text-[11px] font-mono font-medium tracking-wider py-2 rounded-xl transition-all active:scale-[0.97] {rightTab === 'editor' ? 'bg-primary/15 text-primary shadow-sm' : 'text-base-content/50 hover:text-base-content/70 hover:bg-base-content/5'}">Markdown</button>
      <button onclick={() => rightTab = 'reader'} class="flex-1 text-[11px] font-mono font-medium tracking-wider py-2 rounded-xl transition-all active:scale-[0.97] {rightTab === 'reader' ? 'bg-primary/15 text-primary shadow-sm' : 'text-base-content/50 hover:text-base-content/70 hover:bg-base-content/5'}">Reader</button>
    </div>
    {#if rightTab === 'editor'}
      <div class="flex-1 flex flex-col min-h-0 min-w-0">
        <div class="flex items-center gap-2 px-3 py-2 border-b border-base-content/10 bg-base-200/60 backdrop-blur-sm rounded-t-xl shrink-0">
          <span class="text-[10px] font-mono text-base-content/30 font-medium uppercase tracking-wider">markdown</span>
          {#if selected}
            <span class="text-[10px] font-mono text-base-content/20">·</span>
            <span class="text-[10px] font-mono text-base-content/25 truncate">{selected}</span>
          {/if}
        </div>
        <textarea bind:value={input} bind:this={mdScroll} onfocus={(e) => activeTextarea = e.currentTarget} placeholder="select a chapter to start editing..." class="flex-1 font-mono text-sm leading-relaxed p-4 resize-none outline-none rounded-b-xl border-x border-b border-base-content/10 bg-base-300/60 text-base-content/80 placeholder:text-base-content/15 min-h-0 transition-colors focus:bg-base-300/80 focus:border-primary/20"></textarea>
      </div>
    {:else}
      <div class="flex-1 flex flex-col min-h-0 min-w-0">
        <div class="flex items-center gap-2 px-3 py-2 border-b border-base-content/10 bg-base-200/60 backdrop-blur-sm rounded-t-xl shrink-0">
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
<div class="hidden lg:flex flex-1 gap-3 min-h-0 p-3">
  <div class="w-56 flex flex-col bg-base-200/80 backdrop-blur-sm rounded-xl border border-base-content/10 shrink-0 min-h-0 shadow-lg shadow-black/5">
    <div class="flex flex-col border-b border-base-content/10">
      <div class="flex gap-1.5 p-2 pb-1">
        <select bind:value={currentBook}  class="flex-1 bg-base-300/60 text-base-content/70 text-xs px-2.5 py-2 rounded-xl outline-none border border-base-content/10 transition-colors focus:border-primary/30 focus:text-base-content/80 cursor-pointer">
          {#each BOOKS as b}
            <option value={b.slug}>{b.slug}</option>
          {/each}
        </select>
        <select bind:value={translation} onchange={handleTranslationChange} class="flex-1 bg-base-300/60 text-base-content/70 text-xs px-2.5 py-2 rounded-xl outline-none border border-base-content/10 transition-colors focus:border-primary/30 focus:text-base-content/80 cursor-pointer">
          {#each (BOOKS.find(b => b.slug === currentBook)?.translations ?? []) as tl}
            <option value={tl}>{tl}</option>
          {/each}
          {#each customTranslations as t}
            <option value={t}>{t}</option>
          {/each}
        </select>
      </div>
      <div class="flex gap-1.5 px-2 pb-2 pt-0.5">
        <input type="text" bind:value={search} placeholder="search" class="flex-1 bg-base-300/60 text-base-content/70 text-xs px-3 py-2 rounded-xl outline-none border border-base-content/10 min-w-0 placeholder:text-base-content/20 transition-colors focus:border-primary/30 focus:text-base-content/80" />
        <button onclick={refreshChapters} disabled={refreshing} class="text-base-content/40 hover:text-base-content active:scale-95 transition-all p-2 rounded-xl hover:bg-base-content/5 disabled:text-base-content/15 disabled:hover:bg-transparent disabled:active:scale-100 disabled:cursor-not-allowed" title="Refresh chapters">
          <Icon icon={refreshing ? "mdi:loading" : "mdi:refresh"} class="size-3.5 {refreshing ? 'animate-spin' : ''}" />
        </button>
      </div>
    </div>
    <div class="flex-1 overflow-y-auto p-2 min-h-0 space-y-0.5 scrollbar-thin">
      <button onclick={loadSandbox} class="block w-full text-left text-xs px-3 py-2 rounded-xl hover:bg-base-content/5 active:scale-[0.98] transition-all {selected === 'sandbox' ? 'bg-primary/10 text-primary' : 'text-base-content/70'}">blank chapter</button>
      <div class="mx-1 my-1.5 border-t border-base-content/10"></div>
      {#if loading}
        <div class="flex items-center justify-center gap-2 py-6"><Icon icon="mdi:loading" class="size-4 text-base-content/50 animate-spin" /><span class="text-xs text-base-content/50">loading...</span></div>
      {:else if error}
        <p class="text-xs text-error/70 text-center py-6">{error}</p>
      {:else if filtered.length === 0}
        <p class="text-xs text-base-content/40 text-center py-6">none</p>
      {:else}
        {#each filtered as file}
          <button onclick={() => loadChapter(file)} title="{indices.has(file) ? 'ch' + (currentBook === "debut" ? Number(indices.get(file)) + 1 : indices.get(file)) : file}{titles.has(file) ? ' - ' + titles.get(file) : ''}{dirty.has(file) ? ' (modified)' : ''}" class="block w-full text-left text-xs px-3 py-2 rounded-xl active:scale-[0.98] transition-all whitespace-nowrap overflow-hidden text-ellipsis {selected === file ? 'bg-primary/10 text-base-content shadow-sm' : dirty.has(file) ? 'text-success hover:bg-base-content/5' : 'text-base-content/70 hover:bg-base-content/5'}">
            {#if indices.has(file)}<span class="font-medium">ch{currentBook === "debut" ? Number(indices.get(file)) + 1 : indices.get(file)}</span>{:else}<span class="font-medium">{file.replace('.md','')}</span>{/if}
            {#if titles.has(file)}<span class="text-base-content/50 ml-1">— {titles.get(file)}</span>{/if}
            {#if dirty.has(file)}<span class="text-success/60 ml-1">●</span>{/if}
          </button>
        {/each}
      {/if}
    </div>
  </div>
  <div class="flex-1 flex flex-col min-h-0 min-w-0">
    <div class="flex items-center gap-2 px-3 py-2 border-b border-base-content/10 bg-base-200/60 backdrop-blur-sm rounded-t-xl shrink-0">
      <span class="text-[10px] font-mono text-base-content/30 font-medium uppercase tracking-wider">markdown</span>
      {#if selected}
        <span class="text-[10px] font-mono text-base-content/20">·</span>
        <span class="text-[10px] font-mono text-base-content/25 truncate">{selected}</span>
      {/if}
    </div>
    <textarea bind:value={input} bind:this={mdScroll} onfocus={(e) => activeTextarea = e.currentTarget} placeholder="select a chapter to start editing..." class="flex-1 font-mono text-sm leading-relaxed p-4 resize-none outline-none rounded-b-xl border-x border-b border-base-content/10 bg-base-300/60 text-base-content/80 placeholder:text-base-content/15 min-h-0 transition-colors focus:bg-base-300/80 focus:border-primary/20"></textarea>
  </div>
  <div class="flex-1 flex flex-col min-h-0 min-w-0">
    <div class="flex items-center gap-2 px-3 py-2 border-b border-base-content/10 bg-base-200/60 backdrop-blur-sm rounded-t-xl shrink-0">
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
  <div class="w-64 flex flex-col bg-base-200/60 rounded-xl border border-base-content/10 shrink-0 min-h-0 shadow-sm">
    <div class="flex items-center gap-2 px-3 py-2 border-b border-base-content/10 bg-base-200/60 backdrop-blur-sm rounded-t-xl shrink-0">
      <span class="text-[10px] font-mono text-base-content/30 font-medium uppercase tracking-wider">formatting</span>
    </div>
    <div class="flex-1 overflow-y-auto overflow-x-hidden scrollbar-thin p-2 space-y-2">

      {@render section("Colors & Markdown", colorsItems)}
      {@render section("Changing Text", changingItems)}

      <div class="bg-base-300/40 rounded-xl border border-base-content/10 overflow-hidden">
        <button onclick={() => formatSections['windows'] = !formatSections['windows']} class="flex items-center gap-2 w-full px-3 py-2 text-left hover:bg-base-content/[3%] transition-colors">
          <Icon icon={formatSections['windows'] ? "mdi:chevron-down" : "mdi:chevron-right"} class="size-3.5 text-base-content/30 shrink-0 transition-transform" />
          <span class="text-[10px] font-mono font-medium text-base-content/50 uppercase tracking-wider">Windows</span>
        </button>
        {#if !formatSections['windows']}
          <div class="px-2 pb-2 space-y-0.5">
            {#each windowsItems as item}
              <div class="rounded-lg overflow-hidden border border-base-content/5">
                <button onclick={() => expandedSyntax[item.syntax] = !expandedSyntax[item.syntax]} class="flex items-center gap-2 w-full px-2 py-1.5 text-left hover:bg-base-content/[3%] transition-colors">
                  <Icon icon={expandedSyntax[item.syntax] ? "mdi:chevron-down" : "mdi:chevron-right"} class="size-3 text-base-content/20 shrink-0 transition-transform" />
                  <span class="text-[10px] font-mono text-base-content/70 whitespace-nowrap shrink-0">{item.syntax}</span>
                  <span class="text-[10px] text-base-content/15 shrink-0">→</span>
                  <span class="text-[11px] text-base-content/50 truncate">{item.name}</span>
                </button>
                {#if expandedSyntax[item.syntax]}
                  <div class="px-3 py-2 bg-base-200/40 border-t border-base-content/5">
                    {#if item.meta}
                      <p class="text-[8px] font-mono text-base-content/30 mb-2 leading-relaxed">{item.meta}</p>
                    {/if}
                    <div class="flex items-center bg-base-300/60 rounded-lg p-0.5 mb-2">
                      <button onclick={() => windowViewMode[item.syntax] = 'code'} class="flex-1 text-[9px] font-mono py-1 rounded-md transition-all {windowViewMode[item.syntax] !== 'preview' ? 'bg-primary/15 text-primary shadow-sm' : 'text-base-content/40 hover:text-base-content/60'}">markdown</button>
                      <button onclick={() => windowViewMode[item.syntax] = 'preview'} class="flex-1 text-[9px] font-mono py-1 rounded-md transition-all {windowViewMode[item.syntax] === 'preview' ? 'bg-primary/15 text-primary shadow-sm' : 'text-base-content/40 hover:text-base-content/60'}">window</button>
                    </div>
                    {#if windowViewMode[item.syntax] === 'preview'}
                      <div class="reader-container text-[10px] p-2 rounded-lg bg-base-100/80 border border-base-content/5 scale-90 origin-top-left w-[111%]">
                        <div class="{item.cls}">{@html item.html}</div>
                      </div>
                    {:else}
                      <pre class="text-[9px] font-mono text-primary/60 bg-base-300/60 rounded-lg px-2 py-1.5 overflow-x-auto whitespace-pre">{@html item.code.replace(/\\n/g, '\n')}</pre>
                    {/if}
                  </div>
                {/if}
              </div>
            {/each}
          </div>
        {/if}
      </div>

    </div>
  </div>
</div>

<!-- ===== MOBILE MENU ===== -->
{#if showMobileMenu}
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div
    class="fixed inset-0 z-40 lg:hidden"
    onclick={() => showMobileMenu = false}
    onkeydown={(e) => { if (e.key === "Escape") showMobileMenu = false; }}
    role="dialog"
    tabindex="-1"
  >
    <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
    <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" onclick={() => showMobileMenu = false} role="button" tabindex="-1"></div>
    <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
    <div
      class="absolute left-0 top-0 bottom-0 w-72 max-w-[85vw] bg-base-300 border-r border-base-content/10 shadow-2xl shadow-black/30 flex flex-col animate-slide-in-left"
      onclick={(e) => e.stopPropagation()}
      role="dialog"
      tabindex="-1"
    >
      <div class="flex items-center justify-between px-4 py-3 border-b border-base-content/10 shrink-0">
        <span class="text-[11px] font-mono text-base-content/40 font-medium uppercase tracking-wider">Menu</span>
        <button onclick={() => showMobileMenu = false} class="text-base-content/40 hover:text-base-content active:scale-95 transition-all p-2 rounded-xl hover:bg-base-content/5"><Icon icon="mdi:close" class="size-5" /></button>
      </div>
      <div class="flex gap-1 px-3 pt-3 shrink-0">
        <button onclick={() => leftTab = 'chapters'} class="flex-1 text-[11px] font-mono font-medium tracking-wider py-2 rounded-xl transition-all active:scale-[0.97] {leftTab === 'chapters' ? 'bg-primary/15 text-primary shadow-sm' : 'text-base-content/50 hover:text-base-content/70 hover:bg-base-content/5'}">Chapters</button>
        <button onclick={() => leftTab = 'formatting'} class="flex-1 text-[11px] font-mono font-medium tracking-wider py-2 rounded-xl transition-all active:scale-[0.97] {leftTab === 'formatting' ? 'bg-primary/15 text-primary shadow-sm' : 'text-base-content/50 hover:text-base-content/70 hover:bg-base-content/5'}">Formatting</button>
      </div>
      <div class="flex-1 min-h-0 px-3 pb-3 pt-2">
        {#if leftTab === 'chapters'}
          <div class="h-full flex flex-col bg-base-200/80 backdrop-blur-sm rounded-xl border border-base-content/10 shadow-lg">
            <div class="flex flex-col border-b border-base-content/10">
              <div class="flex gap-1.5 p-2 pb-1">
                <select bind:value={currentBook}  class="flex-1 bg-base-300/60 text-base-content/70 text-xs px-2.5 py-2 rounded-xl outline-none border border-base-content/10 transition-colors focus:border-primary/30 focus:text-base-content/80 cursor-pointer">
                  {#each BOOKS as b}
                    <option value={b.slug}>{b.slug}</option>
                  {/each}
                </select>
                <select bind:value={translation} onchange={handleTranslationChange} class="flex-1 bg-base-300/60 text-base-content/70 text-xs px-2.5 py-2 rounded-xl outline-none border border-base-content/10 transition-colors focus:border-primary/30 focus:text-base-content/80 cursor-pointer">
                  {#each (BOOKS.find(b => b.slug === currentBook)?.translations ?? []) as tl}
                    <option value={tl}>{tl}</option>
                  {/each}
                  {#each customTranslations as t}
                    <option value={t}>{t}</option>
                  {/each}
                </select>
              </div>
              <div class="flex gap-1.5 px-2 pb-2 pt-0.5">
                <input type="text" bind:value={search} placeholder="search" class="flex-1 bg-base-300/60 text-base-content/70 text-xs px-3 py-2 rounded-xl outline-none border border-base-content/10 min-w-0 placeholder:text-base-content/20 transition-colors focus:border-primary/30 focus:text-base-content/80" />
                <button onclick={refreshChapters} disabled={refreshing} class="text-base-content/40 hover:text-base-content active:scale-95 transition-all p-2 rounded-xl hover:bg-base-content/5 disabled:text-base-content/15 disabled:hover:bg-transparent disabled:active:scale-100 disabled:cursor-not-allowed" title="Refresh chapters">
                  <Icon icon={refreshing ? "mdi:loading" : "mdi:refresh"} class="size-3.5 {refreshing ? 'animate-spin' : ''}" />
                </button>
              </div>
            </div>
            <div class="flex-1 overflow-y-auto p-2 min-h-0 space-y-0.5 scrollbar-thin">
              <button onclick={() => { loadSandbox(); showMobileMenu = false; }} class="block w-full text-left text-xs px-3 py-2 rounded-xl active:scale-[0.98] transition-all {selected === 'sandbox' ? 'bg-primary/10 text-primary' : 'text-base-content/70 hover:bg-base-content/5'}">blank chapter</button>
              <div class="mx-1 my-1.5 border-t border-base-content/10"></div>
            {#if loading}
              <div class="flex items-center justify-center gap-2 py-6"><Icon icon="mdi:loading" class="size-4 text-base-content/50 animate-spin" /><span class="text-xs text-base-content/50">loading...</span></div>
            {:else if error}
              <p class="text-xs text-error/70 text-center py-6">{error}</p>
            {:else if filtered.length === 0}
              <p class="text-xs text-base-content/40 text-center py-6">none</p>
            {:else}
              {#each filtered as file}
                <button onclick={() => { loadChapter(file); showMobileMenu = false; }} title="{indices.has(file) ? 'ch' + (currentBook === "debut" ? Number(indices.get(file)) + 1 : indices.get(file)) : file}{titles.has(file) ? ' - ' + titles.get(file) : ''}{dirty.has(file) ? ' (modified)' : ''}" class="block w-full text-left text-xs px-3 py-2 rounded-xl active:scale-[0.98] transition-all whitespace-nowrap overflow-hidden text-ellipsis {selected === file ? 'bg-primary/10 text-base-content shadow-sm' : dirty.has(file) ? 'text-success hover:bg-base-content/5' : 'text-base-content/70 hover:bg-base-content/5'}">
                  {#if indices.has(file)}<span class="font-medium">ch{currentBook === "debut" ? Number(indices.get(file)) + 1 : indices.get(file)}</span>{:else}<span class="font-medium">{file.replace('.md','')}</span>{/if}
                  {#if titles.has(file)}<span class="text-base-content/50 ml-1">— {titles.get(file)}</span>{/if}
                  {#if dirty.has(file)}<span class="text-success/60 ml-1">●</span>{/if}
                </button>
              {/each}
            {/if}
          </div>
        </div>
      {:else}
        <div class="h-full min-h-0 flex flex-col bg-base-200/60 rounded-xl border border-base-content/10 overflow-y-auto overflow-x-hidden scrollbar-thin p-2 space-y-2">

          {@render section("Colors & Markdown", colorsItems)}
          {@render section("Changing Text", changingItems)}

          <div class="bg-base-300/40 rounded-xl border border-base-content/10 overflow-hidden">
            <button onclick={() => formatSections['windows'] = !formatSections['windows']} class="flex items-center gap-2 w-full px-3 py-2 text-left hover:bg-base-content/[3%] transition-colors">
              <Icon icon={formatSections['windows'] ? "mdi:chevron-down" : "mdi:chevron-right"} class="size-3.5 text-base-content/30 shrink-0 transition-transform" />
              <span class="text-[10px] font-mono font-medium text-base-content/50 uppercase tracking-wider">Windows</span>
            </button>
            {#if !formatSections['windows']}
              <div class="px-2 pb-2 space-y-0.5">
                {#each windowsItems as item}
                  <div class="rounded-lg overflow-hidden border border-base-content/5">
                    <button onclick={() => expandedSyntax[item.syntax] = !expandedSyntax[item.syntax]} class="flex items-center gap-2 w-full px-2 py-1.5 text-left hover:bg-base-content/[3%] transition-colors">
                      <Icon icon={expandedSyntax[item.syntax] ? "mdi:chevron-down" : "mdi:chevron-right"} class="size-3 text-base-content/20 shrink-0 transition-transform" />
                      <span class="text-[10px] font-mono text-base-content/70 whitespace-nowrap shrink-0">{item.syntax}</span>
                      <span class="text-[10px] text-base-content/15 shrink-0">→</span>
                      <span class="text-[11px] text-base-content/50 truncate">{item.name}</span>
                    </button>
                    {#if expandedSyntax[item.syntax]}
                      <div class="px-3 py-2 bg-base-200/40 border-t border-base-content/5">
                        {#if item.meta}
                          <p class="text-[8px] font-mono text-base-content/30 mb-2 leading-relaxed">{item.meta}</p>
                        {/if}
                        <div class="flex items-center bg-base-300/60 rounded-lg p-0.5 mb-2">
                          <button onclick={() => windowViewMode[item.syntax] = 'code'} class="flex-1 text-[9px] font-mono py-1 rounded-md transition-all {windowViewMode[item.syntax] !== 'preview' ? 'bg-primary/15 text-primary shadow-sm' : 'text-base-content/40 hover:text-base-content/60'}">markdown</button>
                          <button onclick={() => windowViewMode[item.syntax] = 'preview'} class="flex-1 text-[9px] font-mono py-1 rounded-md transition-all {windowViewMode[item.syntax] === 'preview' ? 'bg-primary/15 text-primary shadow-sm' : 'text-base-content/40 hover:text-base-content/60'}">window</button>
                        </div>
                        {#if windowViewMode[item.syntax] === 'preview'}
                          <div class="reader-container text-[10px] p-2 rounded-lg bg-base-100/80 border border-base-content/5 scale-90 origin-top-left w-[111%]">
                            <div class="{item.cls}">{@html item.html}</div>
                          </div>
                        {:else}
                          <pre class="text-[9px] font-mono text-primary/60 bg-base-300/60 rounded-lg px-2 py-1.5 overflow-x-auto whitespace-pre">{@html item.code.replace(/\\n/g, '\n')}</pre>
                        {/if}
                      </div>
                    {/if}
                  </div>
                {/each}
              </div>
            {/if}
          </div>
        </div>
      {/if}
      </div>
    </div>
  </div>
{/if}

<!-- ===== MANAGE TRANSLATIONS MODAL ===== -->
{#if showManageTL}
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div
    class="fixed inset-0 z-50 flex items-start justify-center pt-24 bg-black/60 backdrop-blur-sm animate-in fade-in duration-150"
    onclick={() => showManageTL = false}
    onkeydown={(e) => { if (e.key === "Escape") showManageTL = false; }}
    role="dialog"
    tabindex="-1"
  >
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
    <div
      class="bg-base-200/95 backdrop-blur-xl border border-base-content/10 rounded-2xl p-5 w-96 shadow-2xl shadow-black/30 max-h-[65vh] flex flex-col"
      onclick={(e) => e.stopPropagation()}
      role="group"
      tabindex="-1"
    >
      <h2 class="text-sm font-bold text-base-content/70 font-mono mb-4 tracking-wide">Manage Translations</h2>
      <div class="flex gap-2 mb-4">
        <input
          bind:value={newTranslationName}
          onkeydown={(e) => { if (e.key === "Enter") confirmNewTranslation(); }}
          placeholder="new translation name"
          class="flex-1 bg-base-300/60 text-base-content/70 text-xs px-3 py-2.5 rounded-xl outline-none border border-base-content/10 transition-colors focus:border-primary/30 placeholder:text-base-content/20"
        />
        <button onclick={confirmNewTranslation} disabled={!newTranslationName.trim()} class="btn btn-soft btn-xs btn-primary rounded-xl px-3">Add</button>
      </div>
      <div class="flex-1 overflow-y-auto space-y-0.5 scrollbar-thin">
        {#each customTranslations as tl}
          <div class="flex items-center gap-2 group px-2 py-1.5 rounded-xl hover:bg-base-content/5 transition-colors">
            {#if renameTL === tl}
              <!-- svelte-ignore a11y_autofocus -->
              <input
                bind:value={renameTLValue}
                onkeydown={(e) => { if (e.key === "Enter") confirmRename(); if (e.key === "Escape") renameTL = null; }}
                class="flex-1 bg-base-300/60 text-base-content/70 text-xs px-3 py-2 rounded-xl outline-none border border-primary/40 autofocus"
                autofocus
              />
              <button onclick={confirmRename} class="text-success/60 hover:text-success active:scale-95 transition-all p-1.5 rounded-lg" title="Save"><Icon icon="mdi:check" class="size-4" /></button>
              <button onclick={() => renameTL = null} class="text-base-content/30 hover:text-base-content/60 active:scale-95 transition-all p-1.5 rounded-lg" title="Cancel"><Icon icon="mdi:close" class="size-4" /></button>
            {:else}
              <span class="flex-1 text-xs text-base-content/60 font-mono truncate">{tl}</span>
              <button onclick={() => startRename(tl)} class="text-base-content/20 hover:text-base-content/60 active:scale-95 transition-all p-1.5 rounded-lg opacity-0 group-hover:opacity-100" title="Rename"><Icon icon="mdi:pencil-outline" class="size-3.5" /></button>
              <button onclick={() => deleteTL(tl)} class="text-error/30 hover:text-error active:scale-95 transition-all p-1.5 rounded-lg opacity-0 group-hover:opacity-100" title="Delete"><Icon icon="mdi:delete-outline" class="size-3.5" /></button>
            {/if}
          </div>
        {/each}
      </div>
    </div>
  </div>
{/if}

<!-- ===== FOOTER ===== -->
<div class="flex items-center justify-between px-4 py-2 border-t border-base-content/10 bg-base-200/40 backdrop-blur-sm shrink-0">
  <span class="text-[10px] font-mono text-base-content/30">{currentBook} / {translation}{#if !isSourceTranslation} <span class="text-warning/50">(custom)</span>{/if}</span>
  <div class="flex items-center gap-3">
    {#if selected === "sandbox"}
      <span class="text-[10px] font-mono text-base-content/30">blank chapter</span>
    {:else if selected}
      {#if isSourceTranslation}
        <a
          href="https://github.com/{REPO}/edit/{BRANCH}/chapters/{currentBook}/{tlDir(currentBook, translation)}/{selected}"
          target="_blank"
          class="text-[10px] font-mono text-base-content/35 hover:text-primary active:scale-[0.97] transition-all"
        >↗ {selected}</a>
      {:else}
        <span class="text-[10px] font-mono text-warning/50">{selected}</span>
      {/if}
    {:else}
      <span class="text-[10px] font-mono text-base-content/25">no file</span>
    {/if}
  </div>
</div>
</div>

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
</style>
