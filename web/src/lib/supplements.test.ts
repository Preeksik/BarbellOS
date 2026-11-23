import { describe, expect, it } from "vitest";
import type { SupplementDay } from "./api";
import { likeYesterday, toggled, withTaken, yesterdayGain } from "./supplements";

const item = (id: string, taken = false) => ({
  id,
  name: id,
  dose: null,
  taken,
  streak: 0,
  last7: [false, false, false, false, false, false, false],
});

const DAY: SupplementDay = {
  date: "2026-11-23",
  supplements: [item("d3"), item("magnez", true), item("kreatyna")],
  taken_ids: ["magnez"],
  yesterday_ids: ["d3", "kreatyna"],
};

describe("suplementy", () => {
  it("stuknięcie dodaje albo usuwa, w kolejności listy", () => {
    expect(toggled(DAY, "kreatyna")).toEqual(["magnez", "kreatyna"]);
    expect(toggled(DAY, "magnez")).toEqual([]);
  });

  it("„To co wczoraj” dodaje wczorajsze i niczego nie odznacza", () => {
    expect(likeYesterday(DAY)).toEqual(["d3", "magnez", "kreatyna"]);
    expect(yesterdayGain(DAY)).toBe(2);
    expect(yesterdayGain(withTaken(DAY, ["d3", "magnez", "kreatyna"]))).toBe(0);
  });

  it("podgląd ustawia odhaczenia", () => {
    const next = withTaken(DAY, ["kreatyna", "d3"]);
    expect(next.taken_ids).toEqual(["d3", "kreatyna"]);
    expect(next.supplements.map((s) => s.taken)).toEqual([true, false, true]);
  });
});
