import { describe, expect, it } from "vitest";
import type { DiaryEntry, Meal, Per100 } from "./api";
import { itemsFromEntries, mealEntries } from "./meals";

const NONE: Per100 = {
  kcal: null,
  protein_g: null,
  fat_g: null,
  sat_fat_g: null,
  carbs_g: null,
  sugars_g: null,
  fiber_g: null,
  salt_g: null,
};

const MEAL: Meal = {
  id: "m1",
  name: "Śniadanie standard",
  items: [
    { food_id: 1, food_name: "Owsianka", amount: 300, unit: "g", per_100: { ...NONE, kcal: 100 } },
    { food_id: 2, food_name: "Mleko", amount: 250, unit: "ml", per_100: { ...NONE, kcal: 46 } },
  ],
  totals: { ...NONE, kcal: 415 } as Meal["totals"],
};

describe("mealEntries", () => {
  it("tworzy osobny wpis na każdy produkt, z własnym identyfikatorem", () => {
    let n = 0;
    const now = new Date("2026-11-17T07:30:00Z");
    const entries = mealEntries(MEAL, "2026-11-17", "breakfast", now, () => `e${++n}`);

    expect(entries.map((e) => e.id)).toEqual(["e1", "e2"]);
    expect(entries.map((e) => [e.food_name, e.amount, e.unit])).toEqual([
      ["Owsianka", 300, "g"],
      ["Mleko", 250, "ml"],
    ]);
    expect(entries.every((e) => e.source === "meal" && e.meal_slot === "breakfast")).toBe(true);
    expect(entries[0].values.kcal).toBe(300);
    expect(entries[1].values.kcal).toBeCloseTo(115);
    expect(entries[0].values.fiber_g).toBeNull(); // brak danych zostaje brakiem
    // Kolejność w dzienniku jak w zestawie.
    expect(entries[0].created_at < entries[1].created_at).toBe(true);
  });
});

describe("itemsFromEntries", () => {
  it("pomija wpisy bez produktu", () => {
    const entry = (food_id: number | null, amount: number) =>
      ({ food_id, amount }) as unknown as DiaryEntry;
    expect(itemsFromEntries([entry(1, 300), entry(null, 120), entry(2, 50)])).toEqual([
      { food_id: 1, amount: 300 },
      { food_id: 2, amount: 50 },
    ]);
  });
});
