import { describe, expect, it } from "vitest";
import type { DiaryEntry, Per100 } from "./api";
import {
  dayLabel,
  defaultSlot,
  emptyDay,
  portionOf,
  shiftDay,
  toIsoDay,
  withAmount,
  withEntry,
  withoutEntry,
} from "./diary";

const PER_100: Per100 = {
  kcal: 97,
  protein_g: 11,
  fat_g: 5,
  sat_fat_g: 3.5,
  carbs_g: 2,
  sugars_g: 2,
  fiber_g: null,
  salt_g: 0.7,
};

function entry(overrides: Partial<DiaryEntry> = {}): DiaryEntry {
  return {
    id: "a",
    date: "2026-11-16",
    meal_slot: "lunch",
    food_id: 1,
    food_name: "Serek wiejski",
    amount: 200,
    unit: "g",
    values: portionOf(PER_100, 200),
    source: "scan",
    created_at: "2026-11-16T12:00:00Z",
    ...overrides,
  };
}

describe("daty", () => {
  it("dzień pochodzi z zegara telefonu, nie z UTC", () => {
    // 00:30 czasu lokalnego: w UTC (dla stref na wschód od Greenwich) to jeszcze wczoraj.
    expect(toIsoDay(new Date(2026, 10, 16, 0, 30))).toBe("2026-11-16");
    expect(toIsoDay(new Date(2026, 0, 5, 23, 59))).toBe("2026-01-05");
  });

  it("przesuwa dzień przez granicę miesiąca, roku i zmianę czasu", () => {
    expect(shiftDay("2026-11-30", 1)).toBe("2026-12-01");
    expect(shiftDay("2027-01-01", -1)).toBe("2026-12-31");
    expect(shiftDay("2026-10-25", 1)).toBe("2026-10-26"); // doba 25-godzinna
    expect(shiftDay("2026-03-29", 1)).toBe("2026-03-30"); // doba 23-godzinna
    expect(shiftDay("2028-02-28", 1)).toBe("2028-02-29");
  });

  it("nazywa dni sąsiadujące z dzisiejszym", () => {
    expect(dayLabel("2026-11-16", "2026-11-16")).toBe("Dziś");
    expect(dayLabel("2026-11-15", "2026-11-16")).toBe("Wczoraj");
    expect(dayLabel("2026-11-17", "2026-11-16")).toBe("Jutro");
    expect(dayLabel("2026-11-10", "2026-11-16")).toMatch(/10/);
  });
});

describe("posiłek podpowiadany według godziny", () => {
  it.each([
    [6, "breakfast"],
    [10, "second_breakfast"],
    [13, "lunch"],
    [16, "snack"],
    [18, "dinner"],
    [23, "dinner"],
  ] as const)("godzina %i -> %s", (hour, slot) => {
    expect(defaultSlot(hour)).toBe(slot);
  });
});

describe("podgląd wartości", () => {
  it("liczy porcję i zostawia brak danych brakiem", () => {
    const values = portionOf(PER_100, 150);
    expect(values.kcal).toBeCloseTo(145.5);
    expect(values.protein_g).toBeCloseTo(16.5);
    expect(values.fiber_g).toBeNull();
  });

  it("zmiana ilości skaluje zamrożone wartości", () => {
    const changed = withAmount(entry(), 100);
    expect(changed.amount).toBe(100);
    expect(changed.values.kcal).toBeCloseTo(97);
    expect(changed.values.fiber_g).toBeNull();
  });
});

describe("dzień z podglądem zmian", () => {
  it("pusty dzień ma zerowe sumy i brak posiłków", () => {
    const day = emptyDay("2026-11-16");
    expect(day.entries).toEqual([]);
    expect(day.totals.kcal).toBe(0);
    expect(day.by_slot).toEqual({});
  });

  it("dodaje wpis i liczy sumy dnia oraz posiłku", () => {
    let day = withEntry(emptyDay("2026-11-16"), entry());
    day = withEntry(
      day,
      entry({ id: "b", meal_slot: "breakfast", amount: 100, values: portionOf(PER_100, 100) }),
    );
    expect(day.entries.map((e) => e.id)).toEqual(["b", "a"]); // śniadanie przed obiadem
    expect(day.totals.kcal).toBeCloseTo(291);
    expect(day.totals.fiber_g).toBe(0); // brak danych w sumie liczy się jak zero
    expect(day.by_slot.lunch?.kcal).toBeCloseTo(194);
    expect(day.by_slot.breakfast?.kcal).toBeCloseTo(97);
    expect(day.by_slot.dinner).toBeUndefined();
  });

  it("ten sam identyfikator podmienia wpis zamiast go dublować", () => {
    const day = withEntry(withEntry(emptyDay("2026-11-16"), entry()), withAmount(entry(), 50));
    expect(day.entries).toHaveLength(1);
    expect(day.totals.kcal).toBeCloseTo(48.5);
  });

  it("usuwa wpis; usunięcie nieistniejącego nic nie zmienia", () => {
    const day = withEntry(emptyDay("2026-11-16"), entry());
    expect(withoutEntry(day, "a").entries).toEqual([]);
    expect(withoutEntry(day, "a").by_slot).toEqual({});
    expect(withoutEntry(day, "nie-ma").totals.kcal).toBeCloseTo(194);
  });
});
