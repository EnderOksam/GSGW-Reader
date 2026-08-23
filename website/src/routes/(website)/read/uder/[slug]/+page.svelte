<script lang="ts">
  import { onMount } from "svelte";
  import { page } from "$app/state";
  import { dev } from "$app/environment";
  import JSZip from "jszip";
  import Icon from "@iconify/svelte";
  import bookMeta from "$lib/meta.json";
  import UderText from "../../../dev/editor/UderText.svelte";
  import NodePreview from "../../../dev/editor/NodePreview.svelte";
  import { importUderZip } from "../../../dev/editor/lib/uder-format";
  import type { UderNode, NodeEdge } from "../../../dev/editor/lib/nodes";
  import readerCss from "../../../../../routes/(reader)/reader.css?url";

  const REPO_BASE = "https://raw.githubusercontent.com/EnderOksam/GSGW-Reader/main";

  interface RecordEntry {
    title: string;
    slug: string;
    type: string;
    typeLabel: string;
    faction: string | null;
    code: string;
    classification: string;
    summary: string;
    thumb: string | null;
    hasInteractive: boolean;
  }

  const records = ((bookMeta as any).uder?.records ?? []) as RecordEntry[];

  let slug = $derived(page.params.slug ?? "");
  let entry = $derived(records.find((r) => r.slug === slug) ?? null);

  let loading = $state(true);
  let error = $state("");
  let content = $state("");
  let subRecords = $state<{ title: string; content: string }[]>([]);
  let interactive = $state<{ nodes: UderNode[]; edges: NodeEdge[] } | null>(null);
  let mode = $state<"record" | "interactive">("record");
  let expandedRecords = $state<Record<number, boolean>>({});

  let settings = $state({
    font: "Alegreya",
    fontSize: 25,
    fontWeight: 450,
    lineHeight: 1.8,
    textAlign: "left" as CanvasTextAlign,
    hyphens: false,
    indent: false,
    theme: "sunset",
  });

  let chapterVars = $derived(`
    --chapter-font: ${settings.font}, serif;
    --chapter-size: ${settings.fontSize}px;
    --chapter-weight: ${settings.fontWeight};
    --chapter-lh: ${settings.lineHeight};
    --chapter-indent: ${settings.indent ? "1.5em" : "0"};
    --chapter-align: ${settings.textAlign};
    --chapter-hyphens: ${settings.hyphens ? "auto" : "none"};
  `);

  onMount(() => {
    try {
      const saved = localStorage.getItem("readerSettings");
      if (saved) {
        const parsed = JSON.parse(saved);
        settings = { ...settings, ...parsed };
      }
    } catch {}
    document.documentElement.setAttribute("data-theme", settings.theme);
  });

  $effect(() => {
    const s = slug;
    loading = true;
    error = "";
    content = "";
    subRecords = [];
    interactive = null;
    mode = "record";
    expandedRecords = {};

    if (!s) return;

    (async () => {
      try {
        const url = dev
          ? `/chapters/uder/records/${encodeURIComponent(s)}.uder`
          : `${REPO_BASE}/chapters/uder/records/${encodeURIComponent(s)}.uder`;
        const res = await fetch(url);
        if (!res.ok) throw new Error("record archive not found");
        const blob = await res.blob();

        const imported = await importUderZip(new File([blob], `${s}.uder`));
        content = imported.content;
        subRecords = imported.records;

        if (imported.thumbnailUrl) URL.revokeObjectURL(imported.thumbnailUrl);
        for (const m of imported.mediaUrls) URL.revokeObjectURL(m);

        const zip = await JSZip.loadAsync(blob);
        const interFile = zip.file("interactive.json");
        if (interFile) {
          try {
            const json = JSON.parse(await interFile.async("text"));
            if (Array.isArray(json?.nodes) && Array.isArray(json?.edges)) {
              interactive = { nodes: json.nodes, edges: json.edges };
            }
          } catch {}
        }

        loading = false;
        window.scrollTo(0, 0);
      } catch (e) {
        error = e instanceof Error ? e.message : "failed to load record";
        loading = false;
      }
    })();
  });

  function toggleRecord(i: number) {
    expandedRecords[i] = !expandedRecords[i];
  }
</script>

<svelte:head>
  <link rel="stylesheet" href={readerCss} />
  <title>{entry?.title || slug} - Dark Exploration Records</title>
  {#if entry?.summary}
    <meta name="description" content={entry.summary} />
  {/if}
</svelte:head>

<div class="uder-reader" style={chapterVars}>
  <nav class="reader-topbar">
    <div class="topbar-left">
      <a href="/book/uder" class="topbar-back" aria-label="Back to records">
        <Icon icon="material-symbols:arrow-back-rounded" class="size-5" />
      </a>
    </div>
    <div class="topbar-center">
      <div class="topbar-toggle">
        <button
          class="topbar-toggle-btn"
          class:active={mode === "record"}
          onclick={() => (mode = "record")}
        >record</button>
        <button
          class="topbar-toggle-btn"
          class:active={mode === "interactive"}
          disabled={!interactive}
          onclick={() => (mode = "interactive")}
        >interactive</button>
      </div>
    </div>
    <div class="topbar-right">
      {#if entry?.code}
        <span class="topbar-id">{entry.code}</span>
      {/if}
    </div>
  </nav>

  <div class="reader-scroll">
    {#if loading}
      <div class="state-wrap">
        <span class="loader"></span>
        <p class="state-text">loading record…</p>
      </div>
    {:else if error || !entry}
      <div class="state-wrap">
        <Icon icon="mdi:alert-circle-outline" class="size-8 state-icon" />
        <p class="state-text">{error || "unknown record"}</p>
        <a href="/book/uder" class="state-link">back to records</a>
      </div>
    {:else if mode === "interactive" && interactive}
      <main class="reader-main">
        <div class="interactive-stage">
          <NodePreview nodes={interactive.nodes} edges={interactive.edges} showEntrySelect={false} />
        </div>
      </main>
    {:else}
      <main class="reader-main">
        <div class="reader-card-outer">
          <div class="reader-card-bg"></div>

          <div class="reader-card-inner">
            <div class="uder-grid">

                <section class="reader-card uder-area-title">
                  <div class="card-breadcrumb">
                    <span class="breadcrumb-type">{entry.typeLabel}</span>
                    {#if entry.faction}
                      <span class="breadcrumb-sep">/</span>
                      <span class="breadcrumb-text">{entry.faction}</span>
                    {/if}
                    <span class="breadcrumb-sep">/</span>
                    <span class="breadcrumb-text">entry</span>
                  </div>
                  <h2 class="card-title">{entry.title || "\u00a0"}</h2>
                  {#if entry.faction && (entry.code || entry.classification)}
                    <div class="card-subtitle">
                      {#if entry.code}<span>{entry.code}</span>{/if}
                      {#if entry.classification}<span>{entry.classification}</span>{/if}
                    </div>
                  {/if}
                </section>

              <div class="flex flex-col gap-5 min-w-0 uder-area-main">

                <section class="reader-card card-has-header">
                  <div class="card-header">
                    <Icon icon="mdi:file-document-outline" class="size-3.5 text-base-content/30" />
                    <span class="card-header-label">content</span>
                  </div>
                  <div class="card-body chapter-content">
                    {#if content}
                      <UderText text={content} />
                    {:else}
                      <p class="text-base-content/15 italic">no content yet</p>
                    {/if}
                  </div>
                </section>

                {#if subRecords.length > 0}
                  <section class="reader-card card-has-header">
                    <div class="card-header">
                      <Icon icon="mdi:folder-open-outline" class="size-3.5 text-base-content/30" />
                      <span class="card-header-count">{subRecords.length}</span>
                      <span class="card-header-label">exploration records</span>
                    </div>
                    <div class="card-records">
                      {#each subRecords as sub, i}
                        <div class="record-row">
                          <button class="record-row-header" onclick={() => toggleRecord(i)}>
                            <Icon
                              icon={expandedRecords[i] ? "mdi:chevron-down" : "mdi:chevron-right"}
                              class="size-4 text-base-content/25 shrink-0 transition-transform"
                            />
                            <span class="record-row-title">{sub.title}</span>
                          </button>
                          {#if expandedRecords[i]}
                            <div class="record-row-body chapter-content">
                              {#if sub.content}
                                <UderText text={sub.content} />
                              {:else}
                                <p class="italic text-base-content/15">empty</p>
                              {/if}
                            </div>
                          {/if}
                        </div>
                      {/each}
                    </div>
                  </section>
                {/if}

              </div>

              <div class="flex flex-col gap-5 min-w-0 sticky-col uder-area-side">
                {#if entry.thumb}
                  <section class="reader-card card-has-header">
                    <div class="card-header">
                      <Icon icon="mdi:image-outline" class="size-3.5 text-base-content/30" />
                      <span class="card-header-label">illustration</span>
                    </div>
                    <div class="card-thumb">
                      <img src={entry.thumb} alt="illustration" class="thumb-img" />
                    </div>
                  </section>
                {/if}

                {#if entry.summary}
                  <section class="reader-card card-has-header">
                    <div class="card-header">
                      <Icon icon="mdi:text-box-outline" class="size-3.5 text-base-content/30" />
                      <span class="card-header-label">summary</span>
                    </div>
                    <div class="card-body">
                      <p class="summary-text">{entry.summary}</p>
                    </div>
                  </section>
                {/if}
              </div>

            </div>
          </div>

        </div>
      </main>
    {/if}
  </div>
</div>

<style>
  .uder-reader {
    display: flex;
    flex-direction: column;
    height: 100dvh;
    min-height: 0;
    position: relative;
    background-color: color-mix(in oklch, var(--color-base-100) 100%, transparent);
  }

  .reader-topbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.25rem 0.5rem;
    border-bottom: 1px solid color-mix(in oklch, var(--color-base-content) 5%, transparent);
    background-color: color-mix(in oklch, var(--color-base-100) 80%, transparent);
    backdrop-filter: blur(12px);
    flex-shrink: 0;
    height: 3rem;
  }

  .topbar-left {
    display: flex;
    align-items: center;
    gap: 0.25rem;
    min-width: 0;
  }

  .topbar-back {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 2.25rem;
    height: 2.25rem;
    border-radius: 0.75rem;
    color: color-mix(in oklch, var(--color-base-content) 60%, transparent);
    transition: all 0.12s ease;
  }

  .topbar-back:hover {
    color: var(--color-primary, var(--color-base-content));
    background-color: color-mix(in oklch, var(--color-base-content) 6%, transparent);
  }

  .topbar-center {
    flex: 1;
    display: flex;
    justify-content: center;
  }

  .topbar-toggle {
    display: flex;
    align-items: center;
    gap: 0.125rem;
    padding: 0.125rem;
    border-radius: 0.5rem;
    border: 1px solid color-mix(in oklch, var(--color-base-content) 10%, transparent);
    background-color: color-mix(in oklch, var(--color-base-300) 60%, transparent);
  }

  .topbar-toggle-btn {
    font-size: 10px;
    font-family: ui-monospace, monospace;
    font-weight: 500;
    padding: 0.375rem 0.75rem;
    border-radius: 0.375rem;
    border: none;
    background: none;
    color: color-mix(in oklch, var(--color-base-content) 40%, transparent);
    cursor: pointer;
    transition: all 0.12s ease;
  }

  .topbar-toggle-btn.active {
    background-color: color-mix(in oklch, var(--color-primary) 15%, transparent);
    color: var(--color-primary, var(--color-base-content));
    box-shadow: 0 1px 2px rgb(0 0 0 / 0.06);
  }

  .topbar-toggle-btn:disabled {
    opacity: 0.35;
    cursor: not-allowed;
  }

  .topbar-toggle-btn:hover:not(:disabled):not(.active) {
    color: color-mix(in oklch, var(--color-base-content) 60%, transparent);
  }

  .topbar-right {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    min-width: 0;
  }

  .topbar-id {
    font-size: 9px;
    font-family: ui-monospace, monospace;
    letter-spacing: 0.08em;
    color: color-mix(in oklch, var(--color-base-content) 25%, transparent);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .reader-scroll {
    flex: 1;
    overflow-y: auto;
    padding: 1.5rem;
    scrollbar-width: thin;
  }

  .reader-main {
    max-width: 64rem;
    margin: 0 auto;
  }

  .state-wrap {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0.9rem;
    padding: 6rem 1rem;
    color: color-mix(in oklch, var(--color-base-content) 35%, transparent);
  }

  .state-wrap :global(.state-icon) {
    color: color-mix(in oklch, var(--color-base-content) 20%, transparent);
  }

  .state-text {
    font-size: 11px;
    font-family: ui-monospace, monospace;
    letter-spacing: 0.08em;
  }

  .state-link {
    font-size: 11px;
    font-family: ui-monospace, monospace;
    color: var(--color-primary, var(--color-base-content));
    text-decoration: underline;
    text-underline-offset: 3px;
  }

  .loader {
    width: 1.4rem;
    height: 1.4rem;
    border-radius: 9999px;
    border: 2px solid color-mix(in oklch, var(--color-base-content) 12%, transparent);
    border-top-color: color-mix(in oklch, var(--color-primary) 60%, transparent);
    animation: uder-spin 0.8s linear infinite;
  }

  @keyframes uder-spin {
    to {
      transform: rotate(360deg);
    }
  }

  .interactive-stage {
    height: max(calc(100dvh - 7.5rem), 30rem);
    display: flex;
    flex-direction: column;
  }

  .interactive-stage > :global(*) {
    flex: 1;
  }

  .reader-card-outer {
    position: relative;
    border-radius: 1rem;
    border: 1px solid color-mix(in oklch, var(--color-base-content) 10%, transparent);
    background-color: color-mix(in oklch, var(--color-base-200) 100%, transparent);
    box-shadow: 0 10px 40px rgb(0 0 0 / 0.08);
    overflow: hidden;
  }

  .reader-card-bg {
    position: absolute;
    inset: 0;
    background-color: color-mix(in oklch, var(--color-base-300) 100%, transparent);
    opacity: 1;
    z-index: -1;
  }

  .reader-card-inner {
    padding: 2rem 2.5rem;
  }

  .uder-grid {
    display: grid;
    grid-template-columns: minmax(0, 3fr) minmax(300px, 2fr);
    grid-template-areas:
      "title side"
      "main side";
    gap: 1.5rem;
    align-items: start;
  }

  .uder-area-title {
    grid-area: title;
  }

  .uder-area-main {
    grid-area: main;
  }

  .uder-area-side {
    grid-area: side;
  }

  @media (max-width: 768px) {
    .uder-grid {
      grid-template-columns: 1fr;
      grid-template-areas:
        "title"
        "side"
        "main";
    }
    .sticky-col {
      position: static;
    }
    .reader-card-inner {
      padding: 1.25rem;
    }
    .reader-scroll {
      padding: 1rem;
    }
  }

  .sticky-col {
    position: sticky;
    top: 1.5rem;
  }

  .reader-card {
    border-radius: 1rem;
    border: 1px solid color-mix(in oklch, var(--color-base-content) 10%, transparent);
    background-color: color-mix(in oklch, var(--color-base-200) 50%, transparent);
    padding: 1.25rem;
  }

  .card-has-header {
    padding: 0;
    overflow: hidden;
  }

  .card-breadcrumb {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.625rem;
  }

  .breadcrumb-type {
    font-size: 9px;
    font-family: ui-monospace, monospace;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.14em;
    color: color-mix(in oklch, var(--color-primary) 60%, transparent);
    padding: 0.125rem 0.5rem;
    border-radius: 0.375rem;
    background-color: color-mix(in oklch, var(--color-primary) 10%, transparent);
    border: 1px solid color-mix(in oklch, var(--color-primary) 20%, transparent);
  }

  .breadcrumb-sep,
  .breadcrumb-text {
    font-size: 9px;
    font-family: ui-monospace, monospace;
    color: color-mix(in oklch, var(--color-base-content) 30%, transparent);
  }

  .card-title {
    margin: 0;
    padding: 0;
    text-align: left;
    font-variant: normal;
    text-wrap: wrap;
    font-size: 1.25rem;
    font-weight: 700;
    color: color-mix(in oklch, var(--color-base-content) 80%, transparent);
    line-height: 1.3;
  }

  .card-title::after {
    content: none;
  }

  .card-subtitle {
    display: flex;
    gap: 1rem;
    margin-top: 0.375rem;
    font-size: 11px;
    font-family: ui-monospace, monospace;
    color: color-mix(in oklch, var(--color-base-content) 35%, transparent);
  }

  .card-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.625rem 1rem;
    border-bottom: 1px solid color-mix(in oklch, var(--color-base-content) 10%, transparent);
    background-color: color-mix(in oklch, var(--color-base-300) 40%, transparent);
  }

  .card-header-label {
    font-size: 10px;
    font-family: ui-monospace, monospace;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: color-mix(in oklch, var(--color-base-content) 40%, transparent);
  }

  .card-header-count {
    margin-left: auto;
    font-size: 9px;
    font-family: ui-monospace, monospace;
    color: color-mix(in oklch, var(--color-base-content) 25%, transparent);
  }

  .card-body {
    padding: 1.25rem;
  }

  .chapter-content {
    padding: 1.25rem;
    font-family: var(--chapter-font);
    font-size: var(--chapter-size);
    line-height: var(--chapter-lh);
    text-align: var(--chapter-align);
    hyphens: var(--chapter-hyphens);
    font-weight: var(--chapter-weight, 400);
    overflow-wrap: break-word;
    word-break: break-word;
    color: color-mix(in oklch, var(--color-base-content) 75%, transparent);
  }

  .chapter-content :global(h1),
  .chapter-content :global(h2),
  .chapter-content :global(h3) {
    text-wrap: balance;
  }

  .chapter-content :global(p) {
    text-indent: var(--chapter-indent);
  }

  .card-records {
    display: flex;
    flex-direction: column;
  }

  .record-row {
    border-bottom: 1px solid color-mix(in oklch, var(--color-base-content) 5%, transparent);
  }

  .record-row:last-child {
    border-bottom: none;
  }

  .record-row-header {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    width: 100%;
    padding: 0.75rem 1rem;
    text-align: left;
    cursor: pointer;
    transition: background-color 0.1s ease;
    background: none;
    border: none;
    color: inherit;
    font: inherit;
  }

  .record-row-header:hover {
    background-color: color-mix(in oklch, var(--color-base-content) 3%, transparent);
  }

  .record-row-title {
    font-size: 12px;
    font-family: ui-monospace, monospace;
    font-weight: 600;
    color: color-mix(in oklch, var(--color-base-content) 50%, transparent);
  }

  .record-row-body {
    padding: 0 2.75rem 1rem;
    font-size: 14px;
    line-height: 1.7;
    color: color-mix(in oklch, var(--color-base-content) 40%, transparent);
    white-space: pre-wrap;
    word-break: break-word;
  }

  .card-thumb {
    overflow: hidden;
  }

  .thumb-img {
    width: 100%;
    aspect-ratio: 16 / 9;
    object-fit: cover;
    display: block;
  }

  .summary-text {
    font-size: 12px;
    line-height: 1.7;
    color: color-mix(in oklch, var(--color-base-content) 45%, transparent);
  }
</style>
