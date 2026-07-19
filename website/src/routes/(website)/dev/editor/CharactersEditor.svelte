<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  import Icon from "@iconify/svelte";
  import { slide } from "svelte/transition";
  import { tick } from "svelte";
  import { REPO, BRANCH } from "./lib/github-api";
  import { getCachedJson, setCachedJson, getCachedImage, setCachedImage, removeCachedImage, listCachedImageKeys, deleteCachedJson } from "./lib/character-cache";
  import { exportCharacterZip, exportAllCharactersZip } from "./lib/zip-tools";
  import JSZip from "jszip";
  import localCharacters from "$lib/reader/characters.json";

  let {
    showMobileMenu = $bindable(false),
    currentBook = $bindable("gsgw"),
    charExplorerPath = $bindable<string[]>([]),
    cachedCharImages = $bindable<Set<string>>(new Set()),
    charFolderHasLocalEdits = $bindable(false),
    hasSelectedChar = $bindable(false),
    hasCharacters = $bindable(false),
  } = $props();

  interface Alt {
    id: string;
    name: string;
    chapter: number | null;
    toggleable: boolean;
    manwhaImage: string | null;
    webnovelImage: string | null;
  }

  interface CharacterData {
    id: string;
    name: string;
    faction: string;
    manwhaImage: string | null;
    webnovelImage: string | null;
    firstAppearance: number | null;
    birthday: string;
    alias: string;
    preferredAlt: string | null;
    alts: Alt[];
  }

  let characters = $state<CharacterData[]>([]);
  let charactersLoading = $state(false);
  let charactersError = $state("");
  let objectUrls = $state<Map<string, string>>(new Map());
  let charFolderFiles = $state<string[]>([]);
  let charSelectedFile = $state<string | null>(null);
  let charJsonInput = $state("");
  let charJsonParseError = $state("");
  let jsonEditorRef: HTMLTextAreaElement | null = $state(null);
  let lineNumbersEl: HTMLDivElement | null = $state(null);
  let lineCount = $derived(charJsonInput ? charJsonInput.split('\n').length : 1);
  let charCardModes = $state<Record<string, string>>({});
  let charSelectedAlt = $state<string | null>(null);
  let showNewCharDialog = $state(false);
  let newCharName = $state("");
  let charImageReplaceTarget = $state<string | null>(null);
  let imgLoadCount = $state(0);
  let charactersRefreshing = $state(false);
  let charImageImportRef: HTMLInputElement | undefined = $state();
  let suppressAutoSave = false;

  let charFolderName = $derived(charExplorerPath.length > 0 ? charExplorerPath[charExplorerPath.length - 1] : null);
  let currentCharFolder = $derived(charExplorerPath.length > 0 ? charExplorerPath[charExplorerPath.length - 1] : "");
  let selectedIsImage = $derived(charSelectedFile ? !!charSelectedFile.match(/\.(png|jpg|jpeg|webp|avif)$/i) : false);

  let selectedCharacterData = $derived(
    charExplorerPath.length > 0
      ? characters.find(c => c.name === charExplorerPath[charExplorerPath.length - 1]) ?? null
      : null
  );

  let liveCharData = $derived.by(() => {
    if (!charJsonInput) return null;
    try {
      const parsed = JSON.parse(charJsonInput);
      if (parsed && typeof parsed === 'object' && parsed.id) return parsed as CharacterData;
    } catch {}
    return null;
  });

  let displayCharData = $derived(liveCharData ?? selectedCharacterData);

  let selectedAltObj = $derived(
    displayCharData && charSelectedAlt
      ? displayCharData.alts.find(a => a.id === charSelectedAlt) ?? null
      : null
  );

  let charSelectedImageUrl = $derived(
    charSelectedFile && charExplorerPath.length > 0 && selectedIsImage
      ? cachedOrRemote(charSelectedFile)
      : null
  );

  let mainManwhaImage = $derived(cachedOrRemote(displayCharData?.manwhaImage ?? null));
  let mainWebnovelImage = $derived(cachedOrRemote(displayCharData?.webnovelImage ?? null));
  let altManwhaImage = $derived(selectedAltObj?.manwhaImage ? cachedOrRemote(selectedAltObj.manwhaImage) : null);
  let altWebnovelImage = $derived(selectedAltObj?.webnovelImage ? cachedOrRemote(selectedAltObj.webnovelImage) : null);

  $effect(() => { hasSelectedChar = !!displayCharData; });
  $effect(() => { hasCharacters = characters.length > 0; });

  $effect(() => {
    const folder = charExplorerPath.length > 0 ? charExplorerPath[charExplorerPath.length - 1] : "";
    if (!folder) return;
    const imgKeys = [...cachedCharImages];
    for (const filename of imgKeys) {
      const key = `${folder}/${filename}`;
      if (!objectUrls.has(key)) {
        getCachedImage(folder, filename).then(blob => {
          if (blob && !objectUrls.has(key)) {
            const url = URL.createObjectURL(blob);
            objectUrls.set(key, url);
          }
        });
      }
    }
  });

  $effect(() => {
    if (charJsonInput) {
      try {
        JSON.parse(charJsonInput);
        charJsonParseError = "";
      } catch (e: any) {
        charJsonParseError = e.message;
      }
    } else {
      charJsonParseError = "";
    }
  });

  let charJsonSaveTimer: ReturnType<typeof setTimeout> | undefined;
  $effect(() => {
    if (charJsonInput && !charJsonParseError && charExplorerPath.length > 0 && !suppressAutoSave) {
      clearTimeout(charJsonSaveTimer);
      charJsonSaveTimer = setTimeout(() => {
        const folder = charExplorerPath[charExplorerPath.length - 1];
        setCachedJson(folder, charJsonInput);
        charFolderHasLocalEdits = true;
      }, 800);
    }
    return () => clearTimeout(charJsonSaveTimer);
  });

  function syncJsonScroll() {
    if (lineNumbersEl && jsonEditorRef) {
      lineNumbersEl.scrollTop = jsonEditorRef.scrollTop;
    }
  }

  function cachedOrRemote(filename: string | null): string | null {
    if (!filename) return null;
    if (cachedCharImages.has(filename)) {
      const url = objectUrls.get(`${currentCharFolder}/${filename}`);
      if (url) return url;
    }
    return `/characters/${filename}`;
  }

  function getLocalFolderFiles(name: string): string[] {
    const char = characters.find(c => c.name === name);
    if (!char) return [];
    const files: string[] = ["character.json"];
    if (char.manwhaImage) files.push(char.manwhaImage);
    if (char.webnovelImage) files.push(char.webnovelImage);
    for (const alt of char.alts) {
      if (alt.manwhaImage && !files.includes(alt.manwhaImage)) files.push(alt.manwhaImage);
      if (alt.webnovelImage && !files.includes(alt.webnovelImage)) files.push(alt.webnovelImage);
    }
    return files.sort();
  }

  async function imgErrorFallback(e: Event, filename: string) {
    const img = e.target as HTMLImageElement;
    if (img.dataset.fallback === 'remote') { img.style.display = 'none'; return; }
    if (img.dataset.fallback === 'cache' && charFolderName) {
      img.dataset.fallback = 'remote';
      img.src = `https://raw.githubusercontent.com/${REPO}/${BRANCH}/images/gsgw/references/${charFolderName}/${filename}`;
      return;
    }
    img.dataset.fallback = 'cache';
    if (charFolderName) {
      const cached = await getCachedImage(charFolderName, filename);
      if (cached) {
        const key = `${charFolderName}/${filename}`;
        if (objectUrls.has(key)) URL.revokeObjectURL(objectUrls.get(key)!);
        const url = URL.createObjectURL(cached);
        objectUrls.set(key, url);
        img.src = url;
        return;
      }
      img.dataset.fallback = 'remote';
      img.src = `https://raw.githubusercontent.com/${REPO}/${BRANCH}/images/gsgw/references/${charFolderName}/${filename}`;
    }
  }

  async function loadCharacters() {
    charactersLoading = true;
    charactersError = "";
    try {
      const url = `https://api.github.com/repos/${REPO}/contents/images/gsgw/references`;
      const res = await fetch(url);
      if (!res.ok) throw new Error(`GitHub API: ${res.status}`);
      const data = await res.json();
      const dirs: string[] = data
        .filter((f: any) => f.type === "dir")
        .map((f: any) => f.name);
      const chars: CharacterData[] = [];
      for (const dir of dirs) {
        try {
          const charUrl = `https://raw.githubusercontent.com/${REPO}/${BRANCH}/images/gsgw/references/${dir}/character.json`;
          const charRes = await fetch(charUrl);
          if (charRes.ok) {
            const charData: CharacterData = await charRes.json();
            chars.push(charData);
          }
        } catch {}
      }
      if (chars.length === 0) throw new Error("No characters loaded");
      characters = chars.sort((a, b) => a.name.localeCompare(b.name));
    } catch {
      try {
        characters = (localCharacters as any[]).map(c => ({
          id: c.id,
          name: c.name,
          faction: c.faction ?? "daydream",
          manwhaImage: c.manwhaImage ?? null,
          webnovelImage: c.webnovelImage ?? null,
          firstAppearance: c.firstAppearance ?? null,
          birthday: c.birthday ?? "",
          alias: c.alias ?? "",
          preferredAlt: c.preferredAlt ?? null,
          alts: c.alts ?? [],
        }));
        if (characters.length === 0) throw new Error("empty");
      } catch {
        charactersError = "Failed to load characters";
        characters = [];
      }
    } finally {
      charactersLoading = false;
    }
  }

  async function enterCharFolder(name: string) {
    charExplorerPath = [...charExplorerPath, name];
    charSelectedFile = null;
    charJsonInput = "";
    charSelectedAlt = null;
    cachedCharImages = new Set();
    const cachedImages = await listCachedImageKeys(name);
    for (const img of cachedImages) {
      cachedCharImages.add(img);
    }
    try {
      const url = `https://api.github.com/repos/${REPO}/contents/images/gsgw/references/${charExplorerPath.join('/')}`;
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        charFolderFiles = data.map((f: any) => f.name).sort();
      } else {
        charFolderFiles = getLocalFolderFiles(name);
      }
    } catch {
      charFolderFiles = getLocalFolderFiles(name);
    }
    for (const img of cachedImages) {
      if (!charFolderFiles.includes(img)) charFolderFiles.push(img);
    }
    charFolderFiles.sort();
    if (charFolderFiles.includes("character.json")) {
      await selectCharFile("character.json");
    }
  }

  async function saveCurrentCharJson() {
    if (charJsonInput && charExplorerPath.length > 0) {
      const folder = charExplorerPath[charExplorerPath.length - 1];
      await setCachedJson(folder, charJsonInput);
      charFolderHasLocalEdits = true;
    }
  }

  export async function backToCharList() {
    await saveCurrentCharJson();
    for (const url of objectUrls.values()) URL.revokeObjectURL(url);
    objectUrls.clear();
    cachedCharImages = new Set();
    charExplorerPath = [];
    charFolderFiles = [];
    charSelectedFile = null;
    charJsonInput = "";
    charFolderHasLocalEdits = false;
  }

  async function goBackOneFolder() {
    await saveCurrentCharJson();
    if (charExplorerPath.length <= 1) {
      await backToCharList();
    } else {
      const prev = charExplorerPath.slice(0, -1);
      charExplorerPath = prev;
      charSelectedFile = null;
      charJsonInput = "";
      charSelectedAlt = null;
      enterCharFolder(prev[prev.length - 1]);
    }
  }

  async function selectCharFile(filename: string) {
    charSelectedFile = filename;
    if (!filename.endsWith('.json')) { charJsonInput = ""; return; }
    if (charExplorerPath.length === 0) return;
    const folder = charExplorerPath[charExplorerPath.length - 1];
    const cached = await getCachedJson(folder);
    if (cached !== null) {
      charJsonInput = cached;
      charFolderHasLocalEdits = true;
      return;
    }
    try {
      const url = `https://raw.githubusercontent.com/${REPO}/${BRANCH}/images/gsgw/references/${charExplorerPath.join('/')}/${filename}`;
      const res = await fetch(url);
      if (res.ok) {
        charJsonInput = await res.text();
      } else {
        const char = characters.find(c => c.name === folder);
        if (char) {
          charJsonInput = JSON.stringify(char, null, 2);
        }
      }
    } catch {
      const char = characters.find(c => c.name === folder);
      if (char) {
        charJsonInput = JSON.stringify(char, null, 2);
      }
    }
  }

  export function addNewCharacter(name: string) {
    if (!name) return;
    const id = name.replace(/\s+/g, '');
    const newChar: CharacterData = {
      id,
      name,
      faction: "daydream",
      manwhaImage: `${id}Manwha.webp`,
      webnovelImage: `${id}Webnovel.webp`,
      firstAppearance: null,
      birthday: "",
      alias: "",
      preferredAlt: null,
      alts: [],
    };
    characters = [...characters, newChar].sort((a, b) => a.name.localeCompare(b.name));
    charJsonInput = JSON.stringify(newChar, null, 2);
    enterCharFolder(name);
  }

  export function deleteCharacter() {
    if (!displayCharData) return;
    const isSource = (localCharacters as any[]).some(c => c.id === displayCharData.id);
    if (isSource) {
      alert(`"${displayCharData.name}" is a source character and cannot be deleted.`);
      return;
    }
    if (!confirm(`Delete "${displayCharData.name}"?`)) return;
    characters = characters.filter(c => c.id !== displayCharData.id);
    backToCharList();
  }

  export async function exportCurrentCharacterZip() {
    if (!displayCharData || charExplorerPath.length === 0) return;
    const folder = charExplorerPath[charExplorerPath.length - 1];
    const jsonContent = charJsonInput || JSON.stringify(displayCharData, null, 2);
    const parsed = liveCharData || JSON.parse(jsonContent) as CharacterData;
    const seen = new Set<string>();
    if (parsed.manwhaImage) seen.add(parsed.manwhaImage);
    if (parsed.webnovelImage) seen.add(parsed.webnovelImage);
    for (const alt of (parsed.alts || [])) {
      if (alt.manwhaImage) seen.add(alt.manwhaImage);
      if (alt.webnovelImage) seen.add(alt.webnovelImage);
    }
    const imageFiles = [...new Set([...seen, ...charFolderFiles.filter(f => f !== "character.json")])];
    await exportCharacterZip(folder, jsonContent, imageFiles);
  }

  export async function exportAllChars() {
    const charData = await Promise.all(characters.map(async (char) => {
      const folder = char.name;
      let jsonContent: string | null = null;
      const cachedJson = await getCachedJson(folder);
      if (cachedJson) { jsonContent = cachedJson; }
      else {
        try {
          const url = `https://raw.githubusercontent.com/${REPO}/${BRANCH}/images/gsgw/references/${folder}/character.json`;
          const res = await fetch(url);
          if (res.ok) jsonContent = await res.text();
        } catch {}
      }
      if (!jsonContent) return null;
      const parsed = JSON.parse(jsonContent);
      const imageFiles: string[] = [];
      if (parsed.manwhaImage) imageFiles.push(parsed.manwhaImage);
      if (parsed.webnovelImage) imageFiles.push(parsed.webnovelImage);
      for (const alt of (parsed.alts || [])) {
        if (alt.manwhaImage) imageFiles.push(alt.manwhaImage);
        if (alt.webnovelImage) imageFiles.push(alt.webnovelImage);
      }
      return { name: folder, jsonContent, imageFiles };
    }));
    await exportAllCharactersZip(charData.filter(Boolean) as { name: string; jsonContent: string; imageFiles: string[] }[]);
  }

  function getCharImageSrc(folder: string, filename: string | null): string | null {
    if (!filename) return null;
    if (cachedCharImages.has(filename)) {
      const key = `${folder}/${filename}`;
      if (objectUrls.has(key)) return objectUrls.get(key)!;
    }
    return `/characters/${filename}`;
  }

  async function getCachedObjectUrl(folder: string, filename: string): Promise<string | null> {
    const key = `${folder}/${filename}`;
    if (objectUrls.has(key)) return objectUrls.get(key)!;
    const blob = await getCachedImage(folder, filename);
    if (!blob) return null;
    const url = URL.createObjectURL(blob);
    objectUrls.set(key, url);
    return url;
  }

  async function replaceCharImage(filename: string) {
    charImageReplaceTarget = filename;
    charImageImportRef?.click();
  }

  export async function handleCharImageImport(e: Event) {
    const file = (e.target as HTMLInputElement).files?.[0];
    if (!file) return;
    if (!file.name.toLowerCase().endsWith('.webp')) {
      alert("Only .webp images are supported.");
      (e.target as HTMLInputElement).value = "";
      return;
    }
    if (charExplorerPath.length === 0) return;
    const folder = charExplorerPath[charExplorerPath.length - 1];
    const targetFilename = charImageReplaceTarget || file.name;
    const blob = file;
    await setCachedImage(folder, targetFilename, blob);
    cachedCharImages.add(targetFilename);
    const key = `${folder}/${targetFilename}`;
    if (objectUrls.has(key)) URL.revokeObjectURL(objectUrls.get(key)!);
    const url = URL.createObjectURL(blob);
    objectUrls.set(key, url);
    if (!charFolderFiles.includes(targetFilename)) {
      charFolderFiles = [...charFolderFiles, targetFilename].sort();
    }
    if (charSelectedFile === targetFilename) {
      const tmp = charSelectedFile;
      charSelectedFile = null;
      await tick();
      charSelectedFile = tmp;
    }
    charImageReplaceTarget = null;
    imgLoadCount++;
    (e.target as HTMLInputElement).value = "";
  }

  export function importNewImage() {
    charImageReplaceTarget = null;
    charImageImportRef?.click();
  }

  async function deleteCachedImage(filename: string) {
    if (charExplorerPath.length === 0) return;
    const folder = charExplorerPath[charExplorerPath.length - 1];
    await removeCachedImage(folder, filename);
    cachedCharImages.delete(filename);
    const key = `${folder}/${filename}`;
    if (objectUrls.has(key)) {
      URL.revokeObjectURL(objectUrls.get(key)!);
      objectUrls.delete(key);
    }
    charFolderFiles = charFolderFiles.filter(f => f !== filename);
    if (charSelectedFile === filename) charSelectedFile = null;
    const remaining = await listCachedImageKeys(folder);
    const hasCachedJson = await getCachedJson(folder);
    if (remaining.length === 0 && !hasCachedJson) charFolderHasLocalEdits = false;
  }

  async function revertCharJson() {
    if (charExplorerPath.length === 0) return;
    const folder = charExplorerPath[charExplorerPath.length - 1];
    await deleteCachedJson(folder);
    charFolderHasLocalEdits = false;
    suppressAutoSave = true;
    const remaining = await listCachedImageKeys(folder);
    if (remaining.length > 0) charFolderHasLocalEdits = true;
    await selectCharFile("character.json");
    suppressAutoSave = false;
  }

  async function revertCachedImage(filename: string) {
    await deleteCachedImage(filename);
  }

  export function revertAll() {
    revertCharJson();
    for (const img of [...cachedCharImages]) revertCachedImage(img);
  }

  async function refreshCharacters() {
    charactersRefreshing = true;
    const custom = characters.filter(c => !(localCharacters as any[]).some(lc => lc.id === c.id));
    try {
      const url = `https://api.github.com/repos/${REPO}/contents/images/gsgw/references`;
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        const dirs: string[] = data.filter((f: any) => f.type === "dir").map((f: any) => f.name);
        const chars: CharacterData[] = [];
        for (const dir of dirs) {
          try {
            const charUrl = `https://raw.githubusercontent.com/${REPO}/${BRANCH}/images/gsgw/references/${dir}/character.json`;
            const charRes = await fetch(charUrl);
            if (charRes.ok) {
              const charData: CharacterData = await charRes.json();
              chars.push(charData);
            }
          } catch {}
        }
        if (chars.length > 0) {
          const merged = [...chars];
          for (const c of custom) {
            if (!merged.some(m => m.id === c.id)) merged.push(c);
          }
          characters = merged.sort((a, b) => a.name.localeCompare(b.name));
          charactersRefreshing = false;
          return;
        }
      }
    } catch {}
    const source = (localCharacters as any[]).map(c => ({
      id: c.id, name: c.name, faction: c.faction ?? "daydream",
      manwhaImage: c.manwhaImage ?? null, webnovelImage: c.webnovelImage ?? null,
      firstAppearance: c.firstAppearance ?? null, birthday: c.birthday ?? "",
      alias: c.alias ?? "", preferredAlt: c.preferredAlt ?? null, alts: c.alts ?? [],
    }));
    const merged = [...source];
    for (const c of custom) {
      if (!merged.some(m => m.id === c.id)) merged.push(c);
    }
    characters = merged.sort((a, b) => a.name.localeCompare(b.name));
    charactersRefreshing = false;
  }

  export async function importCharacterZip(e: Event) {
    const file = (e.target as HTMLInputElement).files?.[0];
    if (!file) return;
    try {
      const zip = await JSZip.loadAsync(file);
      const entries: { path: string; data: string }[] = [];
      const promises: Promise<void>[] = [];
      zip.forEach((path, entry) => {
        if (!entry.dir) {
          promises.push(
            entry.async("string").then((data) => {
              entries.push({ path: path.split("/").pop() || path, data });
            })
          );
        }
      });
      await Promise.all(promises);
      const jsonEntry = entries.find(e => e.path === "character.json");
      if (!jsonEntry) { alert("No character.json found in zip."); return; }
      const charData: CharacterData = JSON.parse(jsonEntry.data);
      const existing = characters.findIndex(c => c.id === charData.id);
      if (existing >= 0) {
        characters[existing] = charData;
      } else {
        characters = [...characters, charData].sort((a, b) => a.name.localeCompare(b.name));
      }
      enterCharFolder(charData.name);
    } catch (err) {
      alert("Failed to import: " + (err instanceof Error ? err.message : String(err)));
    }
    (e.target as HTMLInputElement).value = "";
  }

  onDestroy(() => { saveCurrentCharJson(); });
</script>

<div class="flex-1 flex flex-col min-h-0 min-w-0">
<!-- ===== MOBILE LAYOUT (< lg) ===== -->
<div class="flex flex-1 lg:hidden min-h-0 p-2 gap-2">
  <div class="flex-1 flex flex-col min-h-0 min-w-0">
    <div class="flex gap-1 mb-2 shrink-0">
      <button class="flex-1 text-[11px] font-mono font-medium tracking-wider py-2 rounded-xl bg-primary/15 text-primary shadow-sm">Characters</button>
    </div>
    <div class="flex-1 flex flex-col min-h-0 min-w-0 rounded-xl border border-base-content/10 bg-base-300/60 overflow-hidden shadow-sm">
      {#if charExplorerPath.length === 0}
        <div class="p-2 border-b border-base-content/10 flex items-center justify-between">
          <span class="text-[10px] font-mono text-base-content/30 font-medium uppercase tracking-wider">folders</span>
          <button onclick={refreshCharacters} disabled={charactersRefreshing} class="text-base-content/40 hover:text-base-content active:scale-95 transition-all p-1.5 rounded-xl hover:bg-base-content/5 disabled:text-base-content/15 disabled:hover:bg-transparent disabled:active:scale-100 disabled:cursor-not-allowed" title="Fetch source">
            <Icon icon={charactersRefreshing ? "mdi:loading" : "mdi:refresh"} class="size-3.5 {charactersRefreshing ? 'animate-spin' : ''}" />
          </button>
        </div>
        <div class="flex-1 overflow-y-auto p-2 min-h-0 space-y-0.5 scrollbar-thin">
          {#if charactersLoading}
            <div class="flex items-center justify-center py-6"><Icon icon="mdi:loading" class="size-4 text-base-content/50 animate-spin" /></div>
          {:else if charactersError}
            <p class="text-xs text-error/70 text-center py-6">{charactersError}</p>
          {:else if characters.length === 0}
            <p class="text-xs text-base-content/40 text-center py-6">no characters</p>
          {:else}
            {#each characters as char}
              <button onclick={() => enterCharFolder(char.name)} class="flex items-center gap-2.5 w-full text-left text-xs px-3 py-2.5 rounded-xl active:scale-[0.98] transition-all text-base-content/70 hover:bg-base-content/5">
                <Icon icon="mdi:folder-outline" class="size-4 shrink-0" />
                <span class="truncate">{char.name}</span>
              </button>
            {/each}
          {/if}
        </div>
      {:else}
        <div class="p-1.5 border-b border-base-content/10 space-y-0.5">
          <button onclick={goBackOneFolder} class="flex items-center gap-1.5 w-full text-left text-xs px-2.5 py-2 rounded-xl active:scale-[0.98] transition-all text-base-content/50 hover:text-base-content hover:bg-base-content/5">
            <Icon icon="mdi:arrow-left" class="size-3.5" />
            <span class="text-[10px]">..</span>
          </button>
        </div>
        <div class="flex-1 overflow-y-auto p-2 min-h-0 space-y-0.5 scrollbar-thin">
          {#each charFolderFiles.filter(f => f === "character.json") as f}
            <button onclick={() => selectCharFile(f)} class="flex items-center gap-2.5 w-full text-left text-xs px-3 py-2.5 rounded-xl active:scale-[0.98] transition-all {charSelectedFile === f ? 'bg-primary/10 text-primary shadow-sm' : 'text-base-content/70 hover:bg-base-content/5'}">
              <Icon icon="mdi:code-json" class="size-4 shrink-0" />
              <span class="truncate">{f}</span>
            </button>
          {/each}
          {#if charFolderFiles.filter(f => f !== "character.json").length > 0}
            <div class="mx-1 my-1.5 border-t border-base-content/10"></div>
            {#each charFolderFiles.filter(f => f !== "character.json") as f}
              <button onclick={() => selectCharFile(f)} class="flex items-center gap-2.5 w-full text-left text-xs px-3 py-2.5 rounded-xl active:scale-[0.98] transition-all {charSelectedFile === f ? 'bg-primary/10 text-primary shadow-sm' : 'text-base-content/70 hover:bg-base-content/5'}">
                <Icon icon={f.match(/\.(png|jpg|jpeg|webp|avif)$/i) ? 'mdi:image-outline' : 'mdi:file-document-outline'} class="size-4 shrink-0" />
                <span class="truncate">{f}</span>
              </button>
            {/each}
          {/if}
        </div>
      {/if}
    </div>
  </div>
</div>

<!-- ===== DESKTOP LAYOUT (lg+) ===== -->
<div class="hidden lg:flex flex-1 gap-3 min-h-0 p-3">
  <div class="w-56 flex flex-col bg-base-200/80 backdrop-blur-sm rounded-xl border border-base-content/10 shrink-0 min-h-0 shadow-lg shadow-black/5">
    <div class="p-2 border-b border-base-content/10 flex items-center justify-between">
      {#if charExplorerPath.length === 0}
        <span class="text-[10px] font-mono text-base-content/30 font-medium uppercase tracking-wider">folders</span>
        <button onclick={refreshCharacters} disabled={charactersRefreshing} class="text-base-content/40 hover:text-base-content active:scale-95 transition-all p-1.5 rounded-xl hover:bg-base-content/5 disabled:text-base-content/15 disabled:hover:bg-transparent disabled:active:scale-100 disabled:cursor-not-allowed" title="Fetch source">
          <Icon icon={charactersRefreshing ? "mdi:loading" : "mdi:refresh"} class="size-3.5 {charactersRefreshing ? 'animate-spin' : ''}" />
        </button>
      {:else}
        <div class="flex items-center gap-1">
          <button onclick={goBackOneFolder} class="text-base-content/40 hover:text-base-content active:scale-95 transition-all p-1.5 rounded-xl hover:bg-base-content/5" title="Back">
            <Icon icon="mdi:arrow-left" class="size-3.5" />
          </button>
          <span class="text-[10px] font-mono text-base-content/40 truncate">{charExplorerPath[charExplorerPath.length - 1]}/</span>
        </div>
      {/if}
    </div>
    <div class="flex-1 overflow-y-auto p-2 min-h-0 space-y-0.5 scrollbar-thin">
      {#if charactersLoading}
        <div class="flex items-center justify-center py-6"><Icon icon="mdi:loading" class="size-4 text-base-content/50 animate-spin" /></div>
      {:else if charactersError}
        <p class="text-xs text-error/70 text-center py-6">{charactersError}</p>
      {:else if characters.length === 0 && charExplorerPath.length === 0}
        <p class="text-xs text-base-content/40 text-center py-6">no characters</p>
      {:else if charExplorerPath.length === 0}
        {#each characters as char}
          <button onclick={() => enterCharFolder(char.name)} class="flex items-center gap-2.5 w-full text-left text-xs px-3 py-2.5 rounded-xl active:scale-[0.98] transition-all text-base-content/70 hover:bg-base-content/5">
            <Icon icon="mdi:folder-outline" class="size-4 shrink-0" />
            <span class="truncate">{char.name}</span>
          </button>
        {/each}
      {:else}
        {#each charFolderFiles.filter(f => f === "character.json") as f}
          <button onclick={() => selectCharFile(f)} class="flex items-center gap-2.5 w-full text-left text-xs px-3 py-2.5 rounded-xl active:scale-[0.98] transition-all {charSelectedFile === f ? 'bg-primary/10 text-primary shadow-sm' : 'text-base-content/70 hover:bg-base-content/5'}">
            <Icon icon="mdi:code-json" class="size-4 shrink-0" />
            <span class="truncate">{f}</span>
            {#if charFolderHasLocalEdits}<span class="text-success/70 text-[10px] font-mono ml-auto">●</span>{/if}
          </button>
        {/each}
        {#if charFolderFiles.filter(f => f !== "character.json").length > 0}
          <div class="mx-1 my-1.5 border-t border-base-content/10"></div>
          {#each charFolderFiles.filter(f => f !== "character.json") as f}
            <button onclick={() => selectCharFile(f)} class="flex items-center gap-2.5 w-full text-left text-xs px-3 py-2.5 rounded-xl active:scale-[0.98] transition-all {charSelectedFile === f ? 'bg-primary/10 text-primary shadow-sm' : 'text-base-content/70 hover:bg-base-content/5'}">
              <Icon icon={f.match(/\.(png|jpg|jpeg|webp|avif)$/i) ? 'mdi:image-outline' : 'mdi:file-document-outline'} class="size-4 shrink-0" />
              <span class="truncate">{f}</span>
              {#if cachedCharImages.has(f)}<span class="text-success/70 text-[10px] font-mono ml-auto">●</span>{/if}
            </button>
          {/each}
        {/if}
      {/if}
    </div>
  </div>
  <div class="flex-1 flex gap-3 min-h-0 min-w-0">
    {#if displayCharData}
      {@const charMode = charCardModes[displayCharData.id] ?? (displayCharData.manwhaImage ? "manwha" : "webnovel")}
      <div class="flex-1 flex flex-col min-h-0 min-w-0">
        {#if selectedIsImage && charSelectedImageUrl}
          <div class="flex items-center gap-2 px-3 py-2 border-b border-base-content/10 bg-base-200/60 backdrop-blur-sm rounded-t-xl shrink-0">
            <span class="text-[10px] font-mono text-base-content/30 font-medium uppercase tracking-wider">image preview</span>
            <span class="text-[10px] font-mono text-base-content/20">·</span>
            <span class="text-[10px] font-mono text-base-content/25 truncate">{charSelectedFile}</span>
            <div class="ml-auto flex gap-0.5">
              <button onclick={() => replaceCharImage(charSelectedFile!)} class="text-base-content/40 hover:text-base-content active:scale-95 transition-all p-1.5 rounded-xl hover:bg-base-content/5" title="Replace image">
                <Icon icon="mdi:camera-replace-outline" class="size-3.5" />
              </button>
              {#if cachedCharImages.has(charSelectedFile!)}
                <button onclick={() => revertCachedImage(charSelectedFile!)} class="text-success/50 hover:text-success active:scale-95 transition-all p-1.5 rounded-xl hover:bg-base-content/5" title="Revert to source">
                  <Icon icon="mdi:undo-variant" class="size-3.5" />
                </button>
                <button onclick={() => deleteCachedImage(charSelectedFile!)} class="text-base-content/40 hover:text-error active:scale-95 transition-all p-1.5 rounded-xl hover:bg-base-content/5" title="Delete cached image">
                  <Icon icon="mdi:delete-outline" class="size-3.5" />
                </button>
              {/if}
            </div>
          </div>
          <div class="flex-1 flex items-center justify-center rounded-b-xl border-x border-b border-base-content/10 bg-base-300/60 p-4">
            <img src={charSelectedImageUrl} alt={charSelectedFile} class="max-w-full max-h-full object-contain rounded-lg shadow-sm" onerror={(e) => { const img = e.target as HTMLImageElement; if (!img.dataset.fallback) { img.dataset.fallback = '1'; img.src = `https://raw.githubusercontent.com/${REPO}/${BRANCH}/images/gsgw/references/${charExplorerPath.join('/')}/${charSelectedFile}`; } else { img.style.display = 'none'; } }} />
          </div>
        {:else}
          <div class="flex items-center justify-between px-3 py-2 border-b border-base-content/10 bg-base-200/60 backdrop-blur-sm rounded-t-xl shrink-0">
            <span class="text-[10px] font-mono text-base-content/30 font-medium uppercase tracking-wider">character.json</span>
            {#if liveCharData}
              <span class="text-[10px] font-mono text-success font-medium">✓ valid json</span>
            {:else if charJsonInput}
              <span class="text-[10px] font-mono text-error font-medium">✗ {charJsonParseError}</span>
            {/if}
          </div>
          <div class="flex-1 flex rounded-b-xl border-x border-b border-base-content/10 overflow-hidden bg-base-300/60">
            <div bind:this={lineNumbersEl} class="select-none text-right font-mono text-xs leading-relaxed py-3 px-2.5 text-base-content/20 border-r border-base-content/10 overflow-hidden shrink-0" aria-hidden="true">
              {#each Array(lineCount) as _, i}
                <span class="block">{i + 1}</span>
              {/each}
            </div>
            <textarea
              bind:this={jsonEditorRef}
              bind:value={charJsonInput}
              onscroll={syncJsonScroll}
              spellcheck="false"
              placeholder="{`{\n  \"id\": \"...\",\n  \"name\": \"...\",\n  ...\n}`}"
              class="flex-1 font-mono text-xs leading-relaxed p-3 resize-none outline-none bg-transparent text-base-content/70 placeholder:text-base-content/15 min-h-0"
            ></textarea>
          </div>
        {/if}
      </div>
      <div class="w-96 flex flex-col min-h-0 min-w-0 shrink-0">
        <div class="flex items-center gap-2 px-3 py-2 border-b border-base-content/10 bg-base-200/60 backdrop-blur-sm rounded-t-xl shrink-0">
          <span class="text-[10px] font-mono text-base-content/30 font-medium uppercase tracking-wider">preview</span>
          <span class="text-[10px] font-mono text-base-content/20">·</span>
          <span class="text-[10px] font-mono text-base-content/25 truncate">{selectedAltObj?.name ?? displayCharData.name}</span>
        </div>
        <div class="flex-1 overflow-y-auto rounded-b-xl border-x border-b border-base-content/10 bg-base-300/60 scrollbar-thin">
          <div class="rounded-xl bg-base-200/40 border border-base-content/10 overflow-hidden m-3 shadow-sm">
            <div class="w-full h-80 relative bg-base-300/50 group/image">
              {#if displayCharData.manwhaImage || charSelectedAlt}
                <img
                  src={altManwhaImage ?? mainManwhaImage}
                  alt={selectedAltObj?.name ?? displayCharData.name}
                  class="absolute inset-0 w-full h-full object-cover object-top transition-opacity duration-300 pointer-events-none {charMode === 'manwha' ? 'opacity-100' : 'opacity-0'}"
                  style="object-position: center 15%;"
                  loading="lazy"
                  onerror={(e) => imgErrorFallback(e, selectedAltObj?.manwhaImage ?? displayCharData.manwhaImage ?? '')}
                />
                <button onclick={() => replaceCharImage(selectedAltObj?.manwhaImage ?? displayCharData.manwhaImage ?? '')} title="Replace image" class="absolute top-2 left-2 text-base-content/40 hover:text-base-content bg-base-300/80 hover:bg-base-300 backdrop-blur-sm rounded-xl p-1.5 transition-all opacity-0 group-hover/image:opacity-100 active:scale-95 {charMode === 'manwha' ? '' : 'hidden'}">
                  <Icon icon="mdi:camera-replace-outline" class="size-3.5" />
                </button>
              {/if}
              {#if displayCharData.webnovelImage || charSelectedAlt}
                <img
                  src={altWebnovelImage ?? mainWebnovelImage}
                  alt={selectedAltObj?.name ?? displayCharData.name}
                  class="absolute inset-0 w-full h-full object-cover object-top transition-opacity duration-300 pointer-events-none {charMode === 'webnovel' || !displayCharData.manwhaImage ? 'opacity-100' : 'opacity-0'}"
                  style="object-position: center 15%;"
                  loading="lazy"
                  onerror={(e) => imgErrorFallback(e, selectedAltObj?.webnovelImage ?? displayCharData.webnovelImage ?? '')}
                />
                <button onclick={() => replaceCharImage(selectedAltObj?.webnovelImage ?? displayCharData.webnovelImage ?? '')} title="Replace image" class="absolute top-2 right-2 text-base-content/40 hover:text-base-content bg-base-300/80 hover:bg-base-300 backdrop-blur-sm rounded-xl p-1.5 transition-all opacity-0 group-hover/image:opacity-100 active:scale-95 {charMode === 'webnovel' || !displayCharData.manwhaImage ? '' : 'hidden'}">
                  <Icon icon="mdi:camera-replace-outline" class="size-3.5" />
                </button>
              {/if}
              {#if !displayCharData.manwhaImage && !displayCharData.webnovelImage && !charSelectedAlt}
                <div class="absolute inset-0 flex items-center justify-center">
                  <Icon icon="material-symbols:person-off-rounded" class="size-12 opacity-20" />
                </div>
              {/if}
            </div>
            <div class="p-4 pb-2">
              <h3 class="font-bold text-base">{selectedAltObj?.name ?? displayCharData.name}</h3>
            </div>
            <div class="px-4 pb-2">
              <div class="join w-full">
                <button
                  class="join-item btn btn-xs flex-1 {displayCharData.manwhaImage ? (charMode === 'manwha' ? 'btn-primary' : 'btn-ghost bg-base-200') : 'btn-ghost bg-base-200 opacity-30 cursor-not-allowed'}"
                  onclick={() => { if (displayCharData.manwhaImage) charCardModes[displayCharData.id] = 'manwha'; }}
                >Manwha</button>
                <button
                  class="join-item btn btn-xs flex-1 {charMode === 'webnovel' ? 'btn-primary' : 'btn-ghost bg-base-200'} {!displayCharData.webnovelImage ? 'opacity-30 cursor-not-allowed line-through' : ''}"
                  onclick={() => { if (displayCharData.webnovelImage) charCardModes[displayCharData.id] = 'webnovel'; }}
                >Webnovel</button>
              </div>
            </div>
            <div class="px-4 pt-2 pb-4 text-xs space-y-1.5 text-base-content">
              <div class="flex justify-between">
                <span class="font-medium">First Appearance</span>
                <span>{selectedAltObj?.chapter ? 'CH ' + selectedAltObj.chapter : displayCharData.firstAppearance ? 'CH ' + displayCharData.firstAppearance : '■■'}</span>
              </div>
              <div class="flex justify-between">
                <span class="font-medium">Alias</span>
                <span>{displayCharData.alias || '■■'}</span>
              </div>
              <div class="flex justify-between">
                <span class="font-medium">Birthday</span>
                <span>{displayCharData.birthday || '■■'}</span>
              </div>
            </div>
            {#if displayCharData.alts && displayCharData.alts.length > 0}
              <div class="border-t border-base-content/10">
                <div class="px-4 pt-3 pb-1.5">
                  <div class="text-[10px] font-mono text-base-content/30 font-medium uppercase tracking-wider">Alts</div>
                </div>
                <div class="max-h-48 overflow-y-auto px-4 pb-3 space-y-1 scrollbar-thin">
                  {#each displayCharData.alts as alt}
                    <button
                      class="block w-full text-left text-sm px-3 py-2 rounded-xl active:scale-[0.98] transition-all {charSelectedAlt === alt.id ? 'bg-warning/20 text-warning border border-warning/30 shadow-sm' : 'bg-base-300/60 text-base-content/70 border border-base-content/10 hover:border-warning/30 hover:text-base-content'}"
                      onclick={() => charSelectedAlt = charSelectedAlt === alt.id ? null : alt.id}
                    >{alt.name}</button>
                  {/each}
                </div>
              </div>
            {/if}
          </div>
        </div>
      </div>
    {:else}
      <div class="flex-1 flex flex-col min-h-0 min-w-0">
        {#if selectedIsImage && charSelectedImageUrl}
          <div class="flex items-center gap-2 px-3 py-2 border-b border-base-content/10 bg-base-200/60 backdrop-blur-sm rounded-t-xl shrink-0">
            <span class="text-[10px] font-mono text-base-content/30 font-medium uppercase tracking-wider">image preview</span>
            <span class="text-[10px] font-mono text-base-content/20">·</span>
            <span class="text-[10px] font-mono text-base-content/25 truncate">{charSelectedFile}</span>
            <div class="ml-auto flex gap-0.5">
              <button onclick={() => replaceCharImage(charSelectedFile!)} class="text-base-content/40 hover:text-base-content active:scale-95 transition-all p-1.5 rounded-xl hover:bg-base-content/5" title="Replace image">
                <Icon icon="mdi:camera-replace-outline" class="size-3.5" />
              </button>
              {#if cachedCharImages.has(charSelectedFile!)}
                <button onclick={() => revertCachedImage(charSelectedFile!)} class="text-success/50 hover:text-success active:scale-95 transition-all p-1.5 rounded-xl hover:bg-base-content/5" title="Revert to source">
                  <Icon icon="mdi:undo-variant" class="size-3.5" />
                </button>
                <button onclick={() => deleteCachedImage(charSelectedFile!)} class="text-base-content/40 hover:text-error active:scale-95 transition-all p-1.5 rounded-xl hover:bg-base-content/5" title="Delete cached image">
                  <Icon icon="mdi:delete-outline" class="size-3.5" />
                </button>
              {/if}
            </div>
          </div>
          <div class="flex-1 flex items-center justify-center rounded-b-xl border-x border-b border-base-content/10 bg-base-300/60 p-4">
            <img src={charSelectedImageUrl} alt={charSelectedFile} class="max-w-full max-h-full object-contain rounded-lg shadow-sm" onerror={(e) => { const img = e.target as HTMLImageElement; if (!img.dataset.fallback) { img.dataset.fallback = '1'; img.src = `https://raw.githubusercontent.com/${REPO}/${BRANCH}/images/gsgw/references/${charExplorerPath.join('/')}/${charSelectedFile}`; } else { img.style.display = 'none'; } }} />
          </div>
        {:else}
          <div class="flex items-center justify-between px-3 py-2 border-b border-base-content/10 bg-base-200/60 backdrop-blur-sm rounded-t-xl shrink-0">
            <span class="text-[10px] font-mono text-base-content/30 font-medium uppercase tracking-wider">character.json</span>
          </div>
          <div class="flex-1 flex items-center justify-center rounded-b-xl border-x border-b border-base-content/10 bg-base-300/60">
            <p class="text-xs text-base-content/40">select a character folder</p>
          </div>
        {/if}
      </div>
      <div class="w-96 flex flex-col min-h-0 min-w-0 shrink-0">
        <div class="flex items-center gap-2 px-3 py-2 border-b border-base-content/10 bg-base-200/60 backdrop-blur-sm rounded-t-xl shrink-0">
          <span class="text-[10px] font-mono text-base-content/30 font-medium uppercase tracking-wider">preview</span>
        </div>
        <div class="flex-1 flex items-center justify-center rounded-b-xl border-x border-b border-base-content/10 bg-base-300/60">
          <p class="text-xs text-base-content/40">no character</p>
        </div>
      </div>
    {/if}
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
      <div class="flex-1 min-h-0 px-3 pb-3 pt-3">
        <div class="h-full flex flex-col bg-base-200/80 backdrop-blur-sm rounded-xl border border-base-content/10 shadow-lg overflow-hidden">
          {#if charExplorerPath.length === 0}
            <div class="p-2 border-b border-base-content/10 flex items-center justify-between">
              <span class="text-[10px] font-mono text-base-content/30 font-medium uppercase tracking-wider">folders</span>
              <button onclick={refreshCharacters} disabled={charactersRefreshing} class="text-base-content/40 hover:text-base-content active:scale-95 transition-all p-1.5 rounded-xl hover:bg-base-content/5 disabled:text-base-content/15 disabled:hover:bg-transparent disabled:active:scale-100 disabled:cursor-not-allowed" title="Fetch source">
                <Icon icon={charactersRefreshing ? "mdi:loading" : "mdi:refresh"} class="size-3.5 {charactersRefreshing ? 'animate-spin' : ''}" />
              </button>
            </div>
            <div class="flex-1 overflow-y-auto p-2 min-h-0 space-y-0.5 scrollbar-thin">
              {#if charactersLoading}
                <div class="flex items-center justify-center py-6"><Icon icon="mdi:loading" class="size-4 text-base-content/50 animate-spin" /></div>
              {:else if charactersError}
                <p class="text-xs text-error/70 text-center py-6">{charactersError}</p>
              {:else if characters.length === 0}
                <p class="text-xs text-base-content/40 text-center py-6">no characters</p>
              {:else}
              {#each characters as char}
                <button onclick={() => { enterCharFolder(char.name); showMobileMenu = false; }} class="flex items-center gap-2.5 w-full text-left text-xs px-3 py-2.5 rounded-xl active:scale-[0.98] transition-all text-base-content/70 hover:bg-base-content/5">
                  <Icon icon="mdi:folder-outline" class="size-4 shrink-0" />
                  <span class="truncate">{char.name}</span>
                </button>
              {/each}
            {/if}
          </div>
        {:else}
          <div class="p-1.5 border-b border-base-content/10">
            <button onclick={() => { goBackOneFolder(); }} class="flex items-center gap-1.5 w-full text-left text-xs px-2.5 py-2 rounded-xl active:scale-[0.98] transition-all text-base-content/50 hover:text-base-content hover:bg-base-content/5">
              <Icon icon="mdi:arrow-left" class="size-3.5" />
              <span class="text-[10px]">..</span>
            </button>
          </div>
          <div class="flex-1 overflow-y-auto p-2 min-h-0 space-y-0.5 scrollbar-thin">
              {#each charFolderFiles.filter(f => f === "character.json") as f}
                <button onclick={() => { selectCharFile(f); showMobileMenu = false; }} class="flex items-center gap-2.5 w-full text-left text-xs px-3 py-2.5 rounded-xl active:scale-[0.98] transition-all {charSelectedFile === f ? 'bg-primary/10 text-primary shadow-sm' : 'text-base-content/70 hover:bg-base-content/5'}">
                  <Icon icon="mdi:code-json" class="size-4 shrink-0" />
                  <span class="truncate">{f}</span>
                  {#if charFolderHasLocalEdits}<span class="text-success/70 text-[10px] font-mono ml-auto">●</span>{/if}
                </button>
              {/each}
              {#if charFolderFiles.filter(f => f !== "character.json").length > 0}
                <div class="mx-1 my-1.5 border-t border-base-content/10"></div>
                {#each charFolderFiles.filter(f => f !== "character.json") as f}
                  <button onclick={() => { selectCharFile(f); showMobileMenu = false; }} class="flex items-center gap-2.5 w-full text-left text-xs px-3 py-2.5 rounded-xl active:scale-[0.98] transition-all {charSelectedFile === f ? 'bg-primary/10 text-primary shadow-sm' : 'text-base-content/70 hover:bg-base-content/5'}">
                    <Icon icon={f.match(/\.(png|jpg|jpeg|webp|avif)$/i) ? 'mdi:image-outline' : 'mdi:file-document-outline'} class="size-4 shrink-0" />
                    <span class="truncate">{f}</span>
                    {#if cachedCharImages.has(f)}<span class="text-success/70 text-[10px] font-mono ml-auto">●</span>{/if}
                  </button>
                {/each}
              {/if}
            </div>
          {/if}
        </div>
      </div>
    </div>
  </div>
{/if}

<!-- ===== FOOTER ===== -->
<div class="flex items-center justify-between px-4 py-2 border-t border-base-content/10 bg-base-200/40 backdrop-blur-sm shrink-0">
  <span class="text-[10px] font-mono text-base-content/30">{currentBook} / characters</span>
  <div class="flex items-center gap-3">
    {#if charExplorerPath.length > 0}
      <a
        href="https://github.com/{REPO}/tree/{BRANCH}/images/gsgw/references/{charExplorerPath.join('/')}"
        target="_blank"
        class="text-[10px] font-mono text-base-content/35 hover:text-primary active:scale-[0.97] transition-all"
      >↗ {charExplorerPath[charExplorerPath.length - 1]}</a>
    {:else}
      <span class="text-[10px] font-mono text-base-content/25">no folder</span>
    {/if}
  </div>
</div>
</div>
