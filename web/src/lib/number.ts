/** Liczby wpisywane po polsku: przecinek dziesiętny, puste pole jako „brak danych". */

export const INVALID = "invalid" as const;

/**
 * "3,5" -> 3.5, "" -> null (brak danych), "abc" -> INVALID.
 * Etykiety podają czasem „<0,01": znak mniejszości jest pomijany.
 */
export function parseDecimal(text: string): number | null | typeof INVALID {
  const cleaned = text.trim().replace(/^</, "").replace(/\s/g, "").replace(",", ".");
  if (cleaned === "") return null;
  if (!/^\d+(\.\d+)?$/.test(cleaned)) return INVALID;
  return Number(cleaned);
}

/** Wartość do pola formularza: najwyżej dwa miejsca po przecinku, bez zer na końcu. */
export function formatDecimal(value: number | null | undefined): string {
  if (value == null) return "";
  return String(Number(value.toFixed(2))).replace(".", ",");
}
