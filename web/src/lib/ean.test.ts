import { describe, expect, it } from "vitest";
import { isValidEan } from "./ean";

describe("isValidEan", () => {
  it("przyjmuje poprawne kody", () => {
    for (const code of ["5900000000015", "4006381333931", "96385074", "036000291452"]) {
      expect(isValidEan(code), code).toBe(true);
    }
  });

  it("odrzuca błędną cyfrę kontrolną, złą długość i znaki inne niż cyfry", () => {
    for (const code of ["5900000000016", "123", "59000000000a5", ""]) {
      expect(isValidEan(code), code).toBe(false);
    }
  });
});
