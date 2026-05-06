<script>
  // Import cover image assets for the books
  import imgLOTM from "$lib/assets/web-lotm-cover.jpg";
  import imgCOI from "$lib/assets/web-coi-cover.jpg";
</script>

<main
  class="min-h-dvh flex flex-col items-center justify-center gap-10 p-8 md:flex-row md:justify-evenly"
>
  <!-- Book 1: Lord of the Mysteries -->
  <a class="hover-3d static flex flex-col items-center" href="./gsgw" data-sveltekit-preload-data>
    <figure class="md:w-80 w-60 rounded-2xl cursor-pointer">
      <enhanced:img
        src={imgLOTM}
        alt="Lord of the Mysteries Book Cover"
        fetchpriority="high"
      />
    </figure>
    
    <!-- 
      'text-center' handles internal text alignment (like Word's center option).
      'w-full' ensures the text block has enough space to center properly.
    -->
    <span class="mt-4 w-full text-center text-md font-bold uppercase tracking-wider text-primary">
      Got Dropped in a Ghost Story, <br> Still gotta work
    </span>

    <div></div><div></div><div></div><div></div><div></div><div></div><div></div><div></div>
  </a>

  <!-- Book 2: Circle of Inevitability -->
  <a class="hover-3d relative cursor-pointer flex flex-col items-center" href="./temp" data-sveltekit-preload-data>
    <figure class="md:w-80 w-60 rounded-2xl">
      <enhanced:img
        src={imgCOI}
        alt="Conspiracy of the Infinite Book Cover"
        fetchpriority="high"
      />
    </figure>

    <!-- Applying the same 'text-center' logic here -->
    <span class="mt-4 w-full text-center text-md font-bold uppercase tracking-wider text-secondary">
      Unofficial Dark Exploration <br> Records (coming soon..)
    </span>

    <div></div><div></div><div></div><div></div><div></div><div></div><div></div><div></div>
  </a>
</main>