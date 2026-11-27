import { useEffect, useRef, useState } from "react";
import { TechniqueFrames } from "./TechniqueFrames";
import { type Illustration, type VideoStep, videoCountdown } from "./illustrations";

function reducedMotion(): boolean {
  return typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
}

const END_TOLERANCE_S = 0.05;

/**
 * Płynny film ruchu (27.11.2026). Przebieg (prędkość zejścia, pauza na dole z odliczaniem,
 * szybkie wstanie) steruje aplikacja według kroków z `illustrations.ts`, więc warianty
 * korzystają z jednego filmu. Bez sieci albo przy błędzie odtwarzania zostają klatki.
 */
export function TechniqueVideo({
  illustration,
  name,
  points,
}: {
  illustration: Illustration & { video: NonNullable<Illustration["video"]> };
  name: string;
  points: string[];
}) {
  const video = useRef<HTMLVideoElement>(null);
  const [failed, setFailed] = useState(false);
  const [playing, setPlaying] = useState(() => !reducedMotion());
  const [phase, setPhase] = useState<{ label: string; countdown: number | null }>({
    label: illustration.video.steps[0].label,
    countdown: null,
  });

  useEffect(() => {
    const el = video.current;
    if (!el || failed) return;
    if (!playing) {
      el.pause();
      return;
    }
    const steps: VideoStep[] = illustration.video.steps;
    let index = 0;
    let holdStart: number | null = null;
    let frame = 0;
    const show = (label: string, countdown: number | null) =>
      setPhase((old) => (old.label === label && old.countdown === countdown ? old : { label, countdown }));

    const next = () => {
      index += 1;
      holdStart = null;
      if (index >= steps.length) {
        index = 0;
        el.currentTime = 0; // koniec pętli to ta sama pozycja co początek
      }
    };

    const tick = (now: number) => {
      const step = steps[index];
      if (step.kind === "hold") {
        if (holdStart == null) holdStart = now;
        if (!el.paused) el.pause();
        const elapsed = now - holdStart;
        show(step.label, videoCountdown(step, el.currentTime, elapsed));
        if (elapsed >= step.ms) next();
      } else {
        el.playbackRate = step.rate;
        if (el.paused) void el.play().catch(() => setFailed(true));
        show(step.label, videoCountdown(step, el.currentTime, 0));
        if (el.currentTime >= step.to - END_TOLERANCE_S || el.ended) {
          el.pause();
          next();
        }
      }
      frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => {
      cancelAnimationFrame(frame);
      el.pause();
    };
  }, [playing, failed, illustration]);

  if (failed) return <TechniqueFrames illustration={illustration} name={name} points={points} />;

  return (
    <figure className="technique frames">
      <button
        type="button"
        className="framebox"
        aria-label={`${playing ? "Zatrzymaj" : "Odtwórz"} animację: ${name}`}
        onClick={() => setPlaying(!playing)}
      >
        <video
          ref={video}
          src={illustration.video.src}
          poster={illustration.frames[0]}
          muted
          playsInline
          preload="auto"
          disablePictureInPicture
          onError={() => setFailed(true)}
        />
        {phase.countdown != null && (
          <span className="countdown" aria-hidden="true">
            {phase.countdown}
          </span>
        )}
      </button>
      <figcaption>
        <span className="phase">
          {phase.label}
          {phase.countdown != null ? ` ${phase.countdown} s` : ""}
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
