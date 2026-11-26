import { describe, expect, it } from "vitest";
import type { TrainingEntry, TrainingExercise } from "./api";
import {
  dayCodeLabel,
  entryFromTexts,
  entryTexts,
  fmt,
  kgPlaceholder,
  ladderText,
  rangeText,
  thirdHintText,
  longDay,
  platesText,
  prescription,
  repsPlaceholder,
  rpeText,
  shortDay,
  toggledDone,
  toggledOk,
} from "./training";

const EMPTY: TrainingEntry = { kg: null, reps: null, rpe: null, done: false, ok: null };

function exercise(patch: Partial<TrainingExercise>): TrainingExercise {
  return {
    index: 0,
    name: "Przysiad",
    lift: "S",
    kind: "sets",
    tier: "main",
    sets: 4,
    reps: "4",
    percent_tm: 78,
    rpe: "7",
    weight_hint: null,
    attempt: null,
    cue: null,
    load: 130,
    plates: [25, 25, 5],
    entry: EMPTY,
    e1rm: null,
    last: null,
    ...patch,
  };
}

describe("tekst zaleceń", () => {
  it("formatuje liczby, RPE i dni po polsku", () => {
    expect(fmt(92.5)).toBe("92,5");
    expect(fmt(null)).toBe("–");
    expect(rpeText("8.5-9")).toBe("8,5–9");
    expect(shortDay("2026-11-02")).toBe("Pon 2.11");
    expect(longDay("2026-12-29")).toBe("wtorek 29.12.2026");
    expect(dayCodeLabel("OPT")).toBe("opcja");
    expect(dayCodeLabel("D3")).toBe("D3");
  });

  it("opisuje serie, single, akcesoria i podejścia", () => {
    expect(prescription(exercise({}))).toBe("4 × 4 · 78% TM · RPE 7");
    expect(prescription(exercise({ kind: "single", rpe: "8.5" }))).toBe(
      "1 × 1 · single do RPE 8,5",
    );
    expect(
      prescription(
        exercise({ kind: "acc", tier: "acc", sets: 3, reps: "10/str.", rpe: "8", weight_hint: "22.5" }),
      ),
    ).toBe("3 × 10/str. · RPE 8 · ok. 22,5 kg");
    expect(prescription(exercise({ kind: "acc", rpe: null, weight_hint: "+10" }))).toBe(
      "4 × 4 · obciążenie +10 kg",
    );
    expect(prescription(exercise({ kind: "att", attempt: 2 }))).toBe("2. podejście");
  });

  it("podpowiada wartości w polach", () => {
    expect(repsPlaceholder(exercise({}))).toBe("4");
    expect(repsPlaceholder(exercise({ kind: "acc", reps: "8-12" }))).toBe("8-12");
    expect(repsPlaceholder(exercise({ kind: "acc", reps: "10 min" }))).toBe("10");
    expect(kgPlaceholder(exercise({}))).toBe("130");
    expect(kgPlaceholder(exercise({ load: null, weight_hint: "17.5" }))).toBe("17,5");
    expect(platesText([25, 25, 2.5])).toBe("25+25+2,5 /str.");
    expect(platesText([])).toBe("pusta sztanga");
    expect(platesText(null)).toBeNull();
  });
});

describe("wpis z formularza", () => {
  it("czyta liczby z przecinkiem i odrzuca błędne", () => {
    const entry = entryFromTexts({ kg: "92,5", reps: "5", rpe: "8,5" }, EMPTY);
    expect(entry).toEqual({ ...EMPTY, kg: 92.5, reps: 5, rpe: 8.5 });
    expect(entryFromTexts({ kg: "abc", reps: "", rpe: "" }, EMPTY)).toBeNull();
    expect(entryFromTexts({ kg: "", reps: "", rpe: "11" }, EMPTY)).toBeNull();
    expect(entryFromTexts({ kg: "", reps: "", rpe: "" }, { ...EMPTY, done: true })).toEqual({
      ...EMPTY,
      done: true,
    });
    expect(entryTexts({ ...EMPTY, kg: 92.5 })).toEqual({ kg: "92,5", reps: "", rpe: "" });
  });

  it("odhaczenie serii wpisuje ciężar z planu, gdy pole jest puste", () => {
    expect(toggledDone(EMPTY, exercise({}))).toEqual({ ...EMPTY, done: true, kg: 130 });
    expect(toggledDone({ ...EMPTY, kg: 125 }, exercise({}))).toEqual({
      ...EMPTY,
      done: true,
      kg: 125,
    });
    expect(toggledDone(EMPTY, exercise({ kind: "single" }))).toEqual({ ...EMPTY, done: true });
    expect(toggledDone({ ...EMPTY, done: true, kg: 130 }, exercise({}))).toEqual({
      ...EMPTY,
      kg: 130,
    });
  });

  it("ocena podejścia przełącza się drugim stuknięciem", () => {
    expect(toggledOk(EMPTY, "y").ok).toBe("y");
    expect(toggledOk({ ...EMPTY, ok: "y" }, "y").ok).toBeNull();
    expect(toggledOk({ ...EMPTY, ok: "y" }, "n").ok).toBe("n");
  });
});

describe("arkusz podejść", () => {
  it("podpowiada trzecie podejście jak stary plan", () => {
    const hint = (kind: "failed" | "rules" | "need_rpe" | "limit" | "next", kg = 0, rpe = 0) => ({
      kind,
      kg,
      rpe,
    });
    expect(thirdHintText(hint("next", 180, 8), "S")).toEqual({
      text: "3. podejście: 180 kg (drugie na RPE 8).",
      strong: "180 kg",
    });
    expect(thirdHintText(hint("rules"), "B").text).toBe(
      "3. podejście wybierasz po drugim: RPE ≤ 7,5 → +5 kg, RPE 8 → +5 kg, RPE 9 → +2,5 kg.",
    );
    expect(thirdHintText(hint("rules"), "D").text).toContain("+10 kg, RPE 8 → +7,5 kg");
    expect(thirdHintText(hint("limit", 125), "B").text).toBe(
      "3. podejście: 125 kg było na granicy. +2,5 kg tylko przy pewnej technice.",
    );
    expect(thirdHintText(hint("failed"), "S").text).toContain("powtórz ciężar drugiego");
    expect(thirdHintText(hint("need_rpe"), "S").text).toContain("wpisz RPE drugiego");
  });

  it("formatuje rozgrzewkę i przedział", () => {
    expect(ladderText([[20, 8], [62.5, 5]])).toBe("20×8 · 62,5×5");
    expect(rangeText([172.5, 177.5])).toBe("172,5–177,5");
  });
});
