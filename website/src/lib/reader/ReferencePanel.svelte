<script lang="ts">
  import Icon from "@iconify/svelte";
  import { browser } from "$app/environment";
  import { readerState } from "$lib/reader.svelte";
  import charactersData from "$lib/reader/characters.json";

  interface Alt {
    id: string;
    name: string;
    chapter: number | null;
    toggleable: boolean;
    manwhaImage: string | null;
    webnovelImage: string | null;
  }

  interface Character {
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

  const allCharacters = charactersData as Character[];

  let { currentChapter = 0 } = $props();

  let refTab = $state("characters");

  let charModes = $state<Record<string, string>>({});
  let altStates = $state<Record<string, string | null>>({});
  let spoilerStates = $state<Record<string, "covered" | "peek" | "revealed">>({});
  let spoilerTimers: Record<string, ReturnType<typeof setTimeout>> = {};
  let spoilerDisabled = $state(false);
  let discoveryDisabled = $state(false);
  let spoilerDialog = $state<HTMLDialogElement | null>(null);
  let colorDialog = $state<HTMLDialogElement | null>(null);
  let pinned = $state(false);
  let hoverToggles = $state<Record<string, boolean>>({});
  let darkCards = $state(false);

  let factionColors = $state<Record<string, string>>({
    daydream: "#ffffff",
    bureau: "#d0d8ff",
    ghost: "#000000",
  });

  if (browser) {
    const saved = localStorage.getItem("refSettings");
    if (saved) {
      const parsed = JSON.parse(saved);
      spoilerDisabled = parsed.spoilerDisabled ?? false;
      discoveryDisabled = parsed.discoveryDisabled ?? false;
      darkCards = parsed.darkCards ?? false;
      pinned = parsed.pinned ?? false;
      refTab = parsed.refTab ?? "characters";
      charModes = parsed.charModes ?? {};
      factionColors = parsed.factionColors ?? { daydream: "#ffffff", bureau: "#d0d8ff", ghost: "#000000" };
    }
  }

  $effect(() => {
    if (browser) {
      localStorage.setItem("refSettings", JSON.stringify({
        spoilerDisabled,
        discoveryDisabled,
        darkCards,
        pinned,
        refTab,
        charModes,
        factionColors,
      }));
    }
  });

  const factions = [
    { id: "daydream", label: "daydream inc" },
    { id: "bureau", label: "disaster management bureau" },
    { id: "ghost", label: "ghost stories" },
  ] as const;

  let linkedFaction = $state<string | null>(null);

  let hue = $state(0);
  let sat = $state(100);
  let light = $state(50);

  const defaults: Record<string, string> = { daydream: "#ffffff", bureau: "#d0d8ff", ghost: "#000000" };

  function cardBg(faction: string): string | undefined {
    if (darkCards) return undefined;
    const custom = factionColors[faction];
    if (custom && custom !== defaults[faction]) return custom;
    return undefined;
  }

  function isLight(hex: string): boolean {
    hex = hex.replace("#", "");
    const r = parseInt(hex.slice(0, 2), 16);
    const g = parseInt(hex.slice(2, 4), 16);
    const b = parseInt(hex.slice(4, 6), 16);
    return (r * 299 + g * 587 + b * 114) / 1000 > 140;
  }

  function cardTextClass(faction: string): string {
    const custom = factionColors[faction];
    if (!darkCards && custom && custom !== defaults[faction]) {
      return isLight(custom) ? '' : 'custom-text-light';
    }
    return '';
  }

  let pickerColor = $state("#ff0000");

  function hslToHex(h: number, s: number, l: number): string {
    s /= 100;
    l /= 100;
    const a = s * Math.min(l, 1 - l);
    const f = (n: number) => {
      const k = (n + h / 30) % 12;
      return Math.round(255 * (l - a * Math.max(Math.min(k - 3, 9 - k, 1), -1)));
    };
    return "#" + [f(0), f(8), f(4)].map(v => v.toString(16).padStart(2, "0")).join("");
  }

  function hexToHsl(hex: string): [number, number, number] {
    hex = hex.replace("#", "");
    const r = parseInt(hex.slice(0, 2), 16) / 255;
    const g = parseInt(hex.slice(2, 4), 16) / 255;
    const b = parseInt(hex.slice(4, 6), 16) / 255;
    const max = Math.max(r, g, b), min = Math.min(r, g, b);
    let h = 0, s = 0, l = (max + min) / 2;
    if (max !== min) {
      const d = max - min;
      s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
      switch (max) {
        case r: h = ((g - b) / d + (g < b ? 6 : 0)) * 60; break;
        case g: h = ((b - r) / d + 2) * 60; break;
        case b: h = ((r - g) / d + 4) * 60; break;
      }
    }
    return [Math.round(h), Math.round(s * 100), Math.round(l * 100)];
  }

  function updatePickerFromHsl() {
    pickerColor = hslToHex(hue, sat, light);
  }

  function handleSvDrag(e: { clientX: number; clientY: number }, rect: DOMRect) {
    sat = Math.round(((e.clientX - rect.left) / rect.width) * 100);
    light = Math.round(100 - ((e.clientY - rect.top) / rect.height) * 100);
    sat = Math.max(0, Math.min(100, sat));
    light = Math.max(0, Math.min(100, light));
    updatePickerFromHsl();
    if (linkedFaction) {
      factionColors[linkedFaction] = pickerColor;
    }
  }

  function handleHueDrag(e: { clientX: number }, rect: DOMRect) {
    hue = Math.round(((e.clientX - rect.left) / rect.width) * 360);
    hue = Math.max(0, Math.min(360, hue));
    updatePickerFromHsl();
    if (linkedFaction) {
      factionColors[linkedFaction] = pickerColor;
    }
  }

  let svRect = $state<DOMRect | null>(null);
  let hueRect = $state<DOMRect | null>(null);
  let dragging = $state(false);

  function startSvDrag(e: MouseEvent | TouchEvent) {
    e.preventDefault();
    const el = e.currentTarget as HTMLElement;
    svRect = el.getBoundingClientRect();
    dragging = true;
    const pos = "touches" in e ? e.touches[0] : e;
    handleSvDrag(pos, svRect);
  }

  function startHueDrag(e: MouseEvent | TouchEvent) {
    e.preventDefault();
    const el = e.currentTarget as HTMLElement;
    hueRect = el.getBoundingClientRect();
    dragging = true;
    const pos = "touches" in e ? e.touches[0] : e;
    handleHueDrag(pos, hueRect);
  }

  function onGlobalMove(e: globalThis.MouseEvent | globalThis.TouchEvent) {
    if (!dragging) return;
    const pos = "touches" in e ? e.touches[0] : e;
    if (svRect) handleSvDrag(pos, svRect);
    if (hueRect) handleHueDrag(pos, hueRect);
  }

  function onGlobalUp() {
    dragging = false;
    svRect = null;
    hueRect = null;
  }

  function clickSpoiler(id: string) {
    const s = spoilerStates[id] ?? "covered";
    if (s === "covered") {
      spoilerStates[id] = "peek";
      clearTimeout(spoilerTimers[id]);
      spoilerTimers[id] = setTimeout(() => { spoilerStates[id] = "covered"; }, 6000);
    } else if (s === "peek") {
      spoilerStates[id] = "revealed";
      clearTimeout(spoilerTimers[id]);
    }
  }

  function spoilerClass(id: string): string {
    const s = spoilerStates[id] ?? "covered";
    if (s === "covered") return "bg-neutral";
    if (s === "peek") return "bg-neutral/85 backdrop-blur-sm cursor-pointer";
    return "pointer-events-none";
  }

  function spoilerText(id: string): string {
    const s = spoilerStates[id] ?? "covered";
    if (s === "covered") return "Click to peek";
    if (s === "peek") return "Click to reveal";
    return "";
  }

  function getActiveAlt(ch: Character): Alt | null {
    const manual = altStates[ch.id];
    if (manual === null) return null;
    if (manual) {
      const found = ch.alts.find(a => a.id === manual);
      if (found) return found;
    }
    const eligible = ch.alts.filter(a => a.chapter != null && a.chapter <= currentChapter);
    if (eligible.length > 0) return eligible[eligible.length - 1];
    return null;
  }

  function cycleAlt(ch: Character) {
    const current = getActiveAlt(ch);
    const eligible = ch.alts.filter(a => a.chapter != null && a.chapter <= currentChapter);
    const available = eligible.length > 0 ? eligible : ch.alts;
    if (available.length === 0) return;

    const pos = current ? available.findIndex(a => a.id === current.id) + 1 : 0;
    const nextPos = (pos + 1) % (available.length + 1);

    altStates[ch.id] = nextPos === 0 ? null : available[nextPos - 1].id;
  }

  const revealedCharacters = $derived(
    discoveryDisabled
      ? allCharacters.filter(ch => ch.firstAppearance != null)
      : allCharacters.filter(ch => ch.firstAppearance != null && ch.firstAppearance <= currentChapter)
  );
</script>

{#if readerState.refPanelOpen}
  <div class="fixed inset-0 z-50 backdrop-blur-[2px] sm:backdrop-blur-none" class:sm:hidden={pinned} onclick={() => readerState.refPanelOpen = false}></div>
{/if}
<div
  class="fixed top-0 right-0 z-50 h-dvh w-80 sm:w-96 bg-base-100 shadow-2xl border-l border-base-content/10 rounded-l-2xl transition-transform duration-300 ease-out"
  class:translate-x-0={readerState.refPanelOpen}
  class:translate-x-full={!readerState.refPanelOpen}
  style="overflow-y: auto; scrollbar-width: none; -ms-overflow-style: none;"
>
  <div class="sticky top-0 z-20 bg-base-100/95 backdrop-blur flex items-center px-4 pt-2.5 pb-1.5 border-b border-base-content/10 relative">
    <h2 class="font-bold text-lg text-primary">Reference</h2>
    <span class="flex-1"></span>
    <div class="tooltip tooltip-bottom" data-tip="Reference Settings">
      <button class="btn btn-sm btn-circle btn-ghost opacity-50 hover:opacity-100" onclick={() => spoilerDialog?.showModal()} aria-label="Reference Settings">
        <Icon icon="material-symbols:settings-outline-rounded" class="size-5" />
      </button>
    </div>
    <button
      class="btn btn-sm btn-circle btn-ghost opacity-50 hover:opacity-100 max-sm:hidden {pinned ? 'text-primary opacity-100' : ''}"
      onclick={() => pinned = !pinned}
      aria-label={pinned ? 'Unpin panel' : 'Pin panel'}
    >
      <Icon icon={pinned ? "material-symbols:keep" : "material-symbols:keep-off-outline"} class="size-5" />
    </button>
  </div>
  <div class="flex flex-col gap-3 p-4">
    {#if refTab === 'characters'}
      <p class="text-[10px] opacity-40 text-center leading-tight">
        <a href="https://gsgw.miraheze.org/wiki/GDCG_Wiki" target="_blank" rel="noopener noreferrer" class="no-underline hover:opacity-60 transition-opacity">all information used for the reference tab is sourced from the wiki</a>
      </p>
    {/if}
    <div class="join w-full">
      <button class="join-item btn btn-sm flex-1 {refTab === 'characters' ? 'btn-primary' : 'btn-ghost bg-base-200'}" onclick={() => refTab = 'characters'}>Characters</button>
      <button class="join-item btn btn-sm flex-1 cursor-not-allowed {refTab === 'ghost stories' ? 'btn-primary line-through' : 'btn-ghost bg-base-200 line-through opacity-50'}" onclick={() => {}}>Ghost Stories</button>
      <button class="join-item btn btn-sm flex-1 cursor-not-allowed {refTab === 'information' ? 'btn-primary line-through' : 'btn-ghost bg-base-200 line-through opacity-50'}" onclick={() => {}}>Information</button>
    </div>

    <div>
      {#if refTab === 'characters'}
        <div class="flex flex-col gap-4">
          {#if revealedCharacters.length === 0}
            <div class="rounded-xl bg-base-200/40 border border-base-content/10 overflow-hidden">
              <div class="w-full h-48 relative bg-base-300/50 flex items-center justify-center">
                <div class="text-center px-6">
                  <Icon icon="material-symbols:search-rounded" class="size-8 opacity-30 mx-auto mb-2" />
                  <p class="text-xs font-medium opacity-60">Keep reading to discover more characters&hellip;</p>
                </div>
              </div>
            </div>
          {:else}
            {#each revealedCharacters as ch}
              {@const activeAlt = getActiveAlt(ch)}
              {@const manwhaSrc = activeAlt?.manwhaImage ?? ch.manwhaImage}
              {@const webnovelSrc = activeAlt?.webnovelImage ?? ch.webnovelImage}
              {@const preferred = charModes[ch.id] ?? (activeAlt ? "webnovel" : "manwha")}
              {@const mode = ((preferred === "manwha" && manwhaSrc) || (preferred === "webnovel" && webnovelSrc)) ? preferred : (webnovelSrc ? "webnovel" : "manwha")}
              {@const altName = activeAlt?.name ?? null}
              {@const altLocked = activeAlt != null && activeAlt.chapter != null && activeAlt.chapter > currentChapter}
              <div class="id-card faction-{ch.faction} {cardTextClass(ch.faction)}" class:dark-card={darkCards} style={cardBg(ch.faction) ? `background:${cardBg(ch.faction)}` : ''}>
                <div class="portrait" class:hover-toggles={hoverToggles[ch.id]} onclick={() => hoverToggles[ch.id] = !hoverToggles[ch.id]}>
                  {#if manwhaSrc}
                    <img
                      src={'/characters/' + manwhaSrc}
                      alt={ch.name}
                      class:active={mode === 'manwha'}
                      loading="lazy"
                      onerror={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
                    />
                  {/if}
                  {#if webnovelSrc}
                    <img
                      src={'/characters/' + webnovelSrc}
                      alt={ch.name}
                      class:active={mode === 'webnovel' || !manwhaSrc}
                      loading="lazy"
                      onerror={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
                    />
                  {/if}
                  {#if !manwhaSrc && !webnovelSrc}
                    <div class="no-image">
                      <Icon icon="material-symbols:person-off-rounded" class="size-12 opacity-20" />
                    </div>
                  {/if}
                  {#if !spoilerDisabled && altLocked}
                    <div
                      class="spoiler-overlay {spoilerClass(ch.id)}"
                      onclick={() => clickSpoiler(ch.id)}
                      role="button"
                      tabindex="0"
                      onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); clickSpoiler(ch.id); } }}
                    >
                      <span>{spoilerText(ch.id)}</span>
                    </div>
                  {/if}
                  <div class="toggles">
                    <button
                      class:toggle-active={mode === 'manwha'}
                      class:toggle-disabled={!manwhaSrc}
                      onclick={() => { if (manwhaSrc) charModes[ch.id] = 'manwha'; }}
                    >Manwha</button>
                    <button
                      class:toggle-active={mode === 'webnovel'}
                      class:toggle-disabled={!webnovelSrc}
                      onclick={() => { if (webnovelSrc) charModes[ch.id] = 'webnovel'; }}
                    >Webnovel</button>
                  </div>
                </div>
                {#if ch.alts.length > 0}
                  <button
                    class="alt-btn"
                    onclick={() => cycleAlt(ch)}
                    aria-label="Swap illustration"
                  >
                    <Icon icon="material-symbols:sync-alt-rounded" class="size-4" />
                  </button>
                {/if}
                <div class="info">
                  <h3 class="name">{altName ?? ch.name}</h3>
                  <button type="button" class="blood-type">{ch.alias}</button>
                  <div class="meta-footer">
                    <span class="meta-item">
                      <Icon icon="material-symbols:auto-stories-outline-rounded" class="size-3.5 opacity-60" />
                      <span class="meta-value">CH {activeAlt?.chapter ?? ch.firstAppearance ?? '■■'}</span>
                    </span>
                    <span class="meta-item">
                      <span class="meta-value">{ch.birthday}</span>
                      <Icon icon="material-symbols:celebration-outline-rounded" class="size-3.5 opacity-60" />
                    </span>
                  </div>
                </div>
              </div>
            {/each}
            {#if !discoveryDisabled && allCharacters.some(ch => ch.firstAppearance == null || ch.firstAppearance > currentChapter)}
              <div class="rounded-xl bg-base-200/40 border border-base-content/10 overflow-hidden">
                <div class="w-full h-36 relative bg-base-300/50 flex items-center justify-center">
                  <div class="text-center px-6">
                    <Icon icon="material-symbols:search-rounded" class="size-7 opacity-30 mx-auto mb-1.5" />
                    <p class="text-xs font-medium opacity-60">Keep reading to discover more characters&hellip;</p>
                  </div>
                </div>
              </div>
            {/if}
          {/if}
        </div>
      {:else if refTab === 'ghost stories'}
        <p class="text-sm opacity-50 py-8 text-center">Ghost stories coming soon...</p>
      {:else}
        <p class="text-sm opacity-50 py-8 text-center">Information coming soon...</p>
      {/if}
    </div>
  </div>
</div>

<dialog bind:this={spoilerDialog} class="modal">
  <div class="modal-box">
    <form method="dialog">
      <button class="btn btn-sm btn-circle btn-ghost absolute right-2 top-2">
        <Icon icon="material-symbols:close-rounded" class="size-5" />
      </button>
    </form>
    <h3 class="font-bold text-lg mb-4">Reference Settings</h3>
    <div class="rounded-xl bg-base-200 border border-base-content/10 p-3 space-y-4">
      <label class="flex items-start justify-between cursor-pointer gap-3">
        <div class="flex flex-col gap-0.5">
          <span class="text-sm font-medium">Show full spoilers</span>
          <span class="text-xs opacity-50">disable the spoiler warning when seeing alts</span>
        </div>
        <input type="checkbox" class="toggle toggle-sm shrink-0 self-center" bind:checked={spoilerDisabled} />
      </label>
      <label class="flex items-start justify-between cursor-pointer gap-3">
        <div class="flex flex-col gap-0.5">
          <span class="text-sm font-medium">Disable discovery</span>
          <span class="text-xs opacity-50">show characters regardless of chapter number</span>
        </div>
        <input type="checkbox" class="toggle toggle-sm shrink-0 self-center" bind:checked={discoveryDisabled} />
      </label>
      <label class="flex items-start justify-between cursor-pointer gap-3">
        <div class="flex flex-col gap-0.5">
          <span class="text-sm font-medium">Dark card theme</span>
          <span class="text-xs opacity-50">use pre-set character card dark themes (this takes priority over custom colors)</span>
        </div>
        <input type="checkbox" class="toggle toggle-sm shrink-0 self-center" bind:checked={darkCards} />
      </label>
    </div>
    <div class="flex items-center justify-end border-t border-base-content/10 pt-4 gap-2">
      <span class="text-xs opacity-50">pick your own card colors &rarr;</span>
      <button class="btn btn-xs btn-circle btn-ghost opacity-50 hover:opacity-100" onclick={() => { spoilerDialog?.close(); colorDialog?.showModal(); }} aria-label="Card Colors">
        <Icon icon="material-symbols:format-paint-outline-rounded" class="size-4" />
      </button>
    </div>
  <form method="dialog" class="modal-backdrop">
    <button>close</button>
  </form>
</dialog>

<dialog bind:this={colorDialog} class="modal">
  <div class="modal-box">
    <form method="dialog">
      <button class="btn btn-sm btn-circle btn-ghost absolute right-2 top-2">
        <Icon icon="material-symbols:close-rounded" class="size-5" />
      </button>
    </form>
    <h3 class="font-bold text-lg mb-3">Card Colors</h3>
    <div class="rounded-xl bg-base-200/50 border border-base-content/10 p-4">
      <div class="flex gap-6">
        <div class="flex flex-col gap-2 flex-1">
          {#each factions as f}
            <div class="flex items-center gap-3 px-3 py-2 rounded-lg {linkedFaction === f.id ? 'bg-base-content/5' : ''} transition-colors">
              <div
                class="size-6 rounded-md shrink-0 border border-base-content/10"
                style="background: {factionColors[f.id] || '#fff'}"
              ></div>
              <div class="flex flex-col min-w-0 flex-1">
                <span class="text-sm font-medium">{f.label}</span>
                <div class="flex items-center gap-1.5 mt-0.5">
                  <input
                    type="text"
                    class="input input-xs input-bordered font-mono uppercase w-22"
                    placeholder="#______"
                    maxlength={7}
                    bind:value={factionColors[f.id]}
                    oninput={() => {
                      if (linkedFaction === f.id && /^#[0-9a-f]{6}$/i.test(factionColors[f.id])) {
                        pickerColor = factionColors[f.id];
                        const [h, s, l] = hexToHsl(factionColors[f.id]);
                        hue = h; sat = s; light = l;
                      }
                    }}
                  />
                </div>
              </div>
              <div class="flex items-center gap-1">
                <button
                  class="btn btn-xs btn-circle btn-ghost opacity-50 hover:opacity-100 shrink-0 {linkedFaction === f.id ? 'text-primary opacity-100' : ''}"
                  onclick={() => {
                    linkedFaction = linkedFaction === f.id ? null : f.id;
                    if (linkedFaction === f.id) {
                      const hex = factionColors[f.id] || '#ffffff';
                      pickerColor = hex;
                      const [h, s, l] = hexToHsl(hex);
                      hue = h; sat = s; light = l;
                    }
                  }}
                  aria-label="Link to color picker"
                >
                  <Icon icon={linkedFaction === f.id ? "material-symbols:link-rounded" : "material-symbols:link-off-rounded"} class="size-4" />
                </button>
                <button
                  class="btn btn-xs btn-circle btn-ghost opacity-30 hover:opacity-100 shrink-0"
                  onclick={() => {
                    const defaults: Record<string, string> = { daydream: "#ffffff", bureau: "#d0d8ff", ghost: "#000000" };
                    factionColors[f.id] = defaults[f.id];
                    if (linkedFaction === f.id) {
                      const [h, s, l] = hexToHsl(defaults[f.id]);
                      hue = h; sat = s; light = l;
                      pickerColor = defaults[f.id];
                    }
                  }}
                  aria-label="Reset color"
                >
                  <Icon icon="material-symbols:refresh-rounded" class="size-4" />
                </button>
              </div>
            </div>
          {/each}
        </div>
        <div class="flex flex-col items-center justify-center gap-3 shrink-0 pl-4 border-l border-base-content/10">
          <div class="relative size-28 rounded-xl overflow-hidden border-2 border-base-content/10 shadow-lg cursor-crosshair touch-none" style="background: hsl({hue}, 100%, 50%)" onmousedown={startSvDrag} ontouchstart={startSvDrag}>
            <div class="absolute inset-0" style="background: linear-gradient(to right, #fff, transparent)"></div>
            <div class="absolute inset-0" style="background: linear-gradient(to top, #000, transparent)"></div>
            <div class="absolute rounded-full border-2 border-white shadow-md size-4 pointer-events-none -translate-x-1/2 -translate-y-1/2" style="left: {sat}%; top: {100 - light}%; background: {pickerColor}"></div>
          </div>
          <div class="relative w-28 h-4 rounded-full overflow-hidden border border-base-content/20 cursor-pointer touch-none" style="background: linear-gradient(to right, #f00, #ff0, #0f0, #0ff, #00f, #f0f, #f00)" onmousedown={startHueDrag} ontouchstart={startHueDrag}>
            <div class="absolute rounded-full border-2 border-white shadow-md size-4 -translate-x-1/2 -translate-y-1/2 pointer-events-none" style="left: {hue / 360 * 100}%; top: 50%; background: hsl({hue}, 100%, 50%)"></div>
          </div>
          <div class="flex items-center gap-2 text-xs font-mono uppercase bg-base-300/50 px-3 py-1 rounded-full">
            <span class="size-3 rounded-sm" style="background: {pickerColor}"></span>
            <span class="opacity-80">{pickerColor}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
  <form method="dialog" class="modal-backdrop">
    <button>close</button>
  </form>
</dialog>

<svelte:window onmousemove={onGlobalMove} onmouseup={onGlobalUp} ontouchmove={onGlobalMove} ontouchend={onGlobalUp} />

<style>
  h2, h3 {
    text-decoration: none;
  }

  .id-card {
    position: relative;
    border-radius: 24px;
    box-shadow: 0 15px 40px rgba(0,0,0,.4);
    overflow: hidden;
  }

  .id-card.faction-daydream {
    background: #fff;
    box-shadow: 0 15px 40px rgba(0,0,0,.15);
    border: 1px solid rgba(0,0,0,0.06);
  }

  .id-card.faction-bureau {
    background: #d0d8ff;
    box-shadow: 0 15px 40px rgba(0,0,0,.15);
    border: 1px solid rgba(0,0,0,0.06);
  }

  .id-card.faction-ghost {
    background: #000;
    box-shadow: 0 15px 40px rgba(0,0,0,.4);
  }

  .id-card::before {
    content: "";
    position: absolute;
    top: 12px;
    left: 50%;
    transform: translateX(-50%);
    width: 90px;
    height: 16px;
    border-radius: 999px;
    background: var(--color-base-100);
    border: 1px solid rgba(255,255,255,0.08);
    z-index: 10;
  }

  .id-card::after {
    content: "";
    position: absolute;
    top: 34px;
    left: 50%;
    transform: translateX(-50%);
    width: 44px;
    height: 44px;
    background-size: contain;
    background-position: center;
    background-repeat: no-repeat;
    z-index: 11;
  }

  .id-card.faction-daydream::after {
    background-image: url('/assets/daydream.webp');
  }

  .id-card.faction-ghost::after {
    background-image: url('/assets/ghost.webp');
  }

  .portrait {
    position: relative;
    overflow: hidden;
    border-radius: 16px;
    margin: 84px 20px 0;
    aspect-ratio: 4 / 5;
    background: #4b0909;
  }

  .faction-daydream .portrait,
  .faction-bureau .portrait {
    box-shadow: 0 0 0 1px rgba(0,0,0,0.06);
  }

  .portrait img {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
    object-position: center 15%;
    transition: opacity 0.3s;
    opacity: 0;
    pointer-events: none;
  }

  .portrait img.active {
    opacity: 1;
  }

  .no-image {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .spoiler-overlay {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.5s;
    border-radius: 0;
  }

  .spoiler-overlay span {
    font-size: 0.75rem;
    font-weight: 500;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    pointer-events: none;
  }

  .alt-btn {
    position: absolute;
    top: 12px;
    right: 12px;
    z-index: 15;
    width: 28px;
    height: 28px;
    border-radius: 50%;
    border: none;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    opacity: 0.6;
    transition: opacity 0.2s;
  }

  .faction-daydream .alt-btn,
  .faction-bureau .alt-btn {
    background: rgba(0,0,0,.08);
    backdrop-filter: blur(4px);
  }

  .faction-ghost .alt-btn {
    background: rgba(255,255,255,.15);
    backdrop-filter: blur(4px);
  }

  .alt-btn:hover {
    opacity: 1;
  }

  .info {
    padding: 6px 16px 10px;
    text-align: center;
  }

  .name {
    font-size: 1.7rem;
    font-weight: 900;
    margin: -2px 0 0;
    letter-spacing: -0.02em;
  }

  .faction-daydream .name {
    color: #111;
  }

  .faction-bureau .name {
    color: #111;
  }

  .faction-ghost .name {
    color: #fff;
  }

  .name::after {
    display: none;
  }

  .blood-type {
    display: block;
    font-size: 0.95rem;
    font-weight: 500;
    margin-top: -18px;
    border: none;
    background: none;
    cursor: pointer;
    width: 100%;
    position: relative;
    z-index: 1;
    transition: opacity 0.15s;
    color: #999;
  }

  .blood-type:hover {
    opacity: 0.7;
  }

  .faction-daydream .blood-type,
  .faction-bureau .blood-type {
    -webkit-text-stroke: none;
    text-stroke: none;
    color: #000;
  }

  .faction-ghost .blood-type {
    color: #fff;
  }

  .meta-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: -4px;
    padding: 2px 10px;
    border-radius: 8px;
  }

  .meta-item {
    display: flex;
    align-items: center;
    gap: 3px;
  }

  .faction-daydream .meta-item,
  .faction-bureau .meta-item {
    color: #555;
  }

  .faction-ghost .meta-item {
    color: #bbb;
  }

  .meta-label {
    font-size: 0.55rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .faction-daydream .meta-label,
  .faction-bureau .meta-label {
    color: #999;
  }

  .faction-ghost .meta-label {
    color: #aaa;
  }

  .meta-value {
    font-size: 0.7rem;
    font-weight: 700;
  }

  .faction-daydream .meta-value,
  .faction-bureau .meta-value {
    color: #333;
  }

  .faction-ghost .meta-value {
    color: #e0e0f0;
  }

  .toggles {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    display: flex;
    gap: 0;
    padding: 10px;
    justify-content: center;
    background: linear-gradient(transparent, rgba(0,0,0,0.6));
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.2s;
  }

  .portrait:hover .toggles,
  .portrait.hover-toggles .toggles {
    opacity: 1;
    pointer-events: auto;
  }

  .toggles button {
    flex: 1;
    max-width: 100px;
    padding: 3px 0;
    border: 1px solid rgba(255,255,255,0.15);
    font-size: 0.7rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
  }

  .toggles button:first-child {
    border-radius: 999px 0 0 999px;
    border-right: none;
  }

  .toggles button:last-child {
    border-radius: 0 999px 999px 0;
    border-left: none;
  }

  .faction-daydream .toggles button,
  .faction-bureau .toggles button {
    background: rgba(0,0,0,0.2);
    color: rgba(255,255,255,0.5);
  }

  .faction-daydream .toggles button.toggle-active,
  .faction-bureau .toggles button.toggle-active {
    background: rgba(255,255,255,0.25);
    color: #fff;
  }

  .faction-ghost .toggles button {
    background: rgba(255,255,255,0.08);
    color: rgba(255,255,255,0.45);
    border-color: rgba(255,255,255,0.1);
  }

  .faction-ghost .toggles button.toggle-active {
    background: rgba(255,255,255,0.2);
    color: #fff;
    border-color: rgba(255,255,255,0.2);
  }

  .toggles button.toggle-disabled {
    text-decoration: line-through;
    cursor: not-allowed;
    opacity: 0.4;
  }

  .toggles button:not(.toggle-disabled):hover {
    opacity: 0.85;
  }

  .dark-card.faction-daydream {
    background: #2a2a3e;
    border-color: rgba(255,255,255,0.08);
  }

  .dark-card.faction-bureau {
    background: #1e1e3f;
    border-color: rgba(255,255,255,0.08);
  }

  .dark-card.faction-daydream .portrait,
  .dark-card.faction-bureau .portrait {
    box-shadow: none;
  }

  .dark-card.faction-daydream .name,
  .dark-card.faction-bureau .name {
    color: #fff;
  }

  .dark-card.faction-daydream .blood-type,
  .dark-card.faction-bureau .blood-type {
    color: #fff;
  }

  .dark-card.faction-daydream .meta-label,
  .dark-card.faction-bureau .meta-label {
    color: #999;
  }

  .dark-card.faction-daydream .meta-value,
  .dark-card.faction-bureau .meta-value {
    color: #e0e0f0;
  }

  .dark-card.faction-daydream .meta-item,
  .dark-card.faction-bureau .meta-item {
    color: #bbb;
  }

  .dark-card.faction-daydream .toggles button,
  .dark-card.faction-bureau .toggles button {
    background: rgba(255,255,255,0.08);
    color: rgba(255,255,255,0.45);
    border-color: rgba(255,255,255,0.1);
  }

  .dark-card.faction-daydream .toggles button.toggle-active,
  .dark-card.faction-bureau .toggles button.toggle-active {
    background: rgba(255,255,255,0.2);
    color: #fff;
    border-color: rgba(255,255,255,0.2);
  }

  .dark-card.faction-daydream .alt-btn,
  .dark-card.faction-bureau .alt-btn {
    background: rgba(255,255,255,.15);
  }

  .custom-text-light .name {
    color: #fff;
  }

  .custom-text-light .blood-type {
    color: #fff;
  }

  .custom-text-light .meta-label {
    color: #999;
  }

  .custom-text-light .meta-value {
    color: #e0e0f0;
  }

  .custom-text-light .meta-item {
    color: #bbb;
  }

  .custom-text-light .toggles button {
    background: rgba(255,255,255,0.08);
    color: rgba(255,255,255,0.45);
    border-color: rgba(255,255,255,0.1);
  }

  .custom-text-light .toggles button.toggle-active {
    background: rgba(255,255,255,0.2);
    color: #fff;
    border-color: rgba(255,255,255,0.2);
  }

  .custom-text-light .alt-btn {
    background: rgba(255,255,255,.15);
  }
</style>