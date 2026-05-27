<script lang="ts">
  import Icon from "@iconify/svelte";
</script>

<div class="flex flex-col items-center justify-center min-h-dvh p-6 md:p-12">
  <div class="max-w-5xl w-full bg-base-300/70 border border-white/10 rounded-2xl p-8 md:p-12 shadow-2xl relative overflow-hidden">

    <header class="text-center mb-10 relative z-10">
      <h1 class="text-5xl font-bold text-primary mb-3">Dev Tools</h1>
      <p class="text-base-content/70 italic text-base">
        useful tools for working on the website and helping out editors
      </p>
    </header>

    <div class="relative z-10 flex flex-col items-center gap-4 max-w-md mx-auto">
      <a href="/dev/editor" class="btn btn-soft btn-lg btn-primary w-full gap-3">
        <Icon icon="mdi:pencil" class="size-6" />
        Editor
      </a>
    </div>

  </div>
</div>
