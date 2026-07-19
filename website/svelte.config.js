import adapter from "@sveltejs/adapter-cloudflare";
import { vitePreprocess } from "@sveltejs/vite-plugin-svelte";

/** @type {import('@sveltejs/kit').Config} */
const config = {
  extensions: [".svelte"],
  preprocess: [
    vitePreprocess(),
  ],
  kit: {
    adapter: adapter(),

    prerender: {
      concurrency: 5,
      crawl: true,
      handleHttpError: "warn",
    },

    alias: {
      $lib: "./src/lib",
    },
  },
};

export default config;
