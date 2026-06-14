<script lang="ts">
  import Icon from "@iconify/svelte";
  import { readerState } from "$lib/reader.svelte";
  import charactersData from "$lib/reader/characters.json";

  interface Alt {
    id: string;
    name: string;
    chapter: number | null;
    toggleable: boolean;
    hasManwha: boolean;
    hasWebnovel: boolean;
    manwhaImage: string | null;
    webnovelImage: string | null;
  }

  interface Character {
    id: string;
    name: string;
    hasManwha: boolean;
    hasManwhaImage: boolean;
    hasWebnovelImage: boolean;
    manwhaImage: string | null;
    webnovelImage: string | null;
    firstAppearance: number | null;
    birthday: string;
    bloodType: string;
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
  let pinned = $state(false);

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
  class="fixed top-0 right-0 z-50 h-dvh w-72 sm:w-80 bg-base-100 shadow-2xl border-l border-base-content/10 rounded-l-2xl transition-transform duration-300 ease-out"
  class:translate-x-0={readerState.refPanelOpen}
  class:translate-x-full={!readerState.refPanelOpen}
  style="overflow-y: auto; scrollbar-width: none; -ms-overflow-style: none;"
>
  <div class="sticky top-0 z-20 bg-base-100/95 backdrop-blur flex items-center px-4 pt-2.5 pb-1.5 border-b border-base-content/10 relative">
    <h2 class="font-bold text-lg text-primary">Reference</h2>
    <span class="flex-1"></span>
    <div class="tooltip tooltip-bottom" data-tip="Spoiler Settings">
      <button class="btn btn-sm btn-circle btn-ghost opacity-50 hover:opacity-100" onclick={() => spoilerDialog?.showModal()} aria-label="Spoiler Settings">
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
        <a href="https://gsgw.miraheze.org/wiki/GDCG_Wiki" target="_blank" rel="noopener noreferrer" class="hover:opacity-60 transition-opacity">all information used for the reference tab is sourced from the wiki</a>
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
              {@const mode = charModes[ch.id] ?? (activeAlt ? "webnovel" : "manwha")}
              {@const manwhaSrc = activeAlt?.manwhaImage ?? ch.manwhaImage}
              {@const webnovelSrc = activeAlt?.webnovelImage ?? ch.webnovelImage}
              {@const altName = activeAlt?.name ?? null}
              {@const altLocked = activeAlt != null && activeAlt.chapter != null && activeAlt.chapter > currentChapter}
              <div class="rounded-xl bg-base-200/40 border border-base-content/10 overflow-hidden relative">
                <div class="w-full h-80 relative bg-base-300/50">
                  {#if manwhaSrc}
                    <img
                      src={'/characters/' + manwhaSrc}
                      alt={ch.name}
                      class="absolute inset-0 w-full h-full object-cover object-top transition-opacity duration-300 pointer-events-none {mode === 'manwha' ? 'opacity-100' : 'opacity-0'}"
                      style="object-position: center 15%;"
                      loading="lazy"
                      onerror={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
                    />
                  {/if}
                  {#if webnovelSrc}
                    <img
                      src={'/characters/' + webnovelSrc}
                      alt={ch.name}
                      class="absolute inset-0 w-full h-full object-cover object-top transition-opacity duration-300 pointer-events-none {mode === 'webnovel' || !manwhaSrc ? 'opacity-100' : 'opacity-0'}"
                      style="object-position: center 15%;"
                      loading="lazy"
                      onerror={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
                    />
                  {/if}
                  {#if !manwhaSrc && !webnovelSrc}
                    <div class="absolute inset-0 flex items-center justify-center">
                      <Icon icon="material-symbols:person-off-rounded" class="size-12 opacity-20" />
                    </div>
                  {/if}
                  {#if !spoilerDisabled && altLocked}
                    <div
                      class="absolute inset-0 rounded-t-xl flex items-center justify-center transition-all duration-500 {spoilerClass(ch.id)}"
                      onclick={() => clickSpoiler(ch.id)}
                      role="button"
                      tabindex="0"
                      onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); clickSpoiler(ch.id); } }}
                    >
                      <span class="text-neutral-content/60 text-xs font-medium tracking-wider uppercase pointer-events-none">{spoilerText(ch.id)}</span>
                    </div>
                  {/if}
                </div>
                {#if ch.alts.length > 0}
                  <button
                    class="absolute top-2 right-2 z-10 btn btn-xs btn-circle btn-ghost bg-base-100/70 hover:bg-base-100 backdrop-blur-sm opacity-60 hover:opacity-100 transition-opacity"
                    onclick={() => cycleAlt(ch)}
                    aria-label="Swap illustration"
                  >
                    <Icon icon="material-symbols:sync-alt-rounded" class="size-4" />
                  </button>
                {/if}
                <div class="p-4 pb-2">
                  <h3 class="font-bold text-base">{altName ?? ch.name}</h3>
                </div>
                <div class="px-4 pb-2">
                  <div class="join w-full">
                    <button
                      class="join-item btn btn-xs flex-1 {manwhaSrc ? (mode === 'manwha' ? 'btn-primary' : 'btn-ghost bg-base-200') : 'btn-ghost bg-base-200 opacity-30 cursor-not-allowed line-through'}"
                      onclick={() => { if (manwhaSrc) charModes[ch.id] = 'manwha'; }}
                    >Manwha</button>
                    <button
                    class="join-item btn btn-xs flex-1 {mode === 'webnovel' ? 'btn-primary' : 'btn-ghost bg-base-200'} {!webnovelSrc ? 'opacity-30 cursor-not-allowed line-through' : ''}"
                    onclick={() => { if (webnovelSrc) charModes[ch.id] = 'webnovel'; }}
                  >Webnovel</button>
                  </div>
                </div>
                <div class="px-4 pt-2 pb-3 text-xs space-y-1.5 text-base-content">
                  <div class="flex justify-between">
                    <span class="font-medium">First Appearance</span>
                    <span>{activeAlt?.chapter ? 'CH ' + activeAlt.chapter : ch.firstAppearance ? 'CH ' + ch.firstAppearance : '■■'}</span>
                  </div>
                  <div class="flex justify-between">
                    <span class="font-medium">Blood Type</span>
                    <span>{ch.bloodType}</span>
                  </div>
                  <div class="flex justify-between">
                    <span class="font-medium">Birthday</span>
                    <span>{ch.birthday}</span>
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
    <h3 class="font-bold text-lg mb-4">Spoiler Settings</h3>
    <div class="rounded-xl bg-base-200 border border-base-content/10 p-3 space-y-4">
      <label class="flex items-center justify-between cursor-pointer gap-3">
        <span class="text-sm font-medium">Show full spoilers</span>
        <input type="checkbox" class="toggle toggle-sm" bind:checked={spoilerDisabled} />
      </label>
      <label class="flex items-center justify-between cursor-pointer gap-3">
        <span class="text-sm font-medium">Disable discovery</span>
        <input type="checkbox" class="toggle toggle-sm" bind:checked={discoveryDisabled} />
      </label>
    </div>
  </div>
  <form method="dialog" class="modal-backdrop">
    <button>close</button>
  </form>
</dialog>

<style>
  :global(.hide-scrollbar::-webkit-scrollbar) { display: none; }
</style>