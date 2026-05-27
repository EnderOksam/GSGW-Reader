<script>
  import imgLOTM from "$lib/assets/web-lotm-cover.jpg";
  import imgCOI from "$lib/assets/web-coi-cover.jpg";
</script>

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
