import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import type { DiaryEntry, Food, MealSlot } from "../../lib/api";
import { MEAL_SLOTS, dayLabel, defaultSlot, portionOf, toIsoDay } from "../../lib/diary";
import { formatDecimal, INVALID, parseDecimal } from "../../lib/number";
import { type DiaryPutInput, mutationKeys } from "../../lib/offline";
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
  onAdded,
}: {
  food: Food;
  day: string;
  source: EntrySource;
  /** Np. ilość z ostatniego razu, gdy produkt wybrano z listy „Ostatnie". */
  initialAmount?: number;
  onAdded: (added: Added) => void;
}) {
  const [amountText, setAmountText] = useState(
    formatDecimal(initialAmount ?? food.serving_g ?? 100),
  );
  // Posiłek według godziny: „Ostatnie" podpowiada ilość, a nie porę dnia.
  const [slot, setSlot] = useState<MealSlot>(() => defaultSlot(new Date().getHours()));
  const put = useMutation<DiaryEntry, Error, DiaryPutInput>({ mutationKey: mutationKeys.diaryPut });

  const parsed = parseDecimal(amountText);
  const amount =
    typeof parsed === "number" && parsed > 0 && parsed <= MAX_AMOUNT ? parsed : null;
  const preview = amount == null ? null : portionOf(food.per_100, amount);
  const quick = [...new Set([initialAmount, food.serving_g, ...QUICK_AMOUNTS])].filter(
    (value): value is number => value != null && value > 0,
  );

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
            onChange={(e) => setAmountText(e.target.value)}
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
      <div className="chips">
        {quick.map((value) => (
          <button
            key={value}
            type="button"
            className={value === amount ? "active" : ""}
            onClick={() => setAmountText(formatDecimal(value))}
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
