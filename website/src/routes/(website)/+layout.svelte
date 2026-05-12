<script lang="ts">
  import imgBG1 from "$lib/assets/web-bg.jpg";
  import imgBG2 from "$lib/assets/web-bg2.jpg";
  import Icon from "@iconify/svelte";
  import "../../app.css";
  import { page } from "$app/state";
  import { goto, afterNavigate } from "$app/navigation";

  import imgMeta from "$lib/assets/card.jpg?url";

  let { children } = $props();

  let isHomePage = $derived(page.url.pathname === "/");

  let showBg1 = $state(page.url.pathname === "/");
  let showBg2 = $state(page.url.pathname !== "/");
  let transitionMs = $state(0);

  afterNavigate((nav) => {
    const fromHome = nav.from?.url.pathname === "/";
    const toHome = page.url.pathname === "/";

    if (fromHome || toHome) {
      transitionMs = 400;
    }

    showBg1 = toHome;
    showBg2 = !toHome;
  });

  function handleBack() {
    if (typeof window !== "undefined" && window.history.length > 1) {
      goto("../");
    } else {
      goto("/");
    }
  }

  $effect(() => {
    const _ = page.url.href;
    document.documentElement.setAttribute("data-theme", "sunset");
  });
</script>

<svelte:head>
  <title>GSGW-Reader</title>
  <meta
    name="description"
    content="The Fool that doesn't belong to this era, the mysterious ruler above the gray fog..."
  />

  <meta property="og:type" content="website" />
  <meta property="og:title" content="LOTM-Reader" />
  <meta
    property="og:description"
    content="The Fool that doesn't belong to this era, the mysterious ruler above the gray fog; the King of Yellow and Black who wields good luck…"
  />
  <meta property="og:image" content="http://beyonder.pages.dev{imgMeta}" />
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:title" content="LOTM-Reader" />
  <meta
    name="twitter:description"
    content="The Fool that doesn't belong to this era, the mysterious ruler above the gray fog; the King of Yellow and Black who wields good luck…"
  />
  <meta name="twitter:image" content="http://beyonder.pages.dev{imgMeta}" />
</svelte:head>

<div class="fixed inset-0 -z-10 overflow-hidden">
  <enhanced:img src={imgBG1} alt="" class="absolute inset-0 w-full h-full object-cover object-top will-change-opacity"
    style="opacity: {showBg1 ? 1 : 0}; transition: opacity {transitionMs}ms;"
  />
  <enhanced:img src={imgBG2} alt="" class="absolute inset-0 w-full h-full object-cover object-top will-change-opacity"
    style="opacity: {showBg2 ? 1 : 0}; transition: opacity {transitionMs}ms;"
  />
  <div class="absolute inset-0 bg-black/50 backdrop-blur-xs"></div>
</div>

{#if !isHomePage}
  <div class="fixed top-4 left-4 z-50">
    <button
      onclick={handleBack}
      class="btn btn-circle btn-ghost bg-base-300/50 backdrop-blur-md hover:bg-base-300 transition-all shadow-lg"
      aria-label="Go back"
    >
      <Icon icon="material-symbols:arrow-back-rounded" class="size-6" />
    </button>
  </div>
{/if}

{@render children()}
