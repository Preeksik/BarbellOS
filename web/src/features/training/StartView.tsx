import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { type AttemptPlan, type Lift, type StartCard, type TrainingStart, api } from "../../lib/api";
import { toIsoDay } from "../../lib/diary";
import { TRAINING_START_KEY } from "../../lib/offline";
import { LIFT_SHORT, fmt, ladderText, longDay, rangeText } from "../../lib/training";
import { NoteBlocks, NoteSections } from "./Notes";

/** Zakładka „Start": podejścia i rozgrzewka na test i zawody, data zawodów, wyniki. */
export function StartView({ onOpenWeek }: { onOpenWeek: (week: number) => void }) {
  const start = useQuery({
    queryKey: TRAINING_START_KEY,
    queryFn: () => api.get<TrainingStart>("/api/training/start"),
  });
  const data = start.data;
  if (!data) {
    return (
      <section className="card">
        {start.error ? (
          <p className="error">{start.error.message}</p>
        ) : start.fetchStatus === "paused" ? (
          <p className="muted">Brak połączenia, a tej zakładki nie ma jeszcze w pamięci telefonu.</p>
        ) : (
          <p className="muted">Wczytuję…</p>
        )}
      </section>
    );
  }
  return (
    <>
      {data.test && (
        <section className="card">
          <h2>
            {data.test.name} {longDay(data.test.date).split(" ")[1]}
          </h2>
          <NoteBlocks blocks={data.test.intro} />
          <AttemptTable plan={data.test.attempts} />
          <NoteBlocks blocks={data.test.after_table} />
          <h3>Rozgrzewka na teście</h3>
          <Ladders plan={data.test.attempts} />
          <OpenSheet card={data.test} label="Otwórz arkusz testu" onOpenWeek={onOpenWeek} />
        </section>
      )}
      <section className="card">
        <h2>{data.meet.name}</h2>
        <NoteBlocks blocks={data.meet.intro} />
        <MeetDate data={data} />
        <AttemptTable plan={data.meet.attempts} />
        <h3>Rozgrzewka na pomoście rozgrzewkowym</h3>
        <Ladders plan={data.meet.attempts} />
        <NoteSections sections={data.meet.after_ladder} />
        <OpenSheet card={data.meet} label={`Otwórz arkusz: ${data.meet.name}`} onOpenWeek={onOpenWeek} />
      </section>
      <section className="card">
        <h2>Wyniki</h2>
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
              {data.results.map((r) => (
                <tr key={r.label} className={r.baseline ? "base" : ""}>
                  <th scope="row">{r.label}</th>
                  {r.empty ? (
                    <td colSpan={5} className="text muted">
                      jeszcze bez wpisów
                    </td>
                  ) : (
                    <>
                      <td>{fmt(r.S)}</td>
                      <td>{fmt(r.B)}</td>
                      <td>{fmt(r.D)}</td>
                      <td>{fmt(r.total)}</td>
                      <td>{r.gl == null ? "–" : fmt(Math.round(r.gl * 100) / 100)}</td>
                    </>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <NoteBlocks blocks={data.results_note} />
      </section>
    </>
  );
}

function AttemptTable({ plan }: { plan: AttemptPlan }) {
  return (
    <div className="tablewrap">
      <table className="numtable">
        <thead>
          <tr>
            <th>Bój</th>
            <th>1.</th>
            <th>2.</th>
            <th>3.</th>
          </tr>
        </thead>
        <tbody>
          {plan.rows.map((r) => (
            <tr key={r.lift}>
              <th scope="row">
                {LIFT_SHORT[r.lift]}
                <small>
                  maks ≈ {fmt(r.max)}, {r.from_singles ? "z singli" : `TM bloku ${r.fallback_phase}`}
                </small>
              </th>
              <td>{fmt(r.first)}</td>
              <td>{fmt(r.second)}</td>
              <td>{rangeText(r.third)}</td>
            </tr>
          ))}
          <tr className="sumrow">
            <th scope="row">Suma</th>
            <td>{fmt(plan.total_first)}</td>
            <td>{fmt(plan.total_second)}</td>
            <td>{rangeText(plan.total_third)}</td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}

function Ladders({ plan }: { plan: AttemptPlan }) {
  return (
    <ul className="ladders">
      {plan.ladders.map((l) => (
        <li key={l.lift}>
          <strong>{LIFT_SHORT[l.lift as Lift]}:</strong> {ladderText(l.steps)}, otwarcie{" "}
          <strong>{fmt(l.opener)}</strong>
        </li>
      ))}
    </ul>
  );
}

function OpenSheet({
  card,
  label,
  onOpenWeek,
}: {
  card: StartCard;
  label: string;
  onOpenWeek: (week: number) => void;
}) {
  if (card.week_index == null) return null;
  const week = card.week_index;
  return (
    <button type="button" className="primary" onClick={() => onOpenWeek(week)}>
      {label}
    </button>
  );
}

/**
 * Data zawodów: po zmianie serwer dopasowuje długość planu (powtórka albo usunięcie
 * tygodnia). Wymaga sieci, bo przebudowuje kalendarz; błąd mówi, czemu się nie da.
 */
function MeetDate({ data }: { data: TrainingStart }) {
  const queryClient = useQueryClient();
  const [value, setValue] = useState(data.meet.date);
  const change = useMutation<void, Error, string>({
    mutationFn: (date) =>
      api.put<void>("/api/training/meet", { date, today: toIsoDay(new Date()) }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["training"] }),
  });
  return (
    <div className="meetdate">
      <label>
        Dzień startu
        <input
          type="date"
          value={value}
          min={data.meet_range?.[0]}
          max={data.meet_range?.[1]}
          onChange={(e) => {
            setValue(e.target.value);
            if (e.target.value && e.target.value !== data.meet.date) change.mutate(e.target.value);
          }}
        />
      </label>
      {change.isPending ? (
        <p className="muted">Dopasowuję plan…</p>
      ) : change.error ? (
        <p className="error">{change.error.message}</p>
      ) : (
        <p className="muted">
          {data.adjustment} Start: {longDay(data.meet.date)}
          {data.meet_default ? " (data zakładana)" : ""}.
        </p>
      )}
    </div>
  );
}
