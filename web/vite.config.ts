/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  // Wersję widać na zakładce „Start": po niej poznasz, czy telefon ma już nowy kod.
  define: { __BUILD_TIME__: JSON.stringify(new Date().toISOString()) },
  plugins: [
    react(),
    VitePWA({
      // Nowa wersja czeka, aż użytkownik stuknie „Nowa wersja" (src/lib/appUpdate.ts).
      // Rejestrację robi ten moduł, a nie wstrzyknięty skrypt: sam skrypt nie umie
      // powiadomić aplikacji, że nowa wersja jest gotowa.
      registerType: "prompt",
      includeAssets: ["favicon.svg", "apple-touch-icon.png"],
      manifest: {
        name: "BarbellOS",
        short_name: "BarbellOS",
        description: "Dieta, trening i regeneracja w jednej aplikacji.",
        lang: "pl",
        display: "standalone",
        start_url: "/",
        scope: "/",
        background_color: "#16181a",
        theme_color: "#111214",
        icons: [
          { src: "/icon-192.png", sizes: "192x192", type: "image/png" },
          { src: "/icon-512.png", sizes: "512x512", type: "image/png" },
          { src: "/icon-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
        ],
      },
      workbox: {
        // Plik .wasm czytnika kodów też trafia do pamięci podręcznej, żeby skaner działał offline.
        // Klatki ilustracji techniki (.webp) też, żeby działały na siłowni bez zasięgu.
        // Fonty .woff2 tak samo (starsze .woff z paczki pomijamy: iOS czyta .woff2).
        globPatterns: ["**/*.{js,css,html,svg,png,webp,wasm,webmanifest,woff2}"],
        // Znaki wietnamskie nie występują w polskich tekstach: tych fontów telefon nie pobiera.
        globIgnores: ["**/*vietnamese*"],
        maximumFileSizeToCacheInBytes: 4 * 1024 * 1024,
        navigateFallback: "/index.html",
        navigateFallbackDenylist: [/^\/api\//],
      },
    }),
  ],
  // Testy czytają styles.css jako tekst (src/styles.test.ts); domyślnie Vitest podaje pusty CSS.
  test: { css: { include: [/styles\.css/] } },
  server: {
    // Lokalnie frontend (5173) woła backend (8000) pod tym samym adresem co w produkcji.
    proxy: { "/api": "http://localhost:8000" },
  },
});
