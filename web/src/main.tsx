import { PersistQueryClientProvider } from "@tanstack/react-query-persist-client";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import { persistOptions, queryClient, resumeAfterRestore } from "./lib/offline";
import { initTheme } from "./lib/theme";
// Fonty są w paczce aplikacji, a nie z Google: działają bez sieci i nikt nie widzi zapytań.
import "@fontsource/barlow/400.css";
import "@fontsource/barlow/500.css";
import "@fontsource/barlow/600.css";
import "@fontsource/barlow-condensed/600.css";
import "@fontsource/barlow-condensed/700.css";
import "./styles.css";

initTheme();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <PersistQueryClientProvider
      client={queryClient}
      persistOptions={persistOptions}
      // Bez czekania na wynik: offline wznowienie trwa do powrotu sieci, a ekran
      // „Wczytywanie…" znika dopiero po zakończeniu onSuccess.
      onSuccess={() => void resumeAfterRestore()}
    >
      <App />
    </PersistQueryClientProvider>
  </StrictMode>,
);
