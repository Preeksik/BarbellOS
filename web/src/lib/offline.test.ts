import { describe, expect, it } from "vitest";
import { GC_TIME_MS, mutationKeys, queryClient } from "./offline";

const MAX_TIMER_MS = 2 ** 31 - 1; // największe opóźnienie, jakie przyjmuje setTimeout

describe("kolejka zapisów offline", () => {
  it("czas trzymania danych mieści się w liczniku przeglądarki", () => {
    // Większa wartość przepełnia licznik: dane znikają natychmiast zamiast po czasie.
    expect(GC_TIME_MS).toBeLessThanOrEqual(MAX_TIMER_MS);
    const defaults = queryClient.getDefaultOptions();
    expect(defaults.queries?.gcTime).toBeLessThanOrEqual(MAX_TIMER_MS);
    expect(defaults.mutations?.gcTime).toBeLessThanOrEqual(MAX_TIMER_MS);
  });

  it("każdy zapis z rejestru ma funkcję znaną po restarcie aplikacji", () => {
    for (const key of Object.values(mutationKeys)) {
      expect(queryClient.getMutationDefaults(key).mutationFn, key.join("/")).toBeTypeOf("function");
    }
  });
});
