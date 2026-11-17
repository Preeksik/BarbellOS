/**
 * Cele dzienne na ekranie (etap 1, krok 4).
 *
 * Rodzaj celu i zakresy ustala serwer (`backend/app/core/targets.py`). Tutaj tylko
 * zamieniamy sumę dnia i cel na wypełnienie paska i podpis. Suma może być podglądem
 * policzonym na telefonie, gdy wpisy czekają w kolejce offline.
 */

import type { GoalKind, MacroKey } from "./api";

/** Kolejność i nazwy w formularzu celów. Rodzaj jest kopią z serwera (do opisu pola). */
export const GOAL_ROWS: { key: MacroKey; label: string; unit: string; kind: GoalKind }[] = [
  { key: "kcal", label: "Kalorie", unit: "kcal", kind: "target" },
  { key: "protein_g", label: "Białko", unit: "g", kind: "min" },
  { key: "fat_g", label: "Tłuszcz", unit: "g", kind: "target" },
  { key: "carbs_g", label: "Węglowodany", unit: "g", kind: "target" },
  { key: "fiber_g", label: "Błonnik", unit: "g", kind: "min" },
  { key: "sat_fat_g", label: "Nasycone", unit: "g", kind: "max" },
  { key: "sugars_g", label: "Cukry", unit: "g", kind: "max" },
  { key: "salt_g", label: "Sól", unit: "g", kind: "max" },
];

export const KIND_HINT: Record<GoalKind, string> = {
  target: "cel",
  min: "co najmniej",
  max: "najwyżej",
};

export type ProgressState = "under" | "done" | "over";

export interface Progress {
  /** Wypełnienie paska, 0–1. */
  fill: number;
  state: ProgressState;
  /** Ile zostało do celu (dodatnie) albo o ile przekroczono (ujemne). */
  left: number;
}

/**
 * Stan paska. `done` znaczy: cel osiągnięty (dla `min`), mieści się w celu (dla `target`
 * do 100%). `over`: przekroczony limit (`max`) albo cel (`target`). Dla `min` przekroczenie
 * nie jest problemem, więc zostaje `done`.
 */
export function progress(value: number, goal: number, kind: GoalKind): Progress {
  const left = goal - value;
  const fill = goal > 0 ? Math.min(1, Math.max(0, value / goal)) : 0;
  let state: ProgressState;
  if (kind === "min") state = value >= goal ? "done" : "under";
  else if (value > goal) state = "over";
  else state = kind === "target" && value >= goal ? "done" : "under";
  return { fill, state, left };
}

/** Podpis pod paskiem, np. „zostało 650 kcal", „+120 kcal ponad cel". */
export function progressText(p: Progress, kind: GoalKind, unit: string): string {
  const amount = Math.abs(p.left);
  const shown =
    unit === "kcal"
      ? Math.round(amount).toLocaleString("pl-PL")
      : amount.toLocaleString("pl-PL", { maximumFractionDigits: 1 });
  if (p.state === "over") return `+${shown} ${unit} ponad ${kind === "max" ? "limit" : "cel"}`;
  if (kind === "min" && p.state === "done") return "cel osiągnięty";
  if (kind === "max") return `zostało ${shown} ${unit} do limitu`;
  return p.state === "done" ? "cel osiągnięty" : `zostało ${shown} ${unit}`;
}

/** Białko, tłuszcz i węglowodany: bez celu dla nich dziennik nie pokaże „ile na ile". */
export const MACRO_GOAL_KEYS: MacroKey[] = ["protein_g", "fat_g", "carbs_g"];

/** Czy któryś z głównych makroskładników nie ma celu. */
export function missingMacroGoals(goals: Record<MacroKey, number | null> | null): boolean {
  return MACRO_GOAL_KEYS.some((key) => goals?.[key] == null);
}
