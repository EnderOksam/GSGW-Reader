<script lang="ts">
  import { dev } from "$app/environment";
  import Icon from "@iconify/svelte";
  import JSZip from "jszip";
  import { onDestroy, tick, untrack } from "svelte";
  import book_meta from "$lib/meta.json";

  type Chapter = { title: string; slug: string; index: number };
  type PageBounds = {
    index: number;
    left: number;
    top: number;
    width: number;
    height: number;
    naturalWidth: number;
    naturalHeight: number;
  };
  type DragState = {
    pointerId: number;
    startClientX: number;
    startClientY: number;
    startCropX: number;
    startCropY: number;
    page: number;
  };

  const meta = book_meta as unknown as Record<string, Record<string, Chapter[]>>;
  const manwhaData = $derived(meta["manwha"] || {});
  const tls = $derived(Object.keys(manwhaData));

  const CROP_ASPECT = 3 / 4;
  const MIN_CROP_WIDTH = 80;
  const MAX_CROP_WIDTH = 800;
  const OUTPUT_WIDTH = 320;
  const OUTPUT_HEIGHT = 240;

  let selectedTL = $state("");
  let chapters = $derived(selectedTL ? manwhaData[selectedTL] || [] : []);
  let selectedSlug = $state("");
  let images = $state<string[]>([]);
  let loaded = $state(false);
  let loading = $state(false);
  let error = $state("");
  let previewDataUrl = $state("");
  let previewing = $state(false);
  let saving = $state(false);
  let feedback = $state("");
  let feedbackIsError = $state(false);
  let navEl = $state<HTMLElement | null>(null);
  let stripEl = $state<HTMLDivElement | null>(null);
  let bottomBarEl = $state<HTMLDivElement | null>(null);
  let pageBounds = $state<PageBounds[]>([]);
  let cropPage = $state(0);
  let cropX = $state(0);
  let cropY = $state(0);
  let cropWidth = $state(320);
  let cropHeight = $derived(Math.round(cropWidth * CROP_ASPECT));
  let maxCrop = $derived(maxCropForPage(cropPage));
  let loadToken = 0;
  let loadController: AbortController | null = null;
  let drag: DragState | null = null;

  function padSlug(s: string) {
    return s.padStart(4, "0");
  }

  function clamp(value: number, min: number, max: number) {
    return Math.max(min, Math.min(max, value));
  }

  function maxCropForPage(index: number) {
    const page = pageBounds[index];
    if (!page) return MAX_CROP_WIDTH;
    return Math.max(
      1,
      Math.floor(
        Math.min(MAX_CROP_WIDTH, page.width, page.height / CROP_ASPECT),
      ),
    );
  }

  function fitCropWidth(index: number) {
    const max = maxCropForPage(index);
    const min = Math.min(MIN_CROP_WIDTH, max);
    const next = clamp(Math.round(cropWidth), min, max);
    if (next !== cropWidth) cropWidth = next;
    return next;
  }

  function clearImages() {
    for (const src of images) URL.revokeObjectURL(src);
    images = [];
    pageBounds = [];
  }

  function clearPreview() {
    if (previewDataUrl) URL.revokeObjectURL(previewDataUrl);
    previewDataUrl = "";
  }

  function resetChapter() {
    loadToken++;
    loadController?.abort();
    loadController = null;
    clearImages();
    clearPreview();
    loaded = false;
    loading = false;
    error = "";
    feedback = "";
    pageBounds = [];
    cropPage = 0;
  }

  function preloadImages(urls: string[]) {
    return Promise.all(
      urls.map(
        (src) =>
          new Promise<void>((resolve, reject) => {
            const img = new Image();
            img.decoding = "async";
            img.onload = () => resolve();
            img.onerror = () => reject(new Error("Failed to load a page image"));
            img.src = src;
          }),
      ),
    );
  }

  async function loadChapter(tl: string, slug: string) {
    const token = ++loadToken;
    loadController?.abort();
    const controller = new AbortController();
    loadController = controller;

    clearImages();
    clearPreview();
    loaded = false;
    loading = true;
    error = "";
    feedback = "";
    feedbackIsError = false;

    let createdUrls: string[] = [];

    try {
      const url = `/chapters/manwha/${encodeURIComponent(tl)}/${padSlug(slug)}.cbz`;
      const res = await fetch(url, { signal: controller.signal });
      if (!res.ok) throw new Error(`CBZ not found (${res.status})`);
      const blob = await res.blob();
      const zip = await JSZip.loadAsync(blob);
      const names: string[] = [];
      zip.forEach((name, file) => {
        if (!file.dir && /\.(png|jpg|jpeg|webp|gif)$/i.test(name)) {
          names.push(name);
        }
      });
      names.sort((a, b) => a.localeCompare(b, undefined, { numeric: true }));
      if (names.length === 0) throw new Error("No images found in this CBZ");

      createdUrls = [];
      for (const name of names) {
        if (token !== loadToken) return;
        const file = zip.file(name);
        if (!file) continue;
        createdUrls.push(URL.createObjectURL(await file.async("blob")));
      }
      if (token !== loadToken) return;
      if (createdUrls.length === 0) {
        throw new Error("No images found in this CBZ");
      }

      await preloadImages(createdUrls);
      if (token !== loadToken) return;

      images = createdUrls;
      createdUrls = [];
      loaded = true;
      await tick();
      if (token !== loadToken) return;

      window.scrollTo(0, 0);
      measurePages();
      centerCropInView(0);
    } catch (e) {
      if (token !== loadToken || controller.signal.aborted) return;
      error = e instanceof Error ? e.message : String(e);
    } finally {
      if (token === loadToken) loading = false;
      for (const src of createdUrls) URL.revokeObjectURL(src);
    }
  }

  function measurePages() {
    const strip = stripEl;
    if (!strip) {
      pageBounds = [];
      return;
    }

    const stripRect = strip.getBoundingClientRect();
    const next: PageBounds[] = [];
    for (const [fallbackIndex, img] of Array.from(
      strip.querySelectorAll<HTMLImageElement>("img[data-page]"),
    ).entries()) {
      const rect = img.getBoundingClientRect();
      if (rect.width === 0 || rect.height === 0) continue;
      const index = Number(img.dataset.page ?? fallbackIndex);
      next[index] = {
        index,
        left: rect.left - stripRect.left,
        top: rect.top - stripRect.top,
        width: rect.width,
        height: rect.height,
        naturalWidth: img.naturalWidth,
        naturalHeight: img.naturalHeight,
      };
    }
    pageBounds = next;
  }

  function clampCropToPage(index = cropPage) {
    const page = pageBounds[index];
    if (!page) return;
    cropPage = index;
    const width = fitCropWidth(index);
    const height = Math.round(width * CROP_ASPECT);
    cropX = clamp(cropX, page.left, page.left + Math.max(0, page.width - width));
    cropY = clamp(
      cropY,
      page.top,
      page.top + Math.max(0, page.height - height),
    );
  }

  function scrollToPage(index: number) {
    const page = pageBounds[index];
    const strip = stripEl;
    if (!page || !strip) return;
    const stripTop = strip.getBoundingClientRect().top;
    const navHeight = navEl?.offsetHeight ?? 0;
    window.scrollTo({
      top: Math.max(0, window.scrollY + stripTop + page.top - navHeight - 12),
    });
  }

  function focusPage(index: number) {
    const page = pageBounds[index];
    if (!page) return;
    cropPage = index;
    const width = fitCropWidth(index);
    const height = Math.round(width * CROP_ASPECT);
    cropX = page.left + Math.max(0, (page.width - width) / 2);
    cropY = page.top + Math.min(24, Math.max(0, page.height - height));
    scrollToPage(index);
    clampCropToPage(index);
  }

  function centerCropInView(index = cropPage) {
    const page = pageBounds[index];
    const strip = stripEl;
    if (!page || !strip) return;

    cropPage = index;
    const width = fitCropWidth(index);
    const height = Math.round(width * CROP_ASPECT);
    const stripRect = strip.getBoundingClientRect();
    const pageTop = stripRect.top + page.top;
    const pageBottom = pageTop + page.height;
    const viewTop = Math.max(
      pageTop,
      navEl?.getBoundingClientRect().bottom ?? 0,
    );
    const viewBottom = Math.min(
      pageBottom,
      bottomBarEl?.getBoundingClientRect().top ?? window.innerHeight,
    );

    cropX = page.left + Math.max(0, (page.width - width) / 2);
    if (viewBottom - viewTop >= height) {
      cropY = viewTop + (viewBottom - viewTop - height) / 2 - stripRect.top;
    } else {
      cropY = page.top + Math.min(24, Math.max(0, page.height - height));
      scrollToPage(index);
    }
    clampCropToPage(index);
  }

  function setCropWidth(value: number) {
    if (!loaded) return;
    const max = maxCropForPage(cropPage);
    const min = Math.min(MIN_CROP_WIDTH, max);
    cropWidth = clamp(Math.round(value), min, max);
    clampCropToPage(cropPage);
  }

  function pageAtPoint(clientX: number, clientY: number) {
    const strip = stripEl;
    if (!strip) return null;
    const stripRect = strip.getBoundingClientRect();
    const x = clientX - stripRect.left;
    const y = clientY - stripRect.top;
    for (const page of pageBounds) {
      if (!page) continue;
      if (
        x >= page.left &&
        x <= page.left + page.width &&
        y >= page.top &&
        y <= page.top + page.height
      ) {
        return page;
      }
    }
    return null;
  }

  function moveCropToPoint(clientX: number, clientY: number) {
    const page = pageAtPoint(clientX, clientY);
    const strip = stripEl;
    if (!page || !strip) return;
    cropPage = page.index;
    const width = fitCropWidth(page.index);
    const height = Math.round(width * CROP_ASPECT);
    const stripRect = strip.getBoundingClientRect();
    cropX = clientX - stripRect.left - width / 2;
    cropY = clientY - stripRect.top - height / 2;
    clampCropToPage(page.index);
  }

  function onPageClick(e: MouseEvent, index: number) {
    if (e.detail === 0) {
      focusPage(index);
      return;
    }
    moveCropToPoint(e.clientX, e.clientY);
  }

  function onCropPointerDown(e: PointerEvent) {
    if (e.button !== 0 || !loaded) return;
    e.preventDefault();
    e.stopPropagation();
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    drag = {
      pointerId: e.pointerId,
      startClientX: e.clientX,
      startClientY: e.clientY,
      startCropX: cropX,
      startCropY: cropY,
      page: cropPage,
    };
  }

  function onCropPointerMove(e: PointerEvent) {
    if (!drag || drag.pointerId !== e.pointerId) return;
    const page = pageBounds[drag.page];
    if (!page) return;
    cropX = clamp(
      drag.startCropX + e.clientX - drag.startClientX,
      page.left,
      page.left + Math.max(0, page.width - cropWidth),
    );
    cropY = clamp(
      drag.startCropY + e.clientY - drag.startClientY,
      page.top,
      page.top + Math.max(0, page.height - cropHeight),
    );
  }

  function endCropDrag(e: PointerEvent) {
    if (!drag || drag.pointerId !== e.pointerId) return;
    const target = e.currentTarget as HTMLElement;
    if (target.hasPointerCapture?.(e.pointerId)) {
      target.releasePointerCapture(e.pointerId);
    }
    drag = null;
  }

  function loadImage(src: string) {
    return new Promise<HTMLImageElement>((resolve, reject) => {
      const img = new Image();
      img.onload = () => resolve(img);
      img.onerror = () => reject(new Error("Failed to load the crop source"));
      img.src = src;
    });
  }

  async function cropToBlob() {
    const page = pageBounds[cropPage];
    if (!page) throw new Error("No page is ready to crop");
    const src = images[page.index];
    if (!src) throw new Error("No page is ready to crop");
    if (!page.naturalWidth || !page.naturalHeight) {
      throw new Error("Page dimensions are not ready");
    }

    const scaleX = page.naturalWidth / page.width;
    const scaleY = page.naturalHeight / page.height;
    const sx = clamp(
      Math.round((cropX - page.left) * scaleX),
      0,
      page.naturalWidth - 1,
    );
    const sy = clamp(
      Math.round((cropY - page.top) * scaleY),
      0,
      page.naturalHeight - 1,
    );
    const sw = clamp(
      Math.round(cropWidth * scaleX),
      1,
      page.naturalWidth - sx,
    );
    const sh = clamp(
      Math.round(cropHeight * scaleY),
      1,
      page.naturalHeight - sy,
    );

    const img = await loadImage(src);
    const canvas = document.createElement("canvas");
    canvas.width = OUTPUT_WIDTH;
    canvas.height = OUTPUT_HEIGHT;
    const ctx = canvas.getContext("2d");
    if (!ctx) throw new Error("Could not create a canvas context");
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = "high";
    ctx.drawImage(
      img,
      sx,
      sy,
      sw,
      sh,
      0,
      0,
      OUTPUT_WIDTH,
      OUTPUT_HEIGHT,
    );

    return new Promise<Blob>((resolve, reject) => {
      canvas.toBlob(
        (blob) =>
          blob
            ? resolve(blob)
            : reject(new Error("Could not create the thumbnail")),
        "image/webp",
        0.8,
      );
    });
  }

  function blobToBase64(blob: Blob) {
    return new Promise<string>((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        const result = String(reader.result);
        resolve(result.slice(result.indexOf(",") + 1));
      };
      reader.onerror = () =>
        reject(reader.error ?? new Error("Could not read the thumbnail"));
      reader.readAsDataURL(blob);
    });
  }

  async function doPreview() {
    if (!loaded || previewing) return;
    previewing = true;
    feedback = "";
    feedbackIsError = false;
    try {
      const blob = await cropToBlob();
      clearPreview();
      previewDataUrl = URL.createObjectURL(blob);
    } catch (e) {
      feedback = e instanceof Error ? e.message : String(e);
      feedbackIsError = true;
    } finally {
      previewing = false;
    }
  }

  async function doSave() {
    if (!loaded || saving) return;
    const tl = selectedTL;
    const slug = selectedSlug;
    if (!tl || !slug) return;

    saving = true;
    feedback = "";
    feedbackIsError = false;
    try {
      const blob = await cropToBlob();
      const image = await blobToBase64(blob);
      if (tl !== selectedTL || slug !== selectedSlug) return;

      const res = await fetch("/dev/screenshot/save", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ slug, image }),
      });
      if (!res.ok) {
        const message = await res.text();
        throw new Error(message || `Save failed (${res.status})`);
      }
      feedback = "Saved thumbnail";
    } catch (e) {
      feedback = e instanceof Error ? e.message : String(e);
      feedbackIsError = true;
    } finally {
      saving = false;
    }
  }

  $effect(() => {
    const tl = selectedTL;
    const slug = selectedSlug;
    untrack(() => {
      if (!tl || !slug) {
        resetChapter();
        return;
      }
      void loadChapter(tl, slug);
    });
  });

  $effect(() => {
    const strip = stripEl;
    if (!loaded || !strip) return;

    untrack(() => {
      measurePages();
      clampCropToPage(cropPage);
    });

    const observer = new ResizeObserver(() => {
      measurePages();
      clampCropToPage(cropPage);
    });
    observer.observe(strip);
    return () => observer.disconnect();
  });

  onDestroy(() => {
    loadToken++;
    loadController?.abort();
    for (const src of images) URL.revokeObjectURL(src);
    if (previewDataUrl) URL.revokeObjectURL(previewDataUrl);
  });
</script>

<svelte:head>
  <title>Screenshot Tool – GSGW-Reader</title>
</svelte:head>

{#if !dev}
  <div class="flex items-center justify-center min-h-dvh p-8 text-center opacity-50">
    <p>Only available in dev mode</p>
  </div>
{:else}
  <nav
    bind:this={navEl}
    class="sticky top-0 z-50 flex w-full items-center justify-center gap-2 sm:gap-5 bg-base-100 border-b border-base-content/10 p-3"
  >
    <div class="tooltip tooltip-bottom" data-tip="Home">
      <a href="/book/manwha" class="btn btn-ghost btn-sm btn-square rounded-btn">
        <Icon icon="material-symbols:home-outline-rounded" class="size-6" />
      </a>
    </div>

    <select
      class="select select-bordered select-xs sm:select-sm rounded-btn max-w-[120px] sm:max-w-[180px]"
      bind:value={selectedTL}
      onchange={() => (selectedSlug = "")}
    >
      <option value="">TL</option>
      {#each tls as tl}
        <option value={tl}>{tl}</option>
      {/each}
    </select>

    <select class="select select-bordered select-xs sm:select-sm rounded-btn max-w-[100px] sm:max-w-[140px]" bind:value={selectedSlug}>
      <option value="">Ch.</option>
      {#each chapters as ch}
        <option value={ch.slug}>#{ch.slug}</option>
      {/each}
    </select>

    {#if loading}
      <Icon icon="svg-spinners:180-ring" class="size-5" />
    {/if}
  </nav>

  {#if error}
    <div class="flex items-center justify-center h-[60dvh] text-base-content/50 text-sm">{error}</div>
  {:else if loading && !loaded}
    <div class="flex flex-col items-center justify-center h-[60dvh] gap-3 text-base-content/50">
      <Icon icon="svg-spinners:180-ring" class="size-8" />
      <span class="text-sm">Loading chapter...</span>
    </div>
  {:else if !selectedTL || !selectedSlug}
    <div class="flex items-center justify-center h-[60dvh] text-base-content/50 text-sm">
      Select a translation and chapter above
    </div>
  {:else if loaded && images.length > 0}
    <main class="mx-auto w-full px-0 sm:px-6 md:px-12 pb-28" style="max-width: 39.2rem">
      <div
        id="strip"
        bind:this={stripEl}
        class="relative flex flex-col items-center w-full"
      >
        {#each images as src, i}
          <button
            type="button"
            class="block w-full p-0 border-0 bg-transparent leading-none cursor-crosshair"
            onclick={(e) => onPageClick(e, i)}
            aria-label="Move crop frame to page {i + 1}"
          >
            <img
              {src}
              alt="Page {i + 1}"
              class="w-full block select-none pointer-events-none"
              data-page={i}
              draggable="false"
            />
          </button>
        {/each}

        {#if pageBounds.length > 0}
          <div
            data-crop-overlay
            role="group"
            aria-label="Crop frame. Drag to move."
            class="absolute z-40 touch-none cursor-grab active:cursor-grabbing select-none rounded-lg bg-accent/15 outline-4 outline-accent"
            style="left: {cropX}px; top: {cropY}px; width: {cropWidth}px; height: {cropHeight}px; box-shadow: 0 0 0 9999px rgba(0,0,0,0.45);"
            title="Drag to move the crop frame"
            onpointerdown={onCropPointerDown}
            onpointermove={onCropPointerMove}
            onpointerup={endCropDrag}
            onpointercancel={endCropDrag}
          >
            <div class="absolute inset-0 pointer-events-none flex items-center justify-center">
              <div class="w-8 h-0.5 bg-white/80"></div>
              <div class="absolute h-8 w-0.5 bg-white/80"></div>
            </div>
            <div class="absolute top-1 left-1 pointer-events-none text-[10px] font-bold text-white/80 drop-shadow-[0_1px_2px_rgb(0,0,0)]">
              P{cropPage + 1} · {cropWidth}×{cropHeight}
            </div>
          </div>
        {/if}
      </div>
    </main>

    <div
      bind:this={bottomBarEl}
      data-screenshot-controls
      class="fixed bottom-0 z-50 w-full bg-base-100 border-t border-base-content/10 p-2 sm:p-3"
    >
      <div class="mx-auto flex w-full max-w-2xl flex-wrap items-center justify-center gap-2 sm:gap-3">
        <div class="tooltip tooltip-top" data-tip="Center frame in view">
          <button
            class="btn btn-ghost btn-sm btn-square rounded-btn"
            onclick={() => centerCropInView(cropPage)}
            disabled={!loaded}
          >
            <Icon icon="material-symbols:center-focus-strong" class="size-5" />
          </button>
        </div>
        <input
          type="range"
          min={Math.min(MIN_CROP_WIDTH, maxCrop)}
          max={maxCrop}
          step="10"
          value={cropWidth}
          oninput={(e) => setCropWidth(Number(e.currentTarget.value))}
          class="range range-sm w-20 sm:w-28"
          disabled={!loaded}
        />
        <span class="text-xs font-mono w-8 text-right">{cropWidth}</span>
        <div class="w-px h-6 bg-base-content/20"></div>
        <button
          class="btn btn-sm btn-soft rounded-btn gap-1.5"
          onclick={doPreview}
          disabled={!loaded || previewing || saving}
        >
          {#if previewing}
            <Icon icon="svg-spinners:180-ring" class="size-4" />
          {:else}
            <Icon icon="material-symbols:preview" class="size-4" />
          {/if}
          Preview
        </button>
        <button
          class="btn btn-sm btn-accent rounded-btn font-bold gap-1.5"
          onclick={doSave}
          disabled={!loaded || saving || previewing}
        >
          {#if saving}
            <Icon icon="svg-spinners:180-ring" class="size-4" />
          {:else}
            <Icon icon="material-symbols:save-rounded" class="size-4" />
          {/if}
          Save
        </button>
      </div>
      {#if feedback}
        <p
          class="mt-1 text-center text-xs {feedbackIsError ? 'text-error' : 'text-success'}"
          aria-live="polite"
        >
          {feedback}
        </p>
      {/if}
    </div>
  {/if}
{/if}

{#if previewDataUrl}
  <div
    class="fixed inset-0 z-[70] bg-black/70 flex items-center justify-center"
    role="dialog"
    aria-modal="true"
    aria-label="Thumbnail preview"
  >
    <button
      type="button"
      class="absolute inset-0 cursor-default"
      aria-label="Close preview"
      onclick={clearPreview}
    ></button>
    <div class="relative bg-base-100 p-6 rounded-xl shadow-2xl text-center">
      <h3 class="font-bold mb-3">Thumbnail preview</h3>
      <img src={previewDataUrl} alt="preview" class="rounded-lg mx-auto" style="image-rendering: pixelated; width: 320px; height: 240px;" />
      <p class="text-xs opacity-50 mt-2">320x240 WebP</p>
      <button class="btn btn-sm btn-ghost mt-3 rounded-btn" onclick={clearPreview}>Close</button>
    </div>
  </div>
{/if}

<style>
  :global(body) {
    margin: 0;
  }
</style>
