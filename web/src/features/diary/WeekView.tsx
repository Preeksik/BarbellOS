import { useQuery } from "@tanstack/react-query";
import { type Targets, type Week, api } from "../../lib/api";
import { dayLabel, toIsoDay } from "../../lib/diary";
import { coverageState, formatAmount, trustText } from "../../lib/micros";
import { formatGrams, formatKcal } from "../diet/macros";

/**
 * Ostatnie 7 dni (etap 6): średnie dzienne, kalorie dzień po dniu i pokrycie norm
 * witamin i minerałów z informacją, na ile dane pochodzą z tabel, a na ile z szacunku.
 */
export function WeekView({ day, targets }: { day: string; targets: Targets | null }) {
  const week = useQuery({
    queryKey: ["week", day],
    queryFn: () => api.get<Week>(`/api/diary/week/${day}`),
  });

  if (!week.data) {
    return (
      <section className="card">
        {week.error ? (
          <p className="error">{week.error.message}</p>
        ) : week.fetchStatus === "paused" ? (
          <p className="muted">Podsumowanie tygodnia liczy serwer: potrzebne połączenie.</p>
        ) : (
          <p className="muted">Liczę tydzień…</p>
        )}
      </section>
    );
  }
  const w = week.data;
  const avg = w.average;
  const goals = targets?.goals;
  const maxKcal = Math.max(1, ...w.days.map((d) => d.totals.kcal), goals?.kcal ?? 0);
  const today = toIsoDay(new Date());

  return (
    <>
      <section className="card">
        <h2>Średnio dziennie</h2>
        <p className="muted">
          {w.logged_days} z 7 dni z wpisami (średnia tylko z nich: dzień bez wpisów to zwykle
          dzień niezalogowany).
        </p>
        {avg ? (
          <dl className="macros">
            <Avg label="Kalorie" value={formatKcal(avg.kcal)} goal={goals?.kcal} unit="kcal" />
            <Avg label="Białko" value={formatGrams(avg.protein_g)} goal={goals?.protein_g} unit="g" />
            <Avg label="Tłuszcz" value={formatGrams(avg.fat_g)} goal={goals?.fat_g} unit="g" />
            <Avg label="Węgle" value={formatGrams(avg.carbs_g)} goal={goals?.carbs_g} unit="g" />
          </dl>
        ) : (
          <p className="muted">W tym tygodniu nic nie zapisano.</p>
        )}
        <ul className="weekdays">
          {w.days.map((d) => (
            <li key={d.date}>
              <span>{dayLabel(d.date, today)}</span>
              <div className="bar">
                <div style={{ width: `${(d.totals.kcal / maxKcal) * 100}%` }} />
              </div>
              <span>{d.entries ? `${formatKcal(d.totals.kcal)}` : "–"}</span>
            </li>
          ))}
        </ul>
      </section>

      <section className="card">
        <h2>Witaminy i minerały</h2>
        <p className="muted">
          Średnio na dzień względem referencyjnego spożycia z etykiet UE (to nie indywidualna
          norma). Pod każdą wartością: skąd pochodzą dane w kaloriach tygodnia.
        </p>
        <ul className="goals microweek">
          {w.micros.map((m) => {
            const state = coverageState(m);
            const pct = m.percent_rda ?? 0;
            return (
              <li key={m.nutrient_id} className={`goal ${state}`}>
                <div className="goalhead">
                  <span>{m.name_pl}</span>
                  <span>
                    {formatAmount(m.avg_amount)} {m.unit}
                    {m.percent_rda != null && ` · ${Math.round(pct)}%`}
                    {m.nutrient_id === "sodium" ? " limitu" : ""}
                  </span>
                </div>
                <div className="bar">
                  <div style={{ width: `${Math.min(100, pct)}%` }} />
                </div>
                <span className="muted">
                  {state === "low-data" ? "za mało danych · " : ""}
                  {trustText(m)}
                </span>
              </li>
            );
          })}
        </ul>
      </section>
    </>
  );
}

function Avg({
  label,
  value,
  goal,
  unit,
}: {
  label: string;
  value: string;
  goal: number | null | undefined;
  unit: string;
}) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>
        {value}
        {goal != null && (
          <span className="muted">
            {" "}
            / {unit === "kcal" ? formatKcal(goal) : formatGrams(goal)}
          </span>
        )}
      </dd>
    </div>
  );
}
