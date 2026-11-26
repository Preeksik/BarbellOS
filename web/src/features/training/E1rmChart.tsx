import { useState } from "react";
import type { Lift, TrainingMaxes } from "../../lib/api";
import { LIFT_SHORT, dayMonth, fmt } from "../../lib/training";

const W = 340;
const H = 220;
const M = { l: 34, r: 44, t: 18, b: 24 };
const LIFTS: Lift[] = ["S", "B", "D"];
const MONTHS = ["sty", "lut", "mar", "kwi", "maj", "cze", "lip", "sie", "wrz", "paź", "lis", "gru"];

const time = (iso: string) => new Date(`${iso}T12:00:00`).getTime();

interface Point {
  date: string;
  value: number;
  rounded: number;
}

/**
 * Szacowany maks (e1RM) z singli i zaliczonych podejść w czasie, od startu planu do zawodów.
 * Jedna kropka na bój i dzień (najlepsza). Stuknięcie pokazuje wartości z tego dnia.
 * Kolory bojów z talerzy, sprawdzone walidatorem w obu motywach (26.11.2026).
 */
export function E1rmChart({ maxes }: { maxes: TrainingMaxes }) {
  const [focus, setFocus] = useState<string | null>(null);
  const series: Record<Lift, Point[]> = { S: [], B: [], D: [] };
  for (const p of maxes.points) {
    const list = series[p.lift];
    const same = list.find((x) => x.date === p.date);
    if (!same) list.push({ date: p.date, value: p.e1rm, rounded: p.e1rm_rounded });
    else if (same.value < p.e1rm) Object.assign(same, { value: p.e1rm, rounded: p.e1rm_rounded });
  }
  for (const l of LIFTS) series[l].sort((a, b) => a.date.localeCompare(b.date));

  const x0 = time(maxes.start_date);
  const x1 = time(maxes.meet_date);
  const X = (iso: string) => M.l + ((W - M.l - M.r) * (time(iso) - x0)) / (x1 - x0);
  const values = maxes.points.map((p) => p.e1rm);
  const rawLo = Math.min(...values) - 8;
  const rawHi = Math.max(...values) + 8;
  const step = rawHi - rawLo > 120 ? 40 : rawHi - rawLo > 60 ? 20 : 10;
  const lo = Math.floor(rawLo / step) * step;
  const hi = Math.max(Math.ceil(rawHi / step) * step, lo + step);
  const Y = (v: number) => M.t + (H - M.t - M.b) * (1 - (v - lo) / (hi - lo));

  const grid: number[] = [];
  for (let v = lo; v <= hi + 1e-9; v += step) grid.push(v);
  const months: { x: number; label: string }[] = [];
  const startDate = new Date(x0);
  for (let d = new Date(startDate.getFullYear(), startDate.getMonth() + 1, 1); d.getTime() <= x1; d = new Date(d.getFullYear(), d.getMonth() + 1, 1)) {
    const iso = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-01`;
    months.push({ x: X(iso), label: MONTHS[d.getMonth()] });
  }
  const events = [
    maxes.test_date ? { iso: maxes.test_date, label: "TEST" } : null,
    { iso: maxes.meet_date, label: maxes.meet_name.split(" ")[0] },
  ].filter((e): e is { iso: string; label: string } => e != null);

  // Etykiety przy ostatnim punkcie, rozsunięte, żeby się nie nakładały.
  const labels = LIFTS.filter((l) => series[l].length).map((l) => {
    const last = series[l][series[l].length - 1];
    return { lift: l, x: X(last.date), y: Y(last.value), text: fmt(last.rounded) };
  });
  labels.sort((a, b) => a.y - b.y);
  for (let i = 1; i < labels.length; i++) {
    if (labels[i].y - labels[i - 1].y < 13) labels[i].y = labels[i - 1].y + 13;
  }

  const dates = [...new Set(maxes.points.map((p) => p.date))].sort();
  function pick(clientX: number, rect: DOMRect) {
    const sx = ((clientX - rect.left) * W) / rect.width;
    let best: string | null = null;
    let distance = Number.POSITIVE_INFINITY;
    for (const d of dates) {
      const dd = Math.abs(X(d) - sx);
      if (dd < distance) [best, distance] = [d, dd];
    }
    setFocus(best);
  }
  const focusRows = focus
    ? LIFTS.map((l) => {
        const upTo = series[l].filter((p) => p.date <= focus);
        const p = upTo[upTo.length - 1];
        return p ? { lift: l, p } : null;
      }).filter((r): r is { lift: Lift; p: Point } => r != null)
    : [];

  return (
    <div className="chart">
      <ul className="legend" aria-hidden="true">
        {LIFTS.map((l) => (
          <li key={l}>
            <i className={`k-${l}`} />
            {LIFT_SHORT[l]}
          </li>
        ))}
      </ul>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label="Szacowany maks (e1RM) z singli i podejść w czasie; dane w tabeli poniżej"
        onPointerDown={(e) => pick(e.clientX, e.currentTarget.getBoundingClientRect())}
        onPointerMove={(e) => e.buttons && pick(e.clientX, e.currentTarget.getBoundingClientRect())}
      >
        {grid.map((v) => (
          <g key={v}>
            <line className="grid" x1={M.l} x2={W - M.r} y1={Y(v)} y2={Y(v)} />
            <text className="tick" x={M.l - 6} y={Y(v) + 4} textAnchor="end">
              {v}
            </text>
          </g>
        ))}
        {months.map((m) => (
          <text key={m.label + m.x} className="tick" x={m.x} y={H - 6} textAnchor="middle">
            {m.label}
          </text>
        ))}
        {events.map((e) => (
          <g key={e.label}>
            <line className="event" x1={X(e.iso)} x2={X(e.iso)} y1={M.t} y2={H - M.b} />
            <text className="tick" x={X(e.iso)} y={M.t - 6} textAnchor="middle">
              {e.label}
            </text>
          </g>
        ))}
        {LIFTS.map((l) => (
          <g key={l} className={`s-${l}`}>
            {series[l].length > 1 && (
              <polyline points={series[l].map((p) => `${X(p.date)},${Y(p.value)}`).join(" ")} />
            )}
            {series[l].map((p) => (
              <circle key={p.date} cx={X(p.date)} cy={Y(p.value)} r={4} />
            ))}
          </g>
        ))}
        {labels.map((lab) => (
          <g key={lab.lift}>
            <line className={`key s-${lab.lift}`} x1={lab.x + 7} x2={lab.x + 15} y1={lab.y} y2={lab.y} />
            <text className="vlabel" x={lab.x + 18} y={lab.y + 4}>
              {lab.text}
            </text>
          </g>
        ))}
        {focus && <line className="cross" x1={X(focus)} x2={X(focus)} y1={M.t} y2={H - M.b} />}
      </svg>
      <p className="chartnote" aria-live="polite">
        {focus
          ? `${dayMonth(focus)}: ${focusRows.map((r) => `${LIFT_SHORT[r.lift].toLowerCase()} ${fmt(r.p.rounded)} kg`).join(", ")}`
          : "Stuknij wykres, żeby zobaczyć wartości z danego dnia."}
      </p>
    </div>
  );
}
