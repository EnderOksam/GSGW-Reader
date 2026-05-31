<script lang="ts">
  import imgLotm from "$lib/assets/web-lotm-cover.jpg";
  import imgCoi from "$lib/assets/web-coi-cover.jpg";
  import imgManwha from "$lib/assets/webtoon-cover.webp";

  const books = [
    {
      href: "./gsgw",
      img: imgLotm,
      title: "Ghost Story, Still Gotta Work",
      author: "Baek Deoksoo",
      tag: "Webnovel",
      tagClass: "text-primary",
      desc: "A pop-up event for some 'modern fantasy' media… I loved so much that I even took a precious day off work to attend.",
    },
    {
      href: "./manwha",
      img: imgManwha,
      title: "Ghost Story, Gotta Work",
      author: "todac_s",
      tag: "Manwha",
      tagClass: "text-accent",
      desc: "Manwha Adaptation",
    },
    {
      href: "./temp",
      img: imgCoi,
      title: "Dark Exploration Records",
      author: "Fanatics",
      tag: "Unofficial",
      tagClass: "text-warning",
      desc: "A collection of fan-created records exploring the darkness that lies beyond.",
    },
  ];
</script>

<svelte:head>
  <title>Books</title>
</svelte:head>

<main class="relative z-10 min-h-dvh flex flex-col items-center justify-center p-6 md:p-12">
  <div class="flex flex-col md:flex-row items-center justify-center gap-6 md:gap-10 w-full max-w-6xl">
    {#each books as book}
      <a
        href={book.href}
        class="group relative w-80 md:w-96 aspect-[3/4] overflow-hidden rounded-2xl shadow-xl transition-all duration-500 hover:scale-[1.03] hover:shadow-2xl"
        data-sveltekit-preload-data
      >
        <div class="absolute inset-0 transition-all duration-700 group-hover:scale-110">
          <enhanced:img
            src={book.img}
            alt="{book.title} cover"
            class="absolute inset-0 w-full h-full object-cover"
          />
          <div class="absolute inset-0 bg-gradient-to-t from-black/95 via-black/60 via-60% to-black/10 to-100%"></div>
          <div class="absolute inset-0 bg-gradient-to-b from-black/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
        </div>

        <div class="absolute bottom-0 left-0 right-0 p-5 md:p-6 z-10 translate-y-1 group-hover:translate-y-0 transition-transform duration-500">
          <span class="inline-flex items-center gap-1.5 text-xs font-bold uppercase tracking-widest {book.tagClass} drop-shadow mb-1.5">
            <span class="size-1.5 rounded-full bg-current"></span>
            {book.tag}
          </span>
          <h2 class="text-lg md:text-xl font-black text-white drop-shadow leading-tight">
            {book.title}
          </h2>
          <p class="text-xs text-white/70 font-mono mt-1.5">
            {book.author}
          </p>
          <p class="text-xs text-white/50 mt-2 line-clamp-2 leading-relaxed group-hover:text-white/70 transition-colors duration-500">
            {book.desc}
          </p>
        </div>

        <div class="absolute inset-0 ring-1 ring-inset ring-white/10 rounded-2xl pointer-events-none group-hover:ring-white/20 transition-all duration-500"></div>
      </a>
    {/each}
  </div>
</main>
