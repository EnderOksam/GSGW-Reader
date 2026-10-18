<script lang="ts">
  import Icon from "@iconify/svelte";
  import { page } from "$app/state";
  import ChapterComments from "./ChapterComments.svelte";
  import * as api from "./comments-api";

  let { chapter }: { chapter: string } = $props();

  let count = $state(0);
  let me = $state<api.Me | null>(null);
  let meReady = $state(false);

  const returnTo = $derived(page.url.pathname);
</script>

<div
  class="overflow-hidden rounded-2xl border-0 border-base-content/10 bg-base-200 shadow-none sm:border sm:shadow-xl sm:shadow-base-content/5"
>
  <div class="flex items-center gap-2 px-4 pb-2 pt-6 sm:px-8">
    <Icon icon="lucide:message-square-text" class="size-4 shrink-0 text-base-content/30" />
    <span class="font-mono text-xs font-bold uppercase tracking-widest text-base-content/30">Comments</span>
    <span
      class="rounded-full bg-base-content/10 px-2 py-0.5 font-mono text-[10px] font-bold tabular-nums text-base-content/50"
      >{count}</span
    >
    {#if me}
      <div
        class="ml-auto flex items-center gap-2 rounded-full border border-base-content/10 bg-base-100 py-1 pl-1 pr-1.5 shadow-sm transition-colors hover:border-base-content/20"
      >
        {#if me.avatarUrl}
          <img src={me.avatarUrl} alt="" class="me-avatar ring-1 ring-base-content/10" />
        {:else}
          <div class="me-avatar bg-base-content/10"></div>
        {/if}
        <span
          class="max-w-[11rem] truncate text-xs font-semibold leading-none text-base-content/90"
          >{me.displayName}</span
        >
        <button
          type="button"
          class="flex size-6 shrink-0 items-center justify-center rounded-full text-base-content/40 transition-colors hover:bg-error/10 hover:text-error"
          title="Sign out"
          aria-label="Sign out"
          onclick={() => (window.location.href = api.logoutUrl(returnTo))}
        >
          <Icon icon="lucide:log-out" class="size-3.5" />
        </button>
      </div>
    {:else if meReady}
      <div class="ml-auto flex items-center gap-1.5">
        <button
          type="button"
          class="inline-flex items-center gap-1.5 rounded-full border border-[#5865F2]/30 bg-[#5865F2]/10 py-1 pl-1.5 pr-2.5 text-xs font-semibold text-[#5865F2] transition-colors hover:bg-[#5865F2]/20"
          title="Sign in with Discord to comment and react"
          onclick={() => (window.location.href = api.loginUrl(returnTo))}
        >
          <Icon icon="mdi:discord" class="size-3.5" />
          Discord
        </button>
        <button
          type="button"
          class="inline-flex items-center gap-1.5 rounded-full border border-base-content/20 bg-base-content/5 py-1 pl-1.5 pr-2.5 text-xs font-semibold text-base-content/80 transition-colors hover:bg-base-content/10"
          title="Sign in with GitHub to comment and react"
          onclick={() => (window.location.href = api.githubLoginUrl(returnTo))}
        >
          <Icon icon="mdi:github" class="size-3.5" />
          GitHub
        </button>
      </div>
    {/if}
  </div>
  <div class="px-4 pb-8 sm:px-8">
    <ChapterComments {chapter} bind:count bind:me bind:meReady />
  </div>
</div>

<style>
  .me-avatar {
    width: 1.5rem;
    height: 1.5rem;
    flex: none;
    border-radius: 9999px;
    object-fit: cover;
  }
</style>
