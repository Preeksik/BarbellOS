/**
 * Zapisane posiłki po stronie telefonu (etap 1, krok 6).
 *
 * Dodanie zestawu do dnia to zwykłe wpisy dziennika, po jednym na produkt. Wartości we
 * wpisach są podglądem do czasu wysłania: serwer liczy je z produktu i zamraża.
 */

import type { DiaryEntry, Meal, MealSlot, RecentMeal } from "./api";
import { portionOf } from "./diary";

/** Wpisy dziennika z zestawu. Każdy dostaje własny identyfikator (idempotentny zapis). */
export function mealEntries(
  meal: Meal,
  day: string,
  slot: MealSlot,
  now: Date,
  newId: () => string,
): DiaryEntry[] {
  return meal.items.map((item, index) => ({
    id: newId(),
    date: day,
    meal_slot: slot,
    food_id: item.food_id,
    food_name: item.food_name,
    amount: item.amount,
    unit: item.unit,
    values: portionOf(item.per_100, item.amount),
    source: "meal",
    // Kolejne milisekundy: wpisy zachowują w dzienniku kolejność z zestawu.
    created_at: new Date(now.getTime() + index).toISOString(),
  }));
}

/**
 * Kopia posiłku z innego dnia (22.11.2026): te same produkty, ilości i zamrożone wartości.
 * Każda kopia ma nowy identyfikator i wskazuje oryginał, z którego serwer bierze wartości.
 */
export function copiedEntries(
  meal: RecentMeal,
  day: string,
  slot: MealSlot,
  now: Date,
  newId: () => string,
): { entry: DiaryEntry; copyOf: string }[] {
  return meal.entries.map((original, index) => ({
    copyOf: original.id,
    entry: {
      ...original,
      id: newId(),
      date: day,
      meal_slot: slot,
      source: "copy",
      ai_run_id: null,
      created_at: new Date(now.getTime() + index).toISOString(),
    },
  }));
}
