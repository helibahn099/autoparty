import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

export default defineConfig({
  plugins: [react()],
  envDir: repoRoot,
  server: {
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
});
