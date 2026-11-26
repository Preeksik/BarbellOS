import { useMutation, useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { ApiError, type Lift, type TrainingMaxes, api } from "../../lib/api";
import { parseDecimal } from "../../lib/number";
import { TRAINING_MAXES_KEY, type TrainingTmInput, mutationKeys } from "../../lib/offline";
import { LIFT_SHORT, dayMonth, fmt, longDay } from "../../lib/training";
import { E1rmChart } from "./E1rmChart";
import { NoteBlocks, NoteSections } from "./Notes";


/** Zakładka „Maksy": cele, maksy treningowe (TM) z sugestiami, postęp e1RM i kalkulator. */
export function MaxesView() {
  const maxes = useQuery({
    queryKey: TRAINING_MAXES_KEY,
    queryFn: () => api.get<TrainingMaxes>("/api/training/maxes"),
  });
  const data = maxes.data;
  if (!data) {
    return (
      <section className="card">
        {maxes.error ? (
          <p className="error">{maxes.error.message}</p>
        ) : maxes.fetchStatus === "paused" ? (
          <p className="muted">Brak połączenia, a maksów nie ma jeszcze w pamięci telefonu.</p>
        ) : (
          <p className="muted">Wczytuję maksy…</p>
        )}
      </section>
    );
  }
  return (
    <>
      <GoalsCard data={data} />
      <TmCard data={data} />
      <ProgressCard data={data} />
      <CalculatorCard />
    </>
  );
}

function GoalsCard({ data }: { data: TrainingMaxes }) {
  return (
    <section className="card">
      <h2>{data.goals_title}</h2>
      <NoteBlocks blocks={data.goals_intro} />
      <div className="tablewrap">
        <table className="numtable">
          <thead>
            <tr>
              <th />
              <th>Przys.</th>
              <th>Ława</th>
              <th>Martwy</th>
              <th>Suma</th>
              <th>GL</th>
            </tr>
          </thead>
          <tbody>
            {data.goals.map((g) => (
              <tr key={g.label} className={g.baseline ? "base" : ""}>
                <th scope="row">{g.label}</th>
                <td>{fmt(g.S)}</td>
                <td>{fmt(g.B)}</td>
                <td>{fmt(g.D)}</td>
                <td>{fmt(g.total)}</td>
                <td>{fmt(Math.round(g.gl * 10) / 10)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <NoteSections sections={data.goals_after} />
    </section>
  );
}

function TmCard({ data }: { data: TrainingMaxes }) {
  const put = useMutation<void, Error, TrainingTmInput>({ mutationKey: mutationKeys.trainingTm });

  function save(phase: TrainingMaxes["phases"][number], patch: Partial<Record<Lift, number | null>>) {
    // Faza w całości: pozostałe boje z obecnym TM. Serwer zapamięta ręcznie tylko wartości
    // inne niż z planu, więc nic się przy tym nie „przykleja".
    const values = Object.fromEntries(
      phase.lifts.map((c) => [c.lift, c.lift in patch ? (patch[c.lift] ?? null) : c.value]),
    ) as TrainingTmInput["values"];
    put.mutate({ phase: phase.phase, values });
  }

  return (
    <section className="card">
      <h2>Maksy treningowe (TM)</h2>
      <NoteBlocks blocks={data.tm_intro} />
      <div className="tmphases">
        {data.phases.map((phase) => {
          const suggestions = phase.lifts.filter((c) => c.suggestion != null);
          return (
            <div key={phase.phase} className="tmphase">
              <div className="tmhead">
                <strong>
                  Blok {phase.phase}: {phase.name}
                </strong>
                <span className="muted">
                  tyg. {phase.first_week}–{phase.last_week}, od {dayMonth(phase.start)},
                  suma {fmt(phase.total)} kg
                </span>
              </div>
              <div className="tmcells">
                {phase.lifts.map((cell) => (
                  <TmField
                    key={`${cell.lift}-${cell.value}`}
                    phase={phase.phase}
                    cell={cell}
                    onSave={(value) => save(phase, { [cell.lift]: value })}
                  />
                ))}
              </div>
              {suggestions.length > 1 && (
                <button
                  type="button"
                  className="suggest all"
                  onClick={() =>
                    save(phase, Object.fromEntries(suggestions.map((c) => [c.lift, c.suggestion])))
                  }
                >
                  Zastosuj sugestie z dziennika
                </button>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}

function TmField({
  phase,
  cell,
  onSave,
}: {
  phase: number;
  cell: TrainingMaxes["phases"][number]["lifts"][number];
  onSave: (value: number | null) => void;
}) {
  const [text, setText] = useState(fmt(cell.value));
  const parsed = parseDecimal(text);
  const invalid = parsed !== null && (typeof parsed !== "number" || parsed <= 0 || parsed > 600);
  return (
    <div className="tmcell">
      <label>
        {LIFT_SHORT[cell.lift]}
        <input
          inputMode="decimal"
          autoComplete="off"
          aria-label={`TM ${LIFT_SHORT[cell.lift]}, blok ${phase}`}
          aria-invalid={invalid}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onBlur={() => {
            if (invalid) return;
            const value = typeof parsed === "number" ? parsed : null;
            if (value !== cell.value) onSave(value);
          }}
        />
      </label>
      {cell.manual && <small className="muted">wpisane ręcznie</small>}
      {cell.suggestion != null && (
        <button type="button" className="suggest" onClick={() => onSave(cell.suggestion)}>
          z dziennika: {fmt(cell.suggestion)}
        </button>
      )}
    </div>
  );
}

function ProgressCard({ data }: { data: TrainingMaxes }) {
  return (
    <section className="card">
      <h2>Postęp</h2>
      <p className="muted">Szacowany maks (e1RM) z każdego singla i zaliczonego podejścia.</p>
      {data.points.length === 0 ? (
        <p className="muted">
          Wykres pojawi się po pierwszym singlu wpisanym do dziennika (ciężar i RPE).
        </p>
      ) : (
        <>
          <E1rmChart maxes={data} />
          <details>
            <summary>Tabela ({data.points.length})</summary>
            <div className="tablewrap">
              <table className="numtable">
                <thead>
                  <tr>
                    <th>Data</th>
                    <th>Bój</th>
                    <th>kg</th>
                    <th>RPE</th>
                    <th>e1RM</th>
                  </tr>
                </thead>
                <tbody>
                  {[...data.points].reverse().map((p, i) => (
                    <tr key={i}>
                      <th scope="row">{longDay(p.date).split(" ")[1]}</th>
                      <td className="text">
                        {LIFT_SHORT[p.lift]}
                        {p.kind === "att" ? ", podejście" : ""}
                      </td>
                      <td>{fmt(p.kg)}</td>
                      <td>{fmt(p.rpe)}</td>
                      <td>{fmt(p.e1rm_rounded)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </details>
        </>
      )}
    </section>
  );
}

/** Kalkulator e1RM. Liczy serwer, więc wymaga sieci; wynik po krótkiej pauzie w pisaniu. */
function CalculatorCard() {
  const [texts, setTexts] = useState({ kg: "150", reps: "1", rpe: "8" });
  const [query, setQuery] = useState(texts);
  useEffect(() => {
    const timer = setTimeout(() => setQuery(texts), 500);
    return () => clearTimeout(timer);
  }, [texts]);
  const kg = parseDecimal(query.kg);
  const reps = parseDecimal(query.reps);
  const rpe = parseDecimal(query.rpe);
  const ready = typeof kg === "number" && typeof reps === "number" && typeof rpe === "number";
  const result = useQuery({
    queryKey: ["training", "calculator", kg, reps, rpe],
    queryFn: () =>
      api.get<{ e1rm: number; tm: number }>(
        `/api/training/calculator?kg=${kg}&reps=${reps}&rpe=${rpe}`,
      ),
    enabled: ready && kg > 0 && reps > 0 && rpe > 0,
    retry: false,
  });
  const field = (key: keyof typeof texts, label: string) => (
    <label>
      {label}
      <input
        inputMode="decimal"
        autoComplete="off"
        value={texts[key]}
        onChange={(e) => setTexts({ ...texts, [key]: e.target.value })}
      />
    </label>
  );
  return (
    <section className="card">
      <h2>Kalkulator e1RM</h2>
      <p className="muted">
        Ciężar, powtórzenia (1–6) i RPE. Wynik to szacowany maks; zaokrąglony w dół nadaje się na TM.
      </p>
      <div className="calc">
        {field("kg", "kg")}
        {field("reps", "Powt.")}
        {field("rpe", "RPE")}
      </div>
      <p className="calcout" aria-live="polite">
        {result.data ? (
          <>
            ≈ <strong>{fmt(result.data.e1rm)} kg</strong>, TM {fmt(result.data.tm)} kg
          </>
        ) : result.error instanceof ApiError && result.error.status === 422 ? (
          <span className="error">{result.error.message}</span>
        ) : result.fetchStatus === "paused" ? (
          <span className="muted">Kalkulator potrzebuje połączenia.</span>
        ) : (
          "–"
        )}
      </p>
    </section>
  );
}
