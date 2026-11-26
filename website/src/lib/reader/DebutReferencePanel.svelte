<script lang="ts">
  import Icon from "@iconify/svelte";
  import { browser } from "$app/environment";
  import { onMount } from "svelte";
  import { readerState } from "$lib/reader.svelte";
  import { debutCharacters } from "$lib/reader/debut-characters";

  let { currentChapter = 0 } = $props();
  const factionTabs = ["TeSTAR", "Side Cast"] as const;
  type DebutFaction = (typeof factionTabs)[number];
  type DebutIllustrationMode = "manwha" | "webnovel";
  const DARK_CARD_BACKGROUND = "#202332";
  const DARK_CARD_TEXT = "#f0f1f7";
  const debutGroups = [...new Set(debutCharacters.map((character) => character.group))];

  function defaultGroupColors(): Record<string, string> {
    return Object.fromEntries(debutGroups.map((group) => [group, "#ffffff"]));
  }

  function loadSettings() {
    const defaults = defaultGroupColors();
    if (!browser) return { showAllCharacters: false, darkCards: false, groupColors: defaults, selectedFaction: "TeSTAR" as DebutFaction, imageModes: {} };

    try {
      const saved = JSON.parse(localStorage.getItem("debutReferenceSettings") ?? "{}") as {
        showAllCharacters?: boolean;
        darkCards?: boolean;
        groupColors?: Record<string, unknown>;
        selectedFaction?: string;
        imageModes?: Record<string, unknown>;
      };
      const groupColors = { ...defaults };
      const imageModes: Record<string, DebutIllustrationMode> = {};
      for (const group of debutGroups) {
        const value = saved.groupColors?.[group];
        if (typeof value === "string" && /^#[0-9a-f]{6}$/i.test(value)) groupColors[group] = value;
      }
      for (const character of debutCharacters) {
        const value = saved.imageModes?.[character.id];
        if (value === "manwha" || value === "webnovel") imageModes[character.id] = value;
      }
      const savedFaction = saved.selectedFaction === "VTIC" ? "Side Cast" : saved.selectedFaction;
      const selectedFaction = factionTabs.find((faction) => faction === savedFaction) ?? "TeSTAR";
      return { showAllCharacters: saved.showAllCharacters ?? false, darkCards: saved.darkCards ?? false, groupColors, selectedFaction, imageModes };
    } catch {
      return { showAllCharacters: false, darkCards: false, groupColors: defaults, selectedFaction: "TeSTAR" as DebutFaction, imageModes: {} };
    }
  }

  let showAllCharacters = $state(false);
  let darkCards = $state(false);
  let groupColors = $state(defaultGroupColors());
  let selectedFaction = $state<DebutFaction>("TeSTAR");
  let imageModes = $state<Record<string, DebutIllustrationMode>>({});
  let settingsLoaded = $state(false);
  let settingsDialog = $state<HTMLDialogElement | null>(null);
  let colorsDialog = $state<HTMLDialogElement | null>(null);
  let altStates = $state<Record<string, string | null>>({});
  let photoControlsOpen = $state<Record<string, boolean>>({});
  let linkedGroup = $state<string | null>(null);
  let pickerColor = $state("#ffffff");
  let hue = $state(0);
  let sat = $state(0);
  let light = $state(100);
  let svRect = $state<DOMRect | null>(null);
  let hueRect = $state<DOMRect | null>(null);
  let dragging = $state(false);

  onMount(() => {
    const savedSettings = loadSettings();
    showAllCharacters = savedSettings.showAllCharacters;
    darkCards = savedSettings.darkCards;
    groupColors = savedSettings.groupColors;
    selectedFaction = savedSettings.selectedFaction;
    imageModes = savedSettings.imageModes;
    settingsLoaded = true;
  });

  $effect(() => {
    if (settingsLoaded) {
      localStorage.setItem("debutReferenceSettings", JSON.stringify({ showAllCharacters, darkCards, groupColors, selectedFaction, imageModes }));
    }
  });

  function groupTextColor(group: string): string {
    if (darkCards) return DARK_CARD_TEXT;
    const hex = validGroupColor(group);
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return (r * 299 + g * 587 + b * 114) / 1000 > 140 ? "#202938" : "#ffffff";
  }

  function validGroupColor(group: string): string {
    const value = groupColors[group];
    return typeof value === "string" && /^#[0-9a-f]{6}$/i.test(value) ? value : "#ffffff";
  }

  function cardStyle(characterId: string, group: string): string {
    const background = darkCards ? DARK_CARD_BACKGROUND : validGroupColor(group);
    return `--dod-card-bg:${background};--dod-card-text:${groupTextColor(group)};${glossStyle(characterId)}`;
  }

  function glossStyle(characterId: string): string {
    let hash = 2166136261;
    for (const character of characterId) {
      hash = Math.imul(hash ^ character.charCodeAt(0), 16777619);
    }
    const seed = hash >>> 0;
    const x = 18 + ((seed >>> 7) % 65);
    const y = 12 + ((seed >>> 14) % 74);
    return `--dod-gloss-x:${x}%;--dod-gloss-y:${y}%;`;
  }

  function resetGroupColor(group: string) {
    groupColors[group] = "#ffffff";
    if (linkedGroup === group) setPickerColor("#ffffff");
  }

  function resetAllGroupColors() {
    groupColors = defaultGroupColors();
    if (linkedGroup) setPickerColor("#ffffff");
  }

  function hslToHex(h: number, s: number, l: number): string {
    s /= 100;
    l /= 100;
    const a = s * Math.min(l, 1 - l);
    const f = (n: number) => {
      const k = (n + h / 30) % 12;
      return Math.round(255 * (l - a * Math.max(Math.min(k - 3, 9 - k, 1), -1)));
    };
    return "#" + [f(0), f(8), f(4)].map((value) => value.toString(16).padStart(2, "0")).join("");
  }

  function hexToHsl(hex: string): [number, number, number] {
    const value = hex.replace("#", "");
    const r = parseInt(value.slice(0, 2), 16) / 255;
    const g = parseInt(value.slice(2, 4), 16) / 255;
    const b = parseInt(value.slice(4, 6), 16) / 255;
    const max = Math.max(r, g, b);
    const min = Math.min(r, g, b);
    let h = 0;
    let s = 0;
    const l = (max + min) / 2;
    if (max !== min) {
      const delta = max - min;
      s = l > 0.5 ? delta / (2 - max - min) : delta / (max + min);
      switch (max) {
        case r: h = ((g - b) / delta + (g < b ? 6 : 0)) * 60; break;
        case g: h = ((b - r) / delta + 2) * 60; break;
        case b: h = ((r - g) / delta + 4) * 60; break;
      }
    }
    return [Math.round(h), Math.round(s * 100), Math.round(l * 100)];
  }

  function setPickerColor(hex: string) {
    if (!/^#[0-9a-f]{6}$/i.test(hex)) return;
    pickerColor = hex;
    [hue, sat, light] = hexToHsl(hex);
  }

  function chooseGroupForPicker(group: string) {
    linkedGroup = linkedGroup === group ? null : group;
    if (linkedGroup) setPickerColor(validGroupColor(group));
  }

  function setGroupColor(group: string, value: string) {
    groupColors[group] = value;
    if (linkedGroup === group && /^#[0-9a-f]{6}$/i.test(value)) setPickerColor(value);
  }

  function updatePickerFromHsl() {
    pickerColor = hslToHex(hue, sat, light);
    if (linkedGroup) groupColors[linkedGroup] = pickerColor;
  }

  function handleSvDrag(event: { clientX: number; clientY: number }, rect: DOMRect) {
    sat = Math.max(0, Math.min(100, Math.round(((event.clientX - rect.left) / rect.width) * 100)));
    light = Math.max(0, Math.min(100, Math.round(100 - ((event.clientY - rect.top) / rect.height) * 100)));
    updatePickerFromHsl();
  }

  function handleHueDrag(event: { clientX: number }, rect: DOMRect) {
    hue = Math.max(0, Math.min(360, Math.round(((event.clientX - rect.left) / rect.width) * 360)));
    updatePickerFromHsl();
  }

  function startSvDrag(event: MouseEvent | TouchEvent) {
    event.preventDefault();
    svRect = (event.currentTarget as HTMLElement).getBoundingClientRect();
    dragging = true;
    handleSvDrag("touches" in event ? event.touches[0] : event, svRect);
  }

  function startHueDrag(event: MouseEvent | TouchEvent) {
    event.preventDefault();
    hueRect = (event.currentTarget as HTMLElement).getBoundingClientRect();
    dragging = true;
    handleHueDrag("touches" in event ? event.touches[0] : event, hueRect);
  }

  function onGlobalMove(event: globalThis.MouseEvent | globalThis.TouchEvent) {
    if (!dragging) return;
    const position = "touches" in event ? event.touches[0] : event;
    if (svRect) handleSvDrag(position, svRect);
    if (hueRect) handleHueDrag(position, hueRect);
  }

  function onGlobalUp() {
    dragging = false;
    svRect = null;
    hueRect = null;
  }

  function togglePhotoControls(characterId: string) {
    photoControlsOpen[characterId] = !photoControlsOpen[characterId];
  }

  function closeNicknames() {
    document.querySelector<HTMLElement>(".debut-nickname-popover:popover-open")?.hidePopover();
  }

  function positionNicknames(trigger: HTMLElement, popoverId: string) {
    requestAnimationFrame(() => {
      const popover = document.getElementById(popoverId);
      if (!popover?.matches(":popover-open")) return;
      const anchor = trigger.getBoundingClientRect();
      const panel = trigger.closest("aside")!.getBoundingClientRect();
      const padding = 12;
      const gap = 10;
      const leftEdge = Math.max(0, panel.left) + padding;
      const rightEdge = Math.min(window.innerWidth, panel.right) - padding;
      const topEdge = Math.max(0, panel.top) + padding;
      const bottomEdge = Math.min(window.innerHeight, panel.bottom) - padding;
      popover.style.maxWidth = `${rightEdge - leftEdge}px`;
      popover.style.maxHeight = `${bottomEdge - topEdge}px`;
      const { width, height } = popover.getBoundingClientRect();
      const left = Math.max(leftEdge, Math.min(anchor.left + (anchor.width - width) / 2, rightEdge - width));
      const below = bottomEdge - anchor.bottom;
      const top = below >= height + gap || below >= anchor.top - topEdge
        ? anchor.bottom + gap
        : anchor.top - height - gap;
      popover.style.left = `${left}px`;
      popover.style.top = `${Math.max(topEdge, Math.min(top, bottomEdge - height))}px`;
    });
  }

  $effect(() => {
    if (!readerState.refPanelOpen) closeNicknames();
  });

  function availableAlts(character: (typeof debutCharacters)[number]) {
    return character.alts.filter((alt) => showAllCharacters || alt.firstNovelChapter == null || alt.firstNovelChapter <= currentChapter);
  }

  function cycleAlt(character: (typeof debutCharacters)[number]) {
    const alts = availableAlts(character);
    const activeId = altStates[character.id] ?? null;
    const activeIndex = alts.findIndex((alt) => alt.id === activeId);
    altStates[character.id] = alts[activeIndex + 1]?.id ?? null;
  }

  const factionCharacters = $derived(debutCharacters.filter((character) => {
    return selectedFaction === "TeSTAR" ? character.group === "TeSTAR" : character.group !== "TeSTAR";
  }));

  const visibleCharacters = $derived(
    showAllCharacters
      ? factionCharacters
      : factionCharacters.filter((character) => character.firstNovelChapter !== null && character.firstNovelChapter <= currentChapter)
  );
</script>

{#if readerState.refPanelOpen}
  <div
    class="fixed inset-0 z-50 backdrop-blur-[2px] sm:backdrop-blur-none"
    onclick={() => (readerState.refPanelOpen = false)}
    onkeydown={(event) => { if (event.key === "Escape") readerState.refPanelOpen = false; }}
    role="presentation"
  ></div>
{/if}

<aside
  class="fixed top-0 right-0 z-50 h-dvh w-80 sm:w-[30rem] bg-base-100 shadow-2xl border-l border-base-content/10 rounded-l-2xl transition-transform duration-300 ease-out"
  class:translate-x-0={readerState.refPanelOpen}
  class:translate-x-full={!readerState.refPanelOpen}
  style="overflow-y:auto;scrollbar-width:none;-ms-overflow-style:none;scroll-padding-top:6.5rem"
  aria-label="Debut or Die reference panel"
  onscroll={closeNicknames}
>
  <div class="sticky top-0 z-30 border-b border-base-content/10 relative bg-base-100">
    <div class="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-secondary/5 pointer-events-none"></div>
    <div class="relative px-5 pt-4 pb-3">
      <div class="flex items-center justify-between gap-3">
        <span class="font-bold text-lg text-primary flex items-center gap-2">
          <Icon icon="mdi:book-open-page-variant" class="size-5" /> Reference
        </span>
        <button
          class="btn btn-sm btn-circle btn-ghost opacity-60 hover:opacity-100"
          onclick={() => settingsDialog?.showModal()}
          aria-label="Reference Settings"
        >
          <Icon icon="material-symbols:settings-outline-rounded" class="size-5" />
        </button>
      </div>
      <div class="mt-3 flex gap-1.5" role="group" aria-label="Character factions">
        {#each factionTabs as faction}
          <button
            type="button"
            aria-pressed={selectedFaction === faction}
            class="flex-1 btn btn-sm rounded-xl {selectedFaction === faction ? 'btn-primary' : 'btn-ghost bg-base-200/60'}"
            onclick={() => (selectedFaction = faction)}
          >
            {faction}
          </button>
        {/each}
      </div>
    </div>
  </div>

  <div class="px-3 py-4 sm:px-6">
    {#if visibleCharacters.length === 0}
      <div class="rounded-2xl bg-base-200/40 border border-base-content/5 overflow-hidden">
        <div class="w-full h-36 relative bg-base-300/30 flex items-center justify-center">
          <div class="text-center px-6">
            <Icon icon="material-symbols:search-rounded" class="size-8 text-base-content/20 mx-auto mb-2" />
            <p class="text-xs font-medium text-base-content/40">
              {factionCharacters.length === 0 ? "No Side Cast cards yet." : "Keep reading to discover more characters…"}
            </p>
          </div>
        </div>
      </div>
    {:else}
      <div class="flex flex-col gap-8">
        {#each visibleCharacters as character}
          {@const alts = availableAlts(character)}
          {@const activeAlt = alts.find((alt) => alt.id === altStates[character.id]) ?? null}
          {@const nextAlt = alts[alts.findIndex((alt) => alt.id === activeAlt?.id) + 1] ?? null}
          {@const displayedChapter = activeAlt?.firstNovelChapter ?? character.firstNovelChapter}
          {@const displayedName = activeAlt?.name ?? character.name}
          {@const nicknames = (activeAlt ? activeAlt.nicknames : character.nicknames) ?? []}
          {@const nicknamePopoverId = `debut-nicknames-${character.id}`}
          {@const displayedBirthday = activeAlt?.birthday ?? character.birthday}
          {@const displayedMbti = (activeAlt ? activeAlt.mbti : character.mbti)?.trim() || "—"}
          {@const groupName = typeof character.group === "string" ? character.group.trim() : ""}
          {@const groupRole = typeof character.groupRole === "string" ? character.groupRole.trim() : ""}
          {@const groupRoleText = [groupName, groupRole].filter(Boolean).join(" · ") || "—"}
          {@const manwhaImage = activeAlt ? activeAlt.manwhaImage : character.manwhaImage}
          {@const webnovelImage = activeAlt ? activeAlt.webnovelImage : character.webnovelImage}
          {@const preferredImageMode = imageModes[character.id] ?? (activeAlt ? "webnovel" : "manwha")}
          {@const imageMode = preferredImageMode === "manwha" && manwhaImage ? "manwha" : preferredImageMode === "webnovel" && webnovelImage ? "webnovel" : manwhaImage ? "manwha" : "webnovel"}
          {@const displayedImage = imageMode === "manwha" ? manwhaImage : webnovelImage}
          {@const hasIllustrations = Boolean(manwhaImage || webnovelImage)}
          {@const hasPhotoControls = alts.length > 0 || hasIllustrations}
          <article
            class="debut-id-card"
            class:debut-id-card-dark={darkCards}
            class:debut-id-photo-controls-open={photoControlsOpen[character.id]}
            style={cardStyle(character.id, groupName)}
            aria-label={'ID card for ' + displayedName}
          >
            <div
              class="debut-id-rail"
              class:debut-id-rail-testar={groupName === "TeSTAR" && groupRole === "Member"}
              class:debut-id-rail-vtic={groupName === "VTIC"}
            >
              <span>{groupName ? `DEBUT OR DIE / ${groupName}` : "DEBUT OR DIE"}</span>
            </div>

            <div class="debut-id-photo-area">
              <div class="debut-id-portrait-wrap">
                <button
                  type="button"
                  class="debut-id-portrait"
                  class:debut-id-portrait-switchable={hasPhotoControls}
                  aria-label={'Show portrait controls for ' + displayedName}
                  aria-expanded={Boolean(photoControlsOpen[character.id])}
                  disabled={!hasPhotoControls}
                  onclick={() => togglePhotoControls(character.id)}
                >
                  {#if displayedImage}
                    <img src={displayedImage} alt={displayedName} loading="lazy" />
                  {:else}
                    <Icon icon="material-symbols:person-outline-rounded" class="debut-image-icon size-14" aria-hidden="true" />
                  {/if}
                </button>
                {#if alts.length > 0}
                  <button
                    type="button"
                    class="debut-id-alt-button"
                    onclick={() => cycleAlt(character)}
                    aria-label={'Switch to ' + (nextAlt?.name ?? character.name)}
                  >
                    <Icon icon="material-symbols:sync-alt-rounded" class="size-4" />
                  </button>
                {/if}
              </div>
              <div class="debut-id-barcode" aria-hidden="true"></div>
            </div>

            <div class="debut-id-info">
              <div class="debut-id-name-row">
                <div class="debut-id-name">
                  <span>NAME</span>
                  <strong role="heading" aria-level="3">
                    {#if nicknames.length > 0}
                      <button
                        type="button"
                        class="debut-nickname-trigger"
                        popovertarget={nicknamePopoverId}
                        aria-haspopup="dialog"
                        title="View nicknames"
                        onclick={(event) => positionNicknames(event.currentTarget, nicknamePopoverId)}
                      >{displayedName}</button>
                    {:else}
                      {displayedName}
                    {/if}
                  </strong>
                </div>
                {#if groupName === "TeSTAR" && groupRole === "Member"}
                  <img class="debut-id-faction-logo" src="/assets/testar-logo.png" alt="TeSTAR" />
                {:else if groupName === "VTIC"}
                  <img class="debut-id-faction-logo" src="/assets/vtic-logo.png" alt="VTIC" />
                {:else}
                  <img class="debut-id-faction-logo" src="/assets/dod-logo.png" alt="Debut or Die" />
                {/if}
              </div>
              {#if hasIllustrations}
                <div class="debut-id-image-modes" role="group" aria-label="Illustration type">
                  <button
                    type="button"
                    class:debut-id-mode-active={imageMode === "manwha"}
                    class:debut-id-mode-disabled={!manwhaImage}
                    aria-pressed={imageMode === "manwha"}
                    disabled={!manwhaImage}
                    onclick={() => (imageModes[character.id] = "manwha")}
                  >MANWHA</button>
                  <span class="debut-id-mode-separator" aria-hidden="true">·</span>
                  <button
                    type="button"
                    class:debut-id-mode-active={imageMode === "webnovel"}
                    class:debut-id-mode-disabled={!webnovelImage}
                    aria-pressed={imageMode === "webnovel"}
                    disabled={!webnovelImage}
                    onclick={() => (imageModes[character.id] = "webnovel")}
                  >WEBNOVEL</button>
                </div>
              {/if}
              <div class="debut-id-meta">
                <div>
                  <span>BIRTHDAY</span>
                  <strong>{displayedBirthday}</strong>
                </div>
                <div class="debut-id-meta-mbti">
                  <span>MBTI</span>
                  <strong>{displayedMbti}</strong>
                </div>
              </div>
              <div class="debut-id-footer">
                <div class="debut-id-role">
                  <span>GROUP / ROLE</span>
                  <strong>{groupRoleText}</strong>
                </div>
                <div class="debut-id-first-appearance">
                  <span>FIRST APPEARANCE</span>
                  <strong>{displayedChapter === null ? "—" : `Ch. ${displayedChapter}`}</strong>
                </div>
              </div>
            </div>
          </article>
          {#if nicknames.length > 0}
            <div
              id={nicknamePopoverId}
              class="debut-nickname-popover bg-base-100/95 text-base-content backdrop-blur-xl border border-base-content/10 rounded-box shadow-2xl"
              popover="auto"
              role="dialog"
              aria-labelledby={`${nicknamePopoverId}-title`}
            >
              <div class="debut-nickname-header relative border-b border-base-content/10">
                <div class="pointer-events-none absolute inset-0 bg-gradient-to-br from-primary/10 via-transparent to-secondary/5"></div>
                <div class="relative flex items-center justify-between gap-3 px-4 py-3.5">
                  <div class="flex min-w-0 items-center gap-2.5">
                    <span class="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
                      <Icon icon="material-symbols:person-outline-rounded" class="h-4 w-4" aria-hidden="true" />
                    </span>
                    <div class="min-w-0">
                      <span class="block text-[0.625rem] font-bold uppercase tracking-widest text-base-content/40">Also known as</span>
                      <strong id={`${nicknamePopoverId}-title`} class="block truncate text-sm font-bold text-primary">{displayedName}</strong>
                    </div>
                  </div>
                  <div class="flex shrink-0 items-center gap-2">
                    <span class="text-[10px] font-mono text-base-content/30">{nicknames.length} {nicknames.length === 1 ? 'alias' : 'aliases'}</span>
                    <button type="button" class="btn btn-ghost btn-sm btn-circle" popovertarget={nicknamePopoverId} popovertargetaction="hide" aria-label="Close nicknames">
                      <Icon icon="mdi:close" class="h-4 w-4" aria-hidden="true" />
                    </button>
                  </div>
                </div>
              </div>
              <div class="debut-nickname-list space-y-0.5 p-2" role="list">
                {#each nicknames as nickname}
                  <div class="rounded-xl px-3 py-2.5 text-sm leading-snug text-base-content/70 transition-colors hover:bg-base-200/60 hover:text-base-content" role="listitem">{nickname}</div>
                {/each}
              </div>
            </div>
          {/if}
        {/each}
        {#if !showAllCharacters && factionCharacters.some((character) => character.firstNovelChapter === null || character.firstNovelChapter > currentChapter)}
          <div class="debut-discovery-card">
            <Icon icon="material-symbols:search-rounded" class="size-6 text-base-content/20" aria-hidden="true" />
            <p>Keep reading to discover more characters…</p>
          </div>
        {/if}
      </div>
    {/if}
  </div>
</aside>

<dialog bind:this={settingsDialog} class="modal">
  <div class="modal-box bg-base-100 p-0 rounded-box shadow-2xl overflow-hidden">
    <div class="relative shrink-0">
      <div class="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-secondary/5 pointer-events-none"></div>
      <div class="relative flex items-center justify-between px-6 py-4 border-b border-base-content/10">
        <span class="font-bold text-lg text-primary flex items-center gap-2">
          <Icon icon="material-symbols:settings-outline-rounded" class="size-5" /> Reference Settings
        </span>
        <form method="dialog">
          <button class="btn btn-sm btn-circle btn-ghost" aria-label="Close settings">
            <Icon icon="mdi:close" class="size-4" />
          </button>
        </form>
      </div>
    </div>

    <div class="p-5">
      <label class="flex items-center justify-between gap-4 cursor-pointer p-3 rounded-xl bg-base-200/40 border border-base-content/5 hover:bg-base-200/60 transition-colors">
        <div class="flex flex-col gap-0.5">
          <span class="text-sm font-medium">Disable discovery</span>
          <span class="text-xs text-base-content/40">Show characters regardless of chapter number</span>
        </div>
        <input type="checkbox" class="toggle toggle-primary toggle-sm shrink-0" bind:checked={showAllCharacters} />
      </label>
      <label class="mt-3 flex items-center justify-between gap-4 cursor-pointer p-3 rounded-xl bg-base-200/40 border border-base-content/5 hover:bg-base-200/60 transition-colors">
        <div class="flex flex-col gap-0.5">
          <span class="text-sm font-medium">Dark ID cards</span>
          <span class="text-xs text-base-content/40">Preset dark color overrides custom group colors</span>
        </div>
        <input type="checkbox" class="toggle toggle-primary toggle-sm shrink-0" bind:checked={darkCards} />
      </label>
    </div>
    <div class="flex items-center justify-end px-6 py-4 border-t border-base-content/10 gap-2">
      <span class="text-xs text-base-content/40">Card colors &rarr;</span>
      <button
        class="btn btn-xs btn-circle btn-ghost opacity-50 hover:opacity-100"
        onclick={() => { settingsDialog?.close(); colorsDialog?.showModal(); }}
        aria-label="Card Colors"
      >
        <Icon icon="material-symbols:format-paint-outline-rounded" class="size-4" />
      </button>
    </div>
  </div>
  <form method="dialog" class="modal-backdrop"><button>close</button></form>
</dialog>

<dialog bind:this={colorsDialog} class="modal">
  <div class="modal-box w-[min(94vw,52rem)] max-w-3xl bg-base-100 p-0 rounded-box shadow-2xl overflow-hidden max-h-[90vh] flex flex-col">
    <div class="relative shrink-0">
      <div class="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-secondary/5 pointer-events-none"></div>
      <div class="relative flex items-center justify-between px-6 py-4 border-b border-base-content/10">
        <span class="font-bold text-lg text-primary flex items-center gap-2">
          <Icon icon="material-symbols:format-paint-outline-rounded" class="size-5" /> Card Colors
        </span>
        <form method="dialog">
          <button class="btn btn-sm btn-circle btn-ghost" aria-label="Close card colors">
            <Icon icon="mdi:close" class="size-4" />
          </button>
        </form>
      </div>
    </div>

    <div class="dod-color-picker-layout overflow-y-auto p-5">
      <div class="flex min-w-0 flex-col gap-2">
        <div class="flex items-center justify-between gap-3 px-1 pb-1">
          <p class="text-xs text-base-content/40">Cards are white by default.</p>
          <button class="btn btn-xs btn-ghost" onclick={resetAllGroupColors}>Reset all</button>
        </div>
        {#each debutGroups as group}
          <div class="flex items-center gap-2 rounded-xl {linkedGroup === group ? 'bg-base-content/5 ring-1 ring-primary/20' : 'bg-base-200/40 border border-base-content/5'} px-3 py-2.5 transition-all">
            <span class="size-7 shrink-0 rounded-lg border border-base-content/10 shadow-sm" style={'background:' + validGroupColor(group)}></span>
            <div class="flex min-w-0 flex-1 flex-col gap-1">
              <span class="truncate text-sm font-medium">{group}</span>
              <input
                type="text"
                class="input input-xs input-bordered w-24 rounded-lg font-mono uppercase"
                placeholder="#______"
                maxlength={7}
                value={groupColors[group] ?? "#ffffff"}
                oninput={(event) => setGroupColor(group, (event.currentTarget as HTMLInputElement).value)}
                aria-label={'Color for ' + group}
              />
            </div>
            <div class="flex shrink-0 items-center gap-0.5">
              <button
                type="button"
                class="btn btn-xs btn-circle btn-ghost shrink-0 {linkedGroup === group ? 'text-primary opacity-100' : 'opacity-40 hover:opacity-100'}"
                onclick={() => chooseGroupForPicker(group)}
                aria-label={linkedGroup === group ? 'Unlink ' + group + ' from color picker' : 'Link ' + group + ' to color picker'}
              >
                <Icon icon={linkedGroup === group ? "material-symbols:link-rounded" : "material-symbols:link-off-rounded"} class="size-4" />
              </button>
              <button
                type="button"
                class="btn btn-xs btn-circle btn-ghost shrink-0 opacity-20 hover:opacity-100"
                onclick={() => resetGroupColor(group)}
                aria-label={'Reset ' + group + ' to white'}
              >
                <Icon icon="material-symbols:refresh-rounded" class="size-4" />
              </button>
            </div>
          </div>
        {/each}
      </div>

      <div class="flex flex-col items-center justify-center gap-3 border-t border-base-content/10 pt-5 sm:border-l sm:border-t-0 sm:pl-5 sm:pt-0">
        <div class="relative size-40 sm:size-32 cursor-crosshair touch-none overflow-hidden rounded-xl border-2 border-base-content/10 shadow-lg" style={'background:hsl(' + hue + ', 100%, 50%)'} onmousedown={startSvDrag} ontouchstart={startSvDrag} role="presentation">
          <div class="absolute inset-0" style="background:linear-gradient(to right, #fff, transparent)"></div>
          <div class="absolute inset-0" style="background:linear-gradient(to top, #000, transparent)"></div>
          <div class="pointer-events-none absolute size-4 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-white shadow-md" style={'left:' + sat + '%;top:' + (100 - light) + '%;background:' + pickerColor}></div>
        </div>
        <div class="relative h-4 w-40 sm:w-32 cursor-pointer touch-none overflow-hidden rounded-full border border-base-content/20" style="background:linear-gradient(to right, #f00, #ff0, #0f0, #0ff, #00f, #f0f, #f00)" onmousedown={startHueDrag} ontouchstart={startHueDrag} role="presentation">
          <div class="pointer-events-none absolute size-4 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-white shadow-md" style={'left:' + (hue / 360 * 100) + '%;top:50%;background:hsl(' + hue + ', 100%, 50%)'}></div>
        </div>
        <div class="flex items-center gap-2 rounded-full border border-base-content/5 bg-base-200/60 px-3 py-1.5 font-mono text-xs uppercase">
          <span class="size-3 rounded-sm shadow-sm" style={'background:' + pickerColor}></span>
          <span class="opacity-80">{pickerColor}</span>
        </div>
        <p class="max-w-40 text-center text-[0.65rem] text-base-content/40">Link a group to apply the picker color.</p>
      </div>
    </div>
  </div>
  <form method="dialog" class="modal-backdrop"><button>close</button></form>
</dialog>

<svelte:window onmousemove={onGlobalMove} onmouseup={onGlobalUp} ontouchmove={onGlobalMove} ontouchend={onGlobalUp} onresize={closeNicknames} />

<style>
  .debut-nickname-trigger {
    margin: 0;
    border: 0;
    padding: 0;
    background: none;
    color: inherit;
    font: inherit;
    text-align: inherit;
    cursor: pointer;
    text-decoration: none;
    text-underline-offset: 0.2em;
  }

  .debut-nickname-trigger:hover {
    text-decoration: underline dotted color-mix(in srgb, currentColor 45%, transparent);
  }

  .debut-nickname-trigger:focus-visible {
    outline: 2px solid var(--color-primary);
    outline-offset: 4px;
    border-radius: 0.15rem;
  }

  .debut-nickname-popover {
    position: fixed;
    inset: auto;
    box-sizing: border-box;
    width: min(22rem, calc(100vw - 24px));
    max-height: min(24rem, calc(100dvh - 24px));
    margin: 0;
    overflow-y: auto;
    overscroll-behavior: contain;
  }

  .debut-nickname-list > div {
    overflow-wrap: anywhere;
  }

  .debut-id-card {
    position: relative;
    display: grid;
    width: calc(100% - 1.25rem);
    align-self: center;
    transform: scale(1.1);
    transform-origin: center;
    grid-template-columns: 1.7rem minmax(7.25rem, 32%) minmax(0, 1fr);
    min-height: 13rem;
    overflow: hidden;
    border: 1px solid color-mix(in srgb, var(--dod-card-text, #202938) 12%, transparent);
    border-radius: 0.85rem;
    background: var(--dod-card-bg, #ffffff);
    box-shadow: 0 8px 22px color-mix(in srgb, var(--color-base-content) 8%, transparent);
    color: var(--dod-card-text, #202938);
  }

  .debut-id-card-dark {
    border-color: rgba(255, 255, 255, 0.1);
    box-shadow: 0 8px 22px rgba(0, 0, 0, 0.2);
  }

  .debut-id-card-dark .debut-id-faction-logo:not([src*="testar-logo.png"]) {
    filter: brightness(0) invert(1) drop-shadow(0 2px 3px rgba(0, 0, 0, 0.18));
  }

  .debut-discovery-card {
    display: flex;
    min-height: 5.75rem;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0.45rem;
    border: 1px solid color-mix(in srgb, var(--color-base-content) 5%, transparent);
    border-radius: 1rem;
    background: color-mix(in srgb, var(--color-base-200) 40%, transparent);
    text-align: center;
  }

  .debut-discovery-card p {
    color: color-mix(in srgb, var(--color-base-content) 40%, transparent);
    font-size: 0.75rem;
    font-weight: 500;
  }

  .dod-color-picker-layout {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: 1.25rem;
  }

  @media (min-width: 640px) {
    .dod-color-picker-layout {
      grid-template-columns: minmax(0, 1fr) 9rem;
      align-items: center;
    }
  }

  .debut-id-rail {
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
    background: #242337;
    color: #fff;
    writing-mode: vertical-rl;
    transform: rotate(180deg);
  }

  .debut-id-rail-testar {
    background: linear-gradient(180deg, #8162bd 0%, #cb5ba5 52%, #f2ad73 100%);
  }

  .debut-id-rail-vtic {
    background: linear-gradient(180deg, #25243a 0%, #3c3a58 50%, #615d7b 100%);
  }

  .debut-id-rail span {
    max-height: 100%;
    padding: 0.45rem 0.2rem;
    font-size: 0.48rem;
    font-weight: 800;
    letter-spacing: 0.08em;
    text-align: center;
    text-transform: uppercase;
    white-space: nowrap;
    -webkit-text-stroke: 0.3px rgba(38, 22, 48, 0.68);
    paint-order: stroke fill;
    text-shadow: 0 1px 2px rgba(28, 18, 38, 0.5);
  }

  .debut-id-photo-area {
    position: relative;
    display: flex;
    min-width: 0;
    flex-direction: column;
    gap: 0.3rem;
    margin: 0.45rem 0.35rem 0.45rem 0.45rem;
  }

  .debut-id-portrait-wrap {
    position: relative;
    width: 100%;
    height: 10.6rem;
    min-width: 0;
    flex: none;
  }

  .debut-id-portrait {
    position: absolute;
    inset: 0;
    display: flex;
    width: 100%;
    min-width: 0;
    height: 100%;
    min-height: 0;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    overflow: hidden;
    padding: 0;
    color: inherit;
    font: inherit;
    text-align: center;
    border: 1px solid color-mix(in srgb, var(--dod-card-text, #202938) 10%, transparent);
    border-radius: 0.65rem;
    appearance: none;
    background:
      radial-gradient(ellipse at 50% 35%, color-mix(in srgb, var(--dod-card-bg, #ffffff) 80%, white), transparent 72%),
      repeating-linear-gradient(135deg, transparent 0 8px, color-mix(in srgb, var(--dod-card-text, #202938) 3%, transparent) 8px 9px),
      color-mix(in srgb, var(--dod-card-bg, #ffffff) 78%, var(--color-base-200));
  }

  .debut-id-portrait-switchable {
    cursor: pointer;
  }

  .debut-id-alt-button {
    position: absolute;
    z-index: 3;
    top: 0.42rem;
    left: 0.42rem;
    display: grid;
    width: 1.65rem;
    height: 1.65rem;
    place-items: center;
    padding: 0;
    border: 1px solid rgba(255, 255, 255, 0.38);
    border-radius: 50%;
    background: rgba(24, 32, 44, 0.62);
    color: #fff;
    opacity: 0;
    pointer-events: none;
    cursor: pointer;
    backdrop-filter: blur(4px);
    transition: opacity 0.18s ease;
  }

  .debut-id-image-modes {
    position: relative;
    display: flex;
    width: max-content;
    min-height: 1.05rem;
    align-items: center;
    gap: 0.24rem;
    margin-top: -0.12rem;
    padding: 0 0 0.08rem 0.38rem;
    border-left: 1px solid color-mix(in srgb, var(--dod-card-text, #202938) 24%, transparent);
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.18s ease;
  }

  .debut-id-image-modes button {
    position: relative;
    padding: 0.16rem 0.04rem 0.2rem;
    border: 0;
    background: transparent;
    color: color-mix(in srgb, var(--dod-card-text, #202938) 48%, transparent);
    font: inherit;
    font-size: 0.47rem;
    font-weight: 700;
    letter-spacing: 0.09em;
    line-height: 1;
    white-space: nowrap;
    text-transform: uppercase;
    cursor: pointer;
  }

  .debut-id-image-modes .debut-id-mode-active {
    color: var(--dod-card-text, #202938);
    font-weight: 800;
  }

  .debut-id-image-modes .debut-id-mode-active::after {
    position: absolute;
    right: 0;
    bottom: 0.04rem;
    left: 0;
    height: 1px;
    background: currentColor;
    content: "";
  }

  .debut-id-mode-separator {
    margin-top: -0.08rem;
    color: color-mix(in srgb, var(--dod-card-text, #202938) 26%, transparent);
    font-size: 0.55rem;
  }

  .debut-id-image-modes .debut-id-mode-disabled {
    opacity: 0.48;
    cursor: default;
  }

  .debut-id-card:hover .debut-id-alt-button,
  .debut-id-card:focus-within .debut-id-alt-button,
  .debut-id-card.debut-id-photo-controls-open .debut-id-alt-button,
  .debut-id-card:hover .debut-id-image-modes,
  .debut-id-card:focus-within .debut-id-image-modes,
  .debut-id-card.debut-id-photo-controls-open .debut-id-image-modes {
    opacity: 1;
    pointer-events: auto;
  }

  .debut-id-barcode {
    width: 88%;
    height: 0.64rem;
    align-self: center;
    flex: none;
    margin-top: auto;
    border-radius: 1px;
    color: var(--dod-card-text, #202938);
    opacity: 0.84;
    background: repeating-linear-gradient(
      90deg,
      currentColor 0 1px,
      transparent 1px 3px,
      currentColor 3px 5px,
      transparent 5px 8px,
      currentColor 8px 9px,
      transparent 9px 12px,
      currentColor 12px 15px,
      transparent 15px 18px
    );
  }

  .debut-id-portrait img {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
    object-position: 40% 12%;
  }

  .debut-id-info {
    position: relative;
    display: flex;
    min-width: 0;
    flex-direction: column;
    justify-content: space-between;
    gap: 0.45rem;
    padding: 0.72rem 0.8rem 0.7rem 0.65rem;
    background:
      radial-gradient(ellipse 135% 115% at var(--dod-gloss-x, 52%) var(--dod-gloss-y, 18%), color-mix(in srgb, #ffffff 18%, transparent), transparent 76%),
      radial-gradient(ellipse 115% 100% at calc(100% - var(--dod-gloss-x, 52%)) calc(100% - var(--dod-gloss-y, 18%)), color-mix(in srgb, var(--dod-card-text, #202938) 2.1%, transparent), transparent 74%),
      var(--dod-card-bg, #ffffff);
  }

  .debut-id-name-row {
    position: relative;
    display: flex;
    min-width: 0;
    align-items: flex-start;
    justify-content: space-between;
    min-height: 1.8rem;
    padding-right: 1.85rem;
  }

  .debut-id-name {
    display: flex;
    min-width: 0;
    flex-direction: column;
    gap: 0.08rem;
  }

  .debut-id-faction-logo {
    position: absolute;
    top: -0.1rem;
    right: -0.1rem;
    width: 1.75rem;
    height: 1.75rem;
    flex: none;
    object-fit: contain;
    filter: drop-shadow(0 2px 3px rgba(30, 20, 40, 0.12));
  }

  .debut-image-icon {
    color: color-mix(in srgb, var(--dod-card-text, #202938) 20%, transparent);
  }

  .debut-id-meta {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 0.72fr);
    gap: 0.55rem;
    border-top: 1px solid color-mix(in srgb, var(--dod-card-text, #202938) 12%, transparent);
    padding-top: 0.5rem;
  }

  .debut-id-meta > div,
  .debut-id-role,
  .debut-id-first-appearance {
    display: flex;
    min-width: 0;
    flex-direction: column;
    gap: 0.08rem;
  }

  .debut-id-meta-mbti {
    align-items: flex-end;
    text-align: right;
  }

  .debut-id-name span,
  .debut-id-meta span,
  .debut-id-role span,
  .debut-id-first-appearance span {
    color: color-mix(in srgb, var(--dod-card-text, #202938) 48%, transparent);
    font-size: 0.55rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }

  .debut-id-name strong,
  .debut-id-meta strong,
  .debut-id-role strong,
  .debut-id-first-appearance strong {
    color: var(--dod-card-text, #202938);
    font-size: 0.9rem;
    font-weight: 700;
    line-height: 1.2;
    overflow-wrap: anywhere;
  }

  .debut-id-role {
    flex: 1;
  }

  .debut-id-footer {
    display: flex;
    min-width: 0;
    align-items: flex-end;
    justify-content: space-between;
    gap: 0.5rem;
    border-top: 1px solid color-mix(in srgb, var(--dod-card-text, #202938) 12%, transparent);
    padding-top: 0.42rem;
  }

  .debut-id-first-appearance {
    flex: none;
    align-items: flex-end;
    text-align: right;
  }

  .debut-id-first-appearance span {
    white-space: nowrap;
    font-size: 0.46rem;
  }

  .debut-id-first-appearance strong {
    white-space: nowrap;
    font-size: 0.78rem;
  }

  @media (max-width: 639px) {
    .debut-id-card {
      width: calc(100% - 1.25rem);
      grid-template-columns: 1.35rem minmax(5.8rem, 34%) minmax(0, 1fr);
      min-height: 11.5rem;
    }

    .debut-id-photo-area {
      gap: 0.25rem;
      margin: 0.4rem 0.3rem 0.4rem 0.4rem;
    }

    .debut-id-info {
      position: static;
    }

    .debut-id-image-modes {
      position: absolute;
      z-index: 4;
      bottom: 1.5rem;
      left: calc(1.35rem + 0.4rem);
      width: calc(max(5.8rem, 34%) - 0.7rem);
      min-height: 0;
      justify-content: space-between;
      gap: 0.12rem;
      margin-top: 0;
      padding: 0 0.05rem 0.12rem;
      border-left: 0;
      border-bottom: 1px solid color-mix(in srgb, var(--dod-card-text, #202938) 24%, transparent);
    }

    .debut-id-image-modes button {
      padding: 0.14rem 0.02rem 0.2rem;
      font-size: 0.4rem;
      letter-spacing: 0.06em;
    }

    .debut-id-portrait-wrap {
      height: 8.2rem;
    }

    .debut-id-alt-button {
      top: 0.35rem;
      left: 0.35rem;
      width: 1.5rem;
      height: 1.5rem;
    }

    .debut-id-barcode {
      height: 0.48rem;
      opacity: 0.9;
    }

    .debut-id-info {
      gap: 0.4rem;
      padding: 0.62rem 0.6rem 0.6rem 0.5rem;
    }

    .debut-id-name strong,
    .debut-id-meta strong,
    .debut-id-role strong {
      font-size: 0.82rem;
    }

    .debut-id-name span,
    .debut-id-meta span,
    .debut-id-role span {
      font-size: 0.5rem;
    }

    .debut-id-faction-logo {
      width: 1.5rem;
      height: 1.5rem;
    }

    .debut-id-name-row {
      padding-right: 1.55rem;
    }

    .debut-id-name strong,
    .debut-id-meta strong,
    .debut-id-role strong {
      overflow-wrap: normal;
    }

    .debut-id-role {
      min-width: min-content;
    }

    .debut-id-first-appearance {
      max-width: 4.5rem;
      flex-shrink: 1;
    }

    .debut-id-first-appearance span {
      white-space: normal;
    }

    .debut-id-first-appearance strong {
      font-size: 0.72rem;
    }
  }
</style>
