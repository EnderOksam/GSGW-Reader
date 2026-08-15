<script lang="ts">
  import Icon from "@iconify/svelte";

  interface UderOption {
    value: string;
    label: string;
  }

  let {
    value,
    options,
    placeholder = "",
    mono = false,
    class: className = "",
    onchange,
  }: {
    value: string;
    options: UderOption[];
    placeholder?: string;
    mono?: boolean;
    class?: string;
    onchange?: (v: string) => void;
  } = $props();

  let open = $state(false);
  let highlight = $state(-1);
  let triggerEl = $state<HTMLButtonElement | null>(null);
  let listEl = $state<HTMLDivElement | null>(null);
  const listboxId = $state(`listbox-${Math.random().toString(36).slice(2)}`);

  const selected = $derived(options.find((o) => o.value === value) ?? null);

  function choose(v: string) {
    if (v !== value) onchange?.(v);
    open = false;
    triggerEl?.focus();
  }

  function onKeydown(e: KeyboardEvent) {
    if (e.key === "Escape") {
      open = false;
      triggerEl?.focus();
      return;
    }
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      if (options.length === 0) return;
      if (!open) {
        open = true;
        highlight = Math.max(0, options.findIndex((o) => o.value === value));
        return;
      }
      const dir = e.key === "ArrowDown" ? 1 : -1;
      highlight = (highlight + dir + options.length) % options.length;
      return;
    }
    if (e.key === "Enter" || e.key === " ") {
      if (open && highlight >= 0) {
        e.preventDefault();
        const opt = options[highlight];
        if (opt) choose(opt.value);
      }
    }
  }

  function onClickOutside(e: PointerEvent) {
    const target = e.target as Node;
    if (triggerEl?.contains(target) || listEl?.contains(target)) return;
    open = false;
  }
</script>

<svelte:window onpointerdown={onClickOutside} />

<div class="relative {className}">
  <button
    bind:this={triggerEl}
    type="button"
    class="w-full flex items-center justify-between gap-2 bg-base-300/40 border border-base-content/10 rounded-lg px-2 py-2 text-[11px] text-base-content/70 outline-none hover:border-base-content/20 focus:border-base-content/25 transition-colors {mono ? 'font-mono' : ''}"
    aria-haspopup="listbox"
    aria-expanded={open}
    aria-controls={open ? listboxId : undefined}
    onkeydown={onKeydown}
    onclick={() => {
      open = !open;
      highlight = Math.max(0, options.findIndex((o) => o.value === value));
    }}
    onfocusout={(e) => {
      const next = e.relatedTarget as Node | null;
      if (next && (triggerEl?.contains(next) || listEl?.contains(next))) return;
      open = false;
    }}
  >
    <span class="truncate text-left">{selected ? selected.label : placeholder}</span>
    <Icon
      icon="mdi:chevron-down"
      class="size-3.5 shrink-0 text-base-content/40 transition-transform {open ? 'rotate-180' : ''}"
    />
  </button>

  {#if open}
    <div
      bind:this={listEl}
      role="listbox"
      id={listboxId}
      tabindex="-1"
      class="absolute top-full left-0 right-0 z-50 mt-1 max-h-56 overflow-auto rounded-lg border border-base-content/10 bg-base-100 py-1 shadow-2xl"
      onkeydown={onKeydown}
    >
      {#each options as o, i}
        <button
          type="button"
          role="option"
          aria-selected={o.value === value}
          class="w-full flex items-center gap-2 px-2.5 py-1.5 text-left text-[11px] text-base-content/70 transition-colors {i === highlight ? 'bg-base-300/50' : ''} hover:bg-base-300/40 {o.value === value ? 'text-primary' : ''}"
          onmouseenter={() => (highlight = i)}
          onpointerdown={(e) => e.preventDefault()}
          onclick={() => choose(o.value)}
        >
          <span class="w-3.5 shrink-0 flex items-center">
            {#if o.value === value}
              <Icon icon="mdi:check" class="size-3" />
            {/if}
          </span>
          <span class="truncate {mono ? 'font-mono' : ''}">{o.label}</span>
        </button>
      {/each}
    </div>
  {/if}
</div>
