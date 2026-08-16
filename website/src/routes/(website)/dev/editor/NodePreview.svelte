<script lang="ts">
  import Icon from "@iconify/svelte";
  import { graph } from "./lib/node-graph-store.svelte.ts";
  import { NODE_LABELS, type UderNode, type NodeOperator } from "./lib/nodes";
  import UderSelect from "./UderSelect.svelte";
  import UderText from "./UderText.svelte";
  import { onMount } from "svelte";

  let currentId = $state<string | null>(null);
  let entryId = $state<string>("");
  let resources = $state<Record<string, number>>({});
  let loopCounts = $state<Record<string, number>>({});

  const current = $derived(currentId ? graph.nodes.find((n) => n.id === currentId) ?? null : null);
  const currentOutgoing = $derived(current ? graph.edges.filter((e) => e.from === current.id) : []);

  function targetFor(port: number): UderNode | null {
    const cur = current;
    if (!cur) return null;
    const edge = graph.edges.find((e) => e.from === cur.id && e.fromPort === port);
    if (!edge) return null;
    return graph.nodes.find((n) => n.id === edge.to) ?? null;
  }

  function evalCond(resourceId: string, op: NodeOperator, value: number): boolean {
    const res = resources[resourceId] ?? 0;
    if (op === "<=") return res <= value;
    if (op === ">=") return res >= value;
    return res === value;
  }

  function enterNode(id: string | null) {
    if (!id) {
      currentId = null;
      return;
    }
    const n = graph.nodes.find((x) => x.id === id);
    if (!n) {
      currentId = null;
      return;
    }
    if (n.type === "loop_start") {
      const pairId = n.parentId;
      if (pairId) loopCounts = { ...loopCounts, [pairId]: (loopCounts[pairId] ?? 0) + 1 };
      currentId = id;
      return;
    }
    if (n.type === "loop_check") {
      const pairId = n.id;
      const passes = loopCounts[pairId] ?? 0;
      const resourceMet = n.condition.resource
        ? evalCond(n.condition.resource, n.condition.operator, n.condition.value)
        : false;
      const countMet = n.loops > 0 ? passes >= n.loops : false;
      if (resourceMet || countMet) {
        const exitEdge = graph.edges.find((e) => e.from === n.id && e.fromPort === 0);
        if (exitEdge) {
          enterNode(exitEdge.to);
          return;
        }
        currentId = null;
        return;
      }
      const start = graph.nodes.find((c) => c.parentId === n.parentId && c.type === "loop_start");
      if (start) {
        enterNode(start.id);
        return;
      }
      currentId = null;
      return;
    }
    if (n.type === "condition") {
      const pass = n.resource ? evalCond(n.resource, n.operator, n.value) : true;
      const edge = graph.edges.find((e) => e.from === n.id && e.fromPort === (pass ? 0 : 1));
      if (edge) {
        enterNode(edge.to);
        return;
      }
      currentId = null;
      return;
    }
    if (n.type === "chance") {
      const pass = Math.random() * 100 < n.pass;
      const edge = graph.edges.find((e) => e.from === n.id && e.fromPort === (pass ? 0 : 1));
      if (edge) {
        enterNode(edge.to);
        return;
      }
      currentId = null;
      return;
    }
    if (n.type === "addition") {
      const cur = resources[n.resource] ?? 0;
      const next = n.op === "add" ? cur + n.value : n.op === "subtract" ? cur - n.value : n.value;
      resources = { ...resources, [n.resource]: next };
    }
    currentId = id;
  }

  function begin() {
    resources = Object.fromEntries(
      graph.nodes.filter((x) => x.type === "resource").map((x) => [x.id, x.initial])
    );
    loopCounts = {};
    const start =
      graph.nodes.find((n) => n.id === entryId) ?? graph.nodes.find((n) => n.type === "start") ?? graph.nodes[0] ?? null;
    if (!start) {
      currentId = null;
      return;
    }
    entryId = start.id;
    enterNode(start.id);
  }

  function proceed(port: number) {
    const next = targetFor(port);
    if (!next) return;
    enterNode(next.id);
  }

  $effect(() => {
    const cur = current;
    if (!cur) return;
    if (cur.type === "loop_start") {
      const t = setTimeout(() => proceed(0), 40);
      return () => clearTimeout(t);
    }
    if (cur.type === "addition" && !cur.text && !cur.prompt) {
      const t = setTimeout(() => proceed(0), 40);
      return () => clearTimeout(t);
    }
  });

  function bodyText(n: UderNode): string {
    if (n.type === "story" || n.type === "ending" || n.type === "start") return n.text;
    if (n.type === "choice") return n.prompt;
    if (n.type === "loop_check") return n.note;
    if (n.type === "addition" || n.type === "chance") return n.text;
    return "";
  }

  function hasNext(): boolean {
    return currentOutgoing.some((e) => e.fromPort === 0);
  }

  onMount(begin);
</script>

<div class="preview-wrap">
  <div class="preview-toolbar">
    <span class="toolbar-label">starting node</span>
    <UderSelect
      class="flex-1 min-w-0"
      value={entryId}
      options={graph.nodes
        .filter((n) => n.type !== "loop_start" && n.type !== "loop_check")
        .map((n) => ({ value: n.id, label: `${NODE_LABELS[n.type]}: ${n.title}` }))}
      onchange={(v) => {
        entryId = v;
        begin();
      }}
    />
    <button onclick={begin} class="toolbar-restart" title="Restart">
      <Icon icon="mdi:restart" class="size-3.5" />
    </button>
  </div>

  <div class="preview-stage">
    {#if current}
      {#key current.id}
        <div class="story-window">
          <div class="window-bar">
            <span class="window-type">{NODE_LABELS[current.type]}</span>
            {#if current.title}<span class="window-title">{current.title}</span>{/if}
          </div>

          <div class="window-body">
            {#if current.type === "resource"}
              <p class="window-text muted">{current.title} · {current.initial}</p>
            {:else if current.type === "addition"}
              <UderText text={bodyText(current)} class="window-text" />
            {:else}
              <UderText text={bodyText(current)} class="window-text" />
            {/if}
          </div>

          <div class="window-actions">
            {#if current.type === "choice" || current.type === "start"}
              {#if current.choices.length === 0}
                <button class="window-choice" onclick={() => proceed(0)} disabled={!hasNext()}>
                  <span class="choice-dot"></span>
                  <span>continue</span>
                </button>
              {:else}
                  {#each current.choices as c, pi}
                    <button
                      class="window-choice"
                      onclick={() => proceed(pi)}
                      disabled={!currentOutgoing.some((e) => e.fromPort === pi)}
                    >
                      <span class="choice-dot"></span>
                      <UderText text={c} images="placeholder" class="min-w-0 flex-1" />
                    </button>
                  {/each}
              {/if}
            {:else if current.type === "ending"}
              <button class="window-choice" onclick={begin}>
                <span class="choice-dot"></span>
                <span>restart</span>
              </button>
            {:else if current.type === "addition"}
              <button class="window-choice" onclick={() => proceed(0)} disabled={!hasNext()}>
                <span class="choice-dot"></span>
                <span>{current.prompt || "continue"}</span>
              </button>
            {:else}
              <button class="window-choice" onclick={() => proceed(0)} disabled={!hasNext()}>
                <span class="choice-dot"></span>
                <span>continue</span>
              </button>
            {/if}
          </div>
        </div>
      {/key}
    {:else}
      <div class="preview-empty">
        <Icon icon="mdi:play-outline" class="size-7" />
        <p>add nodes and wire them to preview the flow</p>
      </div>
    {/if}
  </div>
</div>

<style>
  .preview-wrap {
    display: flex;
    flex-direction: column;
    height: 100%;
    min-height: 32rem;
    border-radius: 1rem;
    border: 1px solid color-mix(in oklch, var(--color-base-content) 10%, transparent);
    background-color: color-mix(in oklch, var(--color-base-300) 60%, transparent);
    overflow: hidden;
  }

  .preview-toolbar {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 0.75rem;
    border-bottom: 1px solid color-mix(in oklch, var(--color-base-content) 10%, transparent);
    background-color: color-mix(in oklch, var(--color-base-200) 70%, transparent);
  }

  .toolbar-label {
    font-size: 9px;
    font-family: ui-monospace, monospace;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: color-mix(in oklch, var(--color-base-content) 35%, transparent);
  }

  .toolbar-restart {
    padding: 0.3rem;
    border-radius: 0.5rem;
    color: color-mix(in oklch, var(--color-base-content) 40%, transparent);
    cursor: pointer;
    transition: color 0.12s ease;
  }

  .toolbar-restart:hover {
    color: var(--color-primary, var(--color-base-content));
    background-color: color-mix(in oklch, var(--color-base-content) 6%, transparent);
  }

  .preview-stage {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 1.5rem;
    overflow: hidden;
    background-image: radial-gradient(
      circle,
      color-mix(in oklch, var(--color-base-content) 6%, transparent) 1px,
      transparent 1px
    );
    background-size: 24px 24px;
  }

  .story-window {
    width: 100%;
    max-width: 560px;
    max-height: min(520px, 100%);
    border-radius: 0.85rem;
    border: 1px solid color-mix(in oklch, var(--color-base-content) 15%, transparent);
    background-color: color-mix(in oklch, var(--color-base-100) 94%, transparent);
    box-shadow: 0 14px 44px rgb(0 0 0 / 0.28);
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }

  .window-bar {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    padding: 0.6rem 1rem;
    border-bottom: 1px solid color-mix(in oklch, var(--color-base-content) 10%, transparent);
    background-color: color-mix(in oklch, var(--color-base-300) 55%, transparent);
  }

  .window-type {
    font-size: 10px;
    font-family: ui-monospace, monospace;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.14em;
    color: color-mix(in oklch, var(--color-base-content) 50%, transparent);
  }

  .window-title {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    margin-left: auto;
    font-size: 11px;
    color: color-mix(in oklch, var(--color-base-content) 35%, transparent);
  }

  .window-body {
    padding: 1.75rem 1.5rem 1.25rem;
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    overscroll-behavior: contain;
  }

  .window-text {
    white-space: pre-wrap;
    word-break: break-word;
    font-size: 15px;
    line-height: 1.75;
    color: color-mix(in oklch, var(--color-base-content) 85%, transparent);
  }

  .window-text.muted {
    color: color-mix(in oklch, var(--color-base-content) 40%, transparent);
    font-style: italic;
    text-align: center;
  }

  .window-actions {
    display: flex;
    flex-direction: column;
    gap: 0.55rem;
    padding: 1rem 1.5rem 1.4rem;
    border-top: 1px solid color-mix(in oklch, var(--color-base-content) 10%, transparent);
    background-color: color-mix(in oklch, var(--color-base-200) 40%, transparent);
  }

  .window-choice {
    display: flex;
    align-items: center;
    gap: 0.7rem;
    width: 100%;
    text-align: left;
    padding: 0.65rem 0.9rem;
    border-radius: 0.6rem;
    border: 1px solid color-mix(in oklch, var(--color-base-content) 18%, transparent);
    background-color: color-mix(in oklch, var(--color-base-100) 70%, transparent);
    color: color-mix(in oklch, var(--color-base-content) 75%, transparent);
    font-size: 12px;
    cursor: pointer;
    transition: background-color 0.12s ease, border-color 0.12s ease, transform 0.05s ease;
  }

  .window-choice:hover:not(:disabled) {
    border-color: color-mix(in oklch, var(--color-primary, var(--color-base-content)) 50%, transparent);
    background-color: color-mix(in oklch, var(--color-base-100) 100%, transparent);
  }

  .window-choice:active:not(:disabled) {
    transform: translateY(1px);
  }

  .window-choice:disabled {
    opacity: 0.35;
    cursor: not-allowed;
  }

  .choice-dot {
    flex-shrink: 0;
    width: 0.45rem;
    height: 0.45rem;
    border-radius: 9999px;
    background-color: color-mix(in oklch, var(--color-primary, var(--color-base-content)) 60%, transparent);
  }

  .preview-empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0.6rem;
    color: color-mix(in oklch, var(--color-base-content) 20%, transparent);
  }

  .preview-empty p {
    font-size: 10px;
    font-family: ui-monospace, monospace;
    text-align: center;
    padding: 0 1rem;
  }
</style>