/**
 * Aktualizacja zainstalowanej aplikacji (PWA).
 *
 * Service worker podaje aplikację z pamięci telefonu, więc po wdrożeniu telefon dalej
 * pokazuje starą wersję. Nowa pobiera się w tle i czeka. Tutaj dowiadujemy się, że jest
 * gotowa, i pokazujemy przycisk „Nowa wersja". Przełączenie następuje po stuknięciu,
 * a nie samo: przeładowanie w trakcie wpisywania wartości skasowałoby formularz.
 */

import { useSyncExternalStore } from "react";
import { registerSW } from "virtual:pwa-register";

/** Chwila zbudowania tej wersji (wstawia ją Vite). Widać ją na zakładce „Start". */
export const BUILD_TIME: string = __BUILD_TIME__;

let ready = false;
const listeners = new Set<() => void>();

function setReady(): void {
  ready = true;
  for (const listener of listeners) listener();
}

const activateUpdate = registerSW({
  immediate: true,
  onNeedRefresh: setReady,
  onRegisteredSW(_url, registration) {
    if (!registration) return;
    // iOS wznawia aplikację z tła bez ponownego wczytania, więc sama z siebie nie
    // sprawdziłaby nowej wersji przez wiele dni. Sprawdzamy przy każdym powrocie.
    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "visible") void registration.update().catch(() => undefined);
    });
  },
});

/** Czy nowa wersja jest pobrana i czeka na przełączenie. */
export function useUpdateReady(): boolean {
  return useSyncExternalStore(
    (listener) => {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    () => ready,
  );
}

/** Przełącza na nową wersję: service worker przejmuje stronę, a ta wczytuje się ponownie. */
export function applyUpdate(): void {
  void activateUpdate(true);
}
