import { useMutation } from "@tanstack/react-query";
import { type FormEvent, useEffect, useState } from "react";
import type { Food, MacroKey } from "../../lib/api";
import { INVALID, formatDecimal, parseDecimal } from "../../lib/number";
import { type FoodUpdateInput, mutationKeys } from "../../lib/offline";
import { MACRO_ROWS } from "./macros";

type Texts = Record<MacroKey, string>;

// Składnik „w tym…" nie może być większy od składnika, którego jest częścią.
const SUBSETS: [MacroKey, MacroKey, string][] = [
  ["sat_fat_g", "fat_g", "Kwasy nasycone nie mogą przekraczać tłuszczu."],
  ["sugars_g", "carbs_g", "Cukry nie mogą przekraczać węglowodanów."],
];

/** Poprawianie produktu według etykiety. Puste pole oznacza brak danych, nie zero. */
export function FoodEditForm({
  food,
  barcode,
  onDone,
}: {
  food: Food;
  barcode: string;
  onDone: () => void;
}) {
  const [name, setName] = useState(food.name);
  const [brand, setBrand] = useState(food.brand ?? "");
  const [unit, setUnit] = useState<"g" | "ml">(food.unit);
  const [texts, setTexts] = useState<Texts>(
    () =>
      Object.fromEntries(MACRO_ROWS.map(({ key }) => [key, formatDecimal(food.per_100[key])])) as Texts,
  );
  const [problem, setProblem] = useState<string | null>(null);
  // Funkcja zapisu jest w rejestrze lib/offline.ts, więc zapis przetrwa brak sieci.
  const save = useMutation<Food, Error, FoodUpdateInput>({ mutationKey: mutationKeys.foodUpdate });

  // Bez sieci zapis czeka w kolejce: nie trzymamy użytkownika w formularzu.
  useEffect(() => {
    if (save.isPaused) onDone();
  }, [save.isPaused, onDone]);

  function submit(event: FormEvent) {
    event.preventDefault();
    const per_100 = {} as Food["per_100"];
    for (const { key, label } of MACRO_ROWS) {
      const parsed = parseDecimal(texts[key]);
      if (parsed === INVALID) return setProblem(`„${label}": wpisz liczbę albo zostaw puste pole.`);
      per_100[key] = parsed;
    }
    for (const [part, whole, message] of SUBSETS) {
      const a = per_100[part];
      const b = per_100[whole];
      if (a != null && b != null && a > b) return setProblem(message);
    }
    if (!name.trim()) return setProblem("Wpisz nazwę produktu.");
    setProblem(null);
    save.mutate(
      {
        id: food.id,
        barcode,
        body: { name: name.trim(), brand: brand.trim() || null, serving_g: food.serving_g, unit, per_100 },
      },
      { onSuccess: onDone },
    );
  }

  return (
    <form className="card" onSubmit={submit}>
      <h2>Popraw według etykiety</h2>
      <label>
        Nazwa
        <input value={name} onChange={(e) => setName(e.target.value)} />
      </label>
      <label>
        Marka
        <input value={brand} onChange={(e) => setBrand(e.target.value)} />
      </label>

      <fieldset className="segmented">
        <legend>Wartości na</legend>
        {(["g", "ml"] as const).map((option) => (
          <label key={option} className={unit === option ? "active" : ""}>
            <input
              type="radio"
              name="unit"
              checked={unit === option}
              onChange={() => setUnit(option)}
            />
            100 {option}
          </label>
        ))}
      </fieldset>

      <div className="fields">
        {MACRO_ROWS.map(({ key, label, unit: rowUnit, sub }) => (
          <label key={key} className={sub ? "field sub" : "field"}>
            <span>{label}</span>
            <input
              inputMode="decimal"
              autoComplete="off"
              placeholder="brak"
              value={texts[key]}
              onChange={(e) => setTexts({ ...texts, [key]: e.target.value })}
            />
            <span className="muted">{rowUnit}</span>
          </label>
        ))}
      </div>
      <p className="muted">Puste pole oznacza, że etykieta nie podaje tej wartości.</p>

      {(problem || save.error) && <p className="error">{problem ?? save.error?.message}</p>}
      <div className="row">
        <button type="button" onClick={onDone}>
          Anuluj
        </button>
        <button type="submit" className="primary" disabled={save.isPending}>
          Zapisz
        </button>
      </div>
    </form>
  );
}
