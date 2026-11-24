import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import type { DiaryEntry, Food, MealSlot } from "../../lib/api";
import { MEAL_SLOTS, dayLabel, defaultSlot, portionOf, toIsoDay } from "../../lib/diary";
import { formatDecimal, INVALID, parseDecimal } from "../../lib/number";
import { type DiaryPutInput, mutationKeys } from "../../lib/offline";
import { amountOf, portionsOf, stepPortions } from "../../lib/portions";
import { formatGrams, formatKcal } from "./macros";

const MAX_AMOUNT = 5000; // ta sama granica co na serwerze
const QUICK_AMOUNTS = [50, 100, 150, 200];

export interface Added {
  amount: number;
  slot: MealSlot;
}

/** Skąd wpis trafił do dziennika (kolumna `source` na serwerze). */
export type EntrySource = "scan" | "search";

/** Ilość i posiłek, a potem zapis do dziennika (działa także bez sieci). */
export function AddToDay({
  food,
  day,
  source,
  initialAmount,
  initialSlot,
  onAdded,
}: {
  food: Food;
  day: string;
  source: EntrySource;
  /** Np. ilość z ostatniego razu, gdy produkt wybrano z listy „Ostatnie". */
  initialAmount?: number;
  /** Posiłek, przy którym stuknięto „Dodaj". Bez niego: według godziny. */
  initialSlot?: MealSlot;
  onAdded: (added: Added) => void;
}) {
  const serving = food.serving_g != null && food.serving_g > 0 ? food.serving_g : null;
  const startAmount = initialAmount ?? serving ?? 100;
  const [amountText, setAmountText] = useState(formatDecimal(startAmount));
  // Liczba porcji (np. kromek) obok gramów; do dziennika trafiają gramy.
  const [portionsText, setPortionsText] = useState(
    serving == null ? "" : formatDecimal(portionsOf(startAmount, serving)),
  );
  // Posiłek z przycisku „Dodaj" albo według godziny („Ostatnie" podpowiada ilość, nie porę).
  const [slot, setSlot] = useState<MealSlot>(
    () => initialSlot ?? defaultSlot(new Date().getHours()),
  );
  const put = useMutation<DiaryEntry, Error, DiaryPutInput>({ mutationKey: mutationKeys.diaryPut });

  const parsed = parseDecimal(amountText);
  const amount =
    typeof parsed === "number" && parsed > 0 && parsed <= MAX_AMOUNT ? parsed : null;
  const preview = amount == null ? null : portionOf(food.per_100, amount);
  const quick = [...new Set([initialAmount, food.serving_g, ...QUICK_AMOUNTS])].filter(
    (value): value is number => value != null && value > 0,
  );

  function setGrams(text: string) {
    setAmountText(text);
    if (serving == null) return;
    const value = parseDecimal(text);
    setPortionsText(
      typeof value === "number" && value > 0 ? formatDecimal(portionsOf(value, serving)) : "",
    );
  }

  function setPortions(text: string) {
    setPortionsText(text);
    const value = parseDecimal(text);
    if (serving != null && typeof value === "number" && value > 0) {
      setAmountText(formatDecimal(amountOf(value, serving)));
    }
  }

  function step(delta: 1 | -1) {
    if (serving == null) return;
    const current = parseDecimal(portionsText);
    const next = stepPortions(typeof current === "number" ? current : null, delta);
    setPortionsText(formatDecimal(next));
    setAmountText(formatDecimal(amountOf(next, serving)));
  }

  function add() {
    if (amount == null) return;
    put.mutate({
      entry: {
        id: crypto.randomUUID(),
        date: day,
        meal_slot: slot,
        food_id: food.id,
        food_name: food.name,
        amount,
        unit: food.unit,
        values: portionOf(food.per_100, amount),
        source,
        created_at: new Date().toISOString(),
      },
    });
    onAdded({ amount, slot });
  }

  return (
    <div className="add">
      <h3>Dodaj do dnia · {dayLabel(day, toIsoDay(new Date()))}</h3>
      <div className="row">
        <label>
          Ilość ({food.unit})
          <input
            inputMode="decimal"
            value={amountText}
            aria-invalid={amount == null}
            onChange={(e) => setGrams(e.target.value)}
            onFocus={(e) => e.target.select()}
          />
        </label>
        <label>
          Posiłek
          <select value={slot} onChange={(e) => setSlot(e.target.value as MealSlot)}>
            {MEAL_SLOTS.map((s) => (
              <option key={s.id} value={s.id}>
                {s.label}
              </option>
            ))}
          </select>
        </label>
      </div>
      {serving != null && (
        <div className="portions">
          <span>
            Porcje <small>po {formatDecimal(serving)} {food.unit}</small>
          </span>
          <button type="button" aria-label="Jedna porcja mniej" onClick={() => step(-1)}>
            −
          </button>
          <input
            inputMode="decimal"
            aria-label="Liczba porcji"
            value={portionsText}
            onChange={(e) => setPortions(e.target.value)}
            onFocus={(e) => e.target.select()}
          />
          <button type="button" aria-label="Jedna porcja więcej" onClick={() => step(1)}>
            +
          </button>
        </div>
      )}
      <div className="chips">
        {quick.map((value) => (
          <button
            key={value}
            type="button"
            className={value === amount ? "active" : ""}
            onClick={() => setGrams(formatDecimal(value))}
          >
            {value === food.serving_g ? "porcja " : ""}
            {formatDecimal(value)} {food.unit}
          </button>
        ))}
      </div>
      {parsed === INVALID || (parsed != null && amount == null) ? (
        <p className="error">
          Podaj ilość większą od zera, najwyżej {MAX_AMOUNT} {food.unit}.
        </p>
      ) : (
        preview && (
          <p className="muted">
            {preview.kcal == null ? "brak danych o kaloriach" : `${formatKcal(preview.kcal)} kcal`}
            {" · "}B {formatGrams(preview.protein_g)} · T {formatGrams(preview.fat_g)} · W{" "}
            {formatGrams(preview.carbs_g)}
          </p>
        )
      )}
      <button type="button" className="primary" disabled={amount == null} onClick={add}>
        Dodaj do dnia
      </button>
    </div>
  );
}
