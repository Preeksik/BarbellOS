import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type ChangeEvent, useEffect, useRef, useState } from "react";
import {
  type TrainingExercise,
  type TrainingImportResult,
  type TrainingSeason,
  type TrainingSession,
  type TrainingWeek,
  api,
} from "../../lib/api";
import { toIsoDay } from "../../lib/diary";
import { parseDecimal } from "../../lib/number";
import {
  type TrainingEntryInput,
  type TrainingSessionInput,
  mutationKeys,
  trainingSeasonKey,
  trainingWeekKey,
} from "../../lib/offline";
import {
  type EntryTexts,
  dayCodeLabel,
  dayMonth,
  daysWord,
  entryFromTexts,
  entryTexts,
  fmt,
  kgPlaceholder,
  longDay,
  platesText,
  prescription,
  repsPlaceholder,
  rpeText,
  shortDay,
  tierLabel,
  toggledDone,
  toggledOk,
} from "../../lib/training";
import { TechniqueFigure } from "./technique/TechniqueFigure";
import { moveFor } from "./technique/moves";

const LIFT_NAMES = { S: "przysiad", B: "ława", D: "martwy" } as const;
const LIFT_TITLES = { S: "Przysiad", B: "Ława", D: "Martwy ciąg" } as const;
const WRITE_DELAY_MS = 900; // zapis po pauzie w pisaniu, a od razu po wyjściu z pola

const fetchWeek = (index: number) => api.get<TrainingWeek>(`/api/training/week/${index}`);

/**
 * Trening (etap 4, 25.11.2026): plan AMP 2027 przeniesiony ze starego pliku HTML.
 * Oś sezonu, tydzień, dni i sesja z wpisami. Wszystkie liczby liczy serwer; wpisy idą
 * przez trwałą kolejkę offline, więc siłownia bez zasięgu niczego nie gubi.
 */
export function TrainingPage() {
  const today = toIsoDay(new Date());
  const queryClient = useQueryClient();
  const season = useQuery({
    queryKey: trainingSeasonKey(today),
    queryFn: () => api.get<TrainingSeason>(`/api/training/season?today=${today}`),
  });
  // Wybrany tydzień i dzień. Bez wyboru: to, co podpowiada serwer (kolejna sesja).
  const [picked, setPicked] = useState<{ week: number; day: number } | null>(null);
  const data = season.data;
  const position = picked ?? (data?.position ? { week: data.position.week, day: data.position.day } : null);
  const weekIndex = position?.week ?? 0;

  const week = useQuery({
    queryKey: trainingWeekKey(weekIndex),
    queryFn: () => fetchWeek(weekIndex),
    enabled: Boolean(data?.plan_name),
  });

  // Sąsiednie tygodnie trafiają do pamięci telefonu, żeby działały bez zasięgu.
  useEffect(() => {
    if (!data?.plan_name) return;
    for (const i of [weekIndex - 1, weekIndex + 1]) {
      if (i >= 0 && i < data.weeks.length) {
        void queryClient.prefetchQuery({ queryKey: trainingWeekKey(i), queryFn: () => fetchWeek(i) });
      }
    }
  }, [data, weekIndex, queryClient]);

  if (!data) {
    return (
      <section className="card">
        {season.error ? (
          <p className="error">{season.error.message}</p>
        ) : season.fetchStatus === "paused" ? (
          <p className="muted">Brak połączenia, a planu nie ma jeszcze w pamięci telefonu.</p>
        ) : (
          <p className="muted">Wczytuję plan…</p>
        )}
      </section>
    );
  }
  if (!data.plan_name || !position) return <PlanImport first />;

  const atSuggested = !picked || (data.position && picked.week === data.position.week && picked.day === data.position.day);
  const goWeek = (i: number) => setPicked({ week: i, day: 0 });

  return (
    <>
      <section className="season">
        <p className="headline">{data.headline}</p>
        {data.countdowns.length > 0 && (
          <p className="countdowns">
            {data.countdowns.map((c) => (
              <span key={c.label}>
                {c.days === 0 ? (
                  <strong>Dziś {c.label}</strong>
                ) : (
                  <>
                    <strong>{c.days}</strong> {c.label}
                  </>
                )}
              </span>
            ))}
          </p>
        )}
        <SeasonAxis season={data} selected={weekIndex} onPick={goWeek} />
      </section>

      {week.data ? (
        <WeekView
          week={week.data}
          dayIndex={Math.min(position.day, week.data.sessions.length - 1)}
          today={today}
          total={data.weeks.length}
          rest={Boolean(atSuggested && data.position?.rest)}
          showToday={!atSuggested}
          onWeek={goWeek}
          onDay={(day) => setPicked({ week: weekIndex, day })}
          onToday={() => setPicked(null)}
        />
      ) : (
        <section className="card">
          {week.error ? (
            <p className="error">{week.error.message}</p>
          ) : week.fetchStatus === "paused" ? (
            <p className="muted">Brak połączenia, a tego tygodnia nie ma w pamięci telefonu.</p>
          ) : (
            <p className="muted">Wczytuję tydzień…</p>
          )}
        </section>
      )}

      <PlanImport />
    </>
  );
}

/** Oś sezonu: każdy tydzień to krążek w kolorze intensywności, jak w starym pliku. */
function SeasonAxis({
  season,
  selected,
  onPick,
}: {
  season: TrainingSeason;
  selected: number;
  onPick: (index: number) => void;
}) {
  return (
    <div className="axis" role="group" aria-label="Tygodnie sezonu">
      <span className="sleeve" aria-hidden="true" />
      {season.weeks.map((w) => (
        <button
          key={w.key}
          type="button"
          className={[
            "plate",
            `p${String(w.plate ?? 10).replace(".", "")}`,
            w.index === selected ? "sel" : "",
            w.index === season.current_week ? "now" : "",
            w.done === w.total ? "full" : "",
          ].join(" ")}
          aria-label={`Tydzień ${w.n}, ${dayMonth(w.start)}–${dayMonth(w.end)}, ${w.block_name}${
            w.index === season.current_week ? ", bieżący" : ""
          }, zrobione ${w.done} z ${w.total}`}
          aria-pressed={w.index === selected}
          onClick={() => onPick(w.index)}
        >
          {w.label && <span className="plab">{w.label}</span>}
        </button>
      ))}
      <span className="sleeve" aria-hidden="true" />
    </div>
  );
}

function WeekView({
  week,
  dayIndex,
  today,
  total,
  rest,
  showToday,
  onWeek,
  onDay,
  onToday,
}: {
  week: TrainingWeek;
  dayIndex: number;
  today: string;
  total: number;
  rest: boolean;
  showToday: boolean;
  onWeek: (index: number) => void;
  onDay: (index: number) => void;
  onToday: () => void;
}) {
  const session = week.sessions[dayIndex];
  return (
    <>
      <div className="daynav weeknav">
        <button
          type="button"
          aria-label="Poprzedni tydzień"
          disabled={week.index === 0}
          onClick={() => onWeek(week.index - 1)}
        >
          ‹
        </button>
        <div>
          <strong>Tydzień {week.n}</strong>
          <span className="muted">
            {dayMonth(week.start)}–{dayMonth(week.end)}, {week.block_name}
            {week.repeat_of ? `, powtórka tygodnia ${week.repeat_of}` : ""}
          </span>
        </div>
        <button
          type="button"
          aria-label="Następny tydzień"
          disabled={week.index === total - 1}
          onClick={() => onWeek(week.index + 1)}
        >
          ›
        </button>
      </div>
      {week.focus && <p className="weekfocus">{week.focus}</p>}
      {showToday && (
        <button type="button" className="link totoday" onClick={onToday}>
          Wróć do najbliższego treningu
        </button>
      )}

      {week.banner && (
        <section className="card banner">
          <p>
            <strong>Nowy blok: {week.banner.phase_name}.</strong> Ciężary liczę z TM:{" "}
            {(["S", "B", "D"] as const).map((l) => `${LIFT_NAMES[l]} ${fmt(week.tm[l])}`).join(", ")}{" "}
            kg.
          </p>
          <p className="muted">
            {week.banner.suggestions.length > 0
              ? `Z Twojego dziennika wychodzi: ${week.banner.suggestions
                  .map((s) => `${LIFT_NAMES[s.lift]} ${fmt(s.kg)} kg`)
                  .join(", ")}.`
              : "Plan podpowie wyższe TM, gdy pozwolą na to single z poprzedniego bloku."}
          </p>
        </section>
      )}

      {rest && <p className="rest">Dziś wolne. Poniżej najbliższy trening.</p>}

      <div className="days" role="tablist" aria-label="Dni treningowe">
        {week.sessions.map((s, i) => (
          <button
            key={s.key}
            type="button"
            role="tab"
            aria-selected={i === dayIndex}
            className={["day", i === dayIndex ? "sel" : "", `st-${s.status}`].join(" ")}
            onClick={() => onDay(i)}
          >
            <span className="wd">
              {shortDay(s.date)}
              {s.date === today ? " · dziś" : ""}
            </span>
            <span className="code">{dayCodeLabel(s.code)}</span>
          </button>
        ))}
      </div>

      {session && <SessionView key={session.key} week={week} session={session} />}
    </>
  );
}

function SessionView({ week, session }: { week: TrainingWeek; session: TrainingSession }) {
  const attempts = session.exercises.filter((e) => e.kind === "att");
  const meta = [
    longDay(session.date),
    session.minutes ? `ok. ${session.minutes} min` : null,
    session.days_before_meet === 0
      ? "dzień zawodów"
      : session.days_before_meet != null
        ? `${session.days_before_meet} ${daysWord(session.days_before_meet)} przed startem`
        : null,
  ].filter(Boolean);
  return (
    <>
      <section className="card sesshead">
        <h2>{session.title}</h2>
        <p className="muted">{meta.join(", ")}</p>
        {session.holiday && (
          <p className="warnnote">
            {session.holiday}: siłownia może być zamknięta. Przesuń ten trening o dzień.
          </p>
        )}
        {session.note && <p className="plannote">{session.note}</p>}
        <GymField week={week} session={session} />
      </section>

      {attempts.length > 0 && <Attempts week={week} session={session} attempts={attempts} />}
      {session.exercises
        .filter((e) => e.kind !== "att")
        .map((ex) => (
          <ExerciseCard key={ex.index} week={week} session={session} ex={ex} />
        ))}

      <SessionFoot week={week} session={session} />
    </>
  );
}

function useSessionWriter(week: TrainingWeek, session: TrainingSession) {
  const put = useMutation<void, Error, TrainingSessionInput>({
    mutationKey: mutationKeys.trainingSession,
  });
  return (patch: Partial<Pick<TrainingSessionInput, "gym" | "bodyweight" | "note">>) => {
    const next = {
      gym: session.gym,
      bodyweight: session.bodyweight,
      note: session.log_note,
      ...patch,
    };
    if (
      next.gym === session.gym &&
      next.bodyweight === session.bodyweight &&
      next.note === session.log_note
    ) {
      return;
    }
    put.mutate({ week: week.index, session: session.key, ...next });
  };
}

function GymField({ week, session }: { week: TrainingWeek; session: TrainingSession }) {
  const write = useSessionWriter(week, session);
  const [gym, setGym] = useState(session.gym ?? "");
  const listId = `gyms-${session.key}`;
  const commit = (value: string) => write({ gym: value.trim() || null });
  return (
    <div className="gym">
      <label>
        Siłownia
        <input
          list={listId}
          autoComplete="off"
          value={gym}
          placeholder={week.gyms[0] ? `Ostatnio: ${week.gyms[0]}` : "np. nazwa i miasto"}
          onChange={(e) => setGym(e.target.value)}
          onBlur={() => commit(gym)}
        />
      </label>
      <datalist id={listId}>
        {week.gyms.map((g) => (
          <option key={g} value={g} />
        ))}
      </datalist>
      {!gym && week.gyms.length > 0 && (
        <div className="chips">
          {week.gyms.slice(0, 3).map((g) => (
            <button
              key={g}
              type="button"
              onClick={() => {
                setGym(g);
                commit(g);
              }}
            >
              {g}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function SessionFoot({ week, session }: { week: TrainingWeek; session: TrainingSession }) {
  const write = useSessionWriter(week, session);
  const [bw, setBw] = useState(session.bodyweight == null ? "" : fmt(session.bodyweight));
  const [note, setNote] = useState(session.log_note ?? "");
  const parsedBw = parseDecimal(bw);
  const bwValid = parsedBw === null || (typeof parsedBw === "number" && parsedBw > 20 && parsedBw < 400);
  return (
    <section className="card sessfoot">
      <label>
        Masa ciała rano
        <input
          inputMode="decimal"
          autoComplete="off"
          value={bw}
          placeholder="kg, na czczo"
          aria-invalid={!bwValid}
          onChange={(e) => setBw(e.target.value)}
          onBlur={() => {
            if (bwValid) write({ bodyweight: typeof parsedBw === "number" ? parsedBw : null });
          }}
        />
      </label>
      {!bwValid && <p className="error">Podaj masę ciała w kg, np. 78,4.</p>}
      <label>
        Notatki
        <textarea
          rows={3}
          value={note}
          placeholder="Jak poszło, co poprawić, link do nagrania"
          onChange={(e) => setNote(e.target.value)}
          onBlur={() => write({ note: note.trim() || null })}
        />
      </label>
    </section>
  );
}

/** Zapis wpisu ćwiczenia: po pauzie w pisaniu albo od razu (wyjście z pola, przycisk). */
function useEntryWriter(week: TrainingWeek, session: TrainingSession, ex: TrainingExercise) {
  const put = useMutation<void, Error, TrainingEntryInput>({
    mutationKey: mutationKeys.trainingEntry,
  });
  const [texts, setTexts] = useState<EntryTexts>(() => entryTexts(ex.entry));
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const latest = useRef(ex.entry);
  latest.current = ex.entry;

  useEffect(() => () => {
    if (timer.current) clearTimeout(timer.current);
  }, []);

  function send(next: TrainingEntryInput["entry"]) {
    const cur = latest.current;
    if (
      next.kg === cur.kg &&
      next.reps === cur.reps &&
      next.rpe === cur.rpe &&
      next.done === cur.done &&
      next.ok === cur.ok
    ) {
      return;
    }
    latest.current = next;
    put.mutate({ week: week.index, session: session.key, index: ex.index, entry: next });
  }

  function flush(current: EntryTexts = texts) {
    if (timer.current) clearTimeout(timer.current);
    timer.current = null;
    const next = entryFromTexts(current, latest.current);
    if (next) send(next);
  }

  function change(field: keyof EntryTexts, value: string) {
    const next = { ...texts, [field]: value };
    setTexts(next);
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => flush(next), WRITE_DELAY_MS);
  }

  /** Zmiana stanu (odhaczenie, ocena podejścia) razem z tym, co wpisane w polach. */
  function apply(update: (entry: TrainingEntryInput["entry"]) => TrainingEntryInput["entry"]) {
    if (timer.current) clearTimeout(timer.current);
    const base = entryFromTexts(texts, latest.current) ?? latest.current;
    const next = update(base);
    setTexts(entryTexts(next));
    send(next);
  }

  const invalid = entryFromTexts(texts, ex.entry) === null;
  return { texts, change, flush, apply, invalid };
}

function Plates({ plates }: { plates: number[] | null }) {
  const text = platesText(plates);
  if (text == null || plates == null) return null;
  return (
    <div className="barplates" role="img" aria-label={`Na stronę: ${text}`}>
      {plates.map((p, i) => (
        <span key={i} className={`pl p${String(p).replace(".", "")}`} />
      ))}
      <span className="pltxt">{text}</span>
    </div>
  );
}

function ExerciseCard({
  week,
  session,
  ex,
}: {
  week: TrainingWeek;
  session: TrainingSession;
  ex: TrainingExercise;
}) {
  const entry = useEntryWriter(week, session, ex);
  const tag = tierLabel(ex.tier);
  const move = moveFor(ex.name);
  const [showTechnique, setShowTechnique] = useState(false);
  const id = `${session.key}-${ex.index}`;
  return (
    <article className={["card", "ex", `ex-${ex.tier}`, ex.entry.done ? "done" : ""].join(" ")}>
      <div className="extop">
        <div>
          {tag && <span className="extag">{tag}</span>}
          <h3>{ex.name}</h3>
          <p className="rx">{prescription(ex)}</p>
        </div>
        {ex.load != null && (
          <div className="load">
            <span className="kg">
              {ex.kind === "single" && (
                <span className="approx" title="Orientacyjnie, decyduje RPE">
                  ≈
                </span>
              )}
              {fmt(ex.load)}
              <small>kg</small>
            </span>
          </div>
        )}
      </div>
      {ex.load != null && <Plates plates={ex.plates} />}
      {ex.cue && <p className="cue">{ex.cue}</p>}
      {move && (
        <button
          type="button"
          className="techbtn"
          aria-expanded={showTechnique}
          onClick={() => setShowTechnique(!showTechnique)}
        >
          <svg
            aria-hidden="true"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <circle cx="12" cy="4.5" r="2" />
            <path d="M12 7v6M8 10l4 1 4-1M12 13l-3 7M12 13l3 7" />
          </svg>
          {showTechnique ? "Zwiń technikę" : "Technika"}
        </button>
      )}
      {move && showTechnique && <TechniqueFigure move={move} name={ex.name} />}
      {ex.last && (
        <p className="last">
          Ostatnio:{" "}
          {[
            `${fmt(ex.last.kg)} kg${ex.last.reps ? ` × ${fmt(ex.last.reps)}` : ""}`,
            ex.last.rpe ? `RPE ${fmt(ex.last.rpe)}` : null,
            dayMonth(ex.last.date),
            ex.last.gym || null,
          ]
            .filter(Boolean)
            .join(", ")}
        </p>
      )}
      <div className="log">
        <label htmlFor={`kg-${id}`}>
          kg
          <input
            id={`kg-${id}`}
            inputMode="decimal"
            autoComplete="off"
            value={entry.texts.kg}
            placeholder={kgPlaceholder(ex)}
            onChange={(e) => entry.change("kg", e.target.value)}
            onBlur={() => entry.flush()}
          />
        </label>
        {ex.kind !== "single" && (
          <label htmlFor={`reps-${id}`}>
            Powt.
            <input
              id={`reps-${id}`}
              inputMode="decimal"
              autoComplete="off"
              value={entry.texts.reps}
              placeholder={repsPlaceholder(ex)}
              onChange={(e) => entry.change("reps", e.target.value)}
              onBlur={() => entry.flush()}
            />
          </label>
        )}
        <label htmlFor={`rpe-${id}`}>
          RPE
          <input
            id={`rpe-${id}`}
            inputMode="decimal"
            autoComplete="off"
            value={entry.texts.rpe}
            placeholder={ex.rpe ? rpeText(ex.rpe) : ""}
            onChange={(e) => entry.change("rpe", e.target.value)}
            onBlur={() => entry.flush()}
          />
        </label>
        <button
          type="button"
          className={ex.entry.done ? "donebtn on" : "donebtn"}
          aria-pressed={ex.entry.done}
          onClick={() => entry.apply((e) => toggledDone(e, ex))}
        >
          <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={3}>
            <path d="M5 12.5l4.5 4.5L19 7" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          {ex.entry.done ? "Zrobione" : "Odhacz"}
        </button>
      </div>
      {entry.invalid ? (
        <p className="error">Wpisz liczby, np. 92,5. RPE najwyżej 10.</p>
      ) : (
        ex.e1rm != null && <p className="e1">e1RM {fmt(ex.e1rm)} kg</p>
      )}
    </article>
  );
}

/** Podejścia na teście i zawodach: ciężar, RPE i ocena sędziów. Arkusz z podpowiedziami dojdzie. */
function Attempts({
  week,
  session,
  attempts,
}: {
  week: TrainingWeek;
  session: TrainingSession;
  attempts: TrainingExercise[];
}) {
  const lifts = [...new Set(attempts.map((a) => a.lift))];
  return (
    <section className="card attempts">
      <h2>Podejścia</h2>
      {lifts.map((lift) => (
        <div key={lift ?? "x"} className="attlift">
          <h3>{lift ? LIFT_TITLES[lift] : "Bój"}</h3>
          {attempts
            .filter((a) => a.lift === lift)
            .map((a) => (
              <AttemptRow key={a.index} week={week} session={session} ex={a} />
            ))}
        </div>
      ))}
    </section>
  );
}

function AttemptRow({
  week,
  session,
  ex,
}: {
  week: TrainingWeek;
  session: TrainingSession;
  ex: TrainingExercise;
}) {
  const entry = useEntryWriter(week, session, ex);
  const label = `${ex.lift ? LIFT_NAMES[ex.lift] : ex.name}, ${ex.attempt}. podejście`;
  return (
    <div className={`att${ex.entry.ok ? ` ok-${ex.entry.ok}` : ""}`}>
      <span className="attn">{ex.attempt}.</span>
      <input
        inputMode="decimal"
        autoComplete="off"
        aria-label={`${label}, kg`}
        placeholder="kg"
        value={entry.texts.kg}
        onChange={(e) => entry.change("kg", e.target.value)}
        onBlur={() => entry.flush()}
      />
      <input
        inputMode="decimal"
        autoComplete="off"
        aria-label={`${label}, RPE`}
        placeholder="RPE"
        value={entry.texts.rpe}
        onChange={(e) => entry.change("rpe", e.target.value)}
        onBlur={() => entry.flush()}
      />
      <button
        type="button"
        className="good"
        aria-pressed={ex.entry.ok === "y"}
        aria-label={`${label}: zaliczone`}
        onClick={() => entry.apply((e) => toggledOk(e, "y"))}
      >
        ✓
      </button>
      <button
        type="button"
        className="bad"
        aria-pressed={ex.entry.ok === "n"}
        aria-label={`${label}: spalone`}
        onClick={() => entry.apply((e) => toggledOk(e, "n"))}
      >
        ✕
      </button>
    </div>
  );
}

/**
 * Wgranie planu z pliku JSON: sam plan albo plan z dziennikiem ze starego pliku HTML
 * (`{ plan, settings, logs }`). Wymaga sieci; sesje z pliku zastępują te same w bazie.
 */
function PlanImport({ first = false }: { first?: boolean }) {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(first);
  const upload = useMutation<TrainingImportResult, Error, File>({
    mutationFn: async (file) => {
      let parsed: unknown;
      try {
        parsed = JSON.parse(await file.text());
      } catch {
        throw new Error("To nie jest plik JSON z planem.");
      }
      const body =
        parsed && typeof parsed === "object" && "plan" in parsed ? parsed : { plan: parsed };
      return api.put<TrainingImportResult>("/api/training/plan", body);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["training"] }),
  });

  function pick(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (file) upload.mutate(file);
  }

  if (!open) {
    return (
      <button type="button" className="link" onClick={() => setOpen(true)}>
        Wczytaj plan z pliku
      </button>
    );
  }
  return (
    <section className="card">
      <h2>{first ? "Wgraj plan treningowy" : "Wczytaj plan z pliku"}</h2>
      <p className="muted">
        Plik JSON z planem albo z planem i dziennikiem ze starego pliku. Sesje z pliku zastąpią
        te same sesje w aplikacji, pozostałe zostaną.
      </p>
      <label className={upload.isPending ? "file busy" : "file"}>
        {upload.isPending ? "Wgrywam…" : "Wybierz plik"}
        <input type="file" accept="application/json,.json" onChange={pick} />
      </label>
      {upload.error && <p className="error">{upload.error.message}</p>}
      {upload.data && (
        <p className="status ok">
          Wgrano „{upload.data.plan_name}": {upload.data.weeks} tygodni, {upload.data.sessions} sesji,
          z dziennika {upload.data.imported_sessions}.
          {upload.data.skipped.length > 0 && ` Pominięte: ${upload.data.skipped.join(", ")}.`}
        </p>
      )}
    </section>
  );
}
