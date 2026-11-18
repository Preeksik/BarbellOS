/**
 * Motyw kolorów: automatyczny (jak ustawienie iPhone'a), ciemny albo jasny.
 *
 * Wybór jest wygodą tego jednego urządzenia, więc żyje w localStorage, a nie na serwerze.
 * Kolory są w `styles.css`: `:root` to ciemny, `[data-theme="light"]` i
 * `prefers-color-scheme: light` (tylko przy wyborze automatycznym) to jasny.
 */

import { useSyncExternalStore } from "react";

export type ThemeChoice = "auto" | "dark" | "light";

export const THEME_CHOICES: { id: ThemeChoice; label: string }[] = [
  { id: "auto", label: "Jak w telefonie" },
  { id: "dark", label: "Ciemny" },
  { id: "light", label: "Jasny" },
];

const STORAGE_KEY = "barbellos-theme";

/** Odczyt z pamięci: wszystko poza znaną wartością (także brak) to wybór automatyczny. */
export function parseTheme(raw: string | null | undefined): ThemeChoice {
  return raw === "dark" || raw === "light" ? raw : "auto";
}

function readStored(): ThemeChoice {
  try {
    return parseTheme(localStorage.getItem(STORAGE_KEY));
  } catch {
    // Prywatne okno albo zablokowana pamięć: zostaje automatyczny.
    return "auto";
  }
}

let current: ThemeChoice = "auto";
const listeners = new Set<() => void>();

function apply(choice: ThemeChoice): void {
  const root = document.documentElement;
  if (choice === "auto") delete root.dataset.theme;
  else root.dataset.theme = choice;
}

/** Wywołane raz przed pierwszym rysowaniem, żeby ekran nie mignął złym motywem. */
export function initTheme(): void {
  current = readStored();
  apply(current);
}

export function setTheme(choice: ThemeChoice): void {
  current = choice;
  apply(choice);
  try {
    if (choice === "auto") localStorage.removeItem(STORAGE_KEY);
    else localStorage.setItem(STORAGE_KEY, choice);
  } catch {
    // Bez pamięci wybór działa do zamknięcia aplikacji.
  }
  for (const listener of listeners) listener();
}

export function useTheme(): ThemeChoice {
  return useSyncExternalStore(
    (listener) => {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    () => current,
  );
}
