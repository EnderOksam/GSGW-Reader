<script>
  import { onMount } from "svelte";
  import imgLOTM from "$lib/assets/web-lotm-cover.jpg";
  import imgCOI from "$lib/assets/web-coi-cover.jpg";
  import imgBG_Source from "$lib/assets/web-bg.jpg"; 
  import imgBG_Target from "$lib/assets/web-bg2.jpg"; 

  // State to trigger the background fade
  let isTransitioned = $state(false);

  onMount(() => {
    // Check if user has already seen the fade this session
    const hasFaded = sessionStorage.getItem("bg_faded_book_select");

    if (hasFaded) {
      isTransitioned = true;
    } else {
      // Trigger fade-in after a short delay for visual impact
      setTimeout(() => {
        isTransitioned = true;
        sessionStorage.setItem("bg_faded_book_select", "true");
      }, 100);
    }
  });
</script>

<div class="fixed inset-0 -z-10 overflow-hidden pointer-events-none">
  <enhanced:img 
    src={imgBG_Source} 
    alt="" 
    class="absolute inset-0 w-full h-full object-cover object-top" 
  /> <enhanced:img 
    src={imgBG_Target} 
    alt="" 
    class="absolute inset-0 w-full h-full object-cover object-top transition-opacity duration-1000 {isTransitioned ? 'opacity-100' : 'opacity-0'}" 
  /> <div class="absolute inset-0 bg-black/50 backdrop-blur-xs"></div>
</div>

<main class="relative z-10 min-h-dvh flex flex-col items-center justify-center gap-10 p-8 md:flex-row md:justify-evenly">
  
  <a class="hover-3d static flex flex-col items-center" href="./gsgw" data-sveltekit-preload-data>
    <figure class="md:w-80 w-60 rounded-2xl cursor-pointer">
      <enhanced:img
        src={imgLOTM}
        alt="Book Cover"
        fetchpriority="high"
      />
    </figure>
    
    <span class="mt-4 w-full text-center text-md font-bold uppercase tracking-wider text-primary">
      Got Dropped in a Ghost Story, <br> Still gotta work
    </span>
    <div></div><div></div><div></div><div></div><div></div><div></div><div></div><div></div>
  </a>

  <a class="hover-3d relative cursor-pointer flex flex-col items-center" href="./temp" data-sveltekit-preload-data>
    <figure class="md:w-80 w-60 rounded-2xl">
      <enhanced:img
        src={imgCOI}
        alt="Book Cover"
        fetchpriority="high"
      />
    </figure>

    <span class="mt-4 w-full text-center text-md font-bold uppercase tracking-wider text-secondary">
      Unofficial Dark Exploration <br> Records (coming soon..)
    </span>
    <div></div><div></div><div></div><div></div><div></div><div></div><div></div><div></div>
  </a>
</main>