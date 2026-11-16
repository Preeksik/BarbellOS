import { useMutation, useMutationState, useQuery } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { type DiaryDay, type DiaryEntry, type MealSlot, api } from "../../lib/api";
import { MEAL_SLOTS, dayLabel, shiftDay, toIsoDay, withAmount } from "../../lib/diary";
import { formatDecimal, parseDecimal } from "../../lib/number";
import {
  DIARY_MUTATIONS,
  type DiaryDeleteInput,
  type DiaryPutInput,
  diaryQueryKey,
  dismissDiaryErrors,
  mutationKeys,
} from "../../lib/offline";
import { formatGrams, formatKcal } from "../diet/macros";

const MAX_AMOUNT = 5000; // ta sama granica co na serwerze

/** Dziennik dnia: suma, posiłki, zmiana ilości i usuwanie wpisów. */
export function DiaryPage({
  day,
  onDayChange,
  onScan,
}: {
  day: string;
  onDayChange: (day: string) => void;
  onScan: () => void;
}) {
  const today = toIsoDay(new Date());
  const [editingId, setEditingId] = useState<string | null>(null);
  const diary = useQuery({
    queryKey: diaryQueryKey(day),
    queryFn: () => api.get<DiaryDay>(`/api/diary/${day}`),
  });
  // Wpisy, których zapis jeszcze nie dotarł do serwera (np. dodane bez sieci).
  const waiting = new Set(
    useMutationState({
      filters: { mutationKey: mutationKeys.diaryPut, status: "pending" },
      select: (mutation) => (mutation.state.variables as DiaryPutInput).entry.id,
    }),
  );
  const rejected = useMutationState({
    filters: { mutationKey: DIARY_MUTATIONS, status: "error" },
    select: (mutation) => mutation.state.error?.message ?? "nieznany błąd",
  });

  function goTo(next: string) {
    setEditingId(null);
    onDayChange(next);
  }

  return (
    <>
      <nav className="daynav" aria-label="Dzień">
        <button type="button" aria-label="Poprzedni dzień" onClick={() => goTo(shiftDay(day, -1))}>
          ‹
        </button>
        <div>
          <strong>{dayLabel(day, today)}</strong>
          <span className="muted">{formatDate(day)}</span>
        </div>
        <button type="button" aria-label="Następny dzień" onClick={() => goTo(shiftDay(day, 1))}>
          ›
        </button>
      </nav>
      {day !== today && (
        <button type="button" className="wide" onClick={() => goTo(today)}>
          Wróć do dziś
        </button>
      )}

      {rejected.length > 0 && (
        <section className="card">
          <p className="error">
            Serwer odrzucił {rejected.length === 1 ? "zmianę" : `zmiany (${rejected.length})`}:{" "}
            {rejected[0]} Dziennik pokazuje stan z serwera.
          </p>
          <button type="button" onClick={dismissDiaryErrors}>
            Rozumiem
          </button>
        </section>
      )}

      {diary.data ? (
        <>
          <Totals day={diary.data} />
          {MEAL_SLOTS.filter((slot) => diary.data.by_slot[slot.id]).map((slot) => (
            <section className="card" key={slot.id}>
              <div className="slothead">
                <h2>{slot.label}</h2>
                <span>{formatKcal(diary.data.by_slot[slot.id]!.kcal)} kcal</span>
              </div>
              <ul className="entries">
                {diary.data.entries
                  .filter((entry) => entry.meal_slot === slot.id)
                  .map((entry) => (
                    <li key={entry.id}>
                      {editingId === entry.id ? (
                        <EntryEditor entry={entry} onDone={() => setEditingId(null)} />
                      ) : (
                        <button
                          type="button"
                          className="entry"
                          onClick={() => setEditingId(entry.id)}
                        >
                          <span className="name">
                            {entry.food_name}
                            {waiting.has(entry.id) && <em> · czeka na wysłanie</em>}
                          </span>
                          <span className="amount">
                            {formatDecimal(entry.amount)} {entry.unit}
                          </span>
                          <span className="kcal">
                            {entry.values.kcal == null ? "–" : formatKcal(entry.values.kcal)} kcal
                          </span>
                        </button>
                      )}
                    </li>
                  ))}
              </ul>
            </section>
          ))}
          {diary.data.entries.length === 0 && (
            <section className="card">
              <p className="muted">Nic jeszcze nie dodano.</p>
            </section>
          )}
        </>
      ) : (
        <section className="card">
          {diary.error ? (
            <p className="error">{diary.error.message}</p>
          ) : diary.fetchStatus === "paused" ? (
            <p className="muted">
              Brak połączenia, a tego dnia nie ma w pamięci telefonu. Możesz dodawać produkty:
              wyślą się po powrocie sieci.
            </p>
          ) : (
            <p className="muted">Wczytuję dziennik…</p>
          )}
        </section>
      )}

      <button type="button" className="primary wide" onClick={onScan}>
        Skanuj produkt
      </button>
    </>
  );
}

function Totals({ day }: { day: DiaryDay }) {
  const t = day.totals;
  return (
    <section className="card totals">
      <p className="kcal">
        <strong>{formatKcal(t.kcal)}</strong> kcal
      </p>
      <dl className="macros">
        <Macro label="Białko" value={t.protein_g} />
        <Macro label="Tłuszcz" value={t.fat_g} />
        <Macro label="Węglowodany" value={t.carbs_g} />
      </dl>
      <dl className="macros minor">
        <Macro label="nasycone" value={t.sat_fat_g} />
        <Macro label="cukry" value={t.sugars_g} />
        <Macro label="błonnik" value={t.fiber_g} />
        <Macro label="sól" value={t.salt_g} />
      </dl>
    </section>
  );
}

function Macro({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{formatGrams(value)}</dd>
    </div>
  );
}

function EntryEditor({ entry, onDone }: { entry: DiaryEntry; onDone: () => void }) {
  const [amountText, setAmountText] = useState(formatDecimal(entry.amount));
  const [slot, setSlot] = useState<MealSlot>(entry.meal_slot);
  const put = useMutation<DiaryEntry, Error, DiaryPutInput>({ mutationKey: mutationKeys.diaryPut });
  const remove = useMutation<void, Error, DiaryDeleteInput>({
    mutationKey: mutationKeys.diaryDelete,
  });

  const parsed = parseDecimal(amountText);
  const amount =
    typeof parsed === "number" && parsed > 0 && parsed <= MAX_AMOUNT ? parsed : null;

  function save(event: FormEvent) {
    event.preventDefault();
    if (amount == null) return;
    if (amount !== entry.amount || slot !== entry.meal_slot) {
      put.mutate({ entry: { ...withAmount(entry, amount), meal_slot: slot } });
    }
    onDone();
  }

  return (
    <form className="editor" onSubmit={save}>
      <strong>{entry.food_name}</strong>
      <div className="row">
        <label>
          Ilość ({entry.unit})
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
      {amount == null && (
        <p className="error">
          Podaj ilość większą od zera, najwyżej {MAX_AMOUNT} {entry.unit}.
        </p>
      )}
      <div className="row">
        <button type="submit" className="primary" disabled={amount == null}>
          Zapisz
        </button>
        <button
          type="button"
          className="danger"
          onClick={() => {
            remove.mutate({ id: entry.id, date: entry.date });
            onDone();
          }}
        >
          Usuń
        </button>
        <button type="button" onClick={onDone}>
          Anuluj
        </button>
      </div>
    </form>
  );
}

function formatDate(iso: string): string {
  const [year, month, day] = iso.split("-");
  return `${day}.${month}.${year}`;
}
