<script lang="ts">
  import { preprocessMarkdown } from "./lib/editor-markdown";
  import { sanitizeHtml, splitContent } from "./lib/uder-format";

  let {
    text,
    images = "render",
    class: className = "",
  }: {
    text: string;
    images?: "render" | "placeholder" | "skip";
    class?: string;
  } = $props();
</script>

<div class={className}>
  {#each splitContent(text) as part}
    {#if part.type === "html"}
      {@html sanitizeHtml(preprocessMarkdown(part.value).replace(/\n/g, "<br>"))}
    {:else if images === "render"}
      <img src={part.value} alt="illustration" class="ud-image" />
    {:else if images === "placeholder"}
      <span class="ud-image-placeholder">[image]</span>
    {/if}
  {/each}
</div>

<style>
  .ud-image {
    display: block;
    width: 100%;
    max-width: 100%;
    height: auto;
    margin: 0.9rem auto;
    border-radius: 0.6rem;
  }

  .ud-image-placeholder {
    display: inline-block;
    margin: 0.25rem 0;
    padding: 0.1rem 0.45rem;
    border: 1px dashed color-mix(in oklch, var(--color-base-content) 25%, transparent);
    border-radius: 0.375rem;
    background-color: color-mix(in oklch, var(--color-base-content) 5%, transparent);
    font-size: 9px;
    font-family: ui-monospace, monospace;
    letter-spacing: 0.05em;
    color: color-mix(in oklch, var(--color-base-content) 40%, transparent);
  }
</style>
