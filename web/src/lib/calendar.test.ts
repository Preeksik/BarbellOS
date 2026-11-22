import { describe, expect, it } from "vitest";
import { monthGrid, monthLabel, monthOf, shiftMonth } from "./calendar";

describe("monthGrid", () => {
  it("zaczyna tydzień od poniedziałku i dopełnia pustymi polami", () => {
    // 1 listopada 2026 to niedziela: sześć pustych pól przed nim.
    const weeks = monthGrid("2026-11");
    expect(weeks[0]).toEqual([null, null, null, null, null, null, "2026-11-01"]);
    expect(weeks[1][0]).toBe("2026-11-02");
    expect(weeks.at(-1)).toEqual(["2026-11-30", null, null, null, null, null, null]);
    expect(weeks.every((week) => week.length === 7)).toBe(true);
    expect(weeks.flat().filter(Boolean)).toHaveLength(30);
  });

  it("zna luty w roku przestępnym", () => {
    expect(monthGrid("2028-02").flat().filter(Boolean).at(-1)).toBe("2028-02-29");
  });
});

describe("miesiące", () => {
  it("przesuwa przez granicę roku", () => {
    expect(shiftMonth("2026-01", -1)).toBe("2025-12");
    expect(shiftMonth("2026-12", 1)).toBe("2027-01");
    expect(shiftMonth("2026-11", 0)).toBe("2026-11");
  });

  it("bierze miesiąc z dnia i podpisuje go po polsku", () => {
    expect(monthOf("2026-11-22")).toBe("2026-11");
    expect(monthLabel("2026-11")).toBe("listopad 2026");
  });
});
