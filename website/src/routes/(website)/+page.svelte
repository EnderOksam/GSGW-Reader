<script>
  import { onMount } from "svelte";
  import { fade } from "svelte/transition";
  import Icon from "@iconify/svelte";
  
  import imgBG_Constant from "$lib/assets/web-bg.jpg"; 
  import imgBG_TransitionSource from "$lib/assets/web-bg2.jpg"; 

  import card1 from "$lib/assets/card.jpg";
  import card2 from "$lib/assets/card2.jpg";
  import card3 from "$lib/assets/card3.jpg";
  import card4 from "$lib/assets/card4.jpg";
  import card5 from "$lib/assets/card5.jpg";
  import card6 from "$lib/assets/card6.jpg";

  const cardImages = [card1, card2, card3, card4, card5, card6];

  let isTransitioned = $state(false);
  let showTransitionBG = $state(false);
  
  // Initialize with a random index immediately
  let currentIndex = $state(Math.floor(Math.random() * cardImages.length));

  const ROTATION_TIME = 10000;

  function cycleCard() {
    currentIndex = (currentIndex + 1) % cardImages.length;
  }

  onMount(() => {
    const comingBack = sessionStorage.getItem("navigated_to_book");

    if (comingBack === "true") {
      showTransitionBG = true; 
      setTimeout(() => {
        isTransitioned = true;
        sessionStorage.removeItem("navigated_to_book");
      }, 300);
    } else {
      isTransitioned = true;
    }

    const interval = setInterval(cycleCard, ROTATION_TIME);
    return () => clearInterval(interval);
  });

  function handleNavigation() {
    sessionStorage.setItem("navigated_to_book", "true");
  }
</script>

<!-- Background Layer -->
<div class="fixed inset-0 -z-10 overflow-hidden pointer-events-none">
  <enhanced:img 
    src={imgBG_TransitionSource} 
    alt="" 
    class="absolute inset-0 w-full h-full object-cover {showTransitionBG ? 'opacity-100' : 'opacity-0'}" 
  />
  
  <enhanced:img 
    src={imgBG_Constant} 
    alt="" 
    class="absolute inset-0 w-full h-full object-cover transition-opacity duration-1000 {isTransitioned ? 'opacity-100' : 'opacity-0'}" 
  />
  
  <div class="absolute inset-0 bg-black/50 backdrop-blur-xs"></div>
</div>

<main class="relative z-10 flex min-h-dvh flex-col items-center justify-center gap-10 p-8 md:flex-row md:justify-around text-white">
  <div class="flex flex-col items-center gap-4">
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
      <!-- 3D Effect Decoration -->
      <div></div><div></div><div></div><div></div><div></div><div></div><div></div><div></div>
    </div>

    <!-- Artist Credit -->
    <a 
      href="https://twitter.com/nokdock4" 
      target="_blank" 
      rel="noopener noreferrer" 
      class="text-xs text-white/40 hover:text-white/70 transition-colors"
    >
      Background and Cards made by @nokdock4 on twitter
    </a>
  </div>

  <div class="flex flex-col items-center md:items-start">
    <div class="max-w-md text-center">
      <h1 class="lg:text-5xl text-3xl font-bold text-primary filter drop-shadow-[0_0_10px_#c47f0a] w-full block md:text-left">
        Got Dropped into a Ghost Story, Still Gotta Work
      </h1>
      <p class="py-6 lg:text-2xl text-lg lg:w-full md:w-4/5 w-full brightness-95 md:text-left">
        “...Am I happy, you ask?" <br> "Please, just let me go home. I’m begging you.”
      </p>
    </div>

    <div class="flex gap-4">
      <a 
        class="btn btn-lg btn-soft btn-primary" 
        href="/book" 
        onclick={handleNavigation}
      >
        Read Now
      </a>
      <a class="btn btn-lg btn-soft btn-secondary" href="/download">Download</a>
    </div>
  </div>
</main>