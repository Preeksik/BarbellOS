import { describe, expect, it } from "vitest";
import type { DraftItem, Food, MealDraft, Per100 } from "./api";
import { draftEntries, draftTotals, foodOptions, initialState, itemValues } from "./aiDraft";

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

function food(id: number, name: string, kcal: number, extra: Partial<Food> = {}): Food {
  return {
    id,
    barcode: null,
    name,
    brand: null,
    serving_g: null,
    unit: "g",
    origin: "user",
    macro_source: "user",
    source_updated_at: null,
    verified_at: null,
    per_100: { ...NONE, kcal, protein_g: 10 },
    micros: [],
    warnings: [],
    cached: true,
    favorite: false,
    ...extra,
  };
}

function item(name: string, grams: number, match: Food | null, candidates: Food[] = []): DraftItem {
  return {
    name,
    category: "other",
    grams,
    grams_low: grams * 0.8,
    grams_high: grams * 1.2,
    confidence: "medium",
    match,
    candidates,
    estimate_per_100: { ...NONE, kcal: 50, protein_g: 2, fat_g: 1, carbs_g: 8 },
    values: NONE,
  };
}

const OATS = food(1, "Płatki owsiane", 380);
const OATS_OTHER = food(2, "Płatki owsiane górskie", 370, { unit: "g", macro_source: "label" });
const DRAFT: MealDraft = {
  ai_run_id: 7,
  source: "photo",
  items: [item("płatki owsiane", 50, OATS, [OATS_OTHER]), item("mleko", 200, null)],
  notes: null,
  warnings: [],
};

describe("szkic posiłku", () => {
  it("startuje od propozycji serwera", () => {
    const states = initialState(DRAFT);
    expect(states[0]).toEqual({ include: true, grams: 50, choice: { kind: "food", foodId: 1 } });
    expect(states[1].choice).toEqual({ kind: "estimate" });
    expect(foodOptions(DRAFT.items[0]).map((f) => f.id)).toEqual([1, 2]);
  });

  it("przelicza podgląd po zmianie gramatury i wyboru", () => {
    const [oats, milk] = initialState(DRAFT);
    expect(itemValues(DRAFT.items[0], oats).kcal).toBe(190); // 380 × 0,5
    expect(itemValues(DRAFT.items[0], { ...oats, grams: 80 }).kcal).toBeCloseTo(304);
    const other = { ...oats, choice: { kind: "food", foodId: 2 } as const };
    expect(itemValues(DRAFT.items[0], other).kcal).toBe(185);
    expect(itemValues(DRAFT.items[1], milk).kcal).toBe(100); // szacunek: 50 × 2
    expect(itemValues(DRAFT.items[1], milk).salt_g).toBeNull(); // brak danych to brak
  });

  it("suma pomija odznaczone składniki", () => {
    const states = initialState(DRAFT);
    expect(draftTotals(DRAFT, states).kcal).toBe(290);
    states[1] = { ...states[1], include: false };
    expect(draftTotals(DRAFT, states).kcal).toBe(190);
  });

  it("zapisuje produkt jako zwykły wpis, a szacunek z wartościami na 100 g", () => {
    let n = 0;
    const inputs = draftEntries(
      DRAFT,
      initialState(DRAFT),
      "2026-11-17",
      "breakfast",
      new Date("2026-11-17T07:00:00Z"),
      () => `e${++n}`,
    );
    const [oats, milk] = inputs;
    expect(oats.entry).toMatchObject({
      id: "e1",
      food_id: 1,
      food_name: "Płatki owsiane",
      amount: 50,
      source: "photo",
      ai_run_id: 7,
      macro_source: "user",
    });
    expect(oats.estimate).toBeUndefined();
    expect(milk.entry).toMatchObject({
      food_id: null,
      food_name: "mleko",
      amount: 200,
      macro_source: "estimated",
    });
    expect(milk.estimate).toEqual({ name: "mleko", per_100: DRAFT.items[1].estimate_per_100 });
    expect(oats.entry.created_at < milk.entry.created_at).toBe(true);
  });

  it("pomija odznaczone i puste pozycje", () => {
    const states = initialState(DRAFT);
    states[0] = { ...states[0], include: false };
    states[1] = { ...states[1], grams: 0 };
    expect(draftEntries(DRAFT, states, "2026-11-17", "lunch", new Date(), () => "x")).toEqual([]);
  });
});
