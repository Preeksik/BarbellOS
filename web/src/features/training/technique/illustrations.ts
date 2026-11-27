/**
 * Ilustracje techniki z klatek (27.11.2026): dwa obrazy (góra i dół ruchu) przełączane jak
 * w dawnych aplikacjach treningowych. Obrazy generuje właściciel w czacie Gemini
 * (docs/ilustracje-techniki.md), tnie je scripts/technique_frames.py.
 *
 * Warianty różniące się tylko czasem (pauza, tempo) używają tych samych klatek z innym
 * przebiegiem: dłuższy postój na dole z odliczaniem albo wolne przejście.
 */

export interface FrameStep {
  frame: number;
  /** Przejście do tej klatki (ms): krótkie jak przeskok, długie pokazuje wolny ruch. */
  fade: number;
  /** Postój na tej klatce (ms). */
  hold: number;
  label: string;
  /** Odliczanie sekund w czasie postoju (pauza na dole). */
  countdown?: boolean;
  /** Odliczanie w czasie przejścia (np. „3 s w dół" w tempie). */
  countdownFade?: boolean;
}

/**
 * Krok filmu (od 27.11.2026): odtwarzanie do sekundy `to` z prędkością `rate` albo postój.
 * Film z modelu Wan to pętla góra → dół → góra; dół wypada w połowie.
 */
export type VideoStep =
  | { kind: "play"; to: number; rate: number; label: string; countdown?: boolean }
  | { kind: "hold"; ms: number; label: string; countdown?: boolean };

export interface Illustration {
  frames: string[];
  steps: FrameStep[];
  /** Płynny film ruchu; bez sieci albo przy błędzie zostają klatki. */
  video?: { src: string; steps: VideoStep[] };
}

const QUICK = 300;
const frames = (name: string) => [`/technique/${name}-1.webp`, `/technique/${name}-2.webp`];

const SQUAT = frames("przysiad");
// Film przysiadu: 6 s, dół w 3. sekundzie (Wan 2.1 FLF2V z klatek przysiadu, 27.11.2026).
const SQUAT_VIDEO = "/technique/przysiad.mp4";
const SQUAT_BOTTOM = 3;
const SQUAT_END = 6;

const BY_NAME: Record<string, Illustration> = {
  Przysiad: {
    frames: SQUAT,
    video: {
      src: SQUAT_VIDEO,
      steps: [
        { kind: "play", to: SQUAT_BOTTOM, rate: 1.5, label: "w dół" },
        { kind: "hold", ms: 300, label: "dół" },
        { kind: "play", to: SQUAT_END, rate: 1.5, label: "w górę" },
        { kind: "hold", ms: 600, label: "góra" },
      ],
    },
    steps: [
      { frame: 0, fade: QUICK, hold: 1100, label: "góra" },
      { frame: 1, fade: QUICK, hold: 900, label: "dół" },
    ],
  },
  "Przysiad z pauzą 2 s": {
    frames: SQUAT,
    video: {
      src: SQUAT_VIDEO,
      steps: [
        { kind: "play", to: SQUAT_BOTTOM, rate: 1.5, label: "w dół" },
        { kind: "hold", ms: 2000, label: "pauza", countdown: true },
        { kind: "play", to: SQUAT_END, rate: 1.5, label: "w górę" },
        { kind: "hold", ms: 600, label: "góra" },
      ],
    },
    steps: [
      { frame: 0, fade: QUICK, hold: 1100, label: "góra" },
      { frame: 1, fade: QUICK, hold: 2000, label: "pauza", countdown: true },
    ],
  },
  "Przysiad tempo 3-1-0": {
    frames: SQUAT,
    video: {
      src: SQUAT_VIDEO,
      steps: [
        { kind: "play", to: SQUAT_BOTTOM, rate: 1, label: "3 s w dół", countdown: true },
        { kind: "hold", ms: 1000, label: "pauza", countdown: true },
        { kind: "play", to: SQUAT_END, rate: 3, label: "w górę" },
        { kind: "hold", ms: 600, label: "góra" },
      ],
    },
    steps: [
      { frame: 0, fade: QUICK, hold: 900, label: "góra" },
      { frame: 1, fade: 3000, hold: 1000, label: "pauza", countdown: true, countdownFade: true },
    ],
  },
};

/** Ilustracja z klatek dla ćwiczenia z planu albo null (wtedy zostaje ludzik). */
export function illustrationFor(name: string): Illustration | null {
  return BY_NAME[name] ?? null;
}

export function cycleLength(ill: Illustration): number {
  return ill.steps.reduce((sum, s) => sum + s.fade + s.hold, 0);
}

export interface FrameState {
  /** Klatka, do której trwa przejście albo na której jest postój. */
  frame: number;
  /** Klatka pod spodem w czasie przejścia. */
  previous: number;
  /** 0–1: jak bardzo widać `frame` (1 = przejście skończone). */
  opacity: number;
  label: string;
  /** Pozostałe pełne sekundy odliczania albo null. */
  countdown: number | null;
  /** W czasie wolnego przejścia: opis ruchu, np. „3 s w dół". */
  moving: boolean;
}

/** Stan odtwarzania w chwili `t` (ms, zapętlone). */
export function frameAt(ill: Illustration, t: number): FrameState {
  const total = cycleLength(ill);
  let time = ((t % total) + total) % total;
  for (let i = 0; i < ill.steps.length; i++) {
    const step = ill.steps[i];
    const previous = ill.steps[(i - 1 + ill.steps.length) % ill.steps.length].frame;
    if (time < step.fade) {
      const remaining = step.fade - time;
      return {
        frame: step.frame,
        previous,
        opacity: time / step.fade,
        label: step.countdownFade ? `${Math.round(step.fade / 1000)} s w dół` : step.label,
        countdown: step.countdownFade ? Math.ceil(remaining / 1000) : null,
        moving: Boolean(step.countdownFade),
      };
    }
    time -= step.fade;
    if (time < step.hold) {
      return {
        frame: step.frame,
        previous,
        opacity: 1,
        label: step.label,
        countdown: step.countdown ? Math.ceil((step.hold - time) / 1000) : null,
        moving: false,
      };
    }
    time -= step.hold;
  }
  const last = ill.steps[ill.steps.length - 1];
  return { frame: last.frame, previous: last.frame, opacity: 1, label: last.label, countdown: null, moving: false };
}

/** Pozostałe pełne sekundy kroku filmu (odliczanie) albo null. */
export function videoCountdown(
  step: VideoStep,
  currentTime: number,
  holdElapsedMs: number,
): number | null {
  if (!step.countdown) return null;
  if (step.kind === "hold") return Math.max(1, Math.ceil((step.ms - holdElapsedMs) / 1000));
  return Math.max(1, Math.ceil((step.to - currentTime) / step.rate));
}
