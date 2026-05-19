<script lang="ts">
  import { activeHover, clearHideTimeout, scheduleHide } from "$lib/activeHover.svelte";
  import { fade } from "svelte/transition";

  let data = $state<null | { name: string; description: string; followers: number; avatar: string; banner: string }>(null);
  let error = $state(false);
  let loading = $state(false);

  let { user, noFetch }: { user: string; noFetch?: boolean } = $props();

  let active = $derived($activeHover === user);

  function show() {
    if (noFetch) return;
    clearHideTimeout();
    activeHover.set(user);
    if (data || error) return;
    if (loading) return;
    loading = true;
    fetch(`https://api.fxtwitter.com/${user}`)
      .then(r => r.json())
      .then(d => {
        if (d.user) {
          data = {
            name: d.user.name,
            description: d.user.description,
            followers: d.user.followers,
            avatar: d.user.avatar_url || d.user.profile_image_url,
            banner: d.user.banner_url || "",
          };
        } else {
          error = true;
        }
      })
      .catch(() => { error = true; })
      .finally(() => { loading = false; });
  }

  function hide() {
    scheduleHide();
  }
</script>

<div
  class="relative inline-flex"
  onmouseenter={show}
  onmouseleave={hide}
>
  {#if noFetch}
    <span class="text-primary">@{user}</span>
  {:else}
    <a href="https://x.com/{user}" target="_blank" rel="noopener noreferrer" class="text-primary hover:brightness-125 cursor-help transition-all">@{user}</a>
  {/if}
  {#if active && !noFetch}
    <div
      class="absolute bottom-full left-1/2 -translate-x-1/2 mb-3 z-50"
      transition:fade={{ duration: 150 }}
      onmouseenter={clearHideTimeout}
      onmouseleave={hide}
    >
      {#if loading}
        <div class="bg-base-200 border border-white/10 rounded-xl p-4 shadow-2xl text-xs opacity-80 min-w-48 text-center">
          Loading...
        </div>
      {:else if error}
        <div class="bg-base-200 border border-white/10 rounded-xl p-4 shadow-2xl text-xs opacity-80 min-w-48 text-center">
          Can't fetch data on this user
        </div>
      {:else if data}
        <div class="bg-base-200 border border-white/10 rounded-xl shadow-2xl overflow-hidden w-72">
          {#if data.banner}
            <div class="h-16 bg-cover bg-center" style="background-image: url({data.banner})"></div>
          {:else}
            <div class="h-16 bg-base-300"></div>
          {/if}
          <div class="px-4 pb-4 -mt-8 relative">
            <img src={data.avatar} alt="" class="size-14 rounded-full border-2 border-base-200 bg-base-200" />
            <p class="text-sm font-bold mt-1">{data.name}</p>
            <p class="text-xs opacity-70 line-clamp-2">{data.description}</p>
            <p class="text-[10px] opacity-50 mt-1">{data.followers.toLocaleString()} followers</p>
          </div>
        </div>
      {/if}
    </div>
  {/if}
</div>
