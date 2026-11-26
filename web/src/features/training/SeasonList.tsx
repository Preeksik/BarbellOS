import type { TrainingSeason, TrainingWeekSummary } from "../../lib/api";
import { dayMonth } from "../../lib/training";

/** Zakładka „Sezon": wszystkie tygodnie w częściach z pliku planu; stuknięcie otwiera tydzień. */
export function SeasonList({ season, onOpen }: { season: TrainingSeason; onOpen: (week: number) => void }) {
  const groups = season.groups?.length ? season.groups : [{ title: "Sezon", text: "", last_week: null }];
  let from = 1;
  return (
    <>
      {groups.map((group) => {
        const to = group.last_week ?? Number.POSITIVE_INFINITY;
        const weeks = season.weeks.filter((w) => w.n >= from && w.n <= to);
        from = to + 1;
        return (
          <section key={group.title} className="card">
            <h2>{group.title}</h2>
            {group.text && <p className="muted">{group.text}</p>}
            <ol className="weeklist">
              {weeks.map((w) => (
                <li key={w.key}>
                  <WeekRow week={w} current={w.index === season.current_week} onOpen={onOpen} />
                </li>
              ))}
            </ol>
          </section>
        );
      })}
    </>
  );
}

function WeekRow({
  week,
  current,
  onOpen,
}: {
  week: TrainingWeekSummary;
  current: boolean;
  onOpen: (week: number) => void;
}) {
  const extra = [
    week.label === "TEST" ? "test" : null,
    week.label === "AMP" ? "zawody" : null,
    week.repeat_of ? `powtórka tygodnia ${week.repeat_of}` : null,
    ...(week.holidays ?? []),
  ].filter(Boolean);
  const full = week.done === week.total;
  return (
    <button
      type="button"
      className={current ? "weekrow now" : "weekrow"}
      aria-label={`Tydzień ${week.n}, ${dayMonth(week.start)}–${dayMonth(week.end)}, ${week.block_name}${
        current ? ", bieżący" : ""
      }, zrobione ${week.done} z ${week.total}`}
      onClick={() => onOpen(week.index)}
    >
      <span className={`swatch p${String(week.plate ?? 10).replace(".", "")}`} aria-hidden="true" />
      <span className="wn">Tydz. {week.n}</span>
      <span className="wdates">
        {dayMonth(week.start)}–{dayMonth(week.end)}
      </span>
      <span className="wblock">
        {week.block_name}
        {extra.length > 0 && <small>{extra.join(", ")}</small>}
      </span>
      <span className={full ? "wdone full" : "wdone"}>
        {week.done}/{week.total}
      </span>
    </button>
  );
}
