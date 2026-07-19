<script lang="ts">
  import { browser } from "$app/environment";
  import Icon from "@iconify/svelte";
  import { fade } from "svelte/transition";
  import "$lib/reader/reader-windows.css";
  import readerCss from "../../../../routes/(reader)/reader.css?url";
  import ChaptersEditor from "./ChaptersEditor.svelte";
  import CharactersEditor from "./CharactersEditor.svelte";
  import { REPO, BRANCH } from "./lib/github-api";

  type EditorMode = "chapters" | "characters";

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

  let editorMode = $state<EditorMode>((typeof localStorage !== 'undefined' ? localStorage.getItem('gsgw-editor-mode') : null) as EditorMode ?? "chapters");
  let showModeMenu = $state(false);
  let showMobileMenu = $state(false);
  let showInfo = $state(false);
  let expandedVersion = $state<string | null>(null);

  $effect(() => {
    localStorage.setItem('gsgw-editor-mode', editorMode);
  });

  let patchNotes = [
    { version: "v0.6", description: "- cleaned up the editor code and reworked the formatting window" },
    { version: "v0.5", description: "- added character editor" },
    { version: "v0.4", description: "- bug fixing\n- themes\n- changed mobile editing ui to fit the smaller screen" },
    { version: "v0.3", description: "- better ui (hopefully)\n- mobile editing\n- custom translations\n- adding/removing chapters" },
    { version: "v0.2", description: `- added caching chapter changes and scrolling positions\n- reverting to source\n- exporting single or bulk chapters` },
    { version: "v0.1", description: "initial release of the editor to see a live preview of how your changes would look in the reader" }
  ];

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

  let chaptersRef: ChaptersEditor = $state()!;
  let charsRef: CharactersEditor = $state()!;
</script>

<svelte:head>
  <link rel="stylesheet" href={readerCss}>
</svelte:head>

<div class="h-dvh bg-base-300 flex flex-col overflow-hidden selection:bg-primary/30">
  <div class="flex items-center justify-between px-2 sm:px-3 py-2 border-b border-base-content/10 bg-base-200/60 backdrop-blur-md shrink-0 relative z-10">
    <div class="flex items-center gap-1 sm:gap-0.5 relative">
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
    <div class="flex items-center gap-1.5 sm:gap-2">
      <div class="relative hidden lg:block">
        <button onclick={() => showModeMenu = !showModeMenu} class="text-xs font-mono font-medium px-3 py-1.5 rounded-lg border border-base-content/15 text-base-content/60 hover:text-base-content hover:border-base-content/30 hover:bg-base-content/5 transition-all whitespace-nowrap active:scale-95">
          <span class="capitalize">{editorMode}</span>
          <Icon icon="mdi:chevron-down" class="size-3.5 inline-block ml-0.5" />
        </button>
        {#if showModeMenu}
          <div class="absolute top-full right-0 mt-2 bg-base-200/95 backdrop-blur-xl border border-base-content/10 rounded-xl shadow-2xl shadow-black/20 py-1.5 min-w-40 z-50 overflow-hidden">
            <button onclick={() => { editorMode = "chapters"; showModeMenu = false; }} class="flex items-center gap-2 w-full text-left text-xs px-4 py-2.5 hover:bg-primary/10 text-base-content/70 transition-colors {editorMode === 'chapters' ? 'bg-primary/10 text-primary font-medium' : ''}">Chapters</button>
            <button onclick={() => { editorMode = "characters"; showModeMenu = false; }} class="flex items-center gap-2 w-full text-left text-xs px-4 py-2.5 hover:bg-primary/10 text-base-content/70 transition-colors {editorMode === 'characters' ? 'bg-primary/10 text-primary font-medium' : ''}">Characters</button>
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
      <button onclick={() => showInfo = true} class="version-btn text-[10px] sm:text-xs font-mono px-2 py-1 rounded-md bg-base-content/5">v0.6</button>
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
        {:else}
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
        {/if}
      </div>
    {/key}
  </div>
</div>

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
      class="bg-base-200/95 backdrop-blur-xl border border-base-content/10 rounded-2xl p-6 w-96 shadow-2xl shadow-black/30"
      onclick={(e) => e.stopPropagation()}
      role="group"
      tabindex="-1"
    >
      <h2 class="text-sm font-bold text-base-content/70 font-mono mb-5 tracking-wide">Patch Notes</h2>
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
