import { useMutation } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import type { SupplementItem } from "../../lib/api";
import { INVALID, formatDecimal, parseDecimal } from "../../lib/number";
import { type SupplementPutInput, mutationKeys } from "../../lib/offline";
import { useNutrients } from "../diet/FoodMicros";

interface Row {
  nutrient_id: string;
  amount: string;
  unit: string;
}

/** Jednostki do wyboru: mg i µg, a dla witaminy D także IU (przelicza serwer: 40 IU = 1 µg). */
function unitsFor(nutrientId: string): string[] {
  return nutrientId === "vit_d" ? ["IU", "µg", "mg"] : ["mg", "µg"];
}

/**
 * Dodanie albo zmiana suplementu (24.11.2026): nazwa, dawka tekstem i skład jednej dawki.
 * Składniki liczą się do pokrycia norm w widoku tygodnia w dniach, gdy suplement odhaczono.
 */
export function SupplementForm({
  current,
  onDone,
}: {
  /** Zmiana istniejącego; bez niego: nowy suplement. */
  current?: SupplementItem;
  onDone?: () => void;
}) {
  const nutrients = useNutrients();
  const [name, setName] = useState(current?.name ?? "");
  const [dose, setDose] = useState(current?.dose ?? "");
  const [rows, setRows] = useState<Row[]>(() =>
    (current?.micros ?? []).map((m) => ({
      nutrient_id: m.nutrient_id,
      amount: formatDecimal(m.amount),
      unit: nutrients.data?.find((n) => n.id === m.nutrient_id)?.unit ?? "mg",
    })),
  );
  const put = useMutation<void, Error, SupplementPutInput>({
    mutationKey: mutationKeys.supplementPut,
  });
  const known = nutrients.data ?? [];
  const parsed = rows.map((r) => parseDecimal(r.amount));
  const invalid = parsed.some((value) => value === INVALID || value == null || value <= 0);

  function update(index: number, change: Partial<Row>) {
    setRows(rows.map((row, i) => (i === index ? { ...row, ...change } : row)));
  }

  function addRow() {
    const free = known.find((n) => !rows.some((r) => r.nutrient_id === n.id));
    if (free) setRows([...rows, { nutrient_id: free.id, amount: "", unit: unitsFor(free.id)[0] }]);
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!name.trim() || invalid) return;
    put.mutate({
      id: current?.id ?? crypto.randomUUID(),
      name: name.trim(),
      dose: dose.trim() || null,
      micros: rows.map((r, i) => ({
        nutrient_id: r.nutrient_id,
        amount: parsed[i] as number,
        unit: r.unit,
      })),
    });
    if (!current) {
      setName("");
      setDose("");
      setRows([]);
    }
    onDone?.();
  }

  return (
    <form className="card suppform" onSubmit={submit}>
      <h2>{current ? `Zmień: ${current.name}` : "Dodaj suplement"}</h2>
      <div className="row">
        <label>
          Nazwa
          <input
            value={name}
            maxLength={80}
            placeholder="np. Kreatyna"
            onChange={(e) => setName(e.target.value)}
          />
        </label>
        <label className="dose">
          Dawka
          <input
            value={dose}
            maxLength={40}
            placeholder="np. 5 g"
            onChange={(e) => setDose(e.target.value)}
          />
        </label>
      </div>

      <fieldset className="suppmicros">
        <legend>Skład jednej dawki (z opakowania)</legend>
        {rows.length === 0 && (
          <p className="muted">
            Opcjonalnie: np. witamina D 2000 IU. Wtedy suplement liczy się do norm w widoku
            tygodnia.
          </p>
        )}
        {rows.map((row, index) => (
          <div key={index} className="micro-row">
            <select
              aria-label="Składnik"
              value={row.nutrient_id}
              onChange={(e) =>
                update(index, { nutrient_id: e.target.value, unit: unitsFor(e.target.value)[0] })
              }
            >
              {known.map((n) => (
                <option
                  key={n.id}
                  value={n.id}
                  disabled={n.id !== row.nutrient_id && rows.some((r) => r.nutrient_id === n.id)}
                >
                  {n.name_pl}
                </option>
              ))}
            </select>
            <input
              aria-label="Ilość"
              inputMode="decimal"
              value={row.amount}
              aria-invalid={parsed[index] === INVALID || (parsed[index] ?? 0) <= 0}
              onChange={(e) => update(index, { amount: e.target.value })}
            />
            <select
              aria-label="Jednostka"
              value={row.unit}
              onChange={(e) => update(index, { unit: e.target.value })}
            >
              {unitsFor(row.nutrient_id).map((unit) => (
                <option key={unit} value={unit}>
                  {unit}
                </option>
              ))}
            </select>
            <button
              type="button"
              className="forget"
              aria-label="Usuń składnik"
              onClick={() => setRows(rows.filter((_, i) => i !== index))}
            >
              ✕
            </button>
          </div>
        ))}
        {known.length > rows.length && (
          <button type="button" className="link" onClick={addRow}>
            + Dodaj składnik
          </button>
        )}
      </fieldset>

      <div className="row">
        <button type="submit" className={current ? "primary" : ""} disabled={!name.trim() || invalid}>
          {current ? "Zapisz zmiany" : "Dodaj do listy"}
        </button>
        {current && (
          <button type="button" onClick={onDone}>
            Anuluj
          </button>
        )}
      </div>
    </form>
  );
}
