<script lang="ts">
  import { DEFAULT_AVATAR_SRC, brokenAvatars, markAvatarBroken } from "./avatar-fallback";

  let {
    src,
    alt = "",
    class: className = "",
    size = 2.25,
    loading = "lazy",
    onbroken = () => {},
  }: {
    src: string | null | undefined;
    alt?: string;
    class?: string;
    size?: number;
    loading?: "lazy" | "eager";
    onbroken?: () => void;
  } = $props();

  const isBroken = $derived(!!src && $brokenAvatars.has(src));

  function handleError() {
    if (src) markAvatarBroken(src);
    onbroken();
  }
</script>

<img
  {alt}
  src={!src || isBroken ? DEFAULT_AVATAR_SRC : src}
  class={className}
  style="width: {size}rem; height: {size}rem"
  {loading}
  onerror={handleError}
/>

<style>
  img {
    flex: none;
    border-radius: 9999px;
    object-fit: cover;
  }
</style>
