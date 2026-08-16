<script lang="ts">
  import Icon from "@iconify/svelte";
  import {
    NODE_LABELS,
    NODE_ICONS,
    NODE_COLORS,
    OPERATOR_LABELS,
    MUTATION_LABELS,
    nodeOutputs,
    type UderNode,
  } from "./lib/nodes";
  import {
    graph,
    setSelected,
    setViewport,
    deleteNode,
    removeEdge,
    clampNode,
    settleNode,
    addEdge,
    undo,
    redo,
    canUndo,
    canRedo,
    captureHistory,
    CANVAS_SIZE,
    NODE_WIDTH,
  } from "./lib/node-graph-store.svelte.ts";
  import UderText from "./UderText.svelte";

  const MIN_SCALE = 0.25;
  const MAX_SCALE = 3;
  const PORT_Y = 18;
  const PORT_SIZE = 16;
  const CHOICE_PORT_SPACING = 26;
  const PORT_HIT = 18;

  let wrapRef: HTMLDivElement | undefined = $state();
  let wrapSize = $state({ w: 0, h: 0 });

  function minScaleFor(el: HTMLElement): number {
    return Math.max(MIN_SCALE, (Math.max(el.clientWidth, el.clientHeight) * 1.2) / CANVAS_SIZE);
  }

  let canvasX = $state(0);
  let canvasY = $state(0);
  let canvasScale = $state(1);
  let canvasDragging = $state(false);
  let canvasPanStart = $state({ x: 0, y: 0 });
  let canvasOffsetStart = $state({ x: 0, y: 0 });

  let draggingNodeId = $state<string | null>(null);
  let dragPointerStart = $state({ x: 0, y: 0 });
  let dragNodeStart = $state({ x: 0, y: 0 });
  let dragCaptured = false;
  let wiring = $state<{ from: string; fromPort: number; x: number; y: number } | null>(null);

  const resourceNodes = $derived(graph.nodes.filter((n) => n.type === "resource"));

  const cardHeights = $state<Record<string, number>>({});

  $effect(() => {
    const el = wrapRef;
    if (!el) return;
    const handler = (e: WheelEvent) => handleWheel(e);
    el.addEventListener("wheel", handler, { passive: false });
    return () => el.removeEventListener("wheel", handler);
  });

  $effect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.ctrlKey || e.metaKey || e.altKey) return;
      const t = e.target as HTMLElement | null;
      if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.isContentEditable)) return;
      if (e.key === "+" || e.key === "=") {
        e.preventDefault();
        zoomStep(1.25);
      } else if (e.key === "-" || e.key === "_") {
        e.preventDefault();
        zoomStep(1 / 1.25);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  });

  $effect(() => {
    const handler = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement | null;
      if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.isContentEditable)) return;
      if ((e.ctrlKey || e.metaKey) && !e.altKey) {
        const key = e.key.toLowerCase();
        if (key === "z") {
          e.preventDefault();
          if (e.shiftKey) redo();
          else undo();
        } else if (key === "y") {
          e.preventDefault();
          redo();
        }
      } else if (e.key === "Delete" || e.key === "Backspace") {
        if (!graph.selectedId) return;
        e.preventDefault();
        deleteNode(graph.selectedId);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  });

  $effect(() => {
    const el = wrapRef;
    if (!el) return;
    const ro = new ResizeObserver(() => {
      wrapSize = { w: el.clientWidth, h: el.clientHeight };
    });
    ro.observe(el);
    wrapSize = { w: el.clientWidth, h: el.clientHeight };
    return () => ro.disconnect();
  });

  $effect(() => {
    setViewport({ x: canvasX, y: canvasY, scale: canvasScale, width: wrapSize.w, height: wrapSize.h });
  });

  $effect(() => {
    const el = wrapRef;
    if (!el) return;
    const floor = minScaleFor(el);
    if (canvasScale < floor) {
      canvasScale = floor;
      clampCanvas();
    }
  });

  function toCanvas(e: PointerEvent): { x: number; y: number } {
    const el = wrapRef!;
    const rect = el.getBoundingClientRect();
    return {
      x: (e.clientX - rect.left - canvasX) / canvasScale,
      y: (e.clientY - rect.top - canvasY) / canvasScale,
    };
  }

  function clampCanvas() {
    const el = wrapRef;
    if (!el) return;
    const cw = CANVAS_SIZE * canvasScale;
    const ch = CANVAS_SIZE * canvasScale;
    const keep = 48;
    canvasX = Math.max(keep - cw, Math.min(el.clientWidth - keep, canvasX));
    canvasY = Math.max(keep - ch, Math.min(el.clientHeight - keep, canvasY));
  }

  function handleWheel(e: WheelEvent) {
    e.preventDefault();
    const el = wrapRef;
    if (!el) return;
    let dy = e.deltaY;
    if (e.deltaMode === 1) dy *= 16;
    else if (e.deltaMode === 2) dy *= el.clientHeight;
    const rect = el.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    const factor = Math.exp(-dy * 0.0015);
    const newScale = Math.min(MAX_SCALE, Math.max(minScaleFor(el), canvasScale * factor));
    if (newScale === canvasScale) return;
    const cx = (mx - canvasX) / canvasScale;
    const cy = (my - canvasY) / canvasScale;
    canvasScale = newScale;
    canvasX = mx - cx * newScale;
    canvasY = my - cy * newScale;
    clampCanvas();
  }

  function zoomStep(factor: number) {
    const el = wrapRef;
    if (!el) return;
    const mx = el.clientWidth / 2;
    const my = el.clientHeight / 2;
    const newScale = Math.min(MAX_SCALE, Math.max(minScaleFor(el), canvasScale * factor));
    if (newScale === canvasScale) return;
    const cx = (mx - canvasX) / canvasScale;
    const cy = (my - canvasY) / canvasScale;
    canvasScale = newScale;
    canvasX = mx - cx * newScale;
    canvasY = my - cy * newScale;
    clampCanvas();
  }

  function canvasPointerDown(e: PointerEvent) {
    if (e.button !== 0) return;
    const t = e.target as HTMLElement;
    if (t.closest?.(".node-card, .node-port, .node-edges, .zoom-controls")) return;
    setSelected(null);
    canvasDragging = true;
    canvasPanStart = { x: e.clientX, y: e.clientY };
    canvasOffsetStart = { x: canvasX, y: canvasY };
    window.addEventListener("pointermove", panPointerMove);
    window.addEventListener("pointerup", panPointerUp);
    window.addEventListener("pointercancel", panPointerUp);
  }

  function panPointerMove(e: PointerEvent) {
    if (!canvasDragging) return;
    canvasX = canvasOffsetStart.x + (e.clientX - canvasPanStart.x);
    canvasY = canvasOffsetStart.y + (e.clientY - canvasPanStart.y);
    clampCanvas();
  }

  function panPointerUp() {
    canvasDragging = false;
    window.removeEventListener("pointermove", panPointerMove);
    window.removeEventListener("pointerup", panPointerUp);
    window.removeEventListener("pointercancel", panPointerUp);
  }

  function nodePointerDown(e: PointerEvent, id: string) {
    const t = e.target as HTMLElement;
    if (t.closest?.("input, textarea, select, button")) return;
    e.stopPropagation();
    e.preventDefault();
    setSelected(id);
    const n = graph.nodes.find((x) => x.id === id);
    if (!n) return;
    draggingNodeId = id;
    dragCaptured = false;
    dragPointerStart = toCanvas(e);
    dragNodeStart = { x: n.x, y: n.y };
    (e.currentTarget as HTMLElement).setPointerCapture?.(e.pointerId);
  }

  function nodePointerMove(e: PointerEvent, id: string) {
    if (draggingNodeId !== id) return;
    if (!dragCaptured) {
      captureHistory();
      dragCaptured = true;
    }
    const p = toCanvas(e);
    const dx = p.x - dragPointerStart.x;
    const dy = p.y - dragPointerStart.y;
    graph.nodes = graph.nodes.map((n) => {
      if (n.id === id) {
        return clampNode({ ...n, x: dragNodeStart.x + dx, y: dragNodeStart.y + dy });
      }
      return n;
    });
  }

  function nodePointerUp() {
    const id = draggingNodeId;
    draggingNodeId = null;
    if (id) settleNode(id);
  }

  function inputSideOf(n: UderNode): "left" | "right" {
    let stored: "left" | "right" | null = null;
    let left = 0;
    let right = 0;
    const cx = n.x + NODE_WIDTH / 2;
    for (const e of graph.edges) {
      if (e.to !== n.id) continue;
      if (e.toSide) stored = stored ?? e.toSide;
      const src = graph.nodes.find((m) => m.id === e.from);
      if (!src) continue;
      if (src.x + NODE_WIDTH / 2 < cx) left++;
      else right++;
    }
    if (stored) return stored;
    return right > left ? "right" : "left";
  }

  function isFailPort(n: UderNode, i: number): boolean {
    return (n.type === "condition" || n.type === "chance") && i === 1;
  }

  function defaultNodeHeight(n: UderNode): number {
    if (n.type === "loop_start") return 30;
    if (n.type === "resource") return 74;
    if (n.type === "choice" || n.type === "start") return 100;
    return 88;
  }

  function measuredHeight(n: UderNode): number {
    if (n.type === "condition" || n.type === "chance" || n.type === "addition") {
      return cardHeights[n.id] ?? defaultNodeHeight(n);
    }
    return defaultNodeHeight(n);
  }

  function outputPortPos(n: UderNode, i: number): { x: number; y: number } {
    if (isFailPort(n, i)) return { x: n.x + NODE_WIDTH / 2, y: n.y + measuredHeight(n) };
    const count = nodeOutputs(n);
    const y = count > 1 ? PORT_Y + i * CHOICE_PORT_SPACING : PORT_Y;
    const x = inputSideOf(n) === "right" ? n.x : n.x + NODE_WIDTH;
    return { x, y: n.y + y };
  }

  function inputPortPos(n: UderNode): { x: number; y: number } {
    const x = inputSideOf(n) === "right" ? n.x + NODE_WIDTH : n.x;
    return { x, y: n.y + PORT_Y };
  }

  interface Rect { x0: number; y0: number; x1: number; y1: number }

  function nodeRect(n: UderNode): Rect | null {
    const PAD = 8;
    const h = measuredHeight(n);
    return { x0: n.x - PAD, y0: n.y - PAD, x1: n.x + NODE_WIDTH + PAD, y1: n.y + h + PAD };
  }

  function pointInRect(p: { x: number; y: number }, r: Rect): boolean {
    return p.x > r.x0 && p.x < r.x1 && p.y > r.y0 && p.y < r.y1;
  }

  function segHitsRect(s: { x1: number; y1: number; x2: number; y2: number }, r: Rect): boolean {
    const xa = Math.min(s.x1, s.x2), xb = Math.max(s.x1, s.x2);
    const ya = Math.min(s.y1, s.y2), yb = Math.max(s.y1, s.y2);
    return xa < r.x1 && xb > r.x0 && ya < r.y1 && yb > r.y0;
  }

  function polyHitsRect(pts: { x: number; y: number }[], r: Rect): boolean {
    for (let i = 0; i < pts.length - 1; i++) {
      if (segHitsRect({ x1: pts[i].x, y1: pts[i].y, x2: pts[i + 1].x, y2: pts[i + 1].y }, r)) return true;
    }
    return false;
  }

  function bezierPoint(p0: { x: number; y: number }, p1: { x: number; y: number }, p2: { x: number; y: number }, p3: { x: number; y: number }, t: number) {
    const u = 1 - t;
    return {
      x: u * u * u * p0.x + 3 * u * u * t * p1.x + 3 * u * t * t * p2.x + t * t * t * p3.x,
      y: u * u * u * p0.y + 3 * u * u * t * p1.y + 3 * u * t * t * p2.y + t * t * t * p3.y,
    };
  }

  function bezierHitsRect(a: { x: number; y: number }, p1: { x: number; y: number }, p2: { x: number; y: number }, b: { x: number; y: number }, rects: Rect[]): boolean {
    for (let i = 0; i <= 24; i++) {
      const pt = bezierPoint(a, p1, p2, b, i / 24);
      if (rects.some((r) => pointInRect(pt, r))) return true;
    }
    return false;
  }

  function polylinePath(pts: { x: number; y: number }[], r: number): string {
    let d = `M ${pts[0].x} ${pts[0].y}`;
    for (let i = 1; i < pts.length - 1; i++) {
      const p0 = pts[i - 1], p1 = pts[i], p2 = pts[i + 1];
      const l1 = Math.hypot(p1.x - p0.x, p1.y - p0.y);
      const l2 = Math.hypot(p2.x - p1.x, p2.y - p1.y);
      const rr = Math.min(r, l1 / 2, l2 / 2);
      if (rr <= 0) {
        d += ` L ${p1.x} ${p1.y}`;
        continue;
      }
      const c1 = { x: p1.x + (p0.x - p1.x) * (rr / l1), y: p1.y + (p0.y - p1.y) * (rr / l1) };
      const c2 = { x: p1.x + (p2.x - p1.x) * (rr / l2), y: p1.y + (p2.y - p1.y) * (rr / l2) };
      d += ` L ${c1.x} ${c1.y} Q ${p1.x} ${p1.y}, ${c2.x} ${c2.y}`;
    }
    const last = pts[pts.length - 1];
    return d + ` L ${last.x} ${last.y}`;
  }

  function shrunkRect(n: UderNode): Rect | null {
    const h = measuredHeight(n);
    return { x0: n.x, y0: n.y, x1: n.x + NODE_WIDTH, y1: n.y + h };
  }

  function edgePath(
    a: { x: number; y: number },
    b: { x: number; y: number },
    from: UderNode | null,
    to: UderNode | null,
    outSide: "left" | "right" | "down",
    inSide: "left" | "right"
  ): string {
    const excluded = new Set([from?.id, to?.id].filter((id): id is string => !!id));
    const others = graph.nodes
      .filter((n) => !excluded.has(n.id))
      .map(nodeRect)
      .filter((r): r is Rect => r !== null);
    const own = [from, to].map((n) => (n ? shrunkRect(n) : null)).filter((r): r is Rect => r !== null);

    const k = Math.max(40, Math.min(160, Math.abs(b.x - a.x) * 0.45));
    const p1 =
      outSide === "right"
        ? { x: a.x + k, y: a.y }
        : outSide === "down"
          ? { x: a.x, y: a.y + k }
          : { x: a.x - k, y: a.y };
    const p2 = { x: inSide === "right" ? b.x + k : b.x - k, y: b.y };
    if (!bezierHitsRect(a, p1, p2, b, others) && !bezierHitsRect(a, p1, p2, b, own)) {
      return `M ${a.x} ${a.y} C ${p1.x} ${p1.y}, ${p2.x} ${p2.y}, ${b.x} ${b.y}`;
    }

    const midX = (a.x + b.x) / 2;
    const xlo = Math.min(a.x, b.x), xhi = Math.max(a.x, b.x);
    const laneRects = graph.nodes
      .map((n) => (excluded.has(n.id) ? shrunkRect(n) : nodeRect(n)))
      .filter((r): r is Rect => r !== null);
    const relevant = laneRects.filter((r) => r.x1 > xlo - 40 && r.x0 < xhi + 40);
    const laneAbove = Math.min(a.y, b.y, ...relevant.map((r) => r.y0)) - 44;
    const laneBelow = Math.max(a.y, b.y, ...relevant.map((r) => r.y1)) + 44;

    const wrapX = b.x + (inSide === "right" ? 20 : -20);
    const candidates: { x: number; y: number }[][] = [
      [{ x: a.x, y: a.y }, { x: wrapX, y: a.y }, { x: wrapX, y: b.y }, { x: b.x, y: b.y }],
      [{ x: a.x, y: a.y }, { x: midX, y: a.y }, { x: midX, y: b.y }, { x: b.x, y: b.y }],
      [{ x: a.x, y: a.y }, { x: a.x, y: laneAbove }, { x: b.x, y: laneAbove }, { x: b.x, y: b.y }],
      [{ x: a.x, y: a.y }, { x: a.x, y: laneBelow }, { x: b.x, y: laneBelow }, { x: b.x, y: b.y }],
      [{ x: a.x, y: a.y }, { x: b.x, y: a.y }, { x: b.x, y: b.y }],
      [{ x: a.x, y: a.y }, { x: a.x, y: b.y }, { x: b.x, y: b.y }],
    ];

    for (const pts of candidates) {
      if (!laneRects.some((r) => polyHitsRect(pts, r))) return polylinePath(pts, 12);
    }
    return `M ${a.x} ${a.y} L ${b.x} ${b.y}`;
  }

  function portPointerDown(e: PointerEvent, nodeId: string, portIndex: number) {
    e.stopPropagation();
    e.preventDefault();
    const p = toCanvas(e);
    wiring = { from: nodeId, fromPort: portIndex, x: p.x, y: p.y };
    (e.currentTarget as HTMLElement).setPointerCapture?.(e.pointerId);
  }

  function portPointerMove(e: PointerEvent) {
    if (!wiring) return;
    const p = toCanvas(e);
    wiring = { ...wiring, x: p.x, y: p.y };
  }

  function portPointerUp(e: PointerEvent) {
    if (!wiring) return;
    const w = wiring;
    const p = toCanvas(e);
    for (const n of graph.nodes) {
      if (n.id === w.from) continue;
      if (n.type === "resource") continue;
      const ip = inputPortPos(n);
      const nearPort = Math.hypot(ip.x - p.x, ip.y - p.y) < PORT_HIT;
      const hasInput = graph.edges.some((en) => en.to === n.id);
      const freeSide = !hasInput && n.type !== "start";
      const nearAnySide =
        Math.abs(p.y - (n.y + PORT_Y)) < PORT_HIT && p.x > n.x - PORT_HIT && p.x < n.x + NODE_WIDTH + PORT_HIT;
      if (nearPort || (freeSide && nearAnySide)) {
        const toSide: "left" | "right" = p.x > n.x + NODE_WIDTH / 2 ? "right" : "left";
        addEdge(w.from, w.fromPort, n.id, toSide);
        break;
      }
    }
    wiring = null;
  }

  function resourceName(id: string): string {
    return resourceNodes.find((r) => r.id === id)?.title || "";
  }
</script>

<div
  bind:this={wrapRef}
  class="node-graph-wrap {canvasDragging ? 'cursor-grabbing' : 'cursor-grab'}"
  onpointerdown={canvasPointerDown}
  oncontextmenu={(e) => e.preventDefault()}
  role="region"
  aria-label="U-DER node graph"
>
  <div
    class="node-graph-canvas"
    style:transform={`translate3d(${canvasX}px, ${canvasY}px, 0) scale(${canvasScale})`}
  >
    <svg class="node-edges" width={CANVAS_SIZE} height={CANVAS_SIZE} role="presentation">
      {#each graph.edges as edge}
        {@const from = graph.nodes.find((n) => n.id === edge.from)}
        {@const to = graph.nodes.find((n) => n.id === edge.to)}
        {#if from && to && (from.type === "start" || graph.edges.some((en) => en.to === from.id))}
          {@const a = outputPortPos(from, edge.fromPort)}
          {@const b = inputPortPos(to)}
          {@const outSide = isFailPort(from, edge.fromPort) ? "down" : (inputSideOf(from) === "right" ? "left" : "right")}
          {@const d = edgePath(a, b, from, to, outSide, inputSideOf(to))}
          <path
            class="node-edge-hit"
            d={d}
            role="button"
            tabindex="-1"
            onclick={() => removeEdge(edge.id)}
            onkeydown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); removeEdge(edge.id); } }}
          />
          <path class="node-edge {isFailPort(from, edge.fromPort) ? 'node-edge-fail' : ''}" d={d} />
        {/if}
      {/each}
      {#if wiring}
        {@const w = wiring}
        {@const from = graph.nodes.find((n) => n.id === w.from)}
        {#if from}
          {@const outSide = isFailPort(from, w.fromPort) ? "down" : (inputSideOf(from) === "right" ? "left" : "right")}
          <path class="node-wire" d={edgePath(outputPortPos(from, w.fromPort), w, from, null, outSide, "left")} />
        {/if}
      {/if}
    </svg>

    {#each graph.nodes as node (node.id)}
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <div
          class="node-card {graph.selectedId === node.id ? 'selected' : ''}"
          class:dragging={draggingNodeId === node.id}
          bind:clientHeight={cardHeights[node.id]}
          style:left={`${node.x}px`}
          style:top={`${node.y}px`}
          style:--node-color={NODE_COLORS[node.type]}
          onpointerdown={(e) => nodePointerDown(e, node.id)}
          onpointermove={(e) => nodePointerMove(e, node.id)}
          onpointerup={nodePointerUp}
        >
          <div class="node-header">
            <Icon icon={NODE_ICONS[node.type]} class="size-3.5 shrink-0" style="color:var(--node-color)" />
            <span class="node-title-text">{node.title || NODE_LABELS[node.type]}</span>
            <button
              onclick={(e) => { e.stopPropagation(); deleteNode(node.id); }}
              class="node-delete"
              title="Delete node"
            >
              <Icon icon="mdi:close" class="size-3" />
            </button>
          </div>

          <div class="node-body">
            {#if node.type === "start"}
              <UderText text={node.text} class="node-preview" images="placeholder" />
              <div class="choice-list">
                {#each node.choices as choice, i}
                  <div class="choice-row">
                    <span class="choice-badge">{i + 1}</span>
                    <UderText text={choice} class="node-preview" images="placeholder" />
                  </div>
                {/each}
              </div>
            {:else if node.type === "story" || node.type === "ending"}
              <UderText text={node.text} class="node-preview" images="placeholder" />
            {:else if node.type === "choice"}
              <div class="node-field">
                <span>prompt</span>
                <UderText text={node.prompt} class="node-preview" images="placeholder" />
              </div>
              <div class="choice-list">
                {#each node.choices as choice, i}
                  <div class="choice-row">
                    <span class="choice-badge">{i + 1}</span>
                    <UderText text={choice} class="node-preview" images="placeholder" />
                  </div>
                {/each}
              </div>
            {:else if node.type === "condition"}
              <div class="cond-block">
                <div class="cond-line">
                  {#if node.resource}
                    <span class="cond-resource">{resourceName(node.resource)}</span>
                    <span class="cond-op">{OPERATOR_LABELS[node.operator]}</span>
                    <span class="cond-value">{node.value}</span>
                  {:else}
                    <span class="cond-op">no resource</span>
                  {/if}
                </div>
              </div>
            {:else if node.type === "addition"}
              <div class="cond-block">
                <div class="cond-line">
                  {#if node.resource}
                    <span class="cond-resource">{resourceName(node.resource)}</span>
                    <span class="cond-op">{MUTATION_LABELS[node.op]}</span>
                    <span class="cond-value">{node.value}</span>
                  {:else}
                    <span class="cond-op">no resource</span>
                  {/if}
                </div>
              </div>
              <UderText text={node.text} class="node-preview" images="placeholder" />
            {:else if node.type === "chance"}
              <div class="cond-block">
                <div class="cond-line">
                  <span class="cond-op">pass chance</span>
                  <span class="cond-value">{node.pass}%</span>
                </div>
              </div>
              <UderText text={node.text} class="node-preview" images="placeholder" />
            {:else if node.type === "resource"}
              <div class="node-field">
                <span>initial value</span>
                <p class="node-preview">{node.initial}</p>
              </div>
            {:else if node.type === "loop_check"}
              <div class="cond-block">
                <div class="cond-line">
                  {#if node.condition.resource}
                    <span class="cond-resource">{resourceName(node.condition.resource)}</span>
                    <span class="cond-op">{OPERATOR_LABELS[node.condition.operator]}</span>
                    <span class="cond-value">{node.condition.value}</span>
                  {:else if node.loops > 0}
                    <span class="cond-op">until loops = {node.loops}</span>
                  {:else}
                    <span class="cond-op">no exit condition</span>
                  {/if}
                </div>
              </div>
            {/if}
          </div>

          {#if node.type !== "resource" && node.type !== "start"}
            {@const inSide = inputSideOf(node)}
            {@const noIn = !graph.edges.some((en) => en.to === node.id)}
            {@const sides = noIn ? (["left", "right"] as const) : [inSide]}
            {#each sides as s}
              <div
                class="node-port node-port-in"
                style:left={s === "right" ? `${NODE_WIDTH - 6}px` : "-6px"}
                style:top={`${PORT_Y - 6}px`}
                style:--port-color={NODE_COLORS[node.type]}
                title="input"
              ></div>
            {/each}
          {/if}
          {#if nodeOutputs(node) > 0 && (node.type === "start" || graph.edges.some((en) => en.to === node.id))}
            {@const outLeft = inputSideOf(node) === "right"}
            {#each Array(nodeOutputs(node)) as _, i}
              {@const isFail = isFailPort(node, i)}
              <!-- svelte-ignore a11y_no_static_element_interactions -->
              <div
                class="node-port node-port-out {isFail ? 'node-port-fail' : ''}"
                class:out-left={!isFail && outLeft}
                style:left={isFail ? `${NODE_WIDTH / 2 - PORT_SIZE / 2}px` : outLeft ? `-${PORT_SIZE / 2}px` : undefined}
                style:right={isFail ? undefined : outLeft ? undefined : `-${PORT_SIZE / 2}px`}
                style:top={isFail ? `${(cardHeights[node.id] ?? defaultNodeHeight(node)) - 8}px` : `${(nodeOutputs(node) > 1 ? PORT_Y + i * CHOICE_PORT_SPACING : PORT_Y) - PORT_SIZE / 2}px`}
                style:--port-color={isFail ? "#ef4444" : NODE_COLORS[node.type]}
                onpointerdown={(e) => portPointerDown(e, node.id, i)}
                onpointermove={portPointerMove}
                onpointerup={portPointerUp}
                title={isFail ? "fail" : "drag to connect"}
              ></div>
            {/each}
          {/if}
        </div>
    {/each}
  </div>

  <div class="zoom-controls" role="group" aria-label="Zoom controls">
    <button
      class="btn btn-ghost btn-xs"
      onclick={undo}
      disabled={!canUndo()}
      title="Undo (Ctrl+Z)"
      aria-label="Undo"
    >
      <Icon icon="mdi:undo" class="size-4" />
    </button>
    <button
      class="btn btn-ghost btn-xs"
      onclick={redo}
      disabled={!canRedo()}
      title="Redo (Ctrl+Shift+Z)"
      aria-label="Redo"
    >
      <Icon icon="mdi:redo" class="size-4" />
    </button>
    <button
      class="btn btn-ghost btn-xs"
      onclick={() => zoomStep(1 / 1.25)}
      title="Zoom out"
      aria-label="Zoom out"
    >
      <Icon icon="mdi:minus" class="size-4" />
    </button>
    <span class="zoom-label">{Math.round(canvasScale * 100)}%</span>
    <button
      class="btn btn-ghost btn-xs"
      onclick={() => zoomStep(1.25)}
      title="Zoom in"
      aria-label="Zoom in"
    >
      <Icon icon="mdi:plus" class="size-4" />
    </button>
  </div>
</div>

<style>
  .node-graph-wrap {
    position: relative;
    overflow: hidden;
    border-radius: 1rem;
    border: 1px solid color-mix(in oklch, var(--color-base-content) 10%, transparent);
    background-color: color-mix(in oklch, var(--color-base-300) 60%, transparent);
    min-height: 32rem;
    height: 100%;
    touch-action: none;
    user-select: none;
  }

  .node-graph-canvas {
    position: absolute;
    top: 0;
    left: 0;
    width: 3000px;
    height: 3000px;
    background-image: radial-gradient(
      circle,
      color-mix(in oklch, var(--color-base-content) 18%, transparent) 1px,
      transparent 1px
    );
    background-size: 28px 28px;
    border: 1px solid color-mix(in oklch, var(--color-base-content) 15%, transparent);
    transform-origin: 0 0;
    will-change: transform;
  }

  .zoom-controls {
    position: absolute;
    top: 0.75rem;
    right: 0.75rem;
    z-index: 10;
    display: flex;
    align-items: center;
    gap: 0.25rem;
    padding: 0.2rem;
    border-radius: 0.75rem;
    border: 1px solid color-mix(in oklch, var(--color-base-content) 12%, transparent);
    background-color: color-mix(in oklch, var(--color-base-100) 85%, transparent);
    backdrop-filter: blur(4px);
  }

  .zoom-label {
    min-width: 2.5rem;
    text-align: center;
    font-size: 10px;
    font-family: ui-monospace, monospace;
    color: color-mix(in oklch, var(--color-base-content) 70%, transparent);
  }

  .node-edges {
    position: absolute;
    top: 0;
    left: 0;
    overflow: visible;
    pointer-events: none;
  }

  .node-edge-hit {
    fill: none;
    stroke: transparent;
    stroke-width: 12;
    pointer-events: stroke;
    cursor: pointer;
  }

  .node-edge {
    fill: none;
    stroke: color-mix(in oklch, var(--color-base-content) 35%, transparent);
    stroke-width: 2.5;
    stroke-linecap: round;
    stroke-linejoin: round;
    pointer-events: none;
  }

  .node-edge-fail {
    stroke: #ef4444;
  }

  .node-wire {
    fill: none;
    stroke: color-mix(in oklch, var(--color-primary, var(--color-base-content)) 60%, transparent);
    stroke-width: 2.5;
    stroke-linecap: round;
    stroke-linejoin: round;
    stroke-dasharray: 6 4;
    pointer-events: none;
  }

  .node-card {
    position: absolute;
    width: 220px;
    background-color: color-mix(in oklch, var(--color-base-200) 92%, transparent);
    border: 1px solid color-mix(in oklch, var(--color-base-content) 12%, transparent);
    border-radius: 0.75rem;
    box-shadow: 0 4px 16px rgb(0 0 0 / 0.18);
    cursor: grab;
    touch-action: none;
    z-index: 1;
  }

  .node-card.selected {
    border-color: var(--node-color);
    box-shadow: 0 0 0 2px color-mix(in oklch, var(--node-color) 30%, transparent), 0 4px 16px rgb(0 0 0 / 0.25);
  }

  .node-card.dragging {
    cursor: grabbing;
    opacity: 0.9;
    z-index: 2;
  }

  .node-header {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.4rem 0.5rem;
    border-bottom: 1px solid color-mix(in oklch, var(--color-base-content) 8%, transparent);
  }

  .node-title-text {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: color-mix(in oklch, var(--color-base-content) 75%, transparent);
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.02em;
  }

  .node-delete {
    flex-shrink: 0;
    padding: 0.15rem;
    border-radius: 0.375rem;
    color: color-mix(in oklch, var(--color-base-content) 30%, transparent);
    cursor: pointer;
  }

  .node-delete:hover {
    color: var(--color-error, #f87171);
    background-color: color-mix(in oklch, var(--color-base-content) 6%, transparent);
  }

  .node-body {
    padding: 0.5rem;
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
  }

  .node-preview {
    min-width: 0;
    white-space: pre-wrap;
    word-break: break-word;
    color: color-mix(in oklch, var(--color-base-content) 60%, transparent);
    font-size: 11px;
    line-height: 1.45;
    background-color: color-mix(in oklch, var(--color-base-300) 40%, transparent);
    border: 1px solid color-mix(in oklch, var(--color-base-content) 8%, transparent);
    border-radius: 0.5rem;
    padding: 0.4rem 0.5rem;
  }

  .choice-list {
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
  }

  .choice-row {
    display: flex;
    align-items: center;
    gap: 0.4rem;
  }

  .choice-badge {
    flex-shrink: 0;
    width: 1rem;
    text-align: center;
    font-size: 9px;
    font-family: ui-monospace, monospace;
    color: color-mix(in oklch, var(--color-base-content) 35%, transparent);
  }

  .node-field {
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
  }

  .node-field > span {
    font-size: 9px;
    font-family: ui-monospace, monospace;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: color-mix(in oklch, var(--color-base-content) 35%, transparent);
  }

  .cond-block {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.45rem;
    padding: 0.7rem 0.5rem 0.6rem;
    border: 1px solid color-mix(in oklch, var(--node-color) 22%, transparent);
    border-radius: 0.7rem;
    background-color: color-mix(in oklch, var(--node-color) 5%, transparent);
  }

  .cond-line {
    display: flex;
    align-items: baseline;
    justify-content: center;
    flex-wrap: wrap;
    gap: 0.32rem;
    font-size: 11px;
    line-height: 1.5;
    text-align: center;
  }

  .cond-resource {
    font-weight: 700;
    color: var(--node-color);
  }

  .cond-op {
    font-style: italic;
    font-size: 10px;
    color: color-mix(in oklch, var(--color-base-content) 55%, transparent);
  }

  .cond-value {
    font-family: ui-monospace, monospace;
    font-weight: 700;
    color: color-mix(in oklch, var(--color-base-content) 85%, transparent);
  }

  .node-port.node-port-out.node-port-fail {
    width: 16px;
    height: 16px;
    background-color: #ef4444;
    border: none;
    border-radius: 0;
    clip-path: polygon(50% 100%, 0 0, 100% 0);
    filter: drop-shadow(0 1px 2px rgb(0 0 0 / 0.35));
  }

  .node-port.node-port-out.node-port-fail:hover {
    filter: drop-shadow(0 0 3px rgb(239 68 68 / 0.6));
  }

  .node-port {
    position: absolute;
    width: 12px;
    height: 12px;
    border-radius: 9999px;
    box-sizing: border-box;
    cursor: crosshair;
    touch-action: none;
    z-index: 2;
    transition: box-shadow 0.15s ease, filter 0.15s ease, transform 0.15s ease;
  }

  .node-port.node-port-in {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background-color: var(--port-color);
    border: none;
    box-shadow: none;
    filter: drop-shadow(0 1px 2px rgb(0 0 0 / 0.35));
  }

  .node-port.node-port-out {
    width: 16px;
    height: 16px;
    background-color: var(--port-color);
    border: none;
    border-radius: 0;
    clip-path: polygon(50% 0, 100% 50%, 50% 100%);
    filter: drop-shadow(0 1px 2px rgb(0 0 0 / 0.35));
  }

  .node-port.node-port-out.out-left {
    clip-path: polygon(50% 0, 0 50%, 50% 100%);
  }

  .node-port:hover {
    transform: scale(1.2);
  }

  .node-port.node-port-in:hover {
    box-shadow: 0 0 0 3px color-mix(in oklch, var(--port-color) 28%, transparent);
  }

  .node-port.node-port-out:hover {
    filter: drop-shadow(0 0 3px color-mix(in oklch, var(--port-color) 45%, transparent));
  }
</style>