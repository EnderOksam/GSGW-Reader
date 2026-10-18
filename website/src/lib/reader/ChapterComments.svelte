<script lang="ts">
  import { onMount, tick } from "svelte";
  import Icon from "@iconify/svelte";
  import { page } from "$app/state";
  import { renderMarkdown } from "./markdown-lite";
  import CommentComposer from "./CommentComposer.svelte";
  import * as api from "./comments-api";
  import type { Comment } from "./comments-api";

  let {
    chapter,
    count = $bindable(0),
    me = $bindable<api.Me | null>(null),
    meReady = $bindable(false),
  }: { chapter: string; count?: number; me?: api.Me | null; meReady?: boolean } = $props();

  const EMOJIS = ["👍", "❤️", "😂", "🎉", "😮", "😢", "🔥", "👀", "🚀", "👎"];

  let comments = $state<Comment[]>([]);
  let chapterReactions = $state<api.Reaction[]>([]);
  let loadingCount = $state(true);
  let loadingRoots = $state(false);
  let loaded = $state(false);
  let error = $state("");
  let replyTo = $state<number | null>(null);
  let editingId = $state<number | null>(null);
  let editDraft = $state("");
  let pickerFor = $state<number | null>(null);
  let chapterPicker = $state(false);
  let sort = $state<"new" | "old">("new");
  let authError = $state<string | null>(null);
  let highlightId = $state<number | null>(null);
  let expandedThreads = $state<Record<number, boolean>>({});
  let replyCounts = $state<Record<string, number>>({});
  let loadingReplies = $state<Record<number, boolean>>({});
  let counts = $state<api.CommentCounts>({ total: 0, roots: 0, replies: 0 });

  const returnTo = $derived(page.url.pathname);

  function timeOf(iso: string): number {
    const normalized = iso.includes("T") ? iso : iso.replace(" ", "T") + "Z";
    const t = new Date(normalized).getTime();
    return Number.isNaN(t) ? 0 : t;
  }

  function byOldest(a: Comment, b: Comment): number {
    const diff = timeOf(a.createdAt) - timeOf(b.createdAt);
    return diff !== 0 ? diff : a.id - b.id;
  }

  const topLevel = $derived(
    comments.filter((c) => !c.parentId).sort((a, b) => (sort === "old" ? byOldest(a, b) : byOldest(b, a)))
  );

  function repliesFor(id: number): Comment[] {
    return comments.filter((c) => c.parentId === id).sort(byOldest);
  }

  function toggleThread(id: number) {
    expandedThreads = { ...expandedThreads, [id]: !expandedThreads[id] };
  }

  function relTime(iso: string): string {
    const then = timeOf(iso);
    if (!then) return "";
    const diff = Math.max(0, Date.now() - then);
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return "just now";
    if (mins < 60) return `${mins}m ago`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    if (days < 30) return `${days}d ago`;
    return new Date(then).toLocaleDateString();
  }

  function reset() {
    comments = [];
    chapterReactions = [];
    replyCounts = {};
    loadingReplies = {};
    expandedThreads = {};
    loaded = false;
    loadingRoots = false;
    meReady = false;
    error = "";
  }

  async function initChapter() {
    reset();
    loadingCount = true;
    try {
      const [meRes, countRes, reactRes] = await Promise.all([
        api.getMe(),
        api.getCommentCount(chapter),
        api.getChapterReactions(chapter).catch(() => ({ reactions: [] as api.Reaction[] })),
      ]);
      me = meRes.user;
      counts = countRes;
      count = countRes.total;
      chapterReactions = reactRes.reactions;
    } catch (e) {
      error = e instanceof Error ? e.message : "Failed to load comments";
    } finally {
      loadingCount = false;
      meReady = true;
    }
  }

  async function showComments() {
    if (loaded || loadingRoots) return;
    loadingRoots = true;
    error = "";
    try {
      const res = await api.getRootComments(chapter);
      comments = res.comments;
      replyCounts = res.replyCounts ?? {};
      counts = { total: res.total, roots: res.roots, replies: res.replies };
      count = res.total;
      loaded = true;
    } catch (e) {
      error = e instanceof Error ? e.message : "Failed to load comments";
    } finally {
      loadingRoots = false;
    }
  }

  async function refreshRoots() {
    try {
      const res = await api.getRootComments(chapter);
      const roots = res.comments;
      const rootIds = new Set(roots.map((c) => c.id));
      comments = [...roots, ...comments.filter((c) => c.parentId != null && rootIds.has(c.parentId))];
      replyCounts = res.replyCounts ?? {};
      counts = { total: res.total, roots: res.roots, replies: res.replies };
      count = res.total;
      loaded = true;
    } catch {
      /* keep existing list */
    }
  }

  async function loadThread(rootId: number, force = false) {
    if (loadingReplies[rootId]) return;
    if (!force && repliesFor(rootId).length > 0) {
      toggleThread(rootId);
      return;
    }
    loadingReplies = { ...loadingReplies, [rootId]: true };
    try {
      const res = await api.getReplies(rootId);
      comments = [...comments.filter((c) => c.parentId !== rootId), ...res.comments];
      replyCounts = { ...replyCounts, [String(rootId)]: res.comments.length };
      expandedThreads = { ...expandedThreads, [rootId]: true };
    } catch (e) {
      error = e instanceof Error ? e.message : "Failed to load replies";
    } finally {
      loadingReplies = { ...loadingReplies, [rootId]: false };
    }
  }

  function onRepliesClick(rootId: number) {
    if (expandedThreads[rootId]) {
      toggleThread(rootId);
    } else {
      loadThread(rootId);
    }
  }

  function replyTotal(rootId: number): number {
    const known = Number(replyCounts[String(rootId)] ?? 0);
    return Math.max(known, repliesFor(rootId).length);
  }

  $effect(() => {
    chapter;
    initChapter();
  });

  onMount(() => {
    authError = new URLSearchParams(window.location.search).get("auth_error");
    const id = setInterval(async () => {
      if (document.hidden || editingId !== null || !loaded) return;
      try {
        const res = await api.getCommentCount(chapter);
        if (res.total !== counts.total) {
          counts = res;
          count = res.total;
          await refreshRoots();
        }
      } catch {
        /* ignore transient poll errors */
      }
    }, 30000);
    return () => clearInterval(id);
  });

  async function postNew(body: string) {
    await api.postComment(chapter, body, null);
    await refreshRoots();
  }

  async function postReply(parentId: number, body: string) {
    const { comment } = await api.postComment(chapter, body, parentId);
    replyTo = null;
    const rootId = comment?.parentId ?? parentId;
    await loadThread(rootId, true);
    try {
      const res = await api.getCommentCount(chapter);
      counts = res;
      count = res.total;
    } catch {
      /* ignore */
    }
    const id = comment?.id;
    if (id) {
      await tick();
      document
        .querySelector(`[data-cmt-id="${id}"]`)
        ?.scrollIntoView({ block: "center", behavior: "smooth" });
      highlightId = id;
      setTimeout(() => {
        if (highlightId === id) highlightId = null;
      }, 1800);
    }
  }

  async function reactChapter(emoji: string) {
    if (!me) {
      error = "Sign in to react.";
      return;
    }
    try {
      const { reactions } = await api.toggleChapterReaction(chapter, emoji);
      chapterReactions = reactions;
      chapterPicker = false;
    } catch (e) {
      error = e instanceof Error ? e.message : "Failed to react";
    }
  }

  async function react(id: number, emoji: string) {
    if (!me) {
      error = "Sign in to react.";
      return;
    }
    try {
      const { reactions } = await api.toggleReaction(id, emoji);
      comments = comments.map((c) => (c.id === id ? { ...c, reactions } : c));
      pickerFor = null;
    } catch (e) {
      error = e instanceof Error ? e.message : "Failed to react";
    }
  }

  function startEdit(comment: Comment) {
    editingId = comment.id;
    editDraft = comment.body;
  }

  async function saveEdit() {
    if (editingId === null) return;
    const body = editDraft.trim();
    if (!body) return;
    try {
      const id = editingId;
      await api.editComment(id, body);
      comments = comments.map((c) => (c.id === id ? { ...c, body, edited: true } : c));
      editingId = null;
    } catch (e) {
      error = e instanceof Error ? e.message : "Failed to edit";
    }
  }

  async function removeComment(id: number) {
    if (!confirm("Delete this comment?")) return;
    try {
      await api.deleteComment(id);
      comments = comments.filter((c) => c.id !== id && c.parentId !== id);
      await refreshRoots();
    } catch (e) {
      error = e instanceof Error ? e.message : "Failed to delete";
    }
  }
</script>

{#snippet reactionPills(reactions: api.Reaction[], handler: (emoji: string) => void)}
  {#each reactions.filter((r) => r.count > 0) as reaction (reaction.emoji)}
    <button
      type="button"
      class="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium transition-colors {reaction.mine ? 'border-primary/50 bg-primary/10 text-primary' : 'border-base-content/10 bg-base-200/50 text-base-content/70 hover:border-primary/30 hover:bg-base-200'}"
      title={reaction.users.join(", ")}
      onclick={() => handler(reaction.emoji)}
    >
      <span class="text-sm leading-none">{reaction.emoji}</span>
      <span class="tabular-nums">{reaction.count}</span>
    </button>
  {/each}
{/snippet}

{#if authError}
  <div class="mb-4 flex items-start gap-2.5 rounded-xl border border-error/25 bg-error/10 px-4 py-3 text-sm text-error">
    <Icon icon="lucide:alert-circle" class="mt-0.5 size-4 shrink-0" />
    <span>{authError === "state" ? "Sign-in session expired. Please try again." : "Sign-in failed. Please try again."}</span>
  </div>
{/if}

{#if error}
  <div class="mb-4 flex items-start gap-2.5 rounded-xl border border-error/25 bg-error/10 px-4 py-2.5 text-sm text-error">
    <Icon icon="lucide:alert-circle" class="mt-0.5 size-4 shrink-0" />
    <span>{error}</span>
  </div>
{/if}

{#if chapterReactions.some((r) => r.count > 0) || me}
  <div class="mb-5">
    <div class="flex flex-wrap items-center justify-center gap-1.5">
      {@render reactionPills(chapterReactions, reactChapter)}
      {#if me}
        <button
          type="button"
          class="inline-flex items-center rounded-full border p-2 transition-colors {chapterPicker ? 'border-primary/40 text-primary' : 'border-base-content/10 bg-base-200/50 text-base-content/45 hover:border-primary/30 hover:text-primary'}"
          onclick={() => (chapterPicker = !chapterPicker)}
          aria-label="React to this chapter"
        >
          <Icon icon="lucide:smile-plus" class="size-4" />
        </button>
      {/if}
      {#if chapterReactions.length === 0}
        <span class="px-1 text-xs text-base-content/40">React to this chapter</span>
      {/if}
    </div>
    {#if chapterPicker}
      <div class="mx-auto mt-2 flex w-fit flex-wrap justify-center gap-0.5 rounded-xl border border-base-content/10 bg-base-200/40 p-1.5">
        {#each EMOJIS as emoji (emoji)}
          <button type="button" class="rounded-lg px-2 py-1.5 text-base leading-none transition-colors hover:bg-base-200" onclick={() => reactChapter(emoji)}>{emoji}</button>
        {/each}
      </div>
    {/if}
  </div>
{/if}

{#if me}
  <div class="mb-5 flex gap-2.5 sm:gap-3">
    {#if me.avatarUrl}
      <img src={me.avatarUrl} alt="" class="cmt-avatar hidden ring-2 ring-base-content/10 sm:block" />
    {:else}
      <div class="hidden size-9 shrink-0 rounded-full bg-base-content/10 sm:block"></div>
    {/if}
    <div class="min-w-0 flex-1">
      <CommentComposer placeholder="Write a comment…" submitLabel="Comment" onSubmit={postNew} />
    </div>
  </div>
{/if}

{#if loaded}
  <div class="mb-4 flex items-center justify-end gap-3">
    <div class="inline-flex rounded-lg border border-base-content/10 bg-base-200/50 p-0.5 text-xs" role="group" aria-label="Sort comments">
      <button
        type="button"
        class="rounded-md px-2.5 py-1 font-medium transition-colors {sort === 'new' ? 'bg-base-100 text-base-content shadow-sm' : 'text-base-content/50 hover:text-base-content'}"
        aria-pressed={sort === "new"}
        onclick={() => (sort = "new")}
      >
        Newest
      </button>
      <button
        type="button"
        class="rounded-md px-2.5 py-1 font-medium transition-colors {sort === 'old' ? 'bg-base-100 text-base-content shadow-sm' : 'text-base-content/50 hover:text-base-content'}"
        aria-pressed={sort === "old"}
        onclick={() => (sort = "old")}
      >
        Oldest
      </button>
    </div>
  </div>
{/if}

{#if !loaded}
  {#if loadingCount}
    <div class="py-8 text-center text-sm text-base-content/40">Loading comments…</div>
  {:else if counts.total === 0}
    <div class="flex flex-col items-center gap-2 rounded-2xl border border-dashed border-base-content/15 py-10 text-center">
      <Icon icon="lucide:message-square-dashed" class="size-6 text-base-content/25" />
      <p class="text-sm text-base-content/45">No comments yet. Be the first!</p>
    </div>
  {:else}
    <div class="flex flex-col items-center gap-1.5 rounded-2xl border border-dashed border-base-content/15 py-8 text-center">
      <button
        type="button"
        class="inline-flex items-center gap-2 rounded-xl border border-base-content/10 bg-base-100 px-4 py-2.5 text-sm font-semibold text-base-content transition-colors hover:border-primary/40 hover:text-primary disabled:opacity-60"
        onclick={showComments}
        disabled={loadingRoots}
      >
        {#if loadingRoots}
          <Icon icon="svg-spinners:180-ring" class="size-4" />
        {:else}
          <Icon icon="lucide:message-square" class="size-4" />
        {/if}
        Show {counts.total} {counts.total === 1 ? "comment" : "comments"}
      </button>
      {#if counts.replies > 0}
        <p class="text-xs text-base-content/45">
          includes {counts.replies} {counts.replies === 1 ? "reply" : "replies"}
        </p>
      {/if}
    </div>
  {/if}
{:else}
  <ul class="cmt-list space-y-3">
    {#each topLevel as comment (comment.id)}
      {@const replies = repliesFor(comment.id)}
      {@const replyCountTotal = replyTotal(comment.id)}
      <li
        data-cmt-id={comment.id}
        class="rounded-2xl border border-base-content/10 bg-base-100 p-3.5 transition-colors hover:border-base-content/20 sm:p-4 {highlightId === comment.id ? 'cmt-flash' : ''}"
      >
        {@render commentItem(comment, false)}
        {#if replyCountTotal > 0}
          <button
            type="button"
            class="mt-3 flex items-center gap-1.5 text-xs font-semibold text-primary/80 transition-colors hover:text-primary disabled:opacity-60"
            onclick={() => onRepliesClick(comment.id)}
            disabled={loadingReplies[comment.id]}
            aria-expanded={!!expandedThreads[comment.id]}
          >
            {#if loadingReplies[comment.id]}
              <Icon icon="svg-spinners:180-ring" class="size-3.5" />
              Loading replies…
            {:else}
              <Icon icon={expandedThreads[comment.id] ? "lucide:chevron-up" : "lucide:chevron-down"} class="size-3.5" />
              {expandedThreads[comment.id]
                ? "Hide replies"
                : `View ${replyCountTotal} ${replyCountTotal === 1 ? "reply" : "replies"}`}
            {/if}
          </button>
          {#if expandedThreads[comment.id]}
            <div class="cmt-thread mt-2.5 space-y-2.5 border-l-2 border-primary/25 pl-3 sm:pl-4">
              {#each replies as reply (reply.id)}
                <div data-cmt-id={reply.id} class="rounded-xl bg-base-200/50 p-3 {highlightId === reply.id ? 'cmt-flash' : ''}">
                  {@render commentItem(reply, true)}
                </div>
              {/each}
            </div>
          {/if}
        {/if}
      </li>
    {/each}
  </ul>
{/if}

{#snippet commentItem(comment: Comment, compact = false)}
  <div class="flex gap-2.5 sm:gap-3">
    {#if comment.author.avatarUrl}
      <img src={comment.author.avatarUrl} alt="" class="cmt-avatar {compact ? 'cmt-avatar-sm' : ''} ring-1 ring-base-content/10" loading="lazy" />
    {:else}
      <div class="cmt-avatar {compact ? 'cmt-avatar-sm' : ''} bg-base-content/10"></div>
    {/if}
    <div class="min-w-0 flex-1">
      <div class="flex flex-wrap items-center gap-x-2 gap-y-0.5">
        <span class="text-sm font-semibold text-base-content">{comment.author.displayName}</span>
        {#if comment.author.provider === "discord"}
          <span class="inline-flex items-center gap-1 rounded-md bg-[#5865F2]/15 px-1.5 py-0.5 text-[10px] font-semibold text-[#5865F2]">
            <Icon icon="mdi:discord" class="size-3" /> Discord
          </span>
        {:else}
          <span class="inline-flex items-center gap-1 rounded-md bg-base-content/10 px-1.5 py-0.5 text-[10px] font-semibold text-base-content/60">
            <Icon icon="mdi:github" class="size-3" /> GitHub
          </span>
        {/if}
        {#if comment.author.isLegacy}
          <span class="inline-flex items-center gap-1 rounded-md bg-amber-500/15 px-1.5 py-0.5 text-[10px] font-semibold text-amber-600" title="Commented before the new comment system">
            <Icon icon="lucide:history" class="size-3" /> legacy
          </span>
        {/if}
        <span class="text-xs text-base-content/40" title={comment.createdAt}>{relTime(comment.createdAt)}</span>
        {#if comment.edited}<span class="text-xs text-base-content/30">· edited</span>{/if}
      </div>

      {#if editingId === comment.id}
        <div class="mt-2">
          <textarea bind:value={editDraft} rows="3" maxlength="4000" class="block w-full resize-none rounded-xl border border-base-content/15 bg-base-200/50 px-3 py-2 text-sm leading-relaxed text-base-content outline-none focus:border-primary/50"></textarea>
          <div class="mt-1.5 flex gap-2">
            <button type="button" class="rounded-lg bg-primary px-3 py-1 text-xs font-semibold text-primary-content transition-colors hover:bg-primary/90" onclick={saveEdit}>Save</button>
            <button type="button" class="rounded-lg px-3 py-1 text-xs font-medium text-base-content/60 transition-colors hover:bg-base-content/5" onclick={() => (editingId = null)}>Cancel</button>
          </div>
        </div>
      {:else}
        <div class="md mt-1.5 text-sm leading-relaxed text-base-content/90 break-words">
          {@html renderMarkdown(comment.body)}
        </div>
      {/if}

      <div class="mt-2.5 flex flex-wrap items-center gap-1.5">
        {@render reactionPills(comment.reactions, (emoji) => react(comment.id, emoji))}

        <button
          type="button"
          class="inline-flex items-center rounded-full border p-2 transition-colors {pickerFor === comment.id ? 'border-primary/40 text-primary' : 'border-base-content/10 bg-base-200/50 text-base-content/45 hover:border-primary/30 hover:text-primary'}"
          onclick={() => (pickerFor = pickerFor === comment.id ? null : comment.id)}
          aria-label="Add reaction"
        >
          <Icon icon="lucide:smile-plus" class="size-4" />
        </button>

        {#if me}
          <button type="button" class="ml-0.5 rounded-lg px-2 py-1 text-xs font-medium transition-colors hover:bg-base-content/5 hover:text-primary {replyTo === comment.id ? 'text-primary' : 'text-base-content/50'}" onclick={() => (replyTo = replyTo === comment.id ? null : comment.id)}>Reply</button>
        {/if}
        {#if me && me.id === comment.author.id}
          <button type="button" class="rounded-lg px-2 py-1 text-xs font-medium text-base-content/50 transition-colors hover:bg-base-content/5 hover:text-primary" onclick={() => startEdit(comment)}>Edit</button>
        {/if}
        {#if me && (me.isAdmin || me.id === comment.author.id)}
          <button type="button" class="rounded-lg px-2 py-1 text-xs font-medium text-base-content/50 transition-colors hover:bg-error/10 hover:text-error" onclick={() => removeComment(comment.id)}>Delete</button>
        {/if}
      </div>

      {#if pickerFor === comment.id}
        <div class="mt-2 flex flex-wrap gap-0.5 rounded-xl border border-base-content/10 bg-base-200/40 p-1.5">
          {#each EMOJIS as emoji (emoji)}
            <button type="button" class="rounded-lg px-2 py-1.5 text-base leading-none transition-colors hover:bg-base-200" onclick={() => react(comment.id, emoji)}>{emoji}</button>
          {/each}
        </div>
      {/if}

      {#if me && replyTo === comment.id}
        <div class="mt-3">
          <CommentComposer
            autofocus
            placeholder={`Reply to ${comment.author.displayName}…`}
            submitLabel="Reply"
            onSubmit={(body) => postReply(comment.id, body)}
            onCancel={() => (replyTo = null)}
          />
        </div>
      {/if}
    </div>
  </div>
{/snippet}

<style>
  .cmt-list {
    list-style: none;
  }
  .cmt-flash {
    animation: cmt-flash 1.8s ease-out;
  }
  @keyframes cmt-flash {
    0%,
    20% {
      background-color: color-mix(in oklab, var(--color-primary) 22%, transparent);
    }
    100% {
      background-color: transparent;
    }
  }
  .cmt-avatar {
    width: 2.25rem;
    height: 2.25rem;
    min-width: 2.25rem;
    margin: 0;
    object-fit: cover;
    border-radius: 9999px;
    flex-shrink: 0;
  }
  .cmt-avatar-sm {
    width: 1.75rem;
    height: 1.75rem;
    min-width: 1.75rem;
  }
  .md :global(p) {
    margin: 0 0 0.5rem;
  }
  .md :global(p:last-child) {
    margin-bottom: 0;
  }
  .md :global(a) {
    color: var(--color-primary);
    text-decoration: underline;
    text-underline-offset: 2px;
  }
  .md :global(a:hover) {
    text-decoration: none;
  }
  .md :global(code) {
    background: color-mix(in oklab, currentColor 10%, transparent);
    padding: 0.1rem 0.3rem;
    border-radius: 0.25rem;
    font-size: 0.85em;
  }
  .md :global(del) {
    opacity: 0.6;
  }
  .md :global(strong) {
    font-weight: 600;
  }
  .md :global(blockquote) {
    margin: 0.5rem 0;
    padding: 0.1rem 0 0.1rem 0.8rem;
    border-left: 3px solid color-mix(in oklab, currentColor 25%, transparent);
    color: color-mix(in oklab, currentColor 72%, transparent);
  }
  .md :global(blockquote p) {
    margin: 0;
  }
  .md :global(blockquote blockquote) {
    margin: 0.4rem 0;
  }
  .md :global(pre) {
    margin: 0.5rem 0;
    padding: 0.6rem 0.75rem;
    border-radius: 0.5rem;
    background: color-mix(in oklab, currentColor 8%, transparent);
    overflow-x: auto;
  }
  .md :global(pre code) {
    background: none;
    padding: 0;
    border-radius: 0;
    font-size: 0.85em;
    white-space: pre;
  }
  .md :global(img) {
    max-width: 100%;
    height: auto;
    margin: 0.35rem 0;
    border-radius: 0.5rem;
    vertical-align: middle;
  }
  .md :global(ul),
  .md :global(ol) {
    margin: 0.4rem 0 0.5rem;
    padding-left: 1.4rem;
  }
  .md :global(ul) {
    list-style: disc;
  }
  .md :global(ol) {
    list-style: decimal;
  }
  .md :global(li) {
    margin: 0.15rem 0;
  }
  .md :global(li ul),
  .md :global(li ol) {
    margin: 0.15rem 0;
  }
  .md :global(li.cmt-task) {
    list-style: none;
    margin-left: -1.2rem;
  }
  .md :global(li.cmt-task input) {
    margin-right: 0.35rem;
    vertical-align: middle;
  }
  .md :global(h1),
  .md :global(h2),
  .md :global(h3),
  .md :global(h4),
  .md :global(h5),
  .md :global(h6) {
    margin: 0.7rem 0 0.35rem;
    font-weight: 600;
    line-height: 1.3;
  }
  .md :global(h1) {
    font-size: 1.25em;
  }
  .md :global(h2) {
    font-size: 1.15em;
  }
  .md :global(h3) {
    font-size: 1.05em;
  }
  .md :global(h1:first-child),
  .md :global(h2:first-child),
  .md :global(h3:first-child) {
    margin-top: 0;
  }
  .md :global(hr) {
    margin: 0.75rem 0;
    border: 0;
    border-top: 1px solid color-mix(in oklab, currentColor 18%, transparent);
  }
</style>
