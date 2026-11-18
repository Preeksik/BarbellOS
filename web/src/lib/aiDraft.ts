/**
 * Szkic posiłku z AI po stronie telefonu (etap 2).
 *
 * Serwer rozpoznaje składniki, dopasowuje je do bazy i liczy wartości dla gramatury
 * podanej przez model. Tutaj użytkownik zmienia gramaturę i dopasowanie, więc wartości
 * są przeliczane do podglądu (`portionOf`, jak w dzienniku). Po zapisie wpisy liczy
 * i zamraża serwer (`PUT /api/diary/entries/{id}`).
 */

import type { DiaryEntry, DraftItem, Food, MacroTotals, MealDraft, MealSlot, Per100 } from "./api";
import { portionOf, sumValues } from "./diary";
import type { DiaryPutInput } from "./offline";

/** Wybór dla składnika: produkt z bazy (id) albo szacunek modelu. */
export type Choice = { kind: "food"; foodId: number } | { kind: "estimate" };

export interface ItemState {
  include: boolean;
  grams: number;
  choice: Choice;
}

/** Stan początkowy: wszystko zaznaczone, gramatura i dopasowanie od serwera. */
export function initialState(draft: MealDraft): ItemState[] {
  return draft.items.map((item) => ({
    include: true,
    grams: item.grams,
    choice: item.match ? { kind: "food", foodId: item.match.id } : { kind: "estimate" },
  }));
}

/** Produkty z bazy, które można wybrać dla składnika (dopasowany pierwszy). */
export function foodOptions(item: DraftItem): Food[] {
  return item.match ? [item.match, ...item.candidates] : item.candidates;
}

export function chosenFood(item: DraftItem, choice: Choice): Food | null {
  if (choice.kind === "estimate") return null;
  return foodOptions(item).find((food) => food.id === choice.foodId) ?? null;
}

/** Wartości na 100 g dla wyboru: z produktu albo ze szacunku modelu. */
export function per100For(item: DraftItem, choice: Choice): Per100 {
  return chosenFood(item, choice)?.per_100 ?? item.estimate_per_100;
}

/** Podgląd wartości porcji dla składnika w obecnym stanie. */
export function itemValues(item: DraftItem, state: ItemState): Per100 {
  return portionOf(per100For(item, state.choice), state.grams);
}

/** Suma zaznaczonych składników do podglądu. */
export function draftTotals(draft: MealDraft, states: ItemState[]): MacroTotals {
  return sumValues(
    draft.items
      .map((item, i) => ({ item, state: states[i] }))
      .filter(({ state }) => state.include && state.grams > 0)
      .map(({ item, state }) => ({ values: itemValues(item, state) })),
  );
}

/**
 * Wpisy do kolejki zapisów: składnik z produktem idzie jako zwykły wpis, składnik bez
 * produktu z szacunkiem modelu (serwer oznaczy wartości jako `estimated`).
 */
export function draftEntries(
  draft: MealDraft,
  states: ItemState[],
  day: string,
  slot: MealSlot,
  now: Date,
  newId: () => string,
): DiaryPutInput[] {
  const inputs: DiaryPutInput[] = [];
  draft.items.forEach((item, index) => {
    const state = states[index];
    if (!state.include || !(state.grams > 0)) return;
    const food = chosenFood(item, state.choice);
    const entry: DiaryEntry = {
      id: newId(),
      date: day,
      meal_slot: slot,
      food_id: food?.id ?? null,
      food_name: food?.name ?? item.name,
      amount: state.grams,
      unit: food?.unit ?? "g",
      values: itemValues(item, state),
      macro_source: food ? food.macro_source : "estimated",
      source: draft.source,
      ai_run_id: draft.ai_run_id,
      // Kolejne milisekundy: wpisy zachowują w dzienniku kolejność ze szkicu.
      created_at: new Date(now.getTime() + inputs.length).toISOString(),
    };
    inputs.push(
      food
        ? { entry }
        : {
            entry,
            estimate: {
              name: item.name,
              per_100: item.estimate_per_100,
              micros_per_100: item.estimate_micros,
            },
          },
    );
  });
  return inputs;
}
