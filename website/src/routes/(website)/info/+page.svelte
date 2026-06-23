<script lang="ts">
  import Icon from "@iconify/svelte";
  import TwitterHover from "$lib/TwitterHover.svelte";
  import { fade } from "svelte/transition";


  let contributeModal: HTMLDialogElement;

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
      textColor: "#1a1a1a",
      taglineColor: "#1a1a2e",
    },
    {
      name: "Dominus",
      user: "dominusz",
      banner: "",
      avatar: "/assets/dominusz-avatar.png",
      tagline: "■■",
      role: "Editor",
      cardBg: "#131416",
      cardBorder: "#0d0606",
      tagBg: "#fb8462",
      tagColor: "#131416",
      textColor: "#d7d7da",
      taglineColor: "#d7d7da",
    },
    {
      name: "Moon_Angel",
      user: "moon_angels",
      banner: "/assets/moon_angels-banner.png",
      avatar: "/assets/moon_angels-avatar.png",
      tagline: "Moon was here",
      role: "Community Manager",
      cardBg: "#1a1a2e",
      cardBorder: "#494987",
      tagBg: "#494987",
      tagColor: "#ffffff",
      textColor: "#d7d7da",
      taglineColor: "#d7d7da",
    },
  ]);
  let currentDeveloper = $state(0);

  function switchDeveloper() {
    currentDeveloper = (currentDeveloper + 1) % developers.length;
  }

  let dev = $derived(developers[currentDeveloper]);
</script>

<div class="flex flex-col items-center justify-center min-h-dvh p-6 md:p-12">
  <div class="max-w-5xl w-full bg-[#0d0d0d]/80 border border-[#fb8462]/15 rounded-2xl p-8 md:p-12 shadow-2xl relative overflow-hidden">

    <header class="text-center mb-10 relative z-10">
      <h1 class="text-5xl font-bold mb-3 crt-title" style="color:#fb8462">GSGW-Reader</h1>
      <p class="text-white/50 italic text-base">
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
                 style="background-image:url({dev.banner}); background-color:#0d0606;">
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
                  style="color:{dev.textColor};">
                <span class:aurora-text={dev.name === "Moon_Angel"}>
                  {dev.name}
                </span>
                  <span class="inline-flex items-center gap-1 text-[0.65rem] font-semibold px-1.5 py-0.5 rounded-full translate-y-[1px]" style="background:{dev.tagBg}; color:{dev.tagColor};">
                    <Icon icon="mdi:code-tags" class="size-3" />
                    {dev.role}
                  </span>
                </h2>

                <p class="text-sm opacity-70"
                   style="color:{dev.textColor};">
                  {dev.user}
                </p>
              </div>


              <div class="mt-3">
                <p class="text-sm font-bold"
                   style="color:{dev.taglineColor};">
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


        <section class="bg-[#0d0d0d]/60 p-6 rounded-xl border border-[#fb8462]/10 w-full max-w-[400px]">
          <div class="flex items-center gap-2 mb-3">
            <Icon icon="mdi:code-tags" class="text-[#fb8462] size-5" />
            <h2 class="text-lg font-semibold text-white/80">Developer Note</h2>
          </div>
          <p class="text-sm text-white/60 leading-relaxed">this website is a fork of <a href="https://beyonder.pages.dev" target="_blank" rel="noopener noreferrer" class="text-[#fb8462] hover:underline">beyonder.pages.dev</a> it was made as a personal project to learn a bit of web development, I hope you enjoy it as much as I enjoyed making it</p>
          <p class="text-xs text-white/40 mt-2 leading-relaxed">(if there are any issues or concerns I can be contacted through discord, and if there are any suggestions or bugs they can be brought up on the discord server)</p>
        </section>
      </div>


      <div class="md:w-1/2 space-y-6">
        <a href="https://page.kakao.com/content/65171279" target="_blank" rel="noopener noreferrer"
           class="bg-[#0d0d0d]/60 p-6 rounded-xl border border-[#fb8462]/10 block transition-transform hover:scale-[1.02]">
          <div class="flex items-center gap-2 mb-4">
            <Icon icon="mdi:book-open-page-variant" class="text-[#fb8462] size-6" />
            <h2 class="text-xl font-semibold text-white/80">Story</h2>
          </div>
          <ul class="text-sm text-white/60 space-y-3">
            <li class="flex items-center gap-2">
              <Icon icon="mdi:pen" class="size-4 opacity-50 shrink-0" />
              <span><b class="text-white/80">Author:</b> Baek Deoksoo</span>
            </li>
          </ul>
        </a>

        <section class="bg-[#0d0d0d]/60 p-6 rounded-xl border border-[#fb8462]/10">
          <div class="flex items-center gap-2 mb-2">
            <Icon icon="mdi:palette" class="text-[#fb8462] size-5" />
            <h2 class="text-lg font-semibold text-white/80">Artists</h2>
          </div>
          <p class="text-sm text-white/50 mb-4 leading-relaxed">
            Illustrations featured on the reader are Twitter embeds, these link back to the original post so show support whenever you can.
          </p>
          <div class="flex flex-wrap gap-3">
            {#each ["uoongpig", "Katzz_artt", "d_kartonidze", "chiiiiliii", "yjh_ism"] as user}
              <div class="bg-[#0d0d0d]/80 px-3 py-1.5 rounded-full border border-[#fb8462]/10">
                <TwitterHover {user} />
              </div>
            {/each}
          </div>
        </section>

        <div class="grid grid-cols-2 gap-4 mt-8">
          <a href="/download" class="btn btn-soft btn-md btn-secondary shadow-lg gap-2">
            <Icon icon="material-symbols:download" class="size-5" />
            Download
          </a>
          <button onclick={() => contributeModal.showModal()} class="btn btn-soft btn-md btn-warning shadow-lg gap-2">
            <Icon icon="ri:edit-line" class="size-5" />
            Contribute
          </button>
          <a href="https://discord.gg/HHnSjeGN4d" target="_blank" rel="noopener noreferrer" class="btn btn-soft btn-md btn-accent shadow-lg gap-2">
            <Icon icon="mingcute:discord-line" class="size-5" />
            Discord
          </a>
          <a href="https://github.com/EnderOksam/GSGW-Reader" target="_blank" rel="noopener noreferrer" class="btn btn-soft btn-md btn-info shadow-lg gap-2">
            <Icon icon="mdi:github" class="size-5" />
            GitHub
          </a>
        </div>

        <p class="text-xs text-white/40 text-center mt-10 leading-relaxed">
          thank you to <TwitterHover user="dominusz" noFetch /> and <TwitterHover user="wonstryk" noFetch /> for testing early builds of the site
        </p>
      </div>
    </div>


  </div>
</div>

<dialog bind:this={contributeModal} class="modal modal-bottom sm:modal-middle">
  <div class="modal-box bg-base-100 rounded-box">
    <form method="dialog">
      <button class="btn btn-sm btn-circle btn-ghost absolute right-2 top-2">✕</button>
    </form>
    <h3 class="font-bold text-lg mb-4" style="color:#fb8462">Contribute</h3>
    <div class="flex flex-col gap-3">
      <a href="https://github.com/EnderOksam/GSGW-Reader/blob/main/contributing.md" target="_blank" rel="noopener noreferrer" class="btn btn-outline w-full rounded-btn gap-2" style="border-color:#fb8462; color:#fb8462;">
        <Icon icon="mdi:book-open-page-variant" class="size-5" /> Read Guide
      </a>
      <a href="/dev/editor" class="btn btn-outline w-full rounded-btn gap-2" style="border-color:#fb8462; color:#fb8462;">
        <Icon icon="material-symbols:edit-note-rounded" class="size-5" /> Editor
      </a>
    </div>
  </div>
  <form method="dialog" class="modal-backdrop"><button>close</button></form>
</dialog>

<style>
  .crt-title {
    text-shadow:
      0 0 3px rgba(251, 132, 98, 0.3),
      0 0 8px rgba(251, 132, 98, 0.1),
      -0.5px 0 rgba(255, 0, 0, 0.1),
      0.5px 0 rgba(0, 0, 255, 0.1);
    animation: crt-flicker 4s infinite;
  }

  @keyframes crt-flicker {
    0%, 100% { opacity: 1; }
    92% { opacity: 1; }
    93% { opacity: 0.85; }
    94% { opacity: 1; }
    96% { opacity: 0.92; }
    97% { opacity: 1; }
  }

  .aurora-text {
    font-weight: 800;
    background: linear-gradient(135deg, #00c2ff, #33ff8c, #ffc640, #e54cff, #00c2ff);
    background-size: 300% 300%;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    animation: aurora-flow 6s ease-in-out infinite;
    filter: drop-shadow(0 0 6px rgba(0, 194, 255, 0.2)) drop-shadow(0 0 15px rgba(229, 76, 255, 0.1));
  }

  @keyframes aurora-flow {
    0%, 100% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
  }
</style>
