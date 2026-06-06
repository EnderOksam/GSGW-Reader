<script lang="ts">
  import { dev } from "$app/environment";
  import Icon from "@iconify/svelte";
  import JSZip from "jszip";
  import book_meta from "$lib/meta.json";

  const meta = book_meta as Record<string, Record<string, {title: string; slug: string; index: number}[]>>;
  const manwhaData = $derived(meta["manwha"] || {});
  const tls = $derived(Object.keys(manwhaData));

  let selectedTL = $state("");
  let chapters = $derived(selectedTL ? manwhaData[selectedTL] || [] : []);
  let selectedSlug = $state("");
  let images = $state<string[]>([]);
  let loaded = $state(false);
  let loading = $state(false);
  let error = $state("");
  let previewDataUrl = $state("");
  let cropWidth = $state(300);
  let maxCrop = $state(800);

  function getImgBounds() {
    const img = document.querySelector<HTMLImageElement>("#strip img");
    if (!img) return null;
    const r = img.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) return null;
    return r;
  }

  function padSlug(s: string) { return s.padStart(4, "0"); }

  async function loadChapter() {
    if (!selectedTL || !selectedSlug) return;
    loading = true;
    error = "";
    images = [];
    loaded = false;

    try {
      const url = `/chapters/manwha/${encodeURIComponent(selectedTL)}/${padSlug(selectedSlug)}.cbz`;
      const res = await fetch(url);
      if (!res.ok) throw new Error("CBZ not found");
      const blob = await res.blob();
      const zip = await JSZip.loadAsync(blob);
      const names: string[] = [];
      zip.forEach((name, file) => {
        if (!file.dir && /\.(png|jpg|jpeg|webp|gif)$/i.test(name)) names.push(name);
      });
      names.sort((a, b) => a.localeCompare(b, undefined, { numeric: true }));
      const urls: string[] = [];
      for (const name of names) {
        const file = zip.file(name);
        if (!file) continue;
        urls.push(URL.createObjectURL(await file.async("blob")));
      }
      images = urls;
      loaded = true;
      window.scrollTo(0, 0);
    } catch (e) {
      error = String(e);
    }
    loading = false;
  }

  $effect(() => {
    if (selectedTL && selectedSlug) loadChapter();
  });

  function getImageAtPoint(x: number, y: number): {img: HTMLImageElement; rect: DOMRect} | null {
    for (const img of document.querySelectorAll<HTMLImageElement>("#strip img")) {
      const r = img.getBoundingClientRect();
      if (x >= r.left && x <= r.right && y >= r.top && y <= r.bottom) {
        return { img, rect: r };
      }
    }
    return null;
  }

  function getCropRegion(): {page: number; sx: number; sy: number; sw: number; sh: number} | null {
    const overlay = document.getElementById("crop-overlay") as HTMLElement | null;
    if (!overlay) return null;
    const cr = overlay.getBoundingClientRect();
    for (const img of document.querySelectorAll<HTMLImageElement>("#strip img")) {
      const ir = img.getBoundingClientRect();
      if (cr.bottom > ir.top && cr.top < ir.bottom) {
        const scale = img.naturalWidth / ir.width;
        const page = parseInt(img.dataset.page || "0");
        return {
          page,
          sx: Math.round(Math.max(0, (cr.left - ir.left) * scale)),
          sy: Math.round(Math.max(0, (cr.top - ir.top) * scale)),
          sw: Math.round(Math.min(cr.width, ir.right - cr.left) * scale),
          sh: Math.round(Math.min(cr.height, ir.bottom - cr.top) * scale),
        };
      }
    }
    return null;
  }

  async function doPreview() {
    const region = getCropRegion();
    if (!region) return;
    const img = new Image();
    await new Promise<void>((r) => {
      img.onload = () => r();
      img.onerror = () => r();
      img.src = images[region.page];
    });
    const canvas = document.createElement("canvas");
    canvas.width = 320;
    canvas.height = 240;
    const ctx = canvas.getContext("2d")!;
    ctx.drawImage(img, region.sx, region.sy, region.sw, region.sh, 0, 0, 320, 240);
    canvas.toBlob((blob) => {
      if (blob) previewDataUrl = URL.createObjectURL(blob);
    }, "image/webp", 80);
  }

  async function doSave() {
    const region = getCropRegion();
    if (!region || !selectedTL || !selectedSlug) return;
    const img = new Image();
    await new Promise<void>((r) => {
      img.onload = () => r();
      img.onerror = () => r();
      img.src = images[region.page];
    });
    const canvas = document.createElement("canvas");
    canvas.width = 320;
    canvas.height = 240;
    const ctx = canvas.getContext("2d")!;
    ctx.drawImage(img, region.sx, region.sy, region.sw, region.sh, 0, 0, 320, 240);
    canvas.toBlob(async (blob) => {
      if (!blob) return;
      const reader = new FileReader();
      reader.onload = async () => {
        const base64 = (reader.result as string).split(",")[1];
        const res = await fetch("/api/screenshot/save", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({tl: selectedTL, slug: selectedSlug, image: base64}),
        });
        if (res.ok) {
          alert("Saved!");
        } else {
          alert("Error: " + (await res.text()));
        }
      };
      reader.readAsDataURL(blob);
    }, "image/webp", 80);
  }

  function centerOverlay() {
    const overlay = document.getElementById("crop-overlay") as HTMLElement | null;
    if (!overlay) return;
    const b = getImgBounds();
    if (b) {
      overlay.style.left = b.left + (b.width - overlay.offsetWidth) / 2 + "px";
      overlay.style.top = b.top + (b.height - overlay.offsetHeight) / 2 + "px";
    } else {
      const nav = document.querySelector("nav");
      const offset = nav ? nav.getBoundingClientRect().height : 0;
      overlay.style.left = Math.max(0, (window.innerWidth - overlay.offsetWidth) / 2) + "px";
      overlay.style.top = offset + "px";
    }
  }

  $effect(() => {
    if (!loaded || !images.length) return;
    cropWidth;
    const overlay = document.getElementById("crop-overlay") as HTMLElement | null;
    if (!overlay) return;

    const nav = document.querySelector("nav");
    const offset = nav ? nav.getBoundingClientRect().height : 0;
    const bounds = getImgBounds();
    const maxW = bounds ? bounds.width : window.innerWidth;
    maxCrop = Math.min(maxW, 800);
    if (cropWidth > maxCrop) cropWidth = maxCrop;
    overlay.style.width = cropWidth + "px";
    overlay.style.left = bounds ? bounds.left + (bounds.width - overlay.offsetWidth) / 2 + "px" : Math.max(0, (window.innerWidth - overlay.offsetWidth) / 2) + "px";
    overlay.style.top = bounds ? bounds.top + (bounds.height - overlay.offsetHeight) / 2 + "px" : offset + "px";

    let isDrag = false, ox = 0, oy = 0;

    function clampX(x: number) {
      const b = getImgBounds();
      if (!b) return Math.max(0, Math.min(x, window.innerWidth - overlay.offsetWidth));
      return Math.max(b.left, Math.min(x, b.right - overlay.offsetWidth));
    }

    function clampY(y: number) {
      const b = getImgBounds();
      if (!b) {
        const nav = document.querySelector("nav");
        const minY = nav ? nav.getBoundingClientRect().height : 0;
        return Math.max(minY, Math.min(y, window.innerHeight - overlay.offsetHeight));
      }
      return Math.max(b.top, Math.min(y, b.bottom - overlay.offsetHeight));
    }

    function onDown(e: MouseEvent) {
      isDrag = true;
      ox = e.clientX - overlay.offsetLeft;
      oy = e.clientY - overlay.offsetTop;
      document.addEventListener("mousemove", onMove);
      document.addEventListener("mouseup", onUp);
      e.preventDefault();
    }

    function onMove(e: MouseEvent) {
      if (!isDrag) return;
      overlay.style.left = clampX(e.clientX - ox) + "px";
      overlay.style.top = clampY(e.clientY - oy) + "px";
    }

    function onUp() {
      isDrag = false;
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup", onUp);
    }

    function onStripClick(e: MouseEvent) {
      if ((e.target as HTMLElement)?.closest("#crop-overlay")) return;
      const ow = overlay.offsetWidth;
      const oh = overlay.offsetHeight;
      overlay.style.left = clampX(e.clientX - ow / 2) + "px";
      overlay.style.top = clampY(e.clientY - oh / 2) + "px";
    }

    overlay.addEventListener("mousedown", onDown);

    const strip = document.getElementById("strip");
    strip?.addEventListener("click", onStripClick);

    const onResize = () => {
      const b = getImgBounds();
      if (b && overlay) {
        const newMax = Math.min(b.width, 800);
        maxCrop = newMax;
        if (cropWidth > newMax) cropWidth = newMax;
        overlay.style.width = cropWidth + "px";
      }
      const l = parseInt(overlay.style.left) || 0;
      const t = parseInt(overlay.style.top) || 0;
      overlay.style.left = clampX(l) + "px";
      overlay.style.top = clampY(t) + "px";
    };
    window.addEventListener("resize", onResize);

    const ro = new ResizeObserver(onResize);
    const stripEl = document.getElementById("strip");
    if (stripEl) ro.observe(stripEl);

    return () => {
      overlay.removeEventListener("mousedown", onDown);
      strip?.removeEventListener("click", onStripClick);
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup", onUp);
      window.removeEventListener("resize", onResize);
      ro.disconnect();
    };
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
  <nav class="sticky top-0 z-50 flex w-full items-center justify-center gap-2 sm:gap-5 bg-base-100 border-b border-base-content/10 p-3">
    <div class="tooltip tooltip-bottom" data-tip="Home">
      <a href="/book/manwha" class="btn btn-ghost btn-sm btn-square rounded-btn">
        <Icon icon="material-symbols:home-outline-rounded" class="size-6" />
      </a>
    </div>

    <select class="select select-bordered select-xs sm:select-sm rounded-btn max-w-[120px] sm:max-w-[180px]" bind:value={selectedTL}>
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
    <main class="mx-auto w-full px-0 sm:px-6 md:px-12 pb-16" style="max-width: 39.2rem">
      <div id="strip" class="flex flex-col items-center w-full">
        {#each images as src, i}
          <img {src} alt="Page {i + 1}" class="w-full block" data-page={i} />
        {/each}
      </div>
    </main>

    <div id="crop-overlay"
      class="fixed z-40 rounded-lg bg-accent/15 outline-4 outline-accent cursor-grab active:cursor-grabbing select-none"
      style="width: {Math.min(cropWidth, 800)}px; aspect-ratio: 4/3; top: 60px; left: 0; box-shadow: 0 0 0 9999px rgba(0,0,0,0.45);">
      <div class="absolute inset-0 pointer-events-none flex items-center justify-center">
        <div class="w-8 h-0.5 bg-white/80"></div>
        <div class="absolute h-8 w-0.5 bg-white/80"></div>
      </div>
      <div class="absolute top-1 left-1 text-[10px] font-bold text-white/80 drop-shadow-[0_1px_2px_rgb(0,0,0)]">
        {cropWidth}×{Math.round(cropWidth * 3 / 4)}
      </div>
    </div>

    <div class="fixed bottom-0 z-50 flex w-full items-center justify-center gap-3 bg-base-100 border-t border-base-content/10 p-3">
      <div class="tooltip tooltip-top" data-tip="Center frame">
        <button class="btn btn-ghost btn-sm btn-square rounded-btn" onclick={centerOverlay}>
          <Icon icon="material-symbols:center-focus-strong" class="size-5" />
        </button>
      </div>
      <input type="range" min="100" max={maxCrop} step="10" bind:value={cropWidth} class="range range-sm w-20 sm:w-28" />
      <span class="text-xs font-mono w-8 text-right">{cropWidth}</span>
      <div class="w-px h-6 bg-base-content/20"></div>
      <button class="btn btn-sm btn-soft rounded-btn gap-1.5" onclick={doPreview}>
        <Icon icon="material-symbols:preview" class="size-4" /> Preview
      </button>
      <button class="btn btn-sm btn-accent rounded-btn font-bold gap-1.5" onclick={doSave}>
        <Icon icon="material-symbols:save-rounded" class="size-4" /> Save
      </button>
    </div>
  {/if}
{/if}

{#if previewDataUrl}
  <div class="fixed inset-0 z-[70] bg-black/70 flex items-center justify-center" onclick={() => (previewDataUrl = "")}>
    <div class="bg-base-100 p-6 rounded-xl shadow-2xl text-center" onclick={(e) => e.stopPropagation()}>
      <h3 class="font-bold mb-3">Thumbnail preview</h3>
      <img src={previewDataUrl} alt="preview" class="rounded-lg mx-auto" style="image-rendering: pixelated; width: 320px; height: 240px;" />
      <p class="text-xs opacity-50 mt-2">320x240 WebP</p>
      <button class="btn btn-sm btn-ghost mt-3 rounded-btn" onclick={() => (previewDataUrl = "")}>Close</button>
    </div>
  </div>
{/if}

<style>
  :global(body) {
    margin: 0;
  }
</style>
