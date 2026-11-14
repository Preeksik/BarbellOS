import { PersistQueryClientProvider } from "@tanstack/react-query-persist-client";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import { persistOptions, queryClient, resumeAfterRestore } from "./lib/offline";
import "./styles.css";

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
