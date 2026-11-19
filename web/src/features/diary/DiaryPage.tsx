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
  type Plan,
  type ProfileResponse,
  type Targets,
  api,
} from "../../lib/api";
import {
  MACRO_KEYS,
  MEAL_SLOTS,
  dayLabel,
  missingCounts,
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
  PROFILE_QUERY_KEY,
  type TargetsPutInput,
  diaryQueryKey,
  dismissDiaryErrors,
  mutationKeys,
  targetsQueryKey,
} from "../../lib/offline";
import {
  GOAL_ROWS,
  KIND_HINT,
  missingMacroGoals,
  progress,
  progressText,
} from "../../lib/targets";
import { formatGrams, formatKcal } from "../diet/macros";
import { WeekView } from "./WeekView";

const MAX_AMOUNT = 5000; // ta sama granica co na serwerze

/**
 * Dieta: dzień z sumą i celami, a pod nią wszystkie posiłki. Każdy ma przycisk „Dodaj"
 * (decyzja z 19.11.2026: bez osobnej zakładki „Dodaj"). Wpis stuknięty: zmiana ilości, usunięcie.
 */
export function DiaryPage({
  day,
  onDayChange,
  onAdd,
  onOpenProfile,
}: {
  day: string;
  onDayChange: (day: string) => void;
  onAdd: (slot: MealSlot) => void;
  onOpenProfile: () => void;
}) {
  const today = toIsoDay(new Date());
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingGoals, setEditingGoals] = useState(false);
  const [savingSlot, setSavingSlot] = useState<MealSlot | null>(null);
  const [view, setView] = useState<"day" | "week">("day");
  const diary = useQuery({
    queryKey: diaryQueryKey(day),
    queryFn: () => api.get<DiaryDay>(`/api/diary/${day}`),
  });
  const targets = useQuery({
    queryKey: targetsQueryKey(day),
    queryFn: () => api.get<Targets>(`/api/targets/${day}`),
  });
  // Plan z profilu: źródło celów, gdy białko, tłuszcz albo węglowodany nie mają celu.
  const profile = useQuery({
    queryKey: PROFILE_QUERY_KEY,
    queryFn: () => api.get<ProfileResponse>("/api/profile"),
  });
  const plan = profile.data?.plan ?? null;
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

  const applyPlan = useMutation<Targets, Error, TargetsPutInput>({
    mutationKey: mutationKeys.targetsPut,
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
      <fieldset className="segmented viewswitch">
        <legend className="visually-hidden">Widok</legend>
        {(
          [
            ["day", "Dzień"],
            ["week", "Tydzień (7 dni)"],
          ] as const
        ).map(([id, label]) => (
          <label key={id} className={view === id ? "active" : ""}>
            <input type="radio" name="view" checked={view === id} onChange={() => setView(id)} />
            {label}
          </label>
        ))}
      </fieldset>

      {rejected.length > 0 && (
        <section className="card">
          <p className="error">
            Serwer odrzucił {rejected.length === 1 ? "zmianę" : `zmiany (${rejected.length})`}:{" "}
            {rejected[0]} Dieta pokazuje stan z serwera.
          </p>
          <button type="button" onClick={dismissDiaryErrors}>
            Rozumiem
          </button>
        </section>
      )}

      {view === "week" ? (
        <WeekView day={day} targets={targets.data ?? null} />
      ) : diary.data ? (
        <>
          {editingGoals ? (
            <GoalsForm
              day={day}
              today={today}
              current={targets.data ?? null}
              plan={plan}
              onDone={() => setEditingGoals(false)}
            />
          ) : (
            <Totals
              day={diary.data}
              targets={targets.data ?? null}
              plan={plan}
              onApplyPlan={() => plan && applyPlan.mutate({ dateFrom: day, goals: plan.goals })}
              onOpenProfile={onOpenProfile}
              onEditGoals={() => setEditingGoals(true)}
            />
          )}
          {MEAL_SLOTS.map((slot) => {
            const slotTotals = diary.data.by_slot[slot.id];
            const slotEntries = diary.data.entries.filter((entry) => entry.meal_slot === slot.id);
            const addButton = (
              <button type="button" className="addbtn" onClick={() => onAdd(slot.id)}>
                <span aria-hidden="true">+</span> Dodaj
                <span className="visually-hidden"> do: {slot.label}</span>
              </button>
            );
            if (!slotTotals || slotEntries.length === 0) {
              // Pusty posiłek: jedna linijka z nazwą i przyciskiem.
              return (
                <section className="card slot empty" key={slot.id}>
                  <div className="slothead">
                    <h2>{slot.label}</h2>
                    {addButton}
                  </div>
                </section>
              );
            }
            return (
            <section className="card slot" key={slot.id}>
              <div className="slothead">
                <h2>{slot.label}</h2>
                <span>
                  {formatKcal(slotTotals.kcal)} <small>kcal</small>
                </span>
              </div>
              <MacroLine totals={slotTotals} />
              <ul className="entries">
                {slotEntries.map((entry) => (
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
                            {entry.macro_source === "estimated" && (
                              <span className="estimated" title="Wartości oszacowane przez AI">
                                {" "}
                                ≈ szacunek AI
                              </span>
                            )}
                            {waiting.has(entry.id) && <em> · czeka na wysłanie</em>}
                          </span>
                          <span className="amount">
                            {formatDecimal(entry.amount)} {entry.unit}
                          </span>
                          <span className="kcal">
                            {entry.values.kcal == null ? "–" : formatKcal(entry.values.kcal)}{" "}
                            <small>kcal</small>
                          </span>
                        </button>
                      )}
                    </li>
                  ))}
              </ul>
              {savingSlot === slot.id ? (
                <SaveMealForm
                  defaultName={slot.label}
                  entries={slotEntries}
                  onDone={() => setSavingSlot(null)}
                />
              ) : (
                <div className="slotactions">
                  {addButton}
                  <button type="button" className="link" onClick={() => setSavingSlot(slot.id)}>
                    Zapisz jako posiłek
                  </button>
                </div>
              )}
            </section>
            );
          })}
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
    </>
  );
}

/** B, W, T posiłku z kropkami w kolorach talerzy, jak paski na górze. */
function MacroLine({ totals }: { totals: DiaryDay["totals"] }) {
  return (
    <p className="macroline">
      {PLATE_KEYS.map((key) => (
        <span key={key} className={key}>
          {MAIN_ROWS.find((row) => row.key === key)!.letter}{" "}
          <strong>{formatGrams(totals[key])}</strong>
        </span>
      ))}
    </p>
  );
}

function Totals({
  day,
  targets,
  plan,
  onApplyPlan,
  onOpenProfile,
  onEditGoals,
}: {
  day: DiaryDay;
  targets: Targets | null;
  plan: Plan | null;
  onApplyPlan: () => void;
  onOpenProfile: () => void;
  onEditGoals: () => void;
}) {
  const t = day.totals;
  const missing = missingCounts(day.entries);
  const total = day.entries.length;
  const kcalGoal = targets?.goals.kcal ?? null;
  const kcal = kcalGoal != null ? progress(t.kcal, kcalGoal, "target") : null;
  // B, W, T z celem: grube paski w kolorach talerzy. Reszta celów (błonnik, sól…) drobniej.
  const plateGoals = PLATE_KEYS.flatMap((key) => {
    const row = GOAL_ROWS.find((r) => r.key === key)!;
    return targets?.goals[key] != null ? [row] : [];
  });
  const otherGoals = GOAL_ROWS.filter(
    ({ key }) => key !== "kcal" && !PLATE_KEYS.includes(key) && targets?.goals[key] != null,
  );
  // Wartości bez celu: główne (B, W, T) większe, pozostałe drobno.
  const mainWithout = MAIN_ROWS.filter(({ key }) => targets?.goals[key] == null);
  const minorWithout = MINOR_ROWS.filter(({ key }) => targets?.goals[key] == null);
  const partial = MACRO_KEYS.some((key) => key !== "kcal" && missing[key] > 0 && missing[key] < total);
  return (
    <section className="totals" aria-label="Suma dnia">
      {kcal && kcalGoal != null ? (
        <>
          {/* Duża liczba to zjedzone kcal (decyzja z 19.11.2026: „zostało" myliło na pierwszy rzut oka). */}
          <p className="hero">
            {formatKcal(t.kcal)}
            <span className="of"> / {formatKcal(kcalGoal)}</span>
          </p>
          <p className={kcal.state === "over" ? "hero-sub over" : "hero-sub"}>
            kcal zjedzone.{" "}
            {kcal.state === "over"
              ? `${formatKcal(-kcal.left)} ponad cel.`
              : `Zostało ${formatKcal(kcal.left)}.`}
          </p>
          <div
            className="bar kcalbar"
            role="progressbar"
            aria-label="Kalorie"
            aria-valuemin={0}
            aria-valuemax={kcalGoal}
            aria-valuenow={Math.round(t.kcal)}
          >
            <div style={{ width: `${kcal.fill * 100}%` }} />
          </div>
        </>
      ) : (
        <>
          <p className="hero">{formatKcal(t.kcal)}</p>
          <p className="hero-sub">kcal zjedzone. Kalorie nie mają celu.</p>
        </>
      )}
      {plateGoals.length > 0 && (
        <ul className="goals plates">
          {plateGoals.map(({ key, label, unit, kind }) => (
            <GoalBar
              key={key}
              plate={key}
              label={label}
              unit={unit}
              kind={kind}
              value={t[key]}
              goal={targets!.goals[key]!}
              missing={missing[key]}
              total={total}
            />
          ))}
        </ul>
      )}
      {otherGoals.length > 0 && (
        <ul className="goals compact">
          {otherGoals.map(({ key, label, unit, kind }) => (
            <GoalBar
              key={key}
              compact
              label={label}
              unit={unit}
              kind={kind}
              value={t[key]}
              goal={targets!.goals[key]!}
              missing={missing[key]}
              total={total}
            />
          ))}
        </ul>
      )}
      {mainWithout.length > 0 && (
        <dl className="macros">
          {mainWithout.map(({ key, short }) => (
            <Macro key={key} label={short} value={t[key]} missing={missing[key]} total={total} />
          ))}
        </dl>
      )}
      {minorWithout.length > 0 && (
        <dl className="macros minor">
          {minorWithout.map(({ key, short }) => (
            <Macro key={key} label={short} value={t[key]} missing={missing[key]} total={total} />
          ))}
        </dl>
      )}
      {partial && (
        <p className="muted footnote">
          * część wpisów nie ma tej wartości (brak na etykiecie albo w szacunku): suma jest
          zaniżona.
        </p>
      )}
      {missingMacroGoals(targets?.goals ?? null) && (
        <div className="notice">
          {plan ? (
            <>
              <p>
                Białko, tłuszcz i węglowodany nie mają celu, więc nie widać „ile na ile". Twój
                plan z profilu: {formatKcal(plan.kcal)} kcal · B {formatGrams(plan.goals.protein_g)} ·
                T {formatGrams(plan.goals.fat_g)} · W {formatGrams(plan.goals.carbs_g)}.
              </p>
              <button type="button" className="primary" onClick={onApplyPlan}>
                Ustaw cele z planu
              </button>
            </>
          ) : (
            <>
              <p>
                Białko, tłuszcz i węglowodany nie mają celu. Wypełnij profil, a aplikacja je
                policzy.
              </p>
              <button type="button" onClick={onOpenProfile}>
                Przejdź do profilu
              </button>
            </>
          )}
        </div>
      )}
      <button type="button" className="link" onClick={onEditGoals}>
        {targets?.date_from ? "Zmień cele" : "Ustaw cele dzienne"}
      </button>
    </section>
  );
}

// Kolejność jak talerze na sztandze: białko (czerwony), węglowodany (niebieski), tłuszcz (żółty).
const PLATE_KEYS: MacroKey[] = ["protein_g", "carbs_g", "fat_g"];

// Wartości pokazywane bez paska, gdy nie mają celu.
const MAIN_ROWS: { key: MacroKey; short: string; letter: string }[] = [
  { key: "protein_g", short: "Białko", letter: "B" },
  { key: "carbs_g", short: "Węglowodany", letter: "W" },
  { key: "fat_g", short: "Tłuszcz", letter: "T" },
];
const MINOR_ROWS: { key: MacroKey; short: string }[] = [
  { key: "sat_fat_g", short: "nasycone" },
  { key: "sugars_g", short: "cukry" },
  { key: "fiber_g", short: "błonnik" },
  { key: "salt_g", short: "sól" },
];

function GoalBar({
  plate,
  compact = false,
  label,
  unit,
  kind,
  value,
  goal,
  missing,
  total,
}: {
  /** B, W albo T: pasek w kolorze talerza (styles.css, `.goal.plate`). */
  plate?: MacroKey;
  /** Bez podpisu pod paskiem; stan „ponad limit" pokazuje kolor wartości. */
  compact?: boolean;
  label: string;
  unit: string;
  kind: GoalKind;
  value: number;
  goal: number;
  missing: number;
  total: number;
}) {
  const p = progress(value, goal, kind);
  const shown = (x: number) =>
    unit === "kcal" ? formatKcal(x) : x.toLocaleString("pl-PL", { maximumFractionDigits: 1 });
  return (
    <li className={plate ? `goal plate ${plate} ${p.state}` : `goal ${p.state}`}>
      <div className="goalhead">
        <span>{label}</span>
        <span>
          {total > 0 && missing === total ? "brak danych" : shown(value)}
          {missing > 0 && missing < total && "*"}{" "}
          <span className="of">
            / {shown(goal)} {unit}
          </span>
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
      {compact ? (
        <span className="visually-hidden">{progressText(p, kind, unit)}</span>
      ) : (
        <span className="muted">{progressText(p, kind, unit)}</span>
      )}
    </li>
  );
}

/** Cele obowiązują od oglądanego dnia do następnej zmiany. Dni wcześniejsze się nie zmieniają. */
function GoalsForm({
  day,
  today,
  current,
  plan,
  onDone,
}: {
  day: string;
  today: string;
  current: Targets | null;
  plan: Plan | null;
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
      {plan && (
        <button
          type="button"
          onClick={() =>
            setTexts(
              Object.fromEntries(
                GOAL_ROWS.map(({ key }) => [key, formatDecimal(plan.goals[key])]),
              ) as Record<MacroKey, string>,
            )
          }
        >
          Wypełnij z planu ({formatKcal(plan.kcal)} kcal)
        </button>
      )}
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

/** Wartość dnia: „–", gdy żaden wpis jej nie ma; z gwiazdką, gdy nie mają jej niektóre. */
function Macro({
  label,
  value,
  missing,
  total,
}: {
  label: string;
  value: number;
  missing: number;
  total: number;
}) {
  return (
    <div>
      <dt>{label}</dt>
      <dd title={missing > 0 ? `Bez danych: ${missing} z ${total} wpisów` : undefined}>
        {total > 0 && missing === total ? "brak danych" : formatGrams(value)}
        {missing > 0 && missing < total && "*"}
      </dd>
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
