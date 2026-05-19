<script lang="ts">
  import { onMount } from "svelte";
  import { fade } from "svelte/transition";
  import Icon from "@iconify/svelte";
  import StarField from "$lib/StarField.svelte";

  import card1 from "$lib/assets/card.jpg";
  import card2 from "$lib/assets/card2.jpg";
  import card3 from "$lib/assets/card3.jpg";
  import card4 from "$lib/assets/card4.jpg";
  import card5 from "$lib/assets/card5.jpg";

  const cardImages = [card1, card2, card3, card4, card5,];

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
                alt="Character card"
                class="absolute inset-0 h-full w-full object-cover"
              />
            {/key}
          </figure>
          <div></div><div></div><div></div><div></div><div></div><div></div><div></div><div></div>
        </div>
      </a>

      <a 
        href="https://twitter.com/nokdock4" 
        target="_blank" 
        rel="noopener noreferrer" 
        class="hidden md:block text-xs text-white/40 hover:text-white/70 transition-colors"
      >
        Background and Cards made by @nokdock4 on twitter
      </a>
    </div>

    <div class="hidden md:flex flex-col justify-center gap-3">
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
      <div class="tooltip" data-tip="Info">
        <StarField>
          <a href="/info" class="btn btn-soft btn-square btn-lg btn-ghost shadow-lg info-glow">
            <Icon icon="mdi:information-outline" class="size-7" />
          </a>
        </StarField>
      </div>
    </div>
  </div>

  <div class="flex flex-col items-center">
    <div class="max-w-md text-center md:text-left">
      <h1 class="lg:text-5xl text-3xl font-bold text-primary filter drop-shadow-[0_0_10px_#c47f0a] w-full block md:text-left">
        Got Dropped into a Ghost Story, Still Gotta Work
      </h1>
      <p class="py-6 lg:text-2xl text-sm md:text-lg lg:w-full md:w-4/5 w-full brightness-95 md:text-left">
        A pop-up event for some ‘modern fantasy’ media… I loved so much that I even took a precious day off work to attend. <br> <br> On that day, I ended up transmigrating as a character in that very fantasy world.
      </p>
    </div>

    <a
      href="https://twitter.com/nokdock4"
      target="_blank"
      rel="noopener noreferrer"
      class="md:hidden text-xs text-white/40 hover:text-white/70 transition-colors"
    >
      Background and Cards made by @nokdock4 on twitter
    </a>

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
      <div class="tooltip" data-tip="Info">
        <StarField>
          <a href="/info" class="btn btn-soft btn-square btn-lg btn-ghost shadow-lg info-glow">
            <Icon icon="mdi:information-outline" class="size-7" />
          </a>
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