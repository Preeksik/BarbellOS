import type { MacroKey } from "../../lib/api";

/** Kolejność i nazwy jak na polskiej etykiecie. `sub` oznacza wiersz „w tym…". */
export const MACRO_ROWS: { key: MacroKey; label: string; unit: string; sub?: boolean }[] = [
  { key: "kcal", label: "Energia", unit: "kcal" },
  { key: "fat_g", label: "Tłuszcz", unit: "g" },
  { key: "sat_fat_g", label: "w tym nasycone", unit: "g", sub: true },
  { key: "carbs_g", label: "Węglowodany", unit: "g" },
  { key: "sugars_g", label: "w tym cukry", unit: "g", sub: true },
  { key: "fiber_g", label: "Błonnik", unit: "g" },
  { key: "protein_g", label: "Białko", unit: "g" },
  { key: "salt_g", label: "Sól", unit: "g" },
];

export function formatNumber(value: number): string {
  return value.toLocaleString("pl-PL", { maximumFractionDigits: 2 });
}
