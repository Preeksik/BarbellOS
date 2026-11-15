import { describe, expect, it } from "vitest";
import { INVALID, formatDecimal, parseDecimal } from "./number";

describe("parseDecimal", () => {
  it("przyjmuje przecinek i kropkę", () => {
    expect(parseDecimal("3,5")).toBe(3.5);
    expect(parseDecimal("3.5")).toBe(3.5);
    expect(parseDecimal(" 244 ")).toBe(244);
    expect(parseDecimal("0")).toBe(0);
  });

  it("puste pole to brak danych, a nie zero", () => {
    expect(parseDecimal("")).toBeNull();
    expect(parseDecimal("   ")).toBeNull();
  });

  it("pomija znak mniejszości z etykiety", () => {
    expect(parseDecimal("<0,01")).toBe(0.01);
  });

  it("odrzuca tekst, liczby ujemne i podwójne separatory", () => {
    for (const text of ["abc", "-5", "1,2,3", "12g", ","]) {
      expect(parseDecimal(text), text).toBe(INVALID);
    }
  });
});

describe("formatDecimal", () => {
  it("zaokrągla do dwóch miejsc i używa przecinka", () => {
    expect(formatDecimal(20.9)).toBe("20,9");
    expect(formatDecimal(2.6000001)).toBe("2,6");
    expect(formatDecimal(0.186)).toBe("0,19");
    expect(formatDecimal(21)).toBe("21");
  });

  it("brak danych to puste pole", () => {
    expect(formatDecimal(null)).toBe("");
    expect(formatDecimal(undefined)).toBe("");
  });
});
