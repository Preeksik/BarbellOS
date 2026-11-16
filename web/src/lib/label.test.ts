import { afterEach, describe, expect, it, vi } from "vitest";
import { type LabelDraft, type MacroKey, type Per100, api } from "./api";
import { LABEL_MAX_EDGE, applyLabelDraft, fitWithin, labelKeys } from "./label";

const ORDER: MacroKey[] = [
  "kcal",
  "fat_g",
  "sat_fat_g",
  "carbs_g",
  "sugars_g",
  "fiber_g",
  "protein_g",
  "salt_g",
];

function draft(per_100: Partial<Per100>): LabelDraft {
  const empty = Object.fromEntries(ORDER.map((key) => [key, null])) as Per100;
  return {
    name: null,
    brand: null,
    serving_g: null,
    unit: "g",
    per_100: { ...empty, ...per_100 },
    warnings: [],
  };
}

function texts(values: Partial<Record<MacroKey, string>>): Record<MacroKey, string> {
  return { ...(Object.fromEntries(ORDER.map((key) => [key, ""])) as Record<MacroKey, string>), ...values };
}

describe("fitWithin", () => {
  it("zmniejsza zdjęcie z aparatu z zachowaniem proporcji", () => {
    expect(fitWithin(4032, 3024, 2000)).toEqual({ width: 2000, height: 1500 });
    expect(fitWithin(3024, 4032, 2000)).toEqual({ width: 1500, height: 2000 });
  });

  it("nie powiększa małych zdjęć", () => {
    expect(fitWithin(800, 600, LABEL_MAX_EDGE)).toEqual({ width: 800, height: 600 });
  });

  it("wąski pasek nie traci drugiego wymiaru", () => {
    expect(fitWithin(10000, 2, 2000)).toEqual({ width: 2000, height: 1 });
  });
});

describe("applyLabelDraft", () => {
  it("wpisuje odczytane wartości z przecinkiem", () => {
    const next = applyLabelDraft(texts({}), draft({ kcal: 97, sat_fat_g: 3.5, salt_g: 0.07 }));
    expect(next.kcal).toBe("97");
    expect(next.sat_fat_g).toBe("3,5");
    expect(next.salt_g).toBe("0,07");
  });

  it("zero z etykiety to zero, a nie puste pole", () => {
    expect(applyLabelDraft(texts({ sugars_g: "4" }), draft({ sugars_g: 0 })).sugars_g).toBe("0");
  });

  it("brak odczytu nie kasuje wpisanej wartości", () => {
    const before = texts({ fiber_g: "2,1", kcal: "100" });
    const next = applyLabelDraft(before, draft({ kcal: 97 }));
    expect(next.fiber_g).toBe("2,1");
    expect(next.kcal).toBe("97");
    expect(before.kcal).toBe("100"); // wejście zostaje nietknięte
  });
});

describe("labelKeys", () => {
  it("zwraca tylko odczytane pola, w kolejności formularza", () => {
    expect(labelKeys(draft({ salt_g: 0.7, kcal: 97, fiber_g: null, fat_g: 0 }), ORDER)).toEqual([
      "kcal",
      "fat_g",
      "salt_g",
    ]);
  });
});

describe("wysyłka pliku", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("zdjęcie idzie w treści żądania ze swoim typem, a nie jako JSON", async () => {
    const fetchMock = vi.fn(
      async (_path: string, _init?: RequestInit) =>
        new Response(JSON.stringify(draft({ kcal: 97 })), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);
    const photo = new Blob([new Uint8Array([0xff, 0xd8, 0xff])], { type: "image/jpeg" });

    const result = await api.post<LabelDraft>("/api/foods/label", photo);

    expect(result.per_100.kcal).toBe(97);
    const init = fetchMock.mock.calls[0][1];
    expect(init?.body).toBe(photo);
    expect(init?.headers).toEqual({ "Content-Type": "image/jpeg" });
  });

  it("zwykłe dane nadal idą jako JSON", async () => {
    const fetchMock = vi.fn(
      async (_path: string, _init?: RequestInit) => new Response("{}", { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await api.put("/api/foods/1", { name: "x" });

    const init = fetchMock.mock.calls[0][1];
    expect(init?.body).toBe('{"name":"x"}');
    expect(init?.headers).toEqual({ "Content-Type": "application/json" });
  });
});
