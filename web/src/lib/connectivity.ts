/**
 * Wykrywanie braku połączenia z serwerem.
 *
 * Przeglądarka zgłasza „online", gdy telefon jest w sieci Wi-Fi, nawet jeśli ta sieć nie
 * ma internetu (częste na siłowni). Dlatego o stanie decyduje wynik prawdziwego żądania:
 * nieudane żądanie przełącza TanStack Query w tryb offline (zapisy trafiają do kolejki),
 * a lekki endpoint /api/healthz jest odpytywany, aż serwer znów odpowie.
 */

import { onlineManager } from "@tanstack/react-query";

const PROBE_INTERVAL_MS = 5000;
let timer: ReturnType<typeof setInterval> | undefined;

async function serverReachable(): Promise<boolean> {
  try {
    return (await fetch("/api/healthz", { cache: "no-store" })).ok;
  } catch {
    return false;
  }
}

export function reportNetworkFailure(): void {
  onlineManager.setOnline(false);
  if (timer !== undefined) return;
  timer = setInterval(async () => {
    if (await serverReachable()) {
      clearInterval(timer);
      timer = undefined;
      onlineManager.setOnline(true);
    }
  }, PROBE_INTERVAL_MS);
}
