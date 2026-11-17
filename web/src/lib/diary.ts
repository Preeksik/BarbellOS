/**
 * Dziennik dnia po stronie telefonu: daty, posiłki i podgląd przed odpowiedzią serwera.
 *
 * Wartości odżywcze liczy serwer (`backend/app/core/diary.py`). Funkcje liczące tutaj
 * służą wyłącznie do podglądu: żeby wpis dodany bez sieci był od razu widoczny w sumie
 * dnia. Po wysłaniu zapisu ekran pokazuje to, co policzył serwer.
 */

import type { DiaryDay, DiaryEntry, MacroKey, MacroTotals, MealSlot, Per100 } from "./api";

export const MACRO_KEYS: MacroKey[] = [
  "kcal",
  "protein_g",
  "fat_g",
  "sat_fat_g",
  "carbs_g",
  "sugars_g",
  "fiber_g",
  "salt_g",
];

/** Kolejność jak na serwerze (`MEAL_SLOTS`). */
export const MEAL_SLOTS: { id: MealSlot; label: string }[] = [
  { id: "breakfast", label: "Śniadanie" },
  { id: "second_breakfast", label: "II śniadanie" },
  { id: "lunch", label: "Obiad" },
  { id: "snack", label: "Podwieczorek" },
  { id: "dinner", label: "Kolacja" },
];

/** Posiłek podpowiadany przy dodawaniu, według godziny na telefonie. */
export function defaultSlot(hour: number): MealSlot {
  if (hour < 10) return "breakfast";
  if (hour < 12) return "second_breakfast";
  if (hour < 16) return "lunch";
  if (hour < 18) return "snack";
  return "dinner";
}

// ---------- daty ----------

/**
 * Dzień według zegara telefonu. `toISOString()` podaje datę w UTC, więc wpis dodany
 * w Polsce po północy trafiłby do dnia poprzedniego.
 */
export function toIsoDay(date: Date): string {
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${date.getFullYear()}-${month}-${day}`;
}

function fromIsoDay(iso: string): Date {
  const [year, month, day] = iso.split("-").map(Number);
  return new Date(year, month - 1, day);
}

export function shiftDay(iso: string, days: number): string {
  const date = fromIsoDay(iso);
  date.setDate(date.getDate() + days);
  return toIsoDay(date);
}

/** „Dziś", „Wczoraj", „Jutro" albo np. „pon., 16 lis". */
export function dayLabel(iso: string, today: string): string {
  if (iso === today) return "Dziś";
  if (iso === shiftDay(today, -1)) return "Wczoraj";
  if (iso === shiftDay(today, 1)) return "Jutro";
  return fromIsoDay(iso).toLocaleDateString("pl-PL", {
    weekday: "short",
    day: "numeric",
    month: "short",
  });
}

// ---------- podgląd wartości ----------

/** Wartości dla porcji. Brak danych zostaje brakiem. */
export function portionOf(per100: Per100, amount: number): Per100 {
  return scaleValues(per100, amount / 100);
}

export function scaleValues(values: Per100, ratio: number): Per100 {
  const out = {} as Per100;
  for (const key of MACRO_KEYS) {
    const value = values[key];
    out[key] = value == null ? null : value * ratio;
  }
  return out;
}

/** Suma wpisów. Brak danych liczy się jak zero, tak samo jak na serwerze. */
export function sumValues(entries: { values: Per100 }[]): MacroTotals {
  const totals = {} as MacroTotals;
  for (const key of MACRO_KEYS) {
    totals[key] = entries.reduce((sum, entry) => sum + (entry.values[key] ?? 0), 0);
  }
  return totals;
}

function slotIndex(slot: MealSlot): number {
  return MEAL_SLOTS.findIndex((s) => s.id === slot);
}

function buildDay(date: string, entries: DiaryEntry[]): DiaryDay {
  const sorted = [...entries].sort(
    (a, b) =>
      slotIndex(a.meal_slot) - slotIndex(b.meal_slot) || a.created_at.localeCompare(b.created_at),
  );
  const by_slot: DiaryDay["by_slot"] = {};
  for (const { id } of MEAL_SLOTS) {
    const inSlot = sorted.filter((entry) => entry.meal_slot === id);
    if (inSlot.length > 0) by_slot[id] = sumValues(inSlot);
  }
  return { date, entries: sorted, totals: sumValues(sorted), by_slot };
}

export function emptyDay(date: string): DiaryDay {
  return buildDay(date, []);
}

/** Dzień z dodanym albo podmienionym wpisem (ten sam `id` oznacza zmianę). */
export function withEntry(day: DiaryDay, entry: DiaryEntry): DiaryDay {
  return buildDay(day.date, [...day.entries.filter((e) => e.id !== entry.id), entry]);
}

export function withoutEntry(day: DiaryDay, entryId: string): DiaryDay {
  return buildDay(
    day.date,
    day.entries.filter((e) => e.id !== entryId),
  );
}

/** Wpis po zmianie ilości: zamrożone wartości są skalowane, jak na serwerze. */
export function withAmount(entry: DiaryEntry, amount: number): DiaryEntry {
  return { ...entry, amount, values: scaleValues(entry.values, amount / entry.amount) };
}

/**
 * Ile wpisów nie ma danej wartości (brak danych, nie zero). Suma dnia liczy brak jak zero,
 * więc ekran musi pokazać, że „0 g soli" to w rzeczywistości „nie wiadomo".
 */
export function missingCounts(entries: { values: Per100 }[]): Record<MacroKey, number> {
  const counts = {} as Record<MacroKey, number>;
  for (const key of MACRO_KEYS) {
    counts[key] = entries.filter((entry) => entry.values[key] == null).length;
  }
  return counts;
}
