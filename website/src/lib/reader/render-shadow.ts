import { toCanvas } from "html-to-image";

// ---------------------------------------------------------------------------
// Shadow compositing pass.
// ---------------------------------------------------------------------------

const LEN = /^[-+]?(\d*\.)?\d+(px|em|rem)?$/i;

interface ShadowSpec {
  inset: boolean;
  x: number; // px, CSS space
  y: number;
  blur: number;
  spread: number;
  color: string;
}

// Split on a separator that sits outside any parens (keeps colors like
// oklch(0 0 0 / 0.4) intact).
function splitTop(s: string, sep: string): string[] {
  const out: string[] = [];
  let depth = 0;
  let cur = "";
  for (const ch of s) {
    if (ch === "(") depth++;
    else if (ch === ")") depth--;
    if (ch === sep && depth === 0) {
      out.push(cur.trim());
      cur = "";
    } else {
      cur += ch;
    }
  }
  if (cur.trim()) out.push(cur.trim());
  return out;
}

function tokenize(s: string): string[] {
  return splitTop(s, " ");
}

function parseShadowList(str: string, defaultColor: string): ShadowSpec[] {
  return splitTop(str, ",")
    .map((seg) => {
      const toks = tokenize(seg);
      const lens: number[] = [];
      let inset = false;
      let color = "";
      for (const t of toks) {
        if (t === "inset") { inset = true; continue; }
        if (LEN.test(t)) { lens.push(parseFloat(t)); continue; }
        color += (color ? " " : "") + t;
      }
      if (lens.length < 2) return null;
      const [x, y, blur = 0, spread = 0] = lens;
      return { inset, x, y, blur, spread, color: color || defaultColor };
    })
    .filter((s): s is ShadowSpec => s !== null);
}

// Pull every drop-shadow(...) out of a filter string.
function parseDropShadows(filter: string, defaultColor: string): ShadowSpec[] {
  const out: ShadowSpec[] = [];
  let idx = 0;
  while (idx < filter.length) {
    const start = filter.indexOf("drop-shadow(", idx);
    if (start === -1) break;
    // find the matching close paren
    let depth = 0;
    let end = start;
    for (; end < filter.length; end++) {
      const ch = filter[end];
      if (ch === "(") depth++;
      else if (ch === ")") {
        depth--;
        if (depth === 0) break;
      }
    }
    const inner = filter.slice(start + "drop-shadow(".length, end);
    const toks = tokenize(inner);
    const lens: number[] = [];
    let color = "";
    for (const t of toks) {
      if (LEN.test(t)) { lens.push(parseFloat(t)); continue; }
      color += (color ? " " : "") + t;
    }
    if (lens.length >= 2) {
      const [x, y, blur = 0] = lens;
      out.push({ inset: false, x, y, blur, spread: 0, color: color || defaultColor });
    }
    idx = end + 1;
  }
  return out;
}

function roundRectPath(
  ctx: CanvasRenderingContext2D,
  x: number, y: number, w: number, h: number, r: number,
): void {
  const radius = Math.max(0, Math.min(r, w / 2, h / 2));
  ctx.beginPath();
  if (typeof ctx.roundRect === "function") {
    ctx.roundRect(x, y, w, h, radius);
    ctx.closePath();
    return;
  }
  ctx.moveTo(x + radius, y);
  ctx.arcTo(x + w, y, x + w, y + h, radius);
  ctx.arcTo(x + w, y + h, x, y + h, radius);
  ctx.arcTo(x, y + h, x, y, radius);
  ctx.arcTo(x, y, x + w, y, radius);
  ctx.closePath();
}

function parseRadius(v: string): number {
  const m = /(\d+(?:\.\d+)?)px/.exec(v);
  return m ? parseFloat(m[1]) : 0;
}

// true on WebKit rasterizers (macOS Safari + all iOS browsers).
// Blink/Gecko render shadows natively, so the pass is skipped there.
export function needsShadowPass(ua: string = navigator.userAgent): boolean {
  const params = new URLSearchParams(window.location.search);
  if (params.has("forceShadowPass")) return true;
  if (params.has("noShadowPass")) return false;
  const hasWebKit = /AppleWebKit/i.test(ua);
  const isBlinkOrGecko = /Chrome\/|Chromium\/|Edg\/|OPR\/|Firefox\/|Gecko\//i.test(ua);
  return hasWebKit && !isBlinkOrGecko;
}

export interface PaintShadowsOptions {
  pixelRatio?: number;
  blurMultiplier?: number; // canvas shadowBlur is ~2x the CSS blur radius; tune visually
}

export async function paintShadows(
  canvas: HTMLCanvasElement,
  rootEl: HTMLElement,
  opts: PaintShadowsOptions = {},
): Promise<void> {
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  const gctx: CanvasRenderingContext2D = ctx;
  const rootRect = rootEl.getBoundingClientRect();
  if (rootRect.width === 0) return;

  const scale = opts.pixelRatio ?? canvas.width / rootRect.width;
  const blurMul = opts.blurMultiplier ?? 2;

  const scratch = document.createElement("canvas");
  scratch.width = canvas.width;
  scratch.height = canvas.height;
  const sctx = scratch.getContext("2d");
  if (!sctx) return;
  const gsctx: CanvasRenderingContext2D = sctx;

  const layerCache = new Map<Element, HTMLCanvasElement | null>();

  // ---- rect-based shadow (box-shadow, outset + inset) --------------------
  function paintOutset(spec: ShadowSpec, box: { x: number; y: number; w: number; h: number }, radius: number) {
    gsctx.clearRect(0, 0, scratch.width, scratch.height);
    const x = box.x + spec.x * scale - spec.spread * scale;
    const y = box.y + spec.y * scale - spec.spread * scale;
    const w = box.w + spec.spread * 2 * scale;
    const h = box.h + spec.spread * 2 * scale;
    gsctx.save();
    gsctx.shadowColor = spec.color;
    gsctx.shadowBlur = spec.blur * scale * blurMul;
    gsctx.shadowOffsetX = 0;
    gsctx.shadowOffsetY = 0;
    gsctx.fillStyle = spec.color;
    roundRectPath(gsctx, x, y, w, h, Math.max(0, radius + spec.spread * scale));
    gsctx.fill();
    // Erase ONLY the element's own box. The offset shape is the shadow itself
    gsctx.restore();
    gsctx.globalCompositeOperation = "destination-out";
    gsctx.fillStyle = "rgba(0,0,0,1)";
    roundRectPath(gsctx, box.x, box.y, box.w, box.h, radius);
    gsctx.fill();
    gsctx.globalCompositeOperation = "source-over";
    gctx.drawImage(scratch, 0, 0);
  }

  function paintInset(spec: ShadowSpec, box: { x: number; y: number; w: number; h: number }, radius: number) {
    gsctx.clearRect(0, 0, scratch.width, scratch.height);
    // fill a shape shifted by (-x,-y)
    const sx = box.x - spec.x * scale;
    const sy = box.y - spec.y * scale;
    gsctx.save();
    gsctx.shadowColor = spec.color;
    gsctx.shadowBlur = spec.blur * scale * blurMul;
    gsctx.shadowOffsetX = spec.x * scale;
    gsctx.shadowOffsetY = spec.y * scale;
    gsctx.fillStyle = spec.color;
    roundRectPath(gsctx, sx, sy, box.w, box.h, radius);
    gsctx.fill();
    gsctx.restore();
    // Erase the interior so the shape fill (an opaque copy of the shadow
    // color) and the middle of the halo don't wash out the whole box
    const ring = Math.max(0, (spec.spread + spec.blur) * scale);
    if (ring * 2 < Math.min(box.w, box.h)) {
      gsctx.globalCompositeOperation = "destination-out";
      gsctx.fillStyle = "rgba(0,0,0,1)";
      roundRectPath(
        gsctx,
        box.x + ring, box.y + ring,
        box.w - ring * 2, box.h - ring * 2,
        Math.max(0, radius - ring),
      );
      gsctx.fill();
      gsctx.globalCompositeOperation = "source-over";
    }
    // only keep the part inside the box
    gctx.save();
    roundRectPath(gctx, box.x, box.y, box.w, box.h, radius);
    gctx.clip();
    gctx.drawImage(scratch, 0, 0);
    gctx.restore();
  }

  // ---- glyph-based shadow (text-shadow, filter drop-shadow) --------------
  async function glyphLayer(el: Element): Promise<HTMLCanvasElement | null> {
    const cached = layerCache.get(el);
    if (cached !== undefined) return cached;
    let canvasOut: HTMLCanvasElement | null = null;
    try {
      canvasOut = await toCanvas(el as HTMLElement, {
        pixelRatio: scale,
        backgroundColor: "transparent",
      });
    } catch {
      canvasOut = null;
    }
    layerCache.set(el, canvasOut);
    return canvasOut;
  }

  async function paintGlyphShadows(
    el: Element,
    box: { x: number; y: number; w: number; h: number },
    shadows: ShadowSpec[],
  ): Promise<void> {
    if (!shadows.length) return;
    const layer = await glyphLayer(el);
    if (!layer) return;
    gsctx.clearRect(0, 0, scratch.width, scratch.height);
    gsctx.save();
    for (const spec of shadows) {
      gsctx.shadowColor = spec.color;
      gsctx.shadowBlur = spec.blur * scale * blurMul;
      gsctx.shadowOffsetX = spec.x * scale;
      gsctx.shadowOffsetY = spec.y * scale;
      gsctx.drawImage(layer, box.x, box.y, box.w, box.h);
    }
    // erase the element's own pixels from the scratch so shadows sit *behind*
    // the glyphs already present in the base canvas.
    gsctx.globalCompositeOperation = "destination-out";
    gsctx.shadowColor = "transparent";
    gsctx.shadowBlur = 0;
    gsctx.shadowOffsetX = 0;
    gsctx.shadowOffsetY = 0;
    gsctx.drawImage(layer, box.x, box.y, box.w, box.h);
    gsctx.restore();
    gctx.drawImage(scratch, 0, 0);
  }

  const els = Array.from(rootEl.querySelectorAll("*"));
  for (const el of els) {
    // A single element failing to rasterize (e.g. WebKit's shadow-compositing
    // bug on iOS) should skip that element, not abort the whole pass.
    try {
      await paintElement(el);
    } catch {
      continue;
    }
  }

  async function paintElement(el: Element): Promise<void> {
    let cs: CSSStyleDeclaration;
    try {
      cs = getComputedStyle(el);
    } catch {
      return;
    }
    const elRect = (el as HTMLElement).getBoundingClientRect();
    const box = {
      x: (elRect.left - rootRect.left) * scale,
      y: (elRect.top - rootRect.top) * scale,
      w: elRect.width * scale,
      h: elRect.height * scale,
    };
    if (box.w <= 0 || box.h <= 0) return;

    const defaultColor = cs.color;
    const radius = parseRadius(cs.borderRadius) * scale;

    // element-level box-shadow
    if (cs.boxShadow && cs.boxShadow !== "none") {
      for (const spec of parseShadowList(cs.boxShadow, defaultColor)) {
        if (spec.inset) paintInset(spec, box, radius);
        else paintOutset(spec, box, radius);
      }
    }

    // element-level text-shadow + filter drop-shadow
    const textShadows =
      cs.textShadow && cs.textShadow !== "none"
        ? parseShadowList(cs.textShadow, defaultColor)
        : [];
    const dropShadows =
      cs.filter && /drop-shadow/.test(cs.filter)
        ? parseDropShadows(cs.filter, defaultColor)
        : [];
    if (textShadows.length || dropShadows.length) {
      await paintGlyphShadows(el, box, [...textShadows, ...dropShadows]);
    }

    // pseudo-element box-shadows (window glows).
    for (const pseudo of ["::before", "::after"] as const) {
      let pcs: CSSStyleDeclaration;
      try {
        pcs = getComputedStyle(el, pseudo);
      } catch {
        return;
      }
      if (!pcs.boxShadow || pcs.boxShadow === "none") continue;
      const pRadius = parseRadius(pcs.borderRadius) * scale || radius;
      for (const spec of parseShadowList(pcs.boxShadow, defaultColor)) {
        if (spec.inset) paintInset(spec, box, pRadius);
        else paintOutset(spec, box, pRadius);
      }
    }
  }
}
