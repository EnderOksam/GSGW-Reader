<script>
  import { onMount } from "svelte";
  import Icon from "@iconify/svelte";
  
  // Background Asset Imports
  import imgBG_Constant from "$lib/assets/web-bg.jpg";
  import imgBG_TransitionSource from "$lib/assets/web-bg2.jpg";

  // Card Asset Imports (Importing them ensures Vite resolves the path correctly)
  import card1 from "$lib/assets/card.jpg";
  import card2 from "$lib/assets/card2.jpg";
  import card3 from "$lib/assets/card3.jpg";
  import card4 from "$lib/assets/card4.jpg";
  import card5 from "$lib/assets/card5.jpg";
  import card6 from "$lib/assets/card6.jpg";

  // Use the imported variables in your list
  const cardImages = [card1, card2, card3, card4, card5, card6];

  let isTransitioned = $state(false);
  let currentCardIndex = $state(0);
  let isCardFading = $state(false);

  // 10 seconds for testing
  const ROTATION_TIME = 10000;

  function cycleCard() {
    isCardFading = true;
    setTimeout(() => {
      currentCardIndex = (currentCardIndex + 1) % cardImages.length;
      isCardFading = false;
    }, 500); 
  }

  onMount(() => {
    setTimeout(() => { isTransitioned = true; }, 300);
    const interval = setInterval(cycleCard, ROTATION_TIME);
    return () => clearInterval(interval);
  });
</script>

<div class="fixed inset-0 -z-10 overflow-hidden">
  <enhanced:img 
    src={imgBG_TransitionSource} 
    alt="" 
    class="absolute inset-0 w-full h-full object-cover" 
  />
  <enhanced:img 
    src={imgBG_Constant} 
    alt="" 
    class="absolute inset-0 w-full h-full object-cover transition-opacity duration-1000 {isTransitioned ? 'opacity-100' : 'opacity-0'}" 
  />
  <div class="absolute inset-0 bg-black/50 backdrop-blur-xs"></div>
</div>

<main class="flex min-h-dvh flex-col items-center justify-center gap-10 p-8 md:flex-row md:justify-around">
  <div class="hover-3d relative">
    <figure class="max-w-100 rounded-2xl shadow-2xl overflow-hidden bg-black/20">
      <!-- Use standard img here since the src is dynamic -->
      <img
        src={cardImages[currentCardIndex]}
        alt="Rotating character card"
        class="h-[75vh] max-h-[45vh] md:max-h-[75dvh] w-auto object-cover transition-opacity duration-500 {isCardFading ? 'opacity-0' : 'opacity-100'}"
      />
    </figure>
    <div></div><div></div><div></div><div></div><div></div><div></div><div></div><div></div>
  </div>

  <div class="flex flex-col items-center md:items-start text-white">
    <div class="max-w-md text-center">
      <h1 class="lg:text-5xl text-3xl font-bold text-primary filter drop-shadow-[0_0_10px_#c47f0a] w-full block md:text-left">
        Got Dropped into a Ghost Story, Still Gotta Work
      </h1>
      <p class="py-6 lg:text-2xl text-lg lg:w-full md:w-4/5 w-full brightness-95 md:text-left">
        “...Am I happy, you ask?" <br /> "Please, just let me go home. I’m begging you.”
      </p>
    </div>

    <div class="flex gap-4">
      <a class="btn btn-lg btn-soft btn-primary" href="/book" data-sveltekit-preload-data>Read Now</a>
      <a class="btn btn-lg btn-soft btn-secondary" href="/download">Download</a>
    </div>
  </div>

  <div class="fixed right-0 lg:top-1/3 top-2/9 z-50 flex flex-col gap-2 pr-2">
    <!-- Tooltips and Icons -->
    <div class="tooltip tooltip-left" data-tip="Donate">
      <a href="/donate" class="btn btn-soft btn-lg btn-secondary">
        <Icon icon="mdi:heart-outline" class="size-7" />
      </a>
    </div>
    <div class="tooltip tooltip-left" data-tip="Info">
      <a href="https://github.com/EnderOksam/GSGW-Reader" class="btn btn-soft btn-lg btn-info">
        <Icon icon="mdi:information-outline" class="size-7" />
      </a>
    </div>
    <div class="tooltip tooltip-left" data-tip="Contribute">
      <a href="https://github.com/Bittu5134/ORV-Reader/blob/main/contributing.md" class="btn btn-soft btn-lg btn-warning">
        <Icon icon="ri:edit-line" class="size-7" />
      </a>
    </div>
    <div class="tooltip tooltip-left" data-tip="Discord">
      <a href="https://discord.gg/XmzJVsyuTQ" class="btn btn-soft btn-lg btn-accent">
        <Icon icon="mingcute:discord-line" class="size-7" />
      </a>
    </div>
  </div>
</main>