import { useEffect, useRef, useState } from "react";
import { type Move, progressAt } from "./moves";
import { BENCH, PLATE_RADIUS, type Pose, type Vec } from "./skeleton";

const GROUND = 184; // y podłogi w układzie SVG (oś y w dół)
// Kadr dopasowany do ruchu: stojący ludzik jest wąski i wysoki, ława szeroka i niska.
const VIEWBOX: Record<Move["kind"], string> = {
  squat: "30 0 150 190",
  hinge: "30 0 150 190",
  bench: "15 30 195 160",
};
const sx = (v: Vec) => v.x;
const sy = (v: Vec) => GROUND - v.y;

function reducedMotion(): boolean {
  return typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
}

function Bone({ a, b, w }: { a: Vec; b: Vec; w: number }) {
  return <line x1={sx(a)} y1={sy(a)} x2={sx(b)} y2={sy(b)} strokeWidth={w} />;
}

function Figure({ pose }: { pose: Pose }) {
  return (
    <g className="body" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round">
      <Bone a={pose.heel} b={pose.toe} w={5} />
      <Bone a={pose.ankle} b={pose.heel} w={5} />
      <Bone a={pose.ankle} b={pose.knee} w={8} />
      <Bone a={pose.knee} b={pose.hip} w={10} />
      <Bone a={pose.hip} b={pose.shoulder} w={13} />
      <Bone a={pose.shoulder} b={pose.elbow} w={7} />
      <Bone a={pose.elbow} b={pose.hand} w={6} />
      <circle cx={sx(pose.head)} cy={sy(pose.head)} r={10} fill="currentColor" stroke="none" />
    </g>
  );
}

/**
 * Animowany ludzik z techniką ćwiczenia (25.11.2026). Widok z boku, talerz za ludzikiem.
 * Pętla zatrzymuje się stuknięciem; przy ograniczeniu ruchu w telefonie startuje zatrzymana.
 */
export function TechniqueFigure({ move, name }: { move: Move; name: string }) {
  const [playing, setPlaying] = useState(() => !reducedMotion());
  const [time, setTime] = useState(() => (reducedMotion() ? holdTime(move) : 0));
  const origin = useRef<number | null>(null);

  useEffect(() => {
    if (!playing) return;
    let frame = 0;
    origin.current = performance.now() - time;
    const tick = (now: number) => {
      setTime(now - (origin.current ?? now));
      frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
    // Czas wznawia się od miejsca zatrzymania; `time` celowo poza zależnościami.
  }, [playing, move]);

  const { progress, label } = progressAt(move, time);
  const pose = move.pose(progress);
  const pinY = move.pins != null ? move.pose(move.pins).bar : null;

  return (
    <figure className="technique">
      <svg
        viewBox={VIEWBOX[move.kind]}
        role="img"
        aria-label={`Animacja techniki: ${name}`}
        onClick={() => setPlaying(!playing)}
      >
        <line className="floor" x1={0} y1={GROUND} x2={220} y2={GROUND} />
        {move.bench && (
          <g className="equipment">
            <rect x={BENCH.from} y={GROUND - BENCH.top} width={BENCH.to - BENCH.from} height={6} rx={2} />
            <line x1={BENCH.from + 14} y1={GROUND - BENCH.top + 6} x2={BENCH.from + 14} y2={GROUND} />
            <line x1={BENCH.to - 14} y1={GROUND - BENCH.top + 6} x2={BENCH.to - 14} y2={GROUND} />
          </g>
        )}
        {pinY && (
          <g className="equipment">
            <line x1={pinY.x + 34} y1={GROUND - 170} x2={pinY.x + 34} y2={GROUND} />
            <line
              x1={pinY.x - 30}
              y1={GROUND - (pinY.y - 3)}
              x2={pinY.x + 34}
              y2={GROUND - (pinY.y - 3)}
              strokeWidth={4}
            />
          </g>
        )}
        {pose.bar && (
          <g className="plate">
            <circle cx={sx(pose.bar)} cy={sy(pose.bar)} r={PLATE_RADIUS} />
            <circle className="hub" cx={sx(pose.bar)} cy={sy(pose.bar)} r={4.5} />
          </g>
        )}
        <Figure pose={pose} />
        {pose.bar && <circle className="sleeve" cx={sx(pose.bar)} cy={sy(pose.bar)} r={2.6} />}
      </svg>
      <figcaption>
        <span className="phase">{label ?? " "}</span>
        <button type="button" className="link" onClick={() => setPlaying(!playing)}>
          {playing ? "Zatrzymaj" : "Odtwórz"}
        </button>
      </figcaption>
      <ul className="points">
        {move.points.map((p) => (
          <li key={p}>{p}</li>
        ))}
      </ul>
    </figure>
  );
}

/** Chwila najniższej pozycji: kadr na start przy ograniczeniu ruchu. */
function holdTime(move: Move): number {
  let t = 0;
  let from = move.start;
  for (const step of move.steps) {
    if (step.to === from && from !== move.start) return t + step.ms / 2;
    t += step.ms;
    from = step.to;
  }
  return 0;
}
