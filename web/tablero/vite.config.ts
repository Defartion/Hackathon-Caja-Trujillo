import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: { port: 5175, strictPort: true },
  preview: { port: 5175, strictPort: true },
  build: {
    chunkSizeWarningLimit: 700, // recharts va en su propio chunk (~580 kB sin comprimir, ~160 kB gzip)
    rollupOptions: { output: { manualChunks: { recharts: ["recharts"], react: ["react", "react-dom"] } } },
  },
});
