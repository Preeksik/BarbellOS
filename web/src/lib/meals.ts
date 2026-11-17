/**
 * Zapisane posiłki po stronie telefonu (etap 1, krok 6).
 *
 * Dodanie zestawu do dnia to zwykłe wpisy dziennika, po jednym na produkt. Wartości we
 * wpisach są podglądem do czasu wysłania: serwer liczy je z produktu i zamraża.
 */

import type { DiaryEntry, Meal, MealSlot } from "./api";
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

/** Skład zestawu z wpisów posiłku. Wpis bez produktu (np. ze zdjęcia) jest pomijany. */
export function itemsFromEntries(entries: DiaryEntry[]): { food_id: number; amount: number }[] {
  return entries
    .filter((entry): entry is DiaryEntry & { food_id: number } => entry.food_id != null)
    .map((entry) => ({ food_id: entry.food_id, amount: entry.amount }));
}
