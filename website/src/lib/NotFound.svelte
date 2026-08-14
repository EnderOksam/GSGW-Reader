<script lang="ts">
  import img404_1 from "$lib/assets/404_1.png";
  import img404_2 from "$lib/assets/404_2.png";
  import { fade } from "svelte/transition";
  import { onMount, onDestroy } from "svelte";
  import bgImage from "$lib/assets/background.jpg";
  import { BackgroundShader } from "$lib/bgShader";

  let isToggled = $state(false);

  let bgCanvas: HTMLCanvasElement;
  let bgShader: BackgroundShader | null = null;

  onMount(() => {
    bgShader = new BackgroundShader(bgCanvas, bgImage);
    bgShader.start();
  });

  onDestroy(() => {
    bgShader?.dispose();
  });
</script>

<canvas
  bind:this={bgCanvas}
  class="bg"
  aria-hidden="true"
  style="background-image:url({bgImage});background-size:cover;background-position:center;"
></canvas>

<div class="content relative overflow-hidden">
  <main class="relative z-10 flex min-h-dvh items-center justify-center px-4 py-10 md:px-6">
    <div class="w-full max-w-5xl">
      <!-- Terminal panel -->
      <div class="panel relative">
        <!-- Chrome bar -->
        <div class="panel-header">
          <div class="win-buttons" aria-hidden="true">
            <button class="win-btn win-min" aria-label="Minimize"></button>
            <button class="win-btn win-max" aria-label="Maximize"></button>
            <button class="win-btn win-close" aria-label="Close"></button>
          </div>
        </div>

        <!-- Body -->
        <div class="relative flex flex-col lg:flex-row items-center justify-center gap-8 lg:gap-8 px-6 py-12 md:px-12 md:py-14">
          <!-- Soft glow behind the whole body -->
          <div class="body-glow" aria-hidden="true"></div>

          <!-- Left: Text -->
          <div class="relative flex-1 w-full flex flex-col items-center lg:items-start text-center lg:text-left">
            <h1 class="crt-404 font-black leading-none text-[6.5rem] sm:text-[8rem] md:text-[9rem]">
              [404]
            </h1>

            <h2 class="mt-5 font-serif text-2xl md:text-3xl font-bold tracking-tight text-white">
              Risk of <span class="glitch-soft text-error">contamination</span> detected
            </h2>

            <p class="mt-5 max-w-lg font-serif text-lg leading-relaxed text-base-content/75 italic">
              "[seems like you've lost your way friend, but dont you worry this Braun will help you find your way]"
            </p>

            <div class="mt-9 flex flex-col sm:flex-row gap-4 w-full sm:w-auto">
          <a href="/" class="btn btn-primary btn-lg px-8 gap-2 shadow-xl shadow-primary/20 hover:scale-[1.03] hover:shadow-primary/40 transition-all">
            Return to Safety
          </a>
          <button
            onclick={() => window.history.back()}
            class="btn btn-accent btn-lg px-8 gap-2 shadow-xl shadow-accent/20 hover:scale-[1.03] hover:shadow-accent/40 transition-all"
          >
            Go back
          </button>
            </div>
          </div>

          <!-- Right: 404 image -->
          <div class="relative shrink-0 lg:-ml-8">
            <button
              onclick={() => isToggled = !isToggled}
              class="block size-44 md:size-56 lg:size-64 transition-transform active:scale-95 outline-none cursor-pointer hover-animate"
              aria-label="Toggle 404 form"
            >
              {#if isToggled}
                <img
                  in:fade={{ duration: 250 }}
                  src={img404_1}
                  alt="404 alt"
                  class="img-404 h-full w-full object-contain"
                />
              {:else}
                <img
                  in:fade={{ duration: 250 }}
                  src={img404_2}
                  alt="404 primary"
                  class="img-404 h-full w-full object-contain"
                />
              {/if}
            </button>
          </div>
        </div>

        <!-- Footer bar -->
        <div class="panel-footer"></div>
      </div>
    </div>
  </main>
</div>

<style>
  :global(:root) {
    --c1: #1C3760;
    --c2: #4682B4;
    --c3: #FF69B4;
    --c4: #FF4500;
    --c5: #4B0082;
    --c6: #C0C0C0;
    --c7: #FFFF00;
    --c8: #3A2E3B;
    --c9: #E0115F;
  }

  :global(body) {
    background: transparent;
  }

  .bg {
    position: fixed;
    inset: 0;
    z-index: -1;
    display: block;
    width: 100%;
    height: 100%;
    background-color: #0d0d0d;
    filter: blur(6px);
  }

  .content {
    position: relative;
    z-index: 1;
    backdrop-filter: blur(0.8px);
  }

  /* ---- Terminal panel ---- */
  .panel {
    background: color-mix(in srgb, var(--color-base-300, #1d1d1d) 55%, transparent);
    backdrop-filter: blur(14px);
    border: 1px solid color-mix(in srgb, var(--color-base-content, #fff) 12%, transparent);
    border-radius: 1rem;
    box-shadow:
      0 30px 80px -20px rgba(0, 0, 0, 0.8),
      0 0 0 1px rgba(0, 0, 0, 0.4),
      inset 0 1px 0 rgba(255, 255, 255, 0.06);
    overflow: hidden;
  }

  .panel-header {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 1rem;
    padding: 0.35rem 0.35rem;
    border-bottom: 1px solid color-mix(in srgb, var(--color-base-content, #fff) 10%, transparent);
    background: color-mix(in srgb, var(--color-base-200, #171717) 50%, transparent);
  }

  .win-buttons {
    display: flex;
    align-items: center;
    gap: 0.15rem;
  }

  .win-btn {
    width: 2.1rem;
    height: 1.7rem;
    display: flex;
    align-items: center;
    justify-content: center;
    border: none;
    background: transparent;
    color: color-mix(in srgb, var(--color-base-content, #fff) 75%, transparent);
    cursor: pointer;
    border-radius: 0.25rem;
    position: relative;
    transition: background 0.15s ease;
  }

  .win-btn:hover {
    background: color-mix(in srgb, var(--color-base-content, #fff) 12%, transparent);
  }

  .win-min::after {
    content: "";
    width: 0.7rem;
    height: 1px;
    background: currentColor;
  }

  .win-max::before {
    content: "";
    position: absolute;
    width: 0.55rem;
    height: 0.55rem;
    border: 1px solid currentColor;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
  }

  .win-close::before,
  .win-close::after {
    content: "";
    position: absolute;
    width: 0.75rem;
    height: 1px;
    background: currentColor;
  }

  .win-close::before {
    transform: rotate(45deg);
  }

  .win-close::after {
    transform: rotate(-45deg);
  }

  .win-close:hover {
    background: #e81123;
    color: #fff;
  }

  .panel-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    padding: 0.7rem 1.25rem;
    border-top: 1px solid color-mix(in srgb, var(--color-base-content, #fff) 10%, transparent);
    background: color-mix(in srgb, var(--color-base-200, #171717) 40%, transparent);
  }

  /* ---- Aurora 404 ---- */
  .crt-404 {
    position: relative;
    display: inline-block;
    font-family: inherit;
    font-weight: 900;
    letter-spacing: -0.02em;
    background: linear-gradient(135deg, #ff3a1a 0%, #ff8c3a 20%, #ffd644 40%, #ff3a7a 60%, #c820e0 80%, #ff3a1a 100%);
    background-size: 250% 100%;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    animation: aurora-flow 12s linear infinite alternate, fadeInUp 0.7s ease both;
    filter: drop-shadow(0 0 14px rgba(255, 58, 26, 0.35)) drop-shadow(0 0 40px rgba(255, 58, 122, 0.2)) drop-shadow(0 0 80px rgba(200, 32, 224, 0.12));
    will-change: background-position;
  }

  .glitch-soft {
    display: inline-block;
    animation: softGlitch 4s infinite steps(1);
  }

  /* ---- Body glow ---- */
  .body-glow {
    position: absolute;
    inset: 0;
    pointer-events: none;
    background:
      radial-gradient(ellipse 60% 55% at 20% 50%, rgba(255, 58, 26, 0.06), transparent 70%),
      radial-gradient(ellipse 60% 55% at 80% 50%, rgba(200, 32, 224, 0.06), transparent 70%);
  }

  .img-404 {
    background: transparent !important;
    filter: drop-shadow(0 8px 24px rgba(0, 0, 0, 0.55));
  }

  .hover-animate {
    animation: hoverRotate 5s ease-in-out infinite;
  }

  img {
    background: transparent !important;
  }

  /* ---- Animations ---- */
  @keyframes hoverRotate {
    0%, 100% { transform: translateY(0px) rotate(-3deg); }
    50% { transform: translateY(-14px) rotate(3deg); }
  }

  @keyframes aurora-flow {
    0% { background-position: 0% 50%; }
    100% { background-position: 100% 50%; }
  }

  @keyframes fadeInUp {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
  }

  @keyframes softGlitch {
    0%, 92%, 100% { text-shadow: none; transform: translate(0); }
    93% { text-shadow: -2px 0 #0ff, 2px 0 var(--c3, #FF69B4); transform: translate(1px); }
    95% { text-shadow: 2px 0 #0ff, -2px 0 var(--c3, #FF69B4); transform: translate(-1px); }
    97% { text-shadow: -1px 0 #0ff, 1px 0 var(--c3, #FF69B4); transform: translate(0); }
  }

  @media (prefers-reduced-motion: reduce) {
    .crt-404,
    .glitch-soft,
    .hover-animate {
      animation: none !important;
    }
  }
</style>
