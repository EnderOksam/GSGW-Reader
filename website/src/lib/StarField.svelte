<script lang="ts">
  import { onMount } from "svelte";

  let container: HTMLDivElement;

  const COUNT = 10;
  const stars = Array.from({ length: COUNT }, () => {
    const angle = Math.random() * 360;
    const rad = (angle * Math.PI) / 180;
    const dist = 10 + Math.random() * 18;
    return {
      x: Math.cos(rad) * dist,
      y: Math.sin(rad) * dist,
      size: 4 + Math.random() * 4,
      baseOpacity: 0.35 + Math.random() * 0.25,
      phase: Math.random() * Math.PI * 2,
      blinkDelay: Math.random() * 5,
      shineDelay: Math.random() * 3,
      orbitSpeed: 0.3 + Math.random() * 0.3,
      orbitRadiusX: 2 + Math.random() * 4,
      orbitRadiusY: 1.5 + Math.random() * 3,
    };
  });

  let rafId: number;

  onMount(() => {
    let t = 0;
    function loop() {
      t += 0.02;
      if (!container) { rafId = requestAnimationFrame(loop); return; }
      for (let i = 0; i < COUNT; i++) {
        const el = container.children[i + 1] as HTMLElement;
        if (!el) continue;
        const s = stars[i];
        const dx = Math.sin(t * s.orbitSpeed + s.phase) * s.orbitRadiusX;
        const dy = Math.cos(t * s.orbitSpeed * 0.7 + s.phase * 1.2) * s.orbitRadiusY;
        el.style.setProperty("--dx", `${dx}px`);
        el.style.setProperty("--dy", `${dy}px`);
      }
      rafId = requestAnimationFrame(loop);
    }
    rafId = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(rafId);
  });

</script>

<div
  bind:this={container}
  class="relative inline-flex p-3 -m-3 z-10"
>
  <slot />
  {#each stars as s}
    <div
      class="absolute pointer-events-none"
      style="
        left: calc(50% + {s.x}px);
        top: calc(50% + {s.y}px);
        width: {s.size}px;
        height: {s.size}px;
        opacity: {s.baseOpacity};
        clip-path: polygon(50% 0%, 57% 43%, 100% 50%, 57% 57%, 50% 100%, 43% 57%, 0% 50%, 43% 43%);
        background: #ffe066;
        background-image: linear-gradient(135deg, transparent 30%, rgba(255,255,255,0.7) 48%, transparent 65%);
        background-size: 200% 200%;
        background-position: 100% 0%;
        filter: drop-shadow(0 0 2px rgba(255, 224, 102, 0.4));
        transform: rotate(45deg) translate(var(--dx, 0px), var(--dy, 0px));
        animation:
          star-blink 3s ease-in-out {s.blinkDelay}s infinite,
          star-shine 3s ease-in-out {s.shineDelay}s infinite;
      "
    ></div>
  {/each}
</div>

<style>
  @keyframes star-blink {
    0%, 100% { opacity: 0.25; }
    50% { opacity: 0.5; }
  }
  @keyframes star-shine {
    0% { background-position: 100% 0%; }
    100% { background-position: 0% 100%; }
  }
</style>
