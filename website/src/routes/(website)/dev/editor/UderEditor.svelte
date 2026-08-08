<script lang="ts">
  import Icon from "@iconify/svelte";
  import { preprocessMarkdown } from "./lib/editor-markdown";
  import { downloadBlob } from "./lib/zip-tools";
  import { exportUderZip, importUderZip, sanitizeHtml } from "./lib/uder-format";

  type ViewMode = "edit" | "preview";

  let viewMode = $state<ViewMode>("edit");
  let assets = $state<{ name: string; url: string }[]>([]);
  let dragOver = $state(false);
  let draggedAssetIndex = $state<number | null>(null);
  let thumbnailDragOver = $state(false);
  let mediaSlotDragOver = $state(false);
  let fileInputRef: HTMLInputElement | undefined = $state();
  let expandedRecord = $state<number | null>(null);

  let title = $state("");
  let identificationCode = $state("");
  let classification = $state("");
  let content = $state("");
  let shortDescription = $state("");
  let thumbnail = $state<string | null>(null);
  let thumbnailInputRef: HTMLInputElement | undefined = $state();
  let mediaSlots = $state<string[]>([]);
  let records = $state<{ title: string; content: string }[]>([]);

  let activeField: { set: (v: string) => void; get: () => string; el: HTMLTextAreaElement | null } | null = $state(null);

  function insertFormatting(syntax: string) {
    if (!activeField?.el) return;
    const el = activeField.el;
    const start = el.selectionStart;
    const end = el.selectionEnd;
    const current = activeField.get();
    const selected = current.slice(start, end);
    const hasPlaceholder = syntax.includes("text");
    const replacement = hasPlaceholder ? syntax.replace("text", selected || "text") : syntax;
    const before = current.slice(0, start);
    const after = current.slice(end);
    activeField.set(before + replacement + after);
    requestAnimationFrame(() => {
      el.focus();
      const newCursorPos = start + replacement.length;
      el.setSelectionRange(newCursorPos, newCursorPos);
    });
  }

  function splitContent(text: string): { type: "html" | "illustration"; value: string }[] {
    const parts: { type: "html" | "illustration"; value: string }[] = [];
    const regex = /\[illustration\|(.*?)\]/g;
    let lastIndex = 0;
    let match;
    while ((match = regex.exec(text)) !== null) {
      if (match.index > lastIndex) {
        parts.push({ type: "html", value: text.slice(lastIndex, match.index) });
      }
      parts.push({ type: "illustration", value: match[1] });
      lastIndex = match.index + match[0].length;
    }
    if (lastIndex < text.length) {
      parts.push({ type: "html", value: text.slice(lastIndex) });
    }
    return parts;
  }

  let selectedFaction = $state<string | null>(null);
  let isExplorationRecord = $state(false);

  const factions = ["Daydream Inc.", "Disaster Management Bureau", "Church of the Luminous Unknown"];

  const factionStyles: Record<string, string> = {
    "Daydream Inc.": "bg-red-500/20 text-red-300 border-red-500/30",
    "Disaster Management Bureau": "bg-blue-500/20 text-blue-300 border-blue-500/30",
    "Church of the Luminous Unknown": "bg-yellow-500/20 text-yellow-300 border-yellow-500/30",
  };

  const factionStylesInactive: Record<string, string> = {
    "Daydream Inc.": "text-red-400 border-red-400/30",
    "Disaster Management Bureau": "text-blue-400 border-blue-400/30",
    "Church of the Luminous Unknown": "text-yellow-400 border-yellow-400/30",
  };

  const explorationStyle = "bg-base-content/10 text-base-content/60 border-base-content/20";
  const explorationStyleInactive = "text-base-content/60 border-base-content/20";

  function selectFaction(faction: string) {
    selectedFaction = selectedFaction === faction ? null : faction;
  }

  function toggleExplorationRecord() {
    isExplorationRecord = !isExplorationRecord;
  }

  function getPreviewTags(): string[] {
    const tags: string[] = [];
    if (selectedFaction) tags.push(selectedFaction);
    if (isExplorationRecord) tags.push("Exploration Record");
    return tags;
  }

  function getTagStyle(tag: string): string {
    if (tag === "Exploration Record") return explorationStyle;
    return factionStyles[tag] || "";
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

  const colorsItems = [
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
    { syntax: "_text_", text: "underline text", cls: "underline" },
    { syntax: "~~text~~", text: "strikethrough text", cls: "line-through text-base-content/50" },
    { syntax: "$stexts$", text: "smoke text", cls: "smoke-text", expandable: true },
    { syntax: "$atexta$", text: "aurora text", cls: "aurora-text", expandable: true },
    { syntax: "$*text*$", text: "sparkle text", cls: "sparkle-text", expandable: true },
  ];

  let expandedSyntax: Record<string, boolean> = $state({});
  let sidebarView = $state<"metadata" | "formatting">("metadata");

  function handleThumbnailUpload(e: Event) {
    const input = e.target as HTMLInputElement;
    const file = input.files?.[0];
    if (file && file.type.startsWith("image/")) {
      if (thumbnail) URL.revokeObjectURL(thumbnail);
      thumbnail = URL.createObjectURL(file);
    }
    input.value = "";
  }

  function removeThumbnail() {
    if (thumbnail) URL.revokeObjectURL(thumbnail);
    thumbnail = null;
  }

  function addRecord() {
    records = [...records, { title: "", content: "" }];
    expandedRecord = records.length - 1;
  }

  function removeRecord(index: number) {
    records = records.filter((_, i) => i !== index);
    if (expandedRecord === index) expandedRecord = null;
    else if (expandedRecord !== null && expandedRecord > index) expandedRecord--;
  }

  function toggleRecord(index: number) {
    expandedRecord = expandedRecord === index ? null : index;
  }

  function addFiles(files: FileList | null) {
    if (!files) return;
    for (const file of files) {
      if (!file.type.startsWith("image/")) continue;
      const url = URL.createObjectURL(file);
      assets = [...assets, { name: file.name, url }];
    }
  }

  function handleDrop(e: DragEvent) {
    e.preventDefault();
    dragOver = false;
    addFiles(e.dataTransfer?.files ?? null);
  }

  function handleDragOver(e: DragEvent) {
    e.preventDefault();
    dragOver = true;
  }

  function handleDragLeave() {
    dragOver = false;
  }

  function handleAssetDragStart(e: DragEvent, index: number) {
    draggedAssetIndex = index;
    if (e.dataTransfer) {
      e.dataTransfer.effectAllowed = "copy";
    }
  }

  function handleAssetDragEnd() {
    draggedAssetIndex = null;
    thumbnailDragOver = false;
    mediaSlotDragOver = false;
    contentDragOver = false;
    recordDragOver = null;
  }

  let contentDragOver = $state(false);
  let recordDragOver = $state<number | null>(null);

  function handleThumbnailDragOver(e: DragEvent) {
    e.preventDefault();
    thumbnailDragOver = true;
  }

  function handleThumbnailDragLeave() {
    thumbnailDragOver = false;
  }

  function handleThumbnailDrop(e: DragEvent) {
    e.preventDefault();
    thumbnailDragOver = false;
    if (draggedAssetIndex !== null && assets[draggedAssetIndex]) {
      if (thumbnail) URL.revokeObjectURL(thumbnail);
      thumbnail = assets[draggedAssetIndex].url;
    }
  }

  function handleMediaSlotDragOver(e: DragEvent) {
    e.preventDefault();
    mediaSlotDragOver = true;
  }

  function handleMediaSlotDragLeave() {
    mediaSlotDragOver = false;
  }

  function handleMediaSlotDrop(e: DragEvent) {
    e.preventDefault();
    mediaSlotDragOver = false;
    if (draggedAssetIndex !== null && assets[draggedAssetIndex]) {
      mediaSlots = [...mediaSlots, assets[draggedAssetIndex].url];
    }
  }

  function removeMediaSlot(index: number) {
    mediaSlots = mediaSlots.filter((_, i) => i !== index);
  }

  function handleTextareaDrop(e: DragEvent, set: (v: string) => void, get: () => string) {
    e.preventDefault();
    contentDragOver = false;
    recordDragOver = null;
    if (draggedAssetIndex === null || !assets[draggedAssetIndex]) return;
    const el = e.currentTarget as HTMLTextAreaElement;
    const start = el.selectionStart;
    const end = el.selectionEnd;
    const current = get();
    const insertion = `\n[illustration|${assets[draggedAssetIndex].url}]\n`;
    const before = current.slice(0, start);
    const after = current.slice(end);
    set(before + insertion + after);
    requestAnimationFrame(() => {
      el.focus();
      const pos = start + insertion.length;
      el.setSelectionRange(pos, pos);
    });
  }

  function handleFileInput(e: Event) {
    const input = e.target as HTMLInputElement;
    addFiles(input.files);
    input.value = "";
  }

  function removeAsset(index: number) {
    URL.revokeObjectURL(assets[index].url);
    assets = assets.filter((_, i) => i !== index);
  }

  // package everything up into one .uder zip file and download it
  export async function handleExport() {
    if (!title.trim()) { alert("Give the record a title first."); return; }
    try {
      const { blob, slug } = await exportUderZip({
        title,
        type: isExplorationRecord ? "exploration" : "record",
        faction: selectedFaction,
        code: identificationCode,
        classification,
        summary: shortDescription,
        thumbnailUrl: thumbnail,
        mediaUrls: mediaSlots,
        content,
        records,
      });
      downloadBlob(blob, `${slug}.uder`, "application/zip");
    } catch (err) {
      alert("Failed to export: " + (err instanceof Error ? err.message : String(err)));
    }
  }

  // read a .uder (zip) file and put everything back into the editor
  export async function handleImport(e: Event) {
    const file = (e.target as HTMLInputElement).files?.[0];
    if (!file) return;
    try {
      const imported = await importUderZip(file);
      title = imported.title;
      selectedFaction = imported.faction;
      isExplorationRecord = imported.type === "exploration";
      identificationCode = imported.code;
      classification = imported.classification;
      shortDescription = imported.summary;
      content = imported.content;
      records = JSON.parse(JSON.stringify(imported.records));
      thumbnail = imported.thumbnailUrl;
      mediaSlots = imported.mediaUrls;
      assets = imported.images.map((img) => ({ name: img.name, url: img.url }));
    } catch (err) {
      alert("Failed to import: " + (err instanceof Error ? err.message : String(err)));
    }
    (e.target as HTMLInputElement).value = "";
  }
</script>

<!-- ===== DESKTOP LAYOUT ===== -->
<div class="uder-editor flex flex-1 gap-3 min-h-0 p-3">

  <!-- ===== LEFT SIDEBAR: Assets ===== -->
  <aside
    class="w-56 flex flex-col bg-base-200/80 backdrop-blur-sm rounded-xl border border-base-content/10 shrink-0 min-h-0 shadow-lg shadow-black/5"
    ondrop={handleDrop}
    ondragover={handleDragOver}
    ondragleave={handleDragLeave}
    role="region"
  >
    <div class="flex items-center gap-2 px-3 py-2.5 border-b border-base-content/10">
      <Icon icon="mdi:folder-image-outline" class="size-3.5 text-base-content/30" />
      <span class="text-[10px] font-mono font-medium text-base-content/40 uppercase tracking-widest">assets</span>
      <span class="text-[9px] font-mono text-base-content/20 ml-auto">{assets.length}</span>
    </div>
    <div class="flex-1 overflow-y-auto p-2 min-h-0 space-y-1.5 scrollbar-thin">
      <input bind:this={fileInputRef} onchange={handleFileInput} type="file" accept="image/*" multiple class="hidden" />
      <button
        onclick={() => fileInputRef?.click()}
        class="w-full rounded-xl border-2 border-dashed flex flex-col items-center justify-center gap-2 py-6 transition-colors cursor-pointer {dragOver ? 'border-primary/50 bg-primary/5' : 'border-base-content/10 hover:border-base-content/20 hover:bg-base-content/[3%]'}"
      >
        <Icon icon={dragOver ? "mdi:image-plus" : "mdi:image-plus-outline"} class="size-5 {dragOver ? 'text-primary/40' : 'text-base-content/15'}" />
        <span class="text-[10px] font-mono {dragOver ? 'text-primary/40' : 'text-base-content/20'} text-center px-3 leading-relaxed">
          {dragOver ? "drop to add" : "drag or click to upload images"}
        </span>
      </button>
      {#each assets as asset, i}
        <div
          class="group relative rounded-xl border bg-base-300/40 overflow-hidden cursor-grab active:cursor-grabbing transition-all {draggedAssetIndex === i ? 'opacity-40 border-primary/40' : 'border-base-content/10'}"
          draggable="true"
          ondragstart={(e) => handleAssetDragStart(e, i)}
          ondragend={handleAssetDragEnd}
          role="listitem"
        >
          <img src={asset.url} alt={asset.name} class="w-full h-24 object-cover pointer-events-none" />
          <div class="px-2 py-1.5">
            <p class="text-[9px] font-mono text-base-content/35 truncate">{asset.name}</p>
          </div>
          <button
            onclick={() => removeAsset(i)}
            class="absolute top-1.5 right-1.5 p-1 rounded-lg bg-base-300/80 text-base-content/30 hover:text-error hover:bg-base-300 transition-all opacity-0 group-hover:opacity-100"
            title="Remove"
          >
            <Icon icon="mdi:close" class="size-3" />
          </button>
        </div>
      {/each}
    </div>
  </aside>

  <!-- ===== MIDDLE: Content Area ===== -->
  <div class="flex-1 flex flex-col min-h-0 min-w-0">

    <!-- Top bar -->
    <div class="flex items-center gap-2 px-3 py-2 border-b border-base-content/10 bg-base-200/60 backdrop-blur-sm rounded-t-xl shrink-0">
      <span class="text-[10px] font-mono text-base-content/30 font-medium uppercase tracking-wider">u-der</span>
      <div class="ml-auto flex items-center bg-base-300/60 rounded-lg border border-base-content/10 p-0.5">
        <button
          onclick={() => viewMode = "edit"}
          class="text-[10px] font-mono font-medium px-3 py-1.5 rounded-md transition-all {viewMode === 'edit' ? 'bg-primary/15 text-primary shadow-sm' : 'text-base-content/40 hover:text-base-content/60'}"
        >edit</button>
        <button
          onclick={() => viewMode = "preview"}
          class="text-[10px] font-mono font-medium px-3 py-1.5 rounded-md transition-all {viewMode === 'preview' ? 'bg-primary/15 text-primary shadow-sm' : 'text-base-content/40 hover:text-base-content/60'}"
        >preview</button>
      </div>
    </div>

    <!-- Scrollable content -->
    <div class="flex-1 overflow-y-auto rounded-b-xl border-x border-b border-base-content/10 bg-base-300/60 scrollbar-thin">
      <div class="p-6">
        <div class="uder-grid">

          <!-- ===== LEFT COLUMN ===== -->
          <div class="flex flex-col gap-5 min-w-0">

            <!-- Title Card -->
            <section class="rounded-2xl border border-base-content/10 bg-base-200/50 p-5">
              <div class="flex items-center gap-2 mb-2.5">
                <span class="text-[9px] font-mono font-bold text-primary/60 tracking-widest uppercase px-2 py-0.5 rounded-md bg-primary/10 border border-primary/20">record</span>
                {#if selectedFaction}
                  <span class="text-[9px] font-mono text-base-content/25">/</span>
                  <span class="text-[9px] font-mono text-base-content/30">{selectedFaction}</span>
                {/if}
                <span class="text-[9px] font-mono text-base-content/25">/</span>
                <span class="text-[9px] font-mono text-base-content/30">entry</span>
              </div>
          {#if viewMode === "edit"}
            <input
              bind:value={title}
              placeholder="title"
              class="w-full bg-transparent text-xl font-bold text-base-content/80 leading-tight outline-none placeholder:text-base-content/15"
            />
            {#if selectedFaction}
              <div class="flex gap-4 mt-2">
                <input
                  bind:value={identificationCode}
                  placeholder="identification code"
                  class="flex-1 bg-transparent text-[11px] font-mono text-base-content/40 leading-relaxed outline-none placeholder:text-base-content/20"
                />
                <input
                  bind:value={classification}
                  placeholder="classification"
                  class="flex-1 bg-transparent text-[11px] font-mono text-base-content/40 leading-relaxed outline-none placeholder:text-base-content/20"
                />
              </div>
            {/if}
          {:else}
            <h2 class="text-xl font-bold text-base-content/80 leading-tight">{title || "\u00a0"}</h2>
            {#if selectedFaction && (identificationCode || classification)}
              <div class="flex gap-4 mt-1.5 text-[11px] font-mono text-base-content/40">
                {#if identificationCode}<span>{identificationCode}</span>{/if}
                {#if classification}<span>{classification}</span>{/if}
              </div>
            {/if}
          {/if}
            </section>

            <!-- Content Window -->
            <section class="rounded-2xl border border-base-content/10 bg-base-200/50 overflow-hidden">
              <div class="flex items-center gap-2 px-4 py-2.5 border-b border-base-content/10 bg-base-300/40">
                <Icon icon="mdi:file-document-outline" class="size-3.5 text-base-content/30" />
                <span class="text-[10px] font-mono font-medium text-base-content/40 uppercase tracking-widest">content</span>
              </div>
              {#if viewMode === "edit"}
                <textarea
                  bind:value={content}
                  onfocus={(e) => activeField = { set: (v) => content = v, get: () => content, el: e.currentTarget }}
                  ondragover={(e) => { e.preventDefault(); contentDragOver = true; }}
                  ondragleave={() => contentDragOver = false}
                  ondrop={(e) => handleTextareaDrop(e, (v) => content = v, () => content)}
                  placeholder="write your content here..."
                  class="w-full p-5 min-h-[300px] bg-transparent text-sm leading-relaxed text-base-content/70 outline-none resize-none placeholder:text-base-content/15 {contentDragOver ? 'ring-2 ring-primary/30 ring-inset' : ''}"
                ></textarea>
              {:else}
                <div class="p-5 text-sm leading-relaxed text-base-content/60 whitespace-pre-wrap">
                  {#if content}
                    {#each splitContent(content) as part}
                      {#if part.type === "html"}
                        {@html sanitizeHtml(preprocessMarkdown(part.value))}
                      {:else}
                        <img src={part.value} alt="illustration" class="w-full max-w-md rounded-xl my-4" />
                      {/if}
                    {/each}
                  {:else}
                    <p class="text-base-content/15 italic">no content yet</p>
                  {/if}
                </div>
              {/if}
            </section>

            <!-- Exploration Records -->
            <section class="rounded-2xl border border-base-content/10 bg-base-200/50 overflow-hidden">
              <div class="flex items-center gap-2 px-4 py-2.5 border-b border-base-content/10 bg-base-300/40">
                <Icon icon="mdi:folder-open-outline" class="size-3.5 text-base-content/30" />
                <span class="text-[10px] font-mono font-medium text-base-content/40 uppercase tracking-widest">exploration records</span>
                <button
                  onclick={addRecord}
                  class="ml-auto p-1 rounded-lg text-base-content/25 hover:text-primary hover:bg-primary/10 transition-all"
                  title="Add record"
                >
                  <Icon icon="mdi:plus" class="size-4" />
                </button>
              </div>
              <div class="divide-y divide-base-content/5">
                {#if records.length === 0}
                  <div class="px-4 py-6 text-center">
                    <p class="text-[10px] font-mono text-base-content/20">no records yet</p>
                  </div>
                {/if}
                {#each records as record, i}
                  <div>
                    <div class="flex items-center">
                      <button
                        onclick={() => toggleRecord(i)}
                        class="flex-1 flex items-center gap-3 px-4 py-3 text-left hover:bg-base-content/[3%] transition-colors"
                      >
                        <Icon
                          icon={expandedRecord === i ? "mdi:chevron-down" : "mdi:chevron-right"}
                          class="size-4 text-base-content/25 shrink-0 transition-transform"
                        />
                        {#if viewMode === "edit"}
                          <input
                            bind:value={record.title}
                            placeholder="record title"
                            onclick={(e) => e.stopPropagation()}
                            class="flex-1 bg-transparent text-xs font-mono text-base-content/50 outline-none placeholder:text-base-content/20"
                          />
                        {:else}
                          <span class="text-xs font-mono text-base-content/50">{record.title || "untitled"}</span>
                        {/if}
                      </button>
                      <button
                        onclick={() => removeRecord(i)}
                        class="p-3 text-base-content/20 hover:text-error transition-colors shrink-0"
                        title="Delete record"
                      >
                        <Icon icon="mdi:trash-can-outline" class="size-3.5" />
                      </button>
                    </div>
                    {#if expandedRecord === i}
                      <div class="px-4 pb-3 pl-11 pr-11">
                        {#if viewMode === "edit"}
                          <textarea
                            bind:value={record.content}
                            onfocus={(e) => activeField = { set: (v) => records[i].content = v, get: () => records[i].content, el: e.currentTarget }}
                            ondragover={(e) => { e.preventDefault(); recordDragOver = i; }}
                            ondragleave={() => recordDragOver = null}
                            ondrop={(e) => handleTextareaDrop(e, (v) => records[i].content = v, () => records[i].content)}
                            placeholder="..."
                            class="w-full min-h-[80px] bg-transparent text-xs text-base-content/50 leading-relaxed outline-none resize-none placeholder:text-base-content/15 {recordDragOver === i ? 'ring-2 ring-primary/30 ring-inset' : ''}"
                          ></textarea>
                        {:else}
                          <div class="text-xs text-base-content/40 leading-relaxed whitespace-pre-wrap">
                            {#if record.content}
                              {#each splitContent(record.content) as part}
                                {#if part.type === "html"}
                                  {@html sanitizeHtml(preprocessMarkdown(part.value))}
                                {:else}
                                  <img src={part.value} alt="illustration" class="w-full max-w-sm rounded-xl my-3" />
                                {/if}
                              {/each}
                            {:else}
                              <p class="italic text-base-content/15">empty</p>
                            {/if}
                          </div>
                        {/if}
                      </div>
                    {/if}
                  </div>
                {/each}
              </div>
            </section>

          </div>

          <!-- ===== RIGHT COLUMN ===== -->
          <div class="flex flex-col gap-5 min-w-0 uder-sticky-col">

            <!-- Main Illustration (Thumbnail) -->
            <section
              class="rounded-2xl border bg-base-200/50 overflow-hidden transition-colors {thumbnailDragOver ? 'border-primary/50 bg-primary/5' : 'border-base-content/10'}"
              ondragover={handleThumbnailDragOver}
              ondragleave={handleThumbnailDragLeave}
              ondrop={handleThumbnailDrop}
            >
              <input bind:this={thumbnailInputRef} onchange={handleThumbnailUpload} type="file" accept="image/*" class="hidden" />
              <button
                onclick={() => thumbnailInputRef?.click()}
                class="w-full aspect-[16/9] bg-base-300/40 flex items-center justify-center cursor-pointer hover:bg-base-300/60 transition-colors"
              >
                {#if thumbnail}
                  <div class="relative w-full h-full">
                    <img src={thumbnail} alt="thumbnail" class="w-full h-full object-cover" />
                    <button
                      onclick={(e) => { e.stopPropagation(); removeThumbnail(); }}
                      class="absolute top-2 right-2 p-1.5 rounded-lg bg-base-300/80 text-base-content/40 hover:text-error transition-colors"
                      title="Remove thumbnail"
                    >
                      <Icon icon="mdi:close" class="size-3.5" />
                    </button>
                  </div>
                {:else}
                  <div class="flex flex-col items-center gap-2 text-base-content/15">
                    <Icon icon="mdi:image-outline" class="size-10" />
                    <span class="text-[10px] font-mono">click to upload illustration</span>
                  </div>
                {/if}
              </button>
            </section>

            <!-- Summary Card -->
            <section class="rounded-2xl border border-base-content/10 bg-base-200/50 p-4">
              <div class="flex items-center gap-2 mb-2.5">
                <Icon icon="mdi:text-box-outline" class="size-3.5 text-base-content/30" />
                <span class="text-[10px] font-mono font-medium text-base-content/40 uppercase tracking-widest">summary</span>
              </div>
              {#if viewMode === "edit"}
                <textarea
                  bind:value={shortDescription}
                  placeholder="short synopsis, important notes, warnings..."
                  class="w-full min-h-[60px] bg-transparent text-xs text-base-content/45 leading-relaxed outline-none resize-none placeholder:text-base-content/15"
                ></textarea>
              {:else}
                <p class="text-xs text-base-content/45 leading-relaxed">{shortDescription || "\u2014"}</p>
              {/if}
            </section>

            <!-- Additional Media -->
            <section
              class="rounded-2xl border bg-base-200/50 overflow-hidden transition-colors {mediaSlotDragOver ? 'border-primary/50 bg-primary/5' : 'border-base-content/10'}"
              ondragover={handleMediaSlotDragOver}
              ondragleave={handleMediaSlotDragLeave}
              ondrop={handleMediaSlotDrop}
            >
              <div class="flex items-center gap-2 px-4 py-2.5 border-b border-base-content/10 bg-base-300/40">
                <Icon icon="mdi:gallery-outline" class="size-3.5 text-base-content/30" />
                <span class="text-[10px] font-mono font-medium text-base-content/40 uppercase tracking-widest">additional media</span>
                {#if mediaSlots.length > 0}
                  <span class="text-[9px] font-mono text-base-content/20 ml-auto">{mediaSlots.length}</span>
                {/if}
              </div>
              {#if mediaSlots.length > 0}
                <div class="p-3 overflow-x-auto">
                  <div class="flex gap-2.5">
                    {#each mediaSlots as url, i}
                      <div class="group relative shrink-0 w-32 h-24 rounded-xl border border-base-content/10 bg-base-300/40 overflow-hidden">
                        <img src={url} alt="media {i + 1}" class="w-full h-full object-cover" />
                        <button
                          onclick={() => removeMediaSlot(i)}
                          class="absolute top-1.5 right-1.5 p-1 rounded-lg bg-base-300/80 text-base-content/30 hover:text-error hover:bg-base-300 transition-all opacity-0 group-hover:opacity-100"
                          title="Remove"
                        >
                          <Icon icon="mdi:close" class="size-3" />
                        </button>
                      </div>
                    {/each}
                  </div>
                </div>
              {:else}
                <div class="px-4 py-6 flex flex-col items-center gap-1.5 text-base-content/15">
                  <Icon icon="mdi:image-plus-outline" class="size-6" />
                  <span class="text-[10px] font-mono text-center">drag images here</span>
                </div>
              {/if}
            </section>

          </div>

        </div>
      </div>
    </div>
  </div>

  <!-- ===== RIGHT SIDEBAR ===== -->
  <aside class="w-64 flex flex-col bg-base-200/60 rounded-xl border border-base-content/10 shrink-0 min-h-0 shadow-sm">
    <div class="flex items-center bg-base-200/60 backdrop-blur-sm rounded-t-xl border-b border-base-content/10 p-0.5 shrink-0">
      <button
        onclick={() => sidebarView = "metadata"}
        class="flex-1 text-[10px] font-mono font-medium py-1.5 rounded-md transition-all {sidebarView === 'metadata' ? 'bg-primary/15 text-primary shadow-sm' : 'text-base-content/40 hover:text-base-content/60'}"
      >metadata</button>
      <button
        onclick={() => sidebarView = "formatting"}
        class="flex-1 text-[10px] font-mono font-medium py-1.5 rounded-md transition-all {sidebarView === 'formatting' ? 'bg-primary/15 text-primary shadow-sm' : 'text-base-content/40 hover:text-base-content/60'}"
      >formatting</button>
    </div>
    <div class="flex-1 overflow-y-auto scrollbar-thin p-3 space-y-4">

      {#if sidebarView === "metadata"}
        <!-- Thumbnail Preview Card -->
        <div>
          <span class="text-[9px] font-mono text-base-content/30 uppercase tracking-widest mb-1.5 block">thumbnail preview</span>
          <div class="relative flex flex-col rounded-xl bg-base-200/40 border border-base-content/10 overflow-hidden">
            <div class="aspect-[16/9] w-full bg-base-300/50 flex items-center justify-center shrink-0">
              {#if thumbnail}
                <img src={thumbnail} alt="thumbnail" class="w-full h-full object-cover" />
              {:else}
                <Icon icon="material-symbols:image-outline-rounded" class="size-8 text-base-content/20" />
              {/if}
            </div>
            <div class="flex flex-col gap-2 p-4 grow">
              <h3 class="text-sm font-bold leading-snug">{title || "untitled"}</h3>
              <p class="text-xs opacity-50 leading-relaxed line-clamp-3">{shortDescription || "short description"}</p>
              {#if getPreviewTags().length > 0}
                <div class="flex gap-1.5 mt-auto pt-2 flex-nowrap overflow-hidden">
                  {#each getPreviewTags() as tag}
                    <span class="badge badge-xs border font-mono tracking-wider shrink-0 {getTagStyle(tag)}">{tag}</span>
                  {/each}
                </div>
              {/if}
            </div>
          </div>
        </div>

        <!-- Tags -->
        <div>
          <span class="text-[9px] font-mono text-base-content/30 uppercase tracking-widest mb-1.5 block">faction</span>
          <div class="flex flex-wrap gap-1.5">
            {#each factions as faction}
              {@const active = selectedFaction === faction}
              <button
                onclick={() => selectFaction(faction)}
                class="text-[9px] font-mono font-medium px-2 py-1 rounded-lg border transition-all cursor-pointer {active ? factionStyles[faction] : factionStylesInactive[faction]}"
              >
                {#if active}
                  <Icon icon="mdi:check" class="size-2.5 inline-block mr-0.5" />
                {/if}
                {faction}
              </button>
            {/each}
          </div>
        </div>
        <div>
          <span class="text-[9px] font-mono text-base-content/30 uppercase tracking-widest mb-1.5 block">type</span>
          <div class="flex flex-wrap gap-1.5">
            <button
              onclick={toggleExplorationRecord}
              class="text-[9px] font-mono font-medium px-2 py-1 rounded-lg border transition-all cursor-pointer {isExplorationRecord ? explorationStyle : explorationStyleInactive}"
            >
              {#if isExplorationRecord}
                <Icon icon="mdi:check" class="size-2.5 inline-block mr-0.5" />
              {/if}
              Exploration Record
            </button>
          </div>
        </div>

      {:else}
        <div>
          <span class="text-[9px] font-mono text-base-content/30 uppercase tracking-widest mb-1.5 block">colors</span>
          <div class="space-y-0.5">
            {#each colorsItems as item}
              <button
                onclick={() => insertFormatting(item.syntax)}
                class="w-full rounded-lg border border-base-content/5 overflow-hidden hover:bg-base-content/[3%] transition-colors cursor-pointer text-left"
              >
                <div class="flex items-center gap-2 px-2 py-1.5">
                  <span class="text-[10px] font-mono text-base-content/70 whitespace-nowrap shrink-0">{item.syntax}</span>
                  <span class="text-[10px] text-base-content/15 shrink-0">→</span>
                  <span class="text-[11px] {item.cls} truncate">{item.text}</span>
                </div>
              </button>
            {/each}
          </div>
        </div>
        <div>
          <span class="text-[9px] font-mono text-base-content/30 uppercase tracking-widest mb-1.5 block">text effects</span>
          <div class="space-y-0.5">
            {#each changingItems as item}
              <div class="rounded-xl border border-base-content/10 overflow-hidden bg-base-300/40">
                <div class="flex items-center">
                  <button onclick={() => insertFormatting(item.syntax)} class="flex-1 flex items-center gap-2 px-3 py-2 text-left hover:bg-base-content/[3%] transition-colors cursor-pointer">
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
        </div>
      {/if}

    </div>
  </aside>

</div>

<style>
  .uder-grid {
    display: grid;
    grid-template-columns: minmax(0, 3fr) minmax(300px, 2fr);
    gap: 1.5rem;
    align-items: start;
  }

  .uder-sticky-col {
    position: sticky;
    top: 1.5rem;
  }

  :global(.uder-editor h2),
  :global(.uder-editor h2::after),
  :global(.uder-editor h3),
  :global(.uder-editor h3::after) {
    all: unset;
  }
</style>
