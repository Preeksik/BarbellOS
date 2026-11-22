import { describe, expect, it } from "vitest";
import type { DiaryEntry, Meal, Per100 } from "./api";
import { copiedEntries, mealEntries } from "./meals";

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

describe("copiedEntries", () => {
  it("kopiuje wpisy na inny dzień i posiłek, z odnośnikiem do oryginału", () => {
    const original: DiaryEntry = {
      id: "stary",
      date: "2026-11-21",
      meal_slot: "lunch",
      food_id: 7,
      food_name: "Spaghetti z leczo",
      amount: 400,
      unit: "g",
      values: { ...NONE, kcal: 600 },
      macro_source: "estimated",
      source: "photo",
      ai_run_id: 12,
      created_at: "2026-11-21T12:00:00.000Z",
    };
    const ids = ["k1", "k2"];
    const copies = copiedEntries(
      { date: "2026-11-21", meal_slot: "lunch", kcal: 600, entries: [original, original] },
      "2026-11-22",
      "dinner",
      new Date("2026-11-22T18:00:00.000Z"),
      () => ids.shift()!,
    );
    expect(copies.map((c) => c.copyOf)).toEqual(["stary", "stary"]);
    expect(copies[0].entry).toMatchObject({
      id: "k1",
      date: "2026-11-22",
      meal_slot: "dinner",
      food_id: 7,
      amount: 400,
      values: { kcal: 600 },
      macro_source: "estimated",
      source: "copy",
      ai_run_id: null,
    });
    // Kolejność z oryginalnego posiłku zostaje.
    expect(copies[1].entry.created_at > copies[0].entry.created_at).toBe(true);
  });
});
