<script lang="ts">
  import { onMount } from "svelte";
  import { fade } from "svelte/transition";
  import Icon from "@iconify/svelte";

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
      <div></div><div></div><div></div><div></div><div></div><div></div><div></div><div></div>
    </div>

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
        A pop-up event for some ‘modern fantasy’ media… I loved so much that I even took a precious day off work to attend. <br> <br> On that day, I ended up transmigrating as a character in that very fantasy world.
      </p>
    </div>

    <div class="flex gap-4">
      <a 
        class="btn btn-lg btn-soft btn-primary" 
        href="/book" 

      >
        Read Now
      </a>
      <a class="btn btn-lg btn-soft btn-secondary" href="/download">Download</a>
    </div>
  </div>
</main>