import { useEffect, useRef, useState } from "react";
import { type Illustration, frameAt } from "./illustrations";

function reducedMotion(): boolean {
  return typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
}

/**
 * Ilustracja z klatek (27.11.2026): góra i dół ruchu przełączane w pętli, z odliczaniem
 * pauzy w wariantach. Stuknięcie zatrzymuje. Przy ograniczeniu ruchu startuje zatrzymana.
 */
export function TechniqueFrames({
  illustration,
  name,
  points,
}: {
  illustration: Illustration;
  name: string;
  points: string[];
}) {
  const [playing, setPlaying] = useState(() => !reducedMotion());
  const [time, setTime] = useState(0);
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
  }, [playing, illustration]);

  const state = frameAt(illustration, time);
  return (
    <figure className="technique frames">
      <button
        type="button"
        className="framebox"
        aria-label={`${playing ? "Zatrzymaj" : "Odtwórz"} animację: ${name}`}
        onClick={() => setPlaying(!playing)}
      >
        {illustration.frames.map((src, i) => (
          <img
            key={src}
            src={src}
            alt=""
            draggable={false}
            style={{
              opacity: i === state.frame ? state.opacity : i === state.previous ? 1 : 0,
              zIndex: i === state.frame ? 2 : 1,
            }}
          />
        ))}
        {state.countdown != null && (
          <span className={state.moving ? "countdown moving" : "countdown"} aria-hidden="true">
            {state.countdown}
          </span>
        )}
      </button>
      <figcaption>
        <span className="phase">
          {state.label}
          {state.countdown != null && !state.moving ? ` ${state.countdown} s` : ""}
        </span>
        <button type="button" className="link" onClick={() => setPlaying(!playing)}>
          {playing ? "Zatrzymaj" : "Odtwórz"}
        </button>
      </figcaption>
      {points.length > 0 && (
        <ul className="points">
          {points.map((p) => (
            <li key={p}>{p}</li>
          ))}
        </ul>
      )}
    </figure>
  );
}
