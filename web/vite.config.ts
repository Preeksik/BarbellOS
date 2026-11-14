import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: ["favicon.svg", "apple-touch-icon.png"],
      manifest: {
        name: "BarbellOS",
        short_name: "BarbellOS",
        description: "Dieta, trening i regeneracja w jednej aplikacji.",
        lang: "pl",
        display: "standalone",
        start_url: "/",
        scope: "/",
        background_color: "#0f1115",
        theme_color: "#0f1115",
        icons: [
          { src: "/icon-192.png", sizes: "192x192", type: "image/png" },
          { src: "/icon-512.png", sizes: "512x512", type: "image/png" },
          { src: "/icon-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
        ],
      },
      workbox: {
        // Plik .wasm czytnika kodów też trafia do pamięci podręcznej, żeby skaner działał offline.
        globPatterns: ["**/*.{js,css,html,svg,png,wasm,webmanifest}"],
        maximumFileSizeToCacheInBytes: 4 * 1024 * 1024,
        navigateFallback: "/index.html",
        navigateFallbackDenylist: [/^\/api\//],
      },
    }),
  ],
  server: {
    // Lokalnie frontend (5173) woła backend (8000) pod tym samym adresem co w produkcji.
    proxy: { "/api": "http://localhost:8000" },
  },
});
