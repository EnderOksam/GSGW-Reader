<script lang="ts">
  import Icon from "@iconify/svelte";

  let {
    label,
    value,
    onChange,
    presets,
    min = -40,
    max = 100,
    step = 4,
  }: {
    label: string;
    value: number;
    onChange: (value: number) => void;
    presets: { label: string; value: number }[];
    min?: number;
    max?: number;
    step?: number;
  } = $props();

  let customOpen = $state(false);
  const activePreset = $derived(presets.find((p) => p.value === value)?.label);
</script>

<div class="rounded-xl border border-base-content/10 bg-base-200/40 px-4 py-3">
  <div class="flex items-center justify-between gap-3">
    <span class="text-sm font-medium">{label}</span>
    <div class="flex items-center gap-1.5">
      <div class="flex shrink-0 rounded-full bg-base-100 p-0.5 ring-1 ring-base-content/10">
        {#each presets as preset}
          <button
            class="rounded-full px-3 py-1 text-xs font-semibold transition-colors {activePreset === preset.label ? 'bg-primary text-primary-content shadow-sm' : 'text-base-content/50 hover:text-base-content'}"
            onclick={() => {
              onChange(preset.value);
              customOpen = false;
            }}
          >
            {preset.label}
          </button>
        {/each}
      </div>
      <button
        class="rounded-full p-1.5 transition-colors {customOpen ? 'bg-primary text-primary-content shadow-sm' : 'text-base-content/40 hover:bg-base-content/5 hover:text-base-content'}"
        onclick={() => (customOpen = !customOpen)}
        aria-label="Custom {label}"
        title="Custom"
      >
        <Icon icon="mdi:tune-variant" class="size-4" />
      </button>
    </div>
  </div>
  {#if customOpen}
    <div class="mt-3 flex items-center gap-3">
      <input
        type="range"
        {min}
        {max}
        {step}
        class="range range-xs range-primary flex-1"
        value={value}
        oninput={(e) => onChange(Number((e.currentTarget as HTMLInputElement).value))}
      />
      <span class="w-12 shrink-0 text-right text-xs font-mono text-base-content/40">{value}px</span>
    </div>
  {/if}
</div>
