import { useMutation, useMutationState, useQuery } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import {
  type DiaryDay,
  type DiaryEntry,
  type GoalKind,
  type MacroKey,
  type Meal,
  type MealSlot,
  type Per100,
  type Targets,
  api,
} from "../../lib/api";
import {
  MEAL_SLOTS,
  dayLabel,
  scaleValues,
  shiftDay,
  sumValues,
  toIsoDay,
  withAmount,
} from "../../lib/diary";
import { itemsFromEntries } from "../../lib/meals";
import { INVALID, formatDecimal, parseDecimal } from "../../lib/number";
import {
  DIARY_MUTATIONS,
  type DiaryDeleteInput,
  type DiaryPutInput,
  type MealPutInput,
  type TargetsPutInput,
  diaryQueryKey,
  dismissDiaryErrors,
  mutationKeys,
  targetsQueryKey,
} from "../../lib/offline";
import { GOAL_ROWS, KIND_HINT, progress, progressText } from "../../lib/targets";
import { formatGrams, formatKcal } from "../diet/macros";

const MAX_AMOUNT = 5000; // ta sama granica co na serwerze

/** Dziennik dnia: suma z celami, posiłki, zmiana ilości i usuwanie wpisów. */
export function DiaryPage({
  day,
  onDayChange,
  onAdd,
}: {
  day: string;
  onDayChange: (day: string) => void;
  onAdd: () => void;
}) {
  const today = toIsoDay(new Date());
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingGoals, setEditingGoals] = useState(false);
  const [savingSlot, setSavingSlot] = useState<MealSlot | null>(null);
  const diary = useQuery({
    queryKey: diaryQueryKey(day),
    queryFn: () => api.get<DiaryDay>(`/api/diary/${day}`),
  });
  const targets = useQuery({
    queryKey: targetsQueryKey(day),
    queryFn: () => api.get<Targets>(`/api/targets/${day}`),
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
    setEditingGoals(false);
    setSavingSlot(null);
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
          {editingGoals ? (
            <GoalsForm
              day={day}
              today={today}
              current={targets.data ?? null}
              onDone={() => setEditingGoals(false)}
            />
          ) : (
            <Totals
              day={diary.data}
              targets={targets.data ?? null}
              onEditGoals={() => setEditingGoals(true)}
            />
          )}
          {MEAL_SLOTS.filter((slot) => diary.data.by_slot[slot.id]).map((slot) => (
            <section className="card" key={slot.id}>
              <div className="slothead">
                <h2>{slot.label}</h2>
                <span>{formatKcal(diary.data.by_slot[slot.id]!.kcal)} kcal</span>
              </div>
              {savingSlot === slot.id ? (
                <SaveMealForm
                  defaultName={slot.label}
                  entries={diary.data.entries.filter((entry) => entry.meal_slot === slot.id)}
                  onDone={() => setSavingSlot(null)}
                />
              ) : (
                <button type="button" className="link" onClick={() => setSavingSlot(slot.id)}>
                  Zapisz jako posiłek
                </button>
              )}
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

      <button type="button" className="primary wide" onClick={onAdd}>
        Dodaj produkt
      </button>
    </>
  );
}

function Totals({
  day,
  targets,
  onEditGoals,
}: {
  day: DiaryDay;
  targets: Targets | null;
  onEditGoals: () => void;
}) {
  const t = day.totals;
  const withGoals = GOAL_ROWS.filter(({ key }) => targets?.goals[key] != null);
  const withoutGoals = MINOR_ROWS.filter(({ key }) => targets?.goals[key] == null);
  return (
    <section className="card totals">
      <p className="kcal">
        <strong>{formatKcal(t.kcal)}</strong> kcal
        {targets?.goals.kcal != null && (
          <span className="muted"> / {formatKcal(targets.goals.kcal)}</span>
        )}
      </p>
      {withGoals.length > 0 ? (
        <ul className="goals">
          {withGoals.map(({ key, label, unit, kind }) => (
            <GoalBar
              key={key}
              label={label}
              unit={unit}
              kind={kind}
              value={t[key]}
              goal={targets!.goals[key]!}
            />
          ))}
        </ul>
      ) : (
        <dl className="macros">
          <Macro label="Białko" value={t.protein_g} />
          <Macro label="Tłuszcz" value={t.fat_g} />
          <Macro label="Węglowodany" value={t.carbs_g} />
        </dl>
      )}
      {withoutGoals.length > 0 && (
        <dl className="macros minor">
          {withoutGoals.map(({ key, short }) => (
            <Macro key={key} label={short} value={t[key]} />
          ))}
        </dl>
      )}
      <button type="button" className="link" onClick={onEditGoals}>
        {targets?.date_from ? "Zmień cele" : "Ustaw cele dzienne"}
      </button>
    </section>
  );
}

// Wartości pokazywane drobno, gdy nie mają celu.
const MINOR_ROWS: { key: MacroKey; short: string }[] = [
  { key: "sat_fat_g", short: "nasycone" },
  { key: "sugars_g", short: "cukry" },
  { key: "fiber_g", short: "błonnik" },
  { key: "salt_g", short: "sól" },
];

function GoalBar({
  label,
  unit,
  kind,
  value,
  goal,
}: {
  label: string;
  unit: string;
  kind: GoalKind;
  value: number;
  goal: number;
}) {
  const p = progress(value, goal, kind);
  const shown = (x: number) =>
    unit === "kcal" ? formatKcal(x) : x.toLocaleString("pl-PL", { maximumFractionDigits: 1 });
  return (
    <li className={`goal ${p.state}`}>
      <div className="goalhead">
        <span>{label}</span>
        <span>
          {shown(value)} / {shown(goal)} {unit}
        </span>
      </div>
      <div
        className="bar"
        role="progressbar"
        aria-label={label}
        aria-valuemin={0}
        aria-valuemax={goal}
        aria-valuenow={Math.round(value)}
      >
        <div style={{ width: `${p.fill * 100}%` }} />
      </div>
      <span className="muted">{progressText(p, kind, unit)}</span>
    </li>
  );
}

/** Cele obowiązują od oglądanego dnia do następnej zmiany. Dni wcześniejsze się nie zmieniają. */
function GoalsForm({
  day,
  today,
  current,
  onDone,
}: {
  day: string;
  today: string;
  current: Targets | null;
  onDone: () => void;
}) {
  const [texts, setTexts] = useState<Record<MacroKey, string>>(
    () =>
      Object.fromEntries(
        GOAL_ROWS.map(({ key }) => [key, formatDecimal(current?.goals[key])]),
      ) as Record<MacroKey, string>,
  );
  const [problem, setProblem] = useState<string | null>(null);
  const save = useMutation<Targets, Error, TargetsPutInput>({ mutationKey: mutationKeys.targetsPut });

  function submit(event: FormEvent) {
    event.preventDefault();
    const goals = {} as Per100;
    for (const { key, label } of GOAL_ROWS) {
      const parsed = parseDecimal(texts[key]);
      if (parsed === INVALID || parsed === 0) {
        return setProblem(`„${label}": wpisz liczbę większą od zera albo zostaw puste pole.`);
      }
      goals[key] = parsed;
    }
    setProblem(null);
    save.mutate({ dateFrom: day, goals });
    onDone();
  }

  return (
    <form className="card" onSubmit={submit}>
      <h2>Cele dzienne</h2>
      <p className="muted">
        Obowiązują od {day === today ? "dziś" : dayLabel(day, today)} do następnej zmiany. Dni
        wcześniejsze zachowują poprzednie cele. Puste pole: bez celu.
      </p>
      <div className="fields">
        {GOAL_ROWS.map(({ key, label, unit, kind }) => (
          <label key={key} className="field">
            <span>
              {label} <span className="muted">({KIND_HINT[kind]})</span>
            </span>
            <input
              inputMode="decimal"
              autoComplete="off"
              placeholder="brak"
              value={texts[key]}
              onChange={(e) => setTexts({ ...texts, [key]: e.target.value })}
            />
            <span className="muted">{unit}</span>
          </label>
        ))}
      </div>
      {problem && <p className="error">{problem}</p>}
      <div className="row">
        <button type="button" onClick={onDone}>
          Anuluj
        </button>
        <button type="submit" className="primary">
          Zapisz cele
        </button>
      </div>
    </form>
  );
}

/** Zapisuje produkty z posiłku jako zestaw do dodawania jednym stuknięciem. */
function SaveMealForm({
  defaultName,
  entries,
  onDone,
}: {
  defaultName: string;
  entries: DiaryEntry[];
  onDone: () => void;
}) {
  const [name, setName] = useState(defaultName);
  const save = useMutation<void, Error, MealPutInput>({ mutationKey: mutationKeys.mealPut });
  const items = itemsFromEntries(entries);

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!name.trim() || items.length === 0) return;
    const meal: Meal = {
      id: crypto.randomUUID(),
      name: name.trim(),
      // Podgląd do czasu odpowiedzi serwera: wartości na 100 g odtworzone z wpisu.
      items: entries
        .filter((entry) => entry.food_id != null)
        .map((entry) => ({
          food_id: entry.food_id!,
          food_name: entry.food_name,
          amount: entry.amount,
          unit: entry.unit,
          per_100: scaleValues(entry.values, 100 / entry.amount),
        })),
      totals: sumValues(entries.filter((entry) => entry.food_id != null)),
    };
    save.mutate({ meal });
    onDone();
  }

  return (
    <form className="savemeal" onSubmit={submit}>
      <label>
        Nazwa posiłku ({items.length} {items.length === 1 ? "produkt" : "produkty"})
        <input value={name} maxLength={120} onChange={(e) => setName(e.target.value)} />
      </label>
      <div className="row">
        <button type="submit" className="primary" disabled={!name.trim() || items.length === 0}>
          Zapisz
        </button>
        <button type="button" onClick={onDone}>
          Anuluj
        </button>
      </div>
    </form>
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
