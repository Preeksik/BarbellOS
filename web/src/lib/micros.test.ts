import { describe, expect, it } from "vitest";
import type { MicroWeek } from "./api";
import { coverageState, formatAmount, trustText } from "./micros";

function micro(extra: Partial<MicroWeek>): MicroWeek {
  return {
    nutrient_id: "magnesium",
    name_pl: "Magnez",
    unit: "mg",
    group: "mineral",
    rda: 375,
    avg_amount: 200,
    percent_rda: 53,
    share_trusted: 0.7,
    share_estimated: 0.15,
    share_missing: 0.15,
    supplement_amount: 0,
    ...extra,
  };
}

describe("pokrycie normy", () => {
  it("opisuje pochodzenie danych", () => {
    expect(trustText(micro({}))).toBe("dokładne 70% · przybliżone 15% · brak 15%");
    expect(trustText(micro({ share_trusted: 1, share_estimated: 0, share_missing: 0 }))).toBe(
      "dokładne 100%",
    );
  });

  it("przy braku danych nie straszy niedoborem", () => {
    expect(coverageState(micro({ percent_rda: 20, share_missing: 0.6 }))).toBe("low-data");
    expect(coverageState(micro({ percent_rda: 20 }))).toBe("low");
    expect(coverageState(micro({ percent_rda: 90 }))).toBe("ok");
    // Suplement pokrywa normę: brak danych o jedzeniu nie zmienia oceny.
    expect(
      coverageState(micro({ percent_rda: 110, share_missing: 0.6, supplement_amount: 400 })),
    ).toBe("ok");
    expect(
      coverageState(micro({ percent_rda: 40, share_missing: 0.6, supplement_amount: 100 })),
    ).toBe("low-data");
    // Sód ma górną granicę, a nie normę do osiągnięcia.
    expect(coverageState(micro({ nutrient_id: "sodium", percent_rda: 20 }))).toBe("ok");
  });

  it("formatuje ilości z sensowną dokładnością", () => {
    expect(formatAmount(358)).toBe("358");
    expect(formatAmount(27.44)).toBe("27,4");
    expect(formatAmount(0.256)).toBe("0,26");
  });
});
