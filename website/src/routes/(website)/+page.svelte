<script lang="ts">
  import { onMount } from "svelte";
  import { fade } from "svelte/transition";
  import Icon from "@iconify/svelte";
  import StarField from "$lib/StarField.svelte";

  let showBanner = $state(true);

  const cardImages = [
    "/assets/images/static-illustrations/ch7_1.webp",
    "/assets/images/static-illustrations/ch10_1.webp",
    "/assets/images/static-illustrations/ch20_1.webp",
    "/assets/images/static-illustrations/ch28_1.webp",
    "/assets/images/static-illustrations/ch36_1.webp",
    "/assets/images/static-illustrations/ch53_1.webp",
    "/assets/images/static-illustrations/ch75_1.webp",
    "/assets/images/static-illustrations/ch84_1.webp",
    "/assets/images/static-illustrations/ch95_1.webp",
    "/assets/images/static-illustrations/ch101_1.webp",
    "/assets/images/static-illustrations/ch107_1.webp",
    "/assets/images/static-illustrations/ch113_1.webp",
    "/assets/images/static-illustrations/ch138_1.webp",
    "/assets/images/static-illustrations/ch150_1.webp",
    "/assets/images/static-illustrations/ch154_1.webp",
    "/assets/images/static-illustrations/ch155_1.webp",
    "/assets/images/static-illustrations/ch196_1.webp",
  ];

  let currentIndex = $state(Math.floor(Math.random() * cardImages.length));

  const ROTATION_TIME = 10000;

  function cycleCard() {
    currentIndex = (currentIndex + 1) % cardImages.length;
  }

  onMount(() => {
    const interval = setInterval(cycleCard, ROTATION_TIME);
    return () => clearInterval(interval);
  });
</script>

<a 
  href="/error-test-trigger" 
  class="fixed top-4 left-4 z-50 opacity-0 hover:opacity-20 transition-opacity text-white cursor-default"
>
  #
</a>

{#if showBanner}
  <div class="fixed top-0 left-0 right-0 z-50 flex items-center justify-center gap-4 bg-base-300/80 border-b border-white/10 px-4 py-3 text-sm text-white">
    <span class="text-center">
      GSGW-Reader is a <strong class="text-warning font-bold">non-profit</strong> passion project for hosting and reading gsgw translations.
    </span>
    <button
      onclick={() => showBanner = false}
      class="btn btn-soft btn-xs btn-primary shrink-0"
    >
      Acknowledge
    </button>
  </div>
{/if}

<main class="relative z-10 flex min-h-dvh flex-col items-center justify-center gap-10 p-8 md:flex-row md:justify-around text-white">
  
  <div class="flex flex-col md:flex-row items-center gap-4 md:gap-8">
    <div class="flex flex-col items-center gap-4">
      <a href="/book" class="block">
        <div class="hover-3d relative">
          <figure class="max-w-100 rounded-2xl shadow-2xl overflow-hidden bg-black relative aspect-[2/3] w-[30vh] md:w-[50vh]">
            {#key currentIndex}
              <img
                in:fade={{ duration: 1500 }}
                out:fade={{ duration: 1500 }}
                src={cardImages[currentIndex]}
                alt="Chapter illustration"
                class="absolute inset-0 h-full w-full object-cover"
              />
            {/key}
          </figure>
          <div></div><div></div><div></div><div></div><div></div><div></div><div></div><div></div>
        </div>
      </a>
    </div>

    <div class="hidden md:flex flex-col justify-center items-center gap-3">
      <div class="tooltip" data-tip="Download">
        <a href="/download" class="btn btn-soft btn-square btn-lg btn-secondary shadow-lg">
          <Icon icon="material-symbols:download" class="size-7" />
        </a>
      </div>
      <div class="tooltip" data-tip="Contribute">
        <a href="https://github.com/EnderOksam/GSGW-Reader/blob/main/contributing.md" target="_blank" rel="noopener noreferrer" class="btn btn-soft btn-square btn-lg btn-warning shadow-lg">
          <Icon icon="ri:edit-line" class="size-7" />
        </a>
      </div>
      <div class="tooltip" data-tip="Discord">
        <a href="https://discord.gg/HHnSjeGN4d" target="_blank" rel="noopener noreferrer" class="btn btn-soft btn-square btn-lg btn-accent shadow-lg">
          <Icon icon="mingcute:discord-line" class="size-7" />
        </a>
      </div>
      <div class="tooltip" data-tip="GitHub">
        <a href="https://github.com/EnderOksam/GSGW-Reader" target="_blank" rel="noopener noreferrer" class="btn btn-soft btn-square btn-lg btn-info shadow-lg">
          <Icon icon="mdi:github" class="size-7" />
        </a>
      </div>
      <StarField>
        <div class="tooltip" data-tip="Info">
          <a href="/info" class="btn btn-soft btn-square btn-lg btn-ghost shadow-lg info-glow">
            <Icon icon="mdi:information-outline" class="size-7" />
          </a>
        </div>
      </StarField>
    </div>

    <div class="flex flex-col items-center">
      <div class="max-w-md text-center md:text-left">
        <h1 class="lg:text-5xl text-3xl font-bold text-primary filter drop-shadow-[0_0_10px_#c47f0a] w-full block md:text-left">
          Got Dropped into a Ghost Story, Still Gotta Work
        </h1>
        <p class="py-6 lg:text-2xl text-sm md:text-lg lg:w-full md:w-4/5 w-full brightness-95 md:text-left">
          A pop-up event for some 'modern fantasy' media… I loved so much that I even took a precious day off work to attend. <br> <br> On that day, I ended up transmigrating as a character in that very fantasy world.
        </p>
      </div>

      <div class="flex md:hidden flex-row items-center gap-3 mt-4">
        <div class="tooltip" data-tip="Download">
          <a href="/download" class="btn btn-soft btn-square btn-lg btn-secondary shadow-lg">
            <Icon icon="material-symbols:download" class="size-7" />
          </a>
        </div>
        <div class="tooltip" data-tip="Contribute">
          <a href="https://github.com/EnderOksam/GSGW-Reader/blob/main/contributing.md" target="_blank" rel="noopener noreferrer" class="btn btn-soft btn-square btn-lg btn-warning shadow-lg">
            <Icon icon="ri:edit-line" class="size-7" />
          </a>
        </div>
        <div class="tooltip" data-tip="Discord">
          <a href="https://discord.gg/HHnSjeGN4d" target="_blank" rel="noopener noreferrer" class="btn btn-soft btn-square btn-lg btn-accent shadow-lg">
            <Icon icon="mingcute:discord-line" class="size-7" />
          </a>
        </div>
        <div class="tooltip" data-tip="GitHub">
          <a href="https://github.com/EnderOksam/GSGW-Reader" target="_blank" rel="noopener noreferrer" class="btn btn-soft btn-square btn-lg btn-info shadow-lg">
            <Icon icon="mdi:github" class="size-7" />
          </a>
        </div>
        <StarField>
          <div class="tooltip" data-tip="Info">
            <a href="/info" class="btn btn-soft btn-square btn-lg btn-ghost shadow-lg info-glow">
              <Icon icon="mdi:information-outline" class="size-7" />
            </a>
          </div>
        </StarField>
      </div>

    </div>
  </div>
</main>

<style>
  .info-glow {
    position: relative;
    overflow: hidden;
    box-shadow: 0 0 15px 3px rgba(255, 224, 102, 0.25) !important;
    animation: info-shing 1.8s ease-out 1, info-pulse 3s ease-in-out infinite 2s;
  }
  .info-glow::after {
    content: "";
    position: absolute;
    inset: -60%;
    border-radius: inherit;
    background: linear-gradient(135deg, transparent 35%, rgba(255,224,102,0.25) 50%, transparent 65%);
    animation: info-sweep 2.5s ease-in-out infinite;
    pointer-events: none;
  }
  @keyframes info-sweep {
    0% { transform: translate(-70%, -70%); }
    35% { transform: translate(70%, 70%); }
    100% { transform: translate(70%, 70%); }
  }
  @keyframes info-pulse {
    0%, 100% { box-shadow: 0 0 15px 3px rgba(255, 224, 102, 0.25); }
    50% { box-shadow: 0 0 18px 5px rgba(255, 224, 102, 0.35); }
  }
  @keyframes info-shing {
    0% { box-shadow: 0 0 0 0 transparent, 0 0 15px 3px rgba(255, 224, 102, 0.25); }
    15% { box-shadow: 0 0 30px 10px rgba(255, 224, 102, 0.6), 0 0 15px 3px rgba(255, 224, 102, 0.25); }
    30% { box-shadow: 0 0 8px 2px rgba(255, 224, 102, 0.3), 0 0 15px 3px rgba(255, 224, 102, 0.25); }
    100% { box-shadow: 0 0 15px 3px rgba(255, 224, 102, 0.25); }
  }
</style>
