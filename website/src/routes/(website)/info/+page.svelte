<script lang="ts">
  import Icon from "@iconify/svelte";
  import TwitterHover from "$lib/TwitterHover.svelte";
  import { fade } from "svelte/transition";

  let developers = $state([
    {
      name: "Ender Oksam",
      user: "enderoksam",
      banner: "/assets/enderoksam-banner.png",
      avatar: "/assets/enderoksam-avatar.png",
      tagline: "[ Your ■■ is 'Eternity' ]",
      role: "Developer",
      cardBg: "#d1d5db",
      cardBorder: "#96a0a8",
      tagBg: "#6b7280",
      tagColor: "#ffffff",
    },
    {
      name: "Dominus",
      user: "dominusz",
      banner: "",
      avatar: "/assets/dominusz-avatar.png",
      tagline: "■■",
      role: "Editor",
      cardBg: "#374151",
      cardBorder: "#1f2937",
      tagBg: "#f59e0b",
      tagColor: "#1a1a2e",
    },
  ]);
  let currentDeveloper = $state(0);

  function switchDeveloper() {
    currentDeveloper = (currentDeveloper + 1) % developers.length;
  }

  let dev = $derived(developers[currentDeveloper]);
</script>

<div class="flex flex-col items-center justify-center min-h-dvh p-6 md:p-12">
  <div class="max-w-5xl w-full bg-base-300/70 border border-white/10 rounded-2xl p-8 md:p-12 shadow-2xl relative overflow-hidden">

    <header class="text-center mb-10 relative z-10">
      <h1 class="text-5xl font-bold text-primary mb-3">GSGW-Reader</h1>
      <p class="text-base-content/70 italic text-base">
        A website for reading and editing GSGW translations and formatting
      </p>
    </header>

    <div class="relative z-10 flex flex-col md:flex-row gap-8">
      <div class="md:w-1/2 flex flex-col items-center gap-6">
        <div class="max-w-[400px] w-full grid" style="grid-template:1fr/1fr">
          {#key currentDeveloper}
            <div in:fade={{ duration: 300 }} out:fade={{ duration: 200 }}
                 class="relative overflow-hidden rounded-2xl border border-white/10 shadow-xl w-full"
                 style="grid-area:1/1; border-color:{dev.cardBorder}; background:{dev.cardBg};">

            <div class="h-28 bg-cover bg-center"
                 style="background-image:url({dev.banner})">
            </div>


             <div class="relative pl-5 pr-3 pb-3 pt-10">


              <img
                src={dev.avatar}
                alt=""
                class="absolute left-5 -top-10 size-20 rounded-full border-4 shadow-lg"
                style="border-color:{dev.cardBg}; background:{dev.cardBg};"
              />


              <div class="space-y-1">
                <h2 class="text-3xl font-extrabold leading-tight flex items-center gap-2"
                    style="color:#1a1a1a;">
                  {dev.name}
                  <span class="inline-flex items-center gap-1 text-[0.65rem] font-semibold px-1.5 py-0.5 rounded-full translate-y-[1px]" style="background:{dev.tagBg}; color:{dev.tagColor};">
                    <Icon icon="mdi:code-tags" class="size-3" />
                    {dev.role}
                  </span>
                </h2>

                <p class="text-sm opacity-70"
                   style="color:#1a1a1a;">
                  {dev.user}
                </p>
              </div>


              <div class="mt-3">
                <p class="text-sm font-bold"
                   style="color:#1a1a2e;">
                  {dev.tagline}
                </p>
              </div>

            </div>

            <button
              onclick={switchDeveloper}
              class="absolute bottom-2 right-2 btn btn-soft btn-xs btn-square btn-accent shadow-lg opacity-70 hover:opacity-100"
              title="Switch developer"
            >
              <Icon icon="mdi:swap-horizontal-bold" class="size-4" />
            </button>
          </div>
        {/key}
        </div>


        <section class="bg-base-200/50 p-6 rounded-xl border border-white/5 w-full max-w-[400px]">
          <div class="flex items-center gap-2 mb-3">
            <Icon icon="mdi:code-tags" class="text-accent size-5" />
            <h2 class="text-lg font-semibold">Developer Note</h2>
          </div>
          <p class="text-sm text-base-content/80 leading-relaxed">this website is a fork of <a href="https://beyonder.pages.dev" target="_blank" rel="noopener noreferrer" class="text-primary hover:underline">beyonder.pages.dev</a> it was made as a personal project to learn a bit of web development, I hope you enjoy it as much as I enjoyed making it</p>
          <p class="text-xs text-base-content/60 mt-2 leading-relaxed">(if there are any issues or concerns I can be contacted through discord, and if there are any suggestions or bugs they can be brought up on the discord server)</p>
        </section>
      </div>


      <div class="md:w-1/2 space-y-6">
        <a href="https://page.kakao.com/content/65171279" target="_blank" rel="noopener noreferrer"
           class="bg-base-200/50 p-6 rounded-xl border border-white/5 block transition-transform hover:scale-[1.02]">
          <div class="flex items-center gap-2 mb-4">
            <Icon icon="mdi:book-open-page-variant" class="text-secondary size-6" />
            <h2 class="text-xl font-semibold">Story</h2>
          </div>
          <ul class="text-sm text-base-content/80 space-y-3">
            <li class="flex items-center gap-2">
              <Icon icon="mdi:pen" class="size-4 opacity-50 shrink-0" />
              <span><b>Author:</b> Baek Deoksoo</span>
            </li>
          </ul>
        </a>

        <section class="bg-base-200/50 p-6 rounded-xl border border-white/5">
          <div class="flex items-center gap-2 mb-2">
            <Icon icon="mdi:palette" class="text-secondary size-5" />
            <h2 class="text-lg font-semibold">Illustrations</h2>
          </div>
          <p class="text-sm text-base-content/60 mb-4 leading-relaxed">
            Illustrations featured on the reader are Twitter embeds completely client side, Clicking the @'s should take you to the original post.
          </p>
          <div class="flex flex-wrap gap-3">
            <div class="bg-base-300/50 px-3 py-1.5 rounded-full border border-white/5">
              <TwitterHover user="uoongpig" />
            </div>
          </div>
        </section>

        <div class="grid grid-cols-2 gap-4 mt-8">
          <a href="/download" class="btn btn-soft btn-md btn-secondary shadow-lg gap-2">
            <Icon icon="material-symbols:download" class="size-5" />
            Download
          </a>
          <a href="https://github.com/EnderOksam/GSGW-Reader/blob/main/contributing.md" target="_blank" rel="noopener noreferrer" class="btn btn-soft btn-md btn-warning shadow-lg gap-2">
            <Icon icon="ri:edit-line" class="size-5" />
            Contribute
          </a>
          <a href="https://discord.gg/HHnSjeGN4d" target="_blank" rel="noopener noreferrer" class="btn btn-soft btn-md btn-accent shadow-lg gap-2">
            <Icon icon="mingcute:discord-line" class="size-5" />
            Discord
          </a>
          <a href="https://github.com/EnderOksam/GSGW-Reader" target="_blank" rel="noopener noreferrer" class="btn btn-soft btn-md btn-info shadow-lg gap-2">
            <Icon icon="mdi:github" class="size-5" />
            GitHub
          </a>
        </div>

        <div class="flex justify-center mt-8">
          <a href="/dev/editor" class="btn btn-soft btn-md btn-primary gap-2">
            <Icon icon="mdi:developer-board" class="size-5" />
            Editor
          </a>
        </div>

        <p class="text-xs text-base-content/60 text-center mt-10 leading-relaxed">
          thank you to <TwitterHover user="dominusz" noFetch /> and <TwitterHover user="wonstryk" noFetch /> for testing early builds of the site
        </p>
      </div>
    </div>


  </div>
</div>
