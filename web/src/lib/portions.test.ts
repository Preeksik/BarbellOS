import { describe, expect, it } from "vitest";
import { amountOf, portionsOf, stepPortions } from "./portions";

describe("porcje", () => {
  it("przelicza porcje na gramy i z powrotem", () => {
    expect(amountOf(6, 23)).toBe(138);
    expect(portionsOf(138, 23)).toBe(6);
    expect(amountOf(1.5, 23)).toBe(34.5);
    expect(portionsOf(50, 23)).toBe(2.17);
    expect(amountOf(3, 33.3)).toBe(99.9); // bez ogona 99.89999…
  });

  it("przyciski idą do całych porcji i nie schodzą poniżej jednej", () => {
    expect(stepPortions(1, 1)).toBe(2);
    expect(stepPortions(6, -1)).toBe(5);
    expect(stepPortions(1, -1)).toBe(1);
    expect(stepPortions(2.17, 1)).toBe(3);
    expect(stepPortions(2.17, -1)).toBe(2);
    expect(stepPortions(0.5, -1)).toBe(1);
    expect(stepPortions(null, 1)).toBe(1);
    expect(stepPortions(5.999, 1)).toBe(7);
  });
});
