<script lang="ts">
  import { browser } from "$app/environment";
  import { page } from "$app/state";
  import Icon from "@iconify/svelte";
  import bookMeta from "$lib/meta.json";
  import { fade } from "svelte/transition";
  import "$lib/reader/reader-windows.css";
  import readerCss from "../../../../routes/(reader)/reader.css?url";
  import ChaptersEditor from "./ChaptersEditor.svelte";
  import CharactersEditor from "./CharactersEditor.svelte";
  import UderEditor from "./UderEditor.svelte";
  import { REPO, BRANCH } from "./lib/github-api";
  import { NODE_ICONS, NODE_COLORS, NODE_LABELS, type NodeType } from "./lib/nodes";

  type EditorMode = "chapters" | "characters" | "uder";

  function loadCachedTheme(): string {
    if (!browser) return "sunset";
    try {
      const saved = localStorage.getItem("readerSettings");
      if (saved) {
        const parsed = JSON.parse(saved);
        if (parsed.theme) return parsed.theme;
      }
    } catch {}
    return "sunset";
  }

  let theme = $state(loadCachedTheme());
  let showThemeMenu = $state(false);
  let themeBtn: HTMLButtonElement;
  const THEMES = ["sunset", "light", "dark", "retro", "night", "business", "black", "dracula", "cyberpunk"];

  $effect(() => {
    if (browser) {
      const settings = JSON.parse(localStorage.getItem("readerSettings") || "{}");
      settings.theme = theme;
      localStorage.setItem("readerSettings", JSON.stringify(settings));
      document.documentElement.setAttribute("data-theme", theme);
    }
  });

  function initialEditorMode(): EditorMode {
    const m = page.url.searchParams.get("mode");
    if (m === "chapters" || m === "characters" || m === "uder") return m;
    return (typeof localStorage !== 'undefined' ? localStorage.getItem('gsgw-editor-mode') : null) as EditorMode ?? "chapters";
  }

  let editorMode = $state<EditorMode>(initialEditorMode());

  const EDITOR_MODE_LABELS: Record<EditorMode, string> = {
    chapters: "Chapters",
    characters: "Characters",
    uder: "U-DER",
  };
  let showModeMenu = $state(false);
  let showEditExisting = $state(false);
  let showPublish = $state(false);

  const uderRecordsList = ((bookMeta as any)?.uder?.records ?? []) as {
    slug: string;
    title: string;
    typeLabel: string;
    faction: string | null;
    thumb: string | null;
  }[];

  let recordSearch = $state("");
  const filteredUderRecords = $derived(
    uderRecordsList.filter((r) => r.title.toLowerCase().includes(recordSearch.trim().toLowerCase())),
  );

  function importExistingRecord(slug: string) {
    showEditExisting = false;
    uderRef?.importFromServer(slug);
  }
  let showMobileMenu = $state(false);
  let showInfo = $state(false);
  let showNodeInfo = $state(false);
  let expandedVersion = $state<string | null>(null);

  $effect(() => {
    localStorage.setItem('gsgw-editor-mode', editorMode);
  });

  let patchNotes = [
    { version: "v0.7", description: "- add import/export for U-DER records (.uder files)" },
    { version: "v0.6", description: "- cleaned up the editor code and reworked the formatting window" },
    { version: "v0.5", description: "- added character editor" },
    { version: "v0.4", description: "- bug fixing\n- themes\n- changed mobile editing ui to fit the smaller screen" },
    { version: "v0.3", description: "- better ui (hopefully)\n- mobile editing\n- custom translations\n- adding/removing chapters" },
    { version: "v0.2", description: `- added caching chapter changes and scrolling positions\n- reverting to source\n- exporting single or bulk chapters` },
    { version: "v0.1", description: "initial release of the editor to see a live preview of how your changes would look in the reader" }
  ];

  const NODE_DOCS = [
    { type: "start" as const, desc: "Start nodes begin interactive stories. Multiple starting nodes can be placed on the canvas for multiple stories." },
    { type: "story" as const, desc: "Story nodes are text nodes meant to keep the flow going as things progress." },
    { type: "choice" as const, desc: "Choice nodes branch out the story, allowing different outcomes based on the reader's decisions." },
    { type: "addition" as const, desc: `Addition nodes reference a <span class="inline-ref inline-resource">resource</span> and can add, subtract, or set it to a specific value.` },
    { type: "condition" as const, desc: `Condition nodes are checks. If the check passes, they proceed via the <span class="inline-port pass-port"><svg width="10" height="10" viewBox="0 0 10 10"><polygon points="5,0 10,5 5,10" fill="currentColor"/></svg></span> pass port. If it fails, they fail via the <span class="inline-port fail-port"><svg width="10" height="10" viewBox="0 0 10 10"><polygon points="0,0 10,0 5,10" fill="currentColor"/></svg></span> fail port and branch out in another direction.` },
    { type: "chance" as const, desc: `Chance nodes are percentage-based pass or fails. You can set the specific pass chance. They work like <span class="inline-ref inline-condition">condition</span> nodes.` },
    { type: "ending" as const, desc: "Ending nodes conclude stories." },
    { type: "resource" as const, desc: `Resources can be anything \u2014 health, coins, contamination, whatever value you want to keep track of. They can be named, given a value, and referenced by <span class="inline-ref inline-condition">condition</span>, <span class="inline-ref inline-addition">addition</span>, and <span class="inline-ref inline-loop-check">loop check</span> nodes.` },
    { type: "loop_start" as const, desc: `Loop start nodes mark the beginning of a loop body. Paired with a <span class="inline-ref inline-loop-check">loop check</span> node, any nodes between them will repeat.` },
    { type: "loop_check" as const, desc: `Loop checks are like <span class="inline-ref inline-condition">condition</span> nodes for loops. Once the exit condition is met, the loop stops. They also track how many loops have run and can end a loop based on that count.` },
  ];

  $effect(() => {
    if (editorMode === "uder" && uderRef) {
      const rec = page.url.searchParams.get("record");
      if (rec && rec !== lastLoadedRecord) {
        lastLoadedRecord = rec;
        uderRef.importFromServer(rec);
      }
    }
  });

  function toggleVersion(v: string) {
    expandedVersion = expandedVersion === v ? null : v;
  }

  let currentBook = $state("gsgw");

  // Chapters toolbar state
  let showExport = $state(false);
  let showRevert = $state(false);
  let exportBtn: HTMLElement | null = $state(null);
  let revertBtn: HTMLElement | null = $state(null);
  let importRef: HTMLInputElement | undefined = $state();

  function toggleExport() {
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

  function toggleRevert() {
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

  // Chapters-bound state (for toolbar disabled states)
  let selected = $state<string | null>(null);
  let translation = $state("fantl");
  let isSourceTranslation = $state(true);
  let chapterDirty = $state<Set<string>>(new Set());
  let chapterInput = $state("");

  // Characters-bound state (for toolbar disabled states)
  let charExplorerPath = $state<string[]>([]);
  let hasSelectedChar = $state(false);
  let hasCharacters = $state(false);
  let cachedCharImages = $state<Set<string>>(new Set());
  let charFolderHasLocalEdits = $state(false);

  let showCharExport = $state(false);
  let charExportBtn: HTMLElement | null = $state(null);
  let charImportRef: HTMLInputElement | undefined = $state();
  let charImageImportRef: HTMLInputElement | undefined = $state();
  let showNewCharDialog = $state(false);
  let newCharName = $state("");

  function toggleCharExport() {
    showCharExport = !showCharExport;
    if (showCharExport) {
      const handler = (ev: MouseEvent) => {
        if (!charExportBtn?.contains(ev.target as Node) && !(ev.target as HTMLElement)?.closest?.('[data-char-export-dropdown]')) {
          showCharExport = false;
          document.removeEventListener("click", handler);
        }
      };
      requestAnimationFrame(() => document.addEventListener("click", handler));
    }
  }

  let lastLoadedRecord = $state<string | null>(null);

  let chaptersRef: ChaptersEditor = $state()!;
  let charsRef: CharactersEditor = $state()!;
  let uderRef: UderEditor = $state()!;
  let uderImportRef: HTMLInputElement | undefined = $state();
  let showUderExport = $state(false);
  let uderExportBtn: HTMLElement | null = $state(null);
  let showUderDelete = $state(false);
  let uderDeleteBtn: HTMLElement | null = $state(null);

  function toggleUderExport() {
    showUderExport = !showUderExport;
    showUderDelete = false;
    if (showUderExport) {
      const handler = (ev: MouseEvent) => {
        if (!uderExportBtn?.contains(ev.target as Node) && !(ev.target as HTMLElement)?.closest?.('[data-uder-export-dropdown]')) {
          showUderExport = false;
          document.removeEventListener("click", handler);
        }
      };
      setTimeout(() => document.addEventListener("click", handler));
    }
  }

  function toggleUderDelete() {
    showUderDelete = !showUderDelete;
    showUderExport = false;
    if (showUderDelete) {
      const handler = (ev: MouseEvent) => {
        if (!uderDeleteBtn?.contains(ev.target as Node) && !(ev.target as HTMLElement)?.closest?.('[data-uder-delete-dropdown]')) {
          showUderDelete = false;
          document.removeEventListener("click", handler);
        }
      };
      setTimeout(() => document.addEventListener("click", handler));
    }
  }
</script>

<svelte:head>
  <link rel="stylesheet" href={readerCss}>
</svelte:head>

<div class="h-dvh bg-base-300 flex flex-col overflow-hidden selection:bg-primary/30">
  <div class="flex items-center justify-between px-2 sm:px-3 py-2 border-b border-base-content/10 bg-base-200/60 backdrop-blur-md shrink-0 relative z-10">
    <div class="flex items-center gap-1 sm:gap-0.5 overflow-x-auto overflow-y-hidden min-w-0 scrollbar-thin">
      {#if editorMode === "chapters"}
        <button onclick={() => showMobileMenu = true} class="lg:hidden text-base-content/40 hover:text-base-content active:scale-95 transition-all p-2 rounded-lg hover:bg-base-content/5" title="Menu"><Icon icon="mdi:menu" class="size-5" /></button>
        <a href="/" class="text-base-content/40 hover:text-base-content active:scale-95 transition-all p-2 rounded-lg hover:bg-base-content/5" title="Home"><Icon icon="mdi:home-outline" class="size-5" /></a>
        <span class="mx-0.5 w-px h-5 bg-base-content/10"></span>
        <button bind:this={exportBtn} onclick={toggleExport} class="text-base-content/40 hover:text-base-content active:scale-95 transition-all p-2 rounded-lg hover:bg-base-content/5" title="Export"><Icon icon="mdi:export-variant" class="size-4 sm:size-5" /></button>
        <button onclick={() => importRef?.click()} class="text-base-content/40 hover:text-base-content active:scale-95 transition-all p-2 rounded-lg hover:bg-base-content/5" title="Import zip"><Icon icon="mdi:file-import-outline" class="size-4 sm:size-5" /></button>
        <input bind:this={importRef} onchange={(e) => chaptersRef?.handleImportZip(e)} type="file" accept=".zip" class="hidden" />
        <button bind:this={revertBtn} onclick={toggleRevert} class="text-base-content/40 hover:text-base-content active:scale-95 transition-all p-2 rounded-lg hover:bg-base-content/5" title="Revert"><Icon icon="mdi:undo-variant" class="size-4 sm:size-5" /></button>
        <span class="mx-0.5 w-px h-5 bg-base-content/10"></span>
        <button onclick={() => chaptersRef?.newChapter()} disabled={!translation} class="text-base-content/40 hover:text-base-content active:scale-95 transition-all p-2 rounded-lg hover:bg-base-content/5 disabled:text-base-content/15 disabled:hover:bg-transparent disabled:active:scale-100 disabled:cursor-not-allowed" title="New chapter"><Icon icon="mdi:plus" class="size-4 sm:size-5" /></button>
        <button onclick={() => chaptersRef?.deleteCurrentChapter()} disabled={!selected || selected === "sandbox" || isSourceTranslation} class="text-base-content/40 hover:text-base-content active:scale-95 transition-all p-2 rounded-lg hover:bg-base-content/5 disabled:text-base-content/15 disabled:hover:bg-transparent disabled:active:scale-100 disabled:cursor-not-allowed" title="Delete chapter"><Icon icon="mdi:delete-outline" class="size-4 sm:size-5" /></button>
        <span class="mx-0.5 w-px h-5 bg-base-content/10"></span>
        <button onclick={() => chaptersRef?.openManageTL()} class="text-base-content/40 hover:text-base-content active:scale-95 transition-all p-2 rounded-lg hover:bg-base-content/5" title="Manage translations"><Icon icon="mdi:translate" class="size-4 sm:size-5" /></button>
        {#if showExport}
          <div data-export-dropdown class="absolute top-full left-0 mt-2 bg-base-200/95 backdrop-blur-xl border border-base-content/10 rounded-xl shadow-2xl shadow-black/20 py-1.5 min-w-52 z-50 overflow-hidden">
            <button onclick={() => { chaptersRef?.exportCurrentChapter(); showExport = false; }} disabled={!selected || selected === "sandbox" || !chapterInput} class="flex items-center gap-2 w-full text-left text-xs px-4 py-2.5 hover:bg-primary/10 text-base-content/70 disabled:text-base-content/20 disabled:cursor-not-allowed transition-colors">Export current chapter</button>
            <button onclick={() => { chaptersRef?.exportAllEdited(); showExport = false; }} disabled={chapterDirty.size === 0 && isSourceTranslation} class="flex items-center gap-2 w-full text-left text-xs px-4 py-2.5 hover:bg-primary/10 text-base-content/70 disabled:text-base-content/20 disabled:cursor-not-allowed transition-colors">Export all chapters</button>
          </div>
        {/if}
        {#if showRevert}
          <div data-revert-dropdown class="absolute top-full left-0 mt-2 bg-base-200/95 backdrop-blur-xl border border-base-content/10 rounded-xl shadow-2xl shadow-black/20 py-1.5 min-w-52 z-50 overflow-hidden">
            <button onclick={() => { chaptersRef?.revertCurrentChapter(); showRevert = false; }} disabled={!selected || selected === "sandbox" || !chapterDirty.has(selected || "")} class="flex items-center gap-2 w-full text-left text-xs px-4 py-2.5 hover:bg-primary/10 text-base-content/70 disabled:text-base-content/20 disabled:cursor-not-allowed transition-colors">Revert current chapter</button>
            <button onclick={() => { chaptersRef?.revertAllChapters(); showRevert = false; }} disabled={chapterDirty.size === 0} class="flex items-center gap-2 w-full text-left text-xs px-4 py-2.5 hover:bg-primary/10 text-base-content/70 disabled:text-base-content/20 disabled:cursor-not-allowed transition-colors">Revert all edited chapters</button>
          </div>
        {/if}
      {:else if editorMode === "uder"}
        <a href="/" class="text-base-content/40 hover:text-base-content active:scale-95 transition-all p-2 rounded-lg hover:bg-base-content/5" title="Home"><Icon icon="mdi:home-outline" class="size-5" /></a>
        <span class="mx-0.5 w-px h-5 bg-base-content/10"></span>
        <button bind:this={uderExportBtn} onclick={toggleUderExport} class="text-base-content/40 hover:text-base-content active:scale-95 transition-all p-2 rounded-lg hover:bg-base-content/5 disabled:text-base-content/15 disabled:hover:bg-transparent disabled:active:scale-100 disabled:cursor-not-allowed" title="Export"><Icon icon="mdi:export-variant" class="size-4 sm:size-5" /></button>
        {#if showUderExport}
          <div data-uder-export-dropdown class="absolute top-full left-0 mt-2 bg-base-200/95 backdrop-blur-xl border border-base-content/10 rounded-xl shadow-2xl shadow-black/20 py-1.5 min-w-52 z-50 overflow-hidden">
            <button onclick={() => { uderRef?.handleExport(); showUderExport = false; }} class="flex items-center gap-2 w-full text-left text-xs px-4 py-2.5 hover:bg-primary/10 text-base-content/70 transition-colors">Export record</button>
            <button onclick={() => { uderRef?.handleExportInteractive(); showUderExport = false; }} class="flex items-center gap-2 w-full text-left text-xs px-4 py-2.5 hover:bg-primary/10 text-base-content/70 transition-colors">Export interactive</button>
            <button onclick={() => { uderRef?.handleExportBoth(); showUderExport = false; }} class="flex items-center gap-2 w-full text-left text-xs px-4 py-2.5 hover:bg-primary/10 text-base-content/70 transition-colors">Export both</button>
          </div>
        {/if}
        <button onclick={() => uderImportRef?.click()} class="text-base-content/40 hover:text-base-content active:scale-95 transition-all p-2 rounded-lg hover:bg-base-content/5" title="Import .uder"><Icon icon="mdi:file-import-outline" class="size-4 sm:size-5" /></button>
        <input bind:this={uderImportRef} onchange={(e) => uderRef?.handleImport(e)} type="file" accept=".uder,.zip,.json" class="hidden" />
        <button bind:this={uderDeleteBtn} onclick={toggleUderDelete} class="text-base-content/40 hover:text-base-content active:scale-95 transition-all p-2 rounded-lg hover:bg-base-content/5" title="Delete cached data"><Icon icon="mdi:delete-outline" class="size-4 sm:size-5" /></button>
        {#if showUderDelete}
          <div data-uder-delete-dropdown class="absolute top-full left-0 mt-2 bg-base-200/95 backdrop-blur-xl border border-base-content/10 rounded-xl shadow-2xl shadow-black/20 py-1.5 min-w-52 z-50 overflow-hidden">
            <button onclick={() => { uderRef?.handleDeleteRecordCache(); showUderDelete = false; }} class="flex items-center gap-2 w-full text-left text-xs px-4 py-2.5 hover:bg-primary/10 text-base-content/70 transition-colors">Delete record</button>
            <button onclick={() => { uderRef?.handleDeleteInteractiveCache(); showUderDelete = false; }} class="flex items-center gap-2 w-full text-left text-xs px-4 py-2.5 hover:bg-primary/10 text-base-content/70 transition-colors">Delete interactive</button>
            <button onclick={() => { uderRef?.handleDeleteBothCache(); showUderDelete = false; }} class="flex items-center gap-2 w-full text-left text-xs px-4 py-2.5 hover:bg-primary/10 text-base-content/70 transition-colors">Delete both</button>
          </div>
        {/if}
      {:else}
        <button onclick={() => showMobileMenu = true} class="lg:hidden text-base-content/40 hover:text-base-content active:scale-95 transition-all p-2 rounded-lg hover:bg-base-content/5" title="Menu"><Icon icon="mdi:menu" class="size-5" /></button>
        <a href="/" class="text-base-content/40 hover:text-base-content active:scale-95 transition-all p-2 rounded-lg hover:bg-base-content/5" title="Home"><Icon icon="mdi:home-outline" class="size-5" /></a>
        <span class="mx-0.5 w-px h-5 bg-base-content/10"></span>
        <div class="relative">
          <button bind:this={charExportBtn} onclick={toggleCharExport} disabled={!hasSelectedChar && !hasCharacters} class="text-base-content/40 hover:text-base-content active:scale-95 transition-all p-2 rounded-lg hover:bg-base-content/5 disabled:text-base-content/15 disabled:hover:bg-transparent disabled:active:scale-100 disabled:cursor-not-allowed" title="Export">
            <Icon icon="mdi:export-variant" class="size-4 sm:size-5" />
          </button>
          {#if showCharExport}
            <div data-char-export-dropdown class="absolute top-full left-0 mt-2 bg-base-200/95 backdrop-blur-xl border border-base-content/10 rounded-xl shadow-2xl shadow-black/20 py-1.5 min-w-52 z-50 overflow-hidden">
              <button onclick={() => { charsRef?.exportCurrentCharacterZip(); showCharExport = false; }} disabled={!hasSelectedChar} class="flex items-center gap-2 w-full text-left text-xs px-4 py-2.5 hover:bg-primary/10 text-base-content/70 disabled:text-base-content/20 disabled:cursor-not-allowed transition-colors">Export current character</button>
              <button onclick={() => { charsRef?.exportAllChars(); showCharExport = false; }} class="flex items-center gap-2 w-full text-left text-xs px-4 py-2.5 hover:bg-primary/10 text-base-content/70 disabled:text-base-content/20 disabled:cursor-not-allowed transition-colors">Export all characters</button>
            </div>
          {/if}
        </div>
        <button onclick={() => charImportRef?.click()} class="text-base-content/40 hover:text-base-content active:scale-95 transition-all p-2 rounded-lg hover:bg-base-content/5" title="Import character (zip)">
          <Icon icon="mdi:file-import-outline" class="size-4 sm:size-5" />
        </button>
        <input bind:this={charImportRef} onchange={(e) => charsRef?.importCharacterZip(e)} type="file" accept=".zip" class="hidden" />
        <button onclick={() => charsRef?.importNewImage()} disabled={charExplorerPath.length === 0} class="text-base-content/40 hover:text-base-content active:scale-95 transition-all p-2 rounded-lg hover:bg-base-content/5 disabled:text-base-content/15 disabled:hover:bg-transparent disabled:active:scale-100 disabled:cursor-not-allowed" title="Import image (webp)">
          <Icon icon="mdi:image-plus-outline" class="size-4 sm:size-5" />
        </button>
        <input bind:this={charImageImportRef} onchange={(e) => charsRef?.handleCharImageImport(e)} type="file" accept=".webp" class="hidden" />
        <span class="mx-0.5 w-px h-5 bg-base-content/10"></span>
        <div class="relative">
          <button onclick={() => showNewCharDialog = true} class="text-base-content/40 hover:text-base-content active:scale-95 transition-all p-2 rounded-lg hover:bg-base-content/5" title="New character"><Icon icon="mdi:plus" class="size-4 sm:size-5" /></button>
          {#if showNewCharDialog}
            <div class="absolute top-full left-0 mt-2 bg-base-200/95 backdrop-blur-xl border border-base-content/10 rounded-xl shadow-2xl shadow-black/20 p-4 min-w-64 z-50 overflow-hidden space-y-3">
              <span class="text-[10px] font-mono text-base-content/40 font-medium uppercase tracking-wider">new character</span>
              <input bind:value={newCharName} onkeydown={(e) => { if (e.key === "Enter") { charsRef?.addNewCharacter(newCharName); showNewCharDialog = false; newCharName = ""; } }} placeholder="Character name" class="w-full bg-base-300/60 text-base-content/70 text-xs px-3 py-2 rounded-xl outline-none border border-base-content/10 placeholder:text-base-content/20 focus:border-primary/40 transition-colors" />
              <div class="flex gap-2">
                <button onclick={() => { charsRef?.addNewCharacter(newCharName); showNewCharDialog = false; newCharName = ""; }} disabled={!newCharName.trim()} class="text-[10px] px-3 py-1.5 rounded-xl bg-primary/20 text-primary hover:bg-primary/30 transition-colors disabled:opacity-40 font-medium">Add</button>
                <button onclick={() => { showNewCharDialog = false; newCharName = ""; }} class="text-[10px] px-3 py-1.5 rounded-xl text-base-content/40 hover:text-base-content/60 hover:bg-base-content/5 transition-colors">Cancel</button>
              </div>
            </div>
          {/if}
        </div>
        <button onclick={() => charsRef?.revertAll()} disabled={!charFolderHasLocalEdits && cachedCharImages.size === 0} class="text-base-content/40 hover:text-base-content active:scale-95 transition-all p-2 rounded-lg hover:bg-base-content/5 disabled:text-base-content/15 disabled:hover:bg-transparent disabled:active:scale-100 disabled:cursor-not-allowed" title="Revert all local changes">
          <Icon icon="mdi:undo-variant" class="size-4 sm:size-5" />
        </button>
        <button onclick={() => charsRef?.deleteCharacter()} disabled={!hasSelectedChar} class="text-base-content/40 hover:text-base-content active:scale-95 transition-all p-2 rounded-lg hover:bg-base-content/5 disabled:text-base-content/15 disabled:hover:bg-transparent disabled:active:scale-100 disabled:cursor-not-allowed" title="Delete character">
          <Icon icon="mdi:delete-outline" class="size-4 sm:size-5" />
        </button>
      {/if}
    </div>
    {#if editorMode === "uder"}
      <div class="flex items-center gap-1.5">
        <button onclick={() => showEditExisting = true} class="flex items-center gap-1.5 text-[10px] font-mono font-medium px-3 py-1.5 rounded-lg border border-base-content/15 text-base-content/50 hover:text-base-content hover:border-base-content/30 hover:bg-base-content/5 transition-all active:scale-95">
          <Icon icon="mdi:folder-open-outline" class="size-3.5" />
          Edit Existing
        </button>
        <button onclick={() => showNodeInfo = true} class="flex items-center gap-1.5 text-[10px] font-mono font-medium px-3 py-1.5 rounded-lg border border-base-content/15 text-base-content/50 hover:text-base-content hover:border-base-content/30 hover:bg-base-content/5 transition-all active:scale-95">
          <Icon icon="mdi:information-outline" class="size-3.5" />
          Node Reference
        </button>
        <button onclick={() => showPublish = true} class="flex items-center gap-1.5 text-[10px] font-mono font-medium px-3 py-1.5 rounded-lg border border-primary/25 text-primary/60 hover:text-primary hover:border-primary/50 hover:bg-primary/5 transition-all active:scale-95">
          <Icon icon="mdi:rocket-launch-outline" class="size-3.5" />
          Publish
        </button>
      </div>
    {/if}
    <div class="flex items-center gap-1.5 sm:gap-2">
      <div class="relative hidden lg:block">
        <button onclick={() => showModeMenu = !showModeMenu} class="text-xs font-mono font-medium px-3 py-1.5 rounded-lg border border-base-content/15 text-base-content/60 hover:text-base-content hover:border-base-content/30 hover:bg-base-content/5 transition-all whitespace-nowrap active:scale-95">
          <span class="capitalize">{EDITOR_MODE_LABELS[editorMode]}</span>
          <Icon icon="mdi:chevron-down" class="size-3.5 inline-block ml-0.5" />
        </button>
        {#if showModeMenu}
          <div class="absolute top-full right-0 mt-2 bg-base-200/95 backdrop-blur-xl border border-base-content/10 rounded-xl shadow-2xl shadow-black/20 py-1.5 min-w-40 z-50 overflow-hidden">
            <button onclick={() => { editorMode = "chapters"; showModeMenu = false; }} class="flex items-center gap-2 w-full text-left text-xs px-4 py-2.5 hover:bg-primary/10 text-base-content/70 transition-colors {editorMode === 'chapters' ? 'bg-primary/10 text-primary font-medium' : ''}">Chapters</button>
            <button onclick={() => { editorMode = "characters"; showModeMenu = false; }} class="flex items-center gap-2 w-full text-left text-xs px-4 py-2.5 hover:bg-primary/10 text-base-content/70 transition-colors {editorMode === 'characters' ? 'bg-primary/10 text-primary font-medium' : ''}">Characters</button>
            <button onclick={() => { editorMode = "uder"; showModeMenu = false; }} class="flex items-center gap-2 w-full text-left text-xs px-4 py-2.5 hover:bg-primary/10 text-base-content/70 transition-colors {editorMode === 'uder' ? 'bg-primary/10 text-primary font-medium' : ''}">U-DER</button>
          </div>
        {/if}
      </div>
      <div class="relative">
        <button bind:this={themeBtn} onclick={() => showThemeMenu = !showThemeMenu} class="text-base-content/40 hover:text-base-content active:scale-95 transition-all p-2 rounded-lg hover:bg-base-content/5" title="Theme">
          <Icon icon="mdi:palette-outline" class="size-4 sm:size-5" />
        </button>
        {#if showThemeMenu}
          <div class="absolute top-full right-0 mt-2 bg-base-200/95 backdrop-blur-xl border border-base-content/10 rounded-xl shadow-2xl shadow-black/20 py-1.5 min-w-40 z-50 overflow-hidden">
            {#each THEMES as t}
              <button onclick={() => { theme = t; showThemeMenu = false; }} class="flex items-center gap-2 w-full text-left text-xs px-4 py-2.5 hover:bg-primary/10 text-base-content/70 transition-colors {theme === t ? 'bg-primary/10 text-primary font-medium' : ''}">{t.charAt(0).toUpperCase() + t.slice(1)}</button>
            {/each}
          </div>
        {/if}
      </div>
      <button onclick={() => showInfo = true} class="version-btn text-[10px] sm:text-xs font-mono px-2 py-1 rounded-md bg-base-content/5">v0.7</button>
    </div>
  </div>

  <div class="flex-1 flex flex-col min-h-0">
    {#key editorMode}
      <div transition:fade={{ duration: 200 }} class="flex-1 flex flex-col min-h-0">
        {#if editorMode === "chapters"}
          <ChaptersEditor
            bind:this={chaptersRef}
            bind:showMobileMenu
            bind:currentBook
            bind:selected
            bind:translation
            bind:isSourceTranslation
            bind:dirty={chapterDirty}
            bind:input={chapterInput}
          />
        {:else if editorMode === "characters"}
          <CharactersEditor
            bind:this={charsRef}
            bind:showMobileMenu
            bind:currentBook
            bind:charExplorerPath
            bind:cachedCharImages
            bind:charFolderHasLocalEdits
            bind:hasSelectedChar
            bind:hasCharacters
          />
        {:else if editorMode === "uder"}
          <UderEditor bind:this={uderRef} />
        {/if}
      </div>
    {/key}
  </div>
</div>

{#if showEditExisting}
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm animate-in fade-in duration-150"
    onclick={() => showEditExisting = false}
    onkeydown={(e) => { if (e.key === "Escape") showEditExisting = false; }}
    role="dialog"
    tabindex="-1"
  >
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
    <div
      class="bg-base-100 rounded-2xl shadow-2xl max-w-3xl w-full mx-4 max-h-[85vh] flex flex-col overflow-hidden"
      onclick={(e) => e.stopPropagation()}
      role="group"
      tabindex="-1"
    >
      <div class="relative">
        <div class="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-secondary/5"></div>
        <div class="relative flex items-center justify-between px-6 py-4 border-b border-base-content/10">
          <span class="font-bold text-lg text-primary flex items-center gap-2">
            <Icon icon="mdi:folder-open-outline" class="size-5" /> Edit Existing
          </span>
          <button class="btn btn-sm btn-circle btn-ghost" onclick={() => showEditExisting = false} aria-label="Close">
            <Icon icon="mdi:close" class="size-4" />
          </button>
        </div>
      </div>
      <div class="overflow-y-auto overscroll-contain p-5 space-y-3">
        <input
          bind:value={recordSearch}
          placeholder="Search records..."
          class="w-full bg-base-300/60 text-base-content/70 text-xs px-3 py-2 rounded-xl outline-none border border-base-content/10 placeholder:text-base-content/20 focus:border-primary/40 transition-colors"
        />
        {#if uderRecordsList.length === 0}
          <div class="py-16 text-center opacity-40">
            <Icon icon="tabler:ghost" class="size-10 mx-auto mb-2" />
            <p class="text-sm font-semibold">No records yet</p>
            <p class="text-xs opacity-70 mt-1">Build a record first</p>
          </div>
        {:else if filteredUderRecords.length === 0}
          <div class="py-16 text-center opacity-40">
            <Icon icon="mdi:magnify" class="size-10 mx-auto mb-2" />
            <p class="text-sm font-semibold">No matches</p>
            <p class="text-xs opacity-70 mt-1">Try a different name</p>
          </div>
        {:else}
          <div class="grid grid-cols-2 sm:grid-cols-3 gap-3">
            {#each filteredUderRecords as rec (rec.slug)}
              <button
                class="group text-left rounded-xl border border-base-content/10 overflow-hidden hover:border-primary/50 hover:shadow-lg transition-all duration-200"
                onclick={() => importExistingRecord(rec.slug)}
              >
                <div class="aspect-video bg-base-300/50 flex items-center justify-center shrink-0 overflow-hidden">
                  {#if rec.thumb}
                    <img src={rec.thumb} alt="" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" loading="lazy" />
                  {:else}
                    <Icon icon="material-symbols:image-outline-rounded" class="size-7 opacity-20" />
                  {/if}
                </div>
                <div class="p-2.5 space-y-1">
                  <p class="text-xs font-bold leading-tight line-clamp-2 min-h-[2em]">{rec.title}</p>
                  <span class="text-[9px] font-mono uppercase tracking-wider text-base-content/40">{rec.typeLabel}{rec.faction ? ` · ${rec.faction}` : ""}</span>
                </div>
              </button>
            {/each}
          </div>
        {/if}
      </div>
    </div>
  </div>
{/if}

{#if showPublish}
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm animate-in fade-in duration-150"
    onclick={() => showPublish = false}
    onkeydown={(e) => { if (e.key === "Escape") showPublish = false; }}
    role="dialog"
    tabindex="-1"
  >
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
    <div
      class="bg-base-100 rounded-2xl shadow-2xl w-96 max-h-[85vh] flex flex-col overflow-hidden mx-4"
      onclick={(e) => e.stopPropagation()}
      role="group"
      tabindex="-1"
    >
      <div class="relative">
        <div class="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-secondary/5"></div>
        <div class="relative flex items-center justify-between px-6 py-4 border-b border-base-content/10">
          <span class="font-bold text-lg text-primary flex items-center gap-2">
            <Icon icon="mdi:rocket-launch-outline" class="size-5" /> Publish
          </span>
          <button class="btn btn-sm btn-circle btn-ghost" onclick={() => showPublish = false} aria-label="Close">
            <Icon icon="mdi:close" class="size-4" />
          </button>
        </div>
      </div>
      <div class="p-6 pt-5 space-y-4">
        <p class="text-xs sm:text-sm text-base-content/55 leading-relaxed">
          You can either build the project locally and drop .uder files under
          <code class="px-1 py-0.5 rounded bg-base-content/10 text-[11px] font-mono">chapters/uder/records/</code>
          or send them up in the Discord so a lead editor can verify and add them for you.
        </p>
        <div class="space-y-2">
          <a
            href="https://discord.gg/HHnSjeGN4d"
            target="_blank"
            rel="noopener noreferrer"
            class="btn btn-md w-full rounded-xl bg-base-200/60 border border-base-content/10 text-base-content/60 hover:text-primary hover:border-primary/40 shadow-sm transition-all duration-200 gap-2"
          >
            <Icon icon="mdi:discord" class="size-4" />
            Join the Discord
          </a>
          <a
            href="https://github.com/EnderOksam/GSGW-Reader/tree/main/chapters/uder/records"
            target="_blank"
            rel="noopener noreferrer"
            class="btn btn-md w-full rounded-xl bg-base-200/60 border border-base-content/10 text-base-content/60 hover:text-primary hover:border-primary/40 shadow-sm transition-all duration-200 gap-2"
          >
            <Icon icon="mdi:github" class="size-4" />
            Check the GitHub
          </a>
        </div>
      </div>
    </div>
  </div>
{/if}

{#if showInfo}
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm animate-in fade-in duration-150"
    onclick={() => showInfo = false}
    onkeydown={(e) => { if (e.key === "Escape") showInfo = false; }}
    role="dialog"
    tabindex="-1"
  >
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
    <div
      class="bg-base-100 rounded-2xl shadow-2xl w-96 max-h-[80vh] flex flex-col overflow-hidden mx-4"
      onclick={(e) => e.stopPropagation()}
      role="group"
      tabindex="-1"
    >
      <div class="relative">
        <div class="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-secondary/5"></div>
        <div class="relative flex items-center justify-between px-6 py-4 border-b border-base-content/10">
          <span class="font-bold text-lg text-primary flex items-center gap-2">
            <Icon icon="mdi:note-text-outline" class="size-5" /> Patch Notes
          </span>
          <button class="btn btn-sm btn-circle btn-ghost" onclick={() => showInfo = false} aria-label="Close">
            <Icon icon="mdi:close" class="size-4" />
          </button>
        </div>
      </div>
      <div class="overflow-y-auto overscroll-contain p-5">
        {#each patchNotes as note}
          <div class="mb-3 last:mb-0">
            <button
              onclick={() => toggleVersion(note.version)}
              class="flex items-center gap-2 text-xs font-mono text-base-content/60 hover:text-base-content transition-colors w-full text-left py-1"
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
  </div>
{/if}

{#if showNodeInfo}
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm animate-in fade-in duration-150"
    onclick={() => showNodeInfo = false}
    onkeydown={(e) => { if (e.key === "Escape") showNodeInfo = false; }}
    role="dialog"
    tabindex="-1"
  >
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
    <div
      class="bg-base-100 rounded-2xl shadow-2xl max-w-3xl w-full mx-4 max-h-[85vh] flex flex-col overflow-hidden"
      onclick={(e) => e.stopPropagation()}
      role="group"
      tabindex="-1"
    >
      <div class="relative">
        <div class="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-secondary/5"></div>
        <div class="relative flex items-center justify-between px-6 py-4 border-b border-base-content/10">
          <span class="font-bold text-lg text-primary flex items-center gap-2">
            <Icon icon="mdi:information-outline" class="size-5" /> Node Reference
          </span>
          <button class="btn btn-sm btn-circle btn-ghost" onclick={() => showNodeInfo = false} aria-label="Close">
            <Icon icon="mdi:close" class="size-4" />
          </button>
        </div>
      </div>
      <div class="overflow-y-auto overscroll-contain p-5">
        <div class="grid grid-cols-2 gap-3">
          {#each NODE_DOCS as node}
            {@const color = NODE_COLORS[node.type]}
            {@const icon = NODE_ICONS[node.type]}
            {@const label = NODE_LABELS[node.type]}
            <div
              class="flex flex-col rounded-xl border border-base-content/8 overflow-hidden"
              style:--node-color={color}
            >
              <div class="flex items-center gap-2.5 px-4 py-2.5" style="background-color: color-mix(in oklch, var(--node-color) 14%, var(--color-base-200));">
                <Icon {icon} class="size-4 shrink-0" style="color:var(--node-color)" />
                <span class="text-xs font-bold" style="color: color-mix(in oklch, var(--node-color) 90%, var(--color-base-content));">{label}</span>
              </div>
              <div class="flex-1 px-4 py-3" style="background-color: color-mix(in oklch, var(--node-color) 4%, var(--color-base-100));">
                <p class="text-[11px] text-base-content/60 leading-relaxed">{@html node.desc}</p>
              </div>
            </div>
          {/each}
        </div>
      </div>
    </div>
  </div>
{/if}

<style>
  @keyframes slide-in-left {
    from { transform: translateX(-100%); }
    to { transform: translateX(0); }
  }
  :global(.animate-slide-in-left) {
    animation: slide-in-left 0.25s cubic-bezier(0.16, 1, 0.3, 1);
  }

  @keyframes glow-pulse {
    0%, 100% { text-shadow: 0 0 10px oklch(var(--p)/0.3), 0 0 20px oklch(var(--p)/0.1); }
    50% { text-shadow: 0 0 18px oklch(var(--p)/0.55), 0 0 36px oklch(var(--p)/0.25); }
  }
  .version-btn {
    color: oklch(var(--bc)/0.55);
    transition: all 0.2s;
    animation: glow-pulse 2.5s ease-in-out infinite;
  }
  .version-btn:hover {
    color: oklch(var(--bc)/0.85);
    animation: glow-pulse 0.8s ease-in-out infinite;
  }
  :global(.inline-ref) {
    font-weight: 600;
    font-size: 10px;
    padding: 1px 5px;
    border-radius: 4px;
  }
  :global(.inline-resource) {
    color: #ef4444;
    background: rgba(239, 68, 68, 0.12);
  }
  :global(.inline-condition) {
    color: #06b6d4;
    background: rgba(6, 182, 212, 0.12);
  }
  :global(.inline-addition) {
    color: #f472b6;
    background: rgba(244, 114, 182, 0.12);
  }
  :global(.inline-loop-check) {
    color: #f59e0b;
    background: rgba(245, 158, 11, 0.12);
  }
  :global(.inline-port) {
    display: inline-flex;
    align-items: center;
    vertical-align: middle;
  }
  :global(.pass-port) {
    color: #22c55e;
  }
  :global(.fail-port) {
    color: #ef4444;
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
</style>
