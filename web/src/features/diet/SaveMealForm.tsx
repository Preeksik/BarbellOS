import { useMutation } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import type { DiaryEntry, Meal } from "../../lib/api";
import { scaleValues, sumValues } from "../../lib/diary";
import { formatDecimal } from "../../lib/number";
import { type MealPutInput, mutationKeys } from "../../lib/offline";
import { formatKcal } from "./macros";

/**
 * Zapis wpisów jako posiłku do dodawania jednym stuknięciem, z wyborem produktów
 * (22.11.2026: np. spaghetti bez zjedzonych przy okazji żelków). Używany w Diecie przy
 * posiłku i po dodaniu szacunku AI. Posiłek wskazuje wpisy, a produkty bierze z nich
 * serwer, więc działa także dla szacunków AI, których produktu telefon jeszcze nie zna.
 */
export function SaveMealForm({
  defaultName,
  entries,
  onDone,
}: {
  defaultName: string;
  entries: DiaryEntry[];
  /** Nazwa zapisanego posiłku albo null po „Anuluj". */
  onDone: (savedName: string | null) => void;
}) {
  const [name, setName] = useState(defaultName);
  const [chosen, setChosen] = useState<Set<string>>(() => new Set(entries.map((e) => e.id)));
  const save = useMutation<void, Error, MealPutInput>({ mutationKey: mutationKeys.mealPut });
  const selected = entries.filter((entry) => chosen.has(entry.id));

  function toggle(id: string) {
    const next = new Set(chosen);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setChosen(next);
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!name.trim() || selected.length === 0) return;
    // Podgląd na liście tylko, gdy telefon zna wszystkie produkty; inaczej pojawi się po
    // odpowiedzi serwera (szacunek AI dostaje produkt dopiero na serwerze).
    const known = selected.every((entry) => entry.food_id != null);
    const meal: Meal = {
      id: crypto.randomUUID(),
      name: name.trim(),
      items: known
        ? selected.map((entry) => ({
            food_id: entry.food_id!,
            food_name: entry.food_name,
            amount: entry.amount,
            unit: entry.unit,
            per_100: scaleValues(entry.values, 100 / entry.amount),
          }))
        : [],
      totals: sumValues(selected),
    };
    save.mutate({ meal, entryIds: selected.map((entry) => entry.id) });
    onDone(meal.name);
  }

  return (
    <form className="savemeal" onSubmit={submit}>
      <label>
        Nazwa posiłku
        <input value={name} maxLength={120} onChange={(e) => setName(e.target.value)} />
      </label>
      {entries.length > 1 && (
        <fieldset className="pick">
          <legend>Co wchodzi do posiłku</legend>
          {entries.map((entry) => (
            <label key={entry.id} className={chosen.has(entry.id) ? "pickrow on" : "pickrow"}>
              <input
                type="checkbox"
                checked={chosen.has(entry.id)}
                onChange={() => toggle(entry.id)}
              />
              <span className="name">
                {entry.food_name}
                <span className="muted">
                  {" "}
                  {formatDecimal(entry.amount)} {entry.unit}
                </span>
              </span>
              <span className="muted">
                {entry.values.kcal == null ? "–" : formatKcal(entry.values.kcal)} kcal
              </span>
            </label>
          ))}
        </fieldset>
      )}
      <div className="row">
        <button type="submit" className="primary" disabled={!name.trim() || selected.length === 0}>
          Zapisz ({selected.length})
        </button>
        <button type="button" onClick={() => onDone(null)}>
          Anuluj
        </button>
      </div>
    </form>
  );
}
