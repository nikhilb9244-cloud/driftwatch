import { defineConfig } from "vite";

// A static site: relative asset paths so the build works from any sub-path
// (GitHub Pages, Cloudflare Pages, a local file server).
export default defineConfig({
  base: "./",
  worker: { format: "es" },
  build: {
    // No source maps in the deployed bundle. They were 9.5 MB of the 12 MB dist, they publish
    // the unminified sources and the comments with them, and nothing about a static viewer
    // needs them on a CDN. `npm run build -- --sourcemap` turns them back on for a local debug.
    sourcemap: false,
    target: "es2022",
    chunkSizeWarningLimit: 1500,
  },
});
