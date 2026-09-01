import { defineConfig } from "vite";

// A static site: relative asset paths so the build works from any sub-path
// (GitHub Pages, Cloudflare Pages, a local file server).
export default defineConfig({
  base: "./",
  worker: { format: "es" },
  build: {
    target: "es2022",
    sourcemap: true,
    chunkSizeWarningLimit: 1500,
  },
});
