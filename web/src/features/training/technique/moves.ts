/**
 * Ruchy do animacji techniki: poza w funkcji postępu i przebieg czasu z pauzami.
 * Ćwiczenie z planu trafia tu po nazwie (`moveFor`). Akcesoria dojdą później.
 */

import {
  LOCKOUT_BAR_Y,
  PLATE_RADIUS,
  type Pose,
  benchPose,
  hingePose,
  lerp,
  smooth,
  squatPose,
} from "./skeleton";

/** Odcinek przebiegu: przejście do `to` (0–1) w `ms` milisekund; to samo `to` = pauza. */
export interface Step {
  to: number;
  ms: number;
  label?: string; // co się teraz dzieje, np. „pauza 2 s"
}

export interface Move {
  id: string;
  kind: "squat" | "bench" | "hinge";
  pose: (progress: number) => Pose;
  start: number;
  steps: Step[];
  /** Elementy sceny: ławka, piny na wysokości postępu, podest pod stopami. */
  bench?: boolean;
  pins?: number;
  platform?: number;
  points: string[];
}

// Postęp 0 = pozycja startowa, 1 = najniższy punkt (przysiad, ława) albo najwyżej (martwy).
const squat = (opts: { platform?: number } = {}) => (p: number) => squatPose(smooth(p), opts);
const bench = (opts: { legsUp?: boolean; stopAbove?: number } = {}) => (p: number) =>
  benchPose(smooth(p), opts);

/** Martwy ciąg: start na podłodze, kolana wracają, zanim sztanga je minie. */
const deadlift = (opts: { platform?: number } = {}) => (p: number) => {
  const t = smooth(p);
  const barY = lerp(PLATE_RADIUS, LOCKOUT_BAR_Y, t);
  const shin = lerp(17, 1, smooth(Math.min(1, p / 0.55)));
  return hingePose(barY, shin, opts);
};

/** RDL: od wyprostu w dół do połowy piszczeli, kolana lekko ugięte przez cały ruch. */
const rdl = (p: number) => {
  const t = smooth(p);
  return hingePose(lerp(LOCKOUT_BAR_Y, 36, t), lerp(2, 9, t));
};

const SQUAT_POINTS = [
  "Stopa cała na podłodze, sztanga nad środkiem stopy przez cały ruch.",
  "Kolana idą w kierunku palców, biodro w tył i w dół.",
  "Na dole biodro poniżej górnej krawędzi kolana.",
  "Wstajesz barkami i biodrami naraz, bez wypychania bioder pierwszych.",
];

const BENCH_POINTS = [
  "Łopatki ściągnięte, łuk w odcinku piersiowym, pośladki na ławce.",
  "Sztanga schodzi lekko ukośnie, na dół mostka.",
  "Łokcie pod sztangą, przedramiona pionowo w dolnej pozycji.",
  "Wyciskasz w górę i lekko w stronę twarzy, nad barki.",
];

const DEADLIFT_POINTS = [
  "Sztanga nad środkiem stopy, przy piszczelach.",
  "Barki lekko przed sztangą, plecy neutralnie, napięte najszersze.",
  "Pchasz podłogę nogami, sztanga sunie po nogach.",
  "Wyprost bioder i kolan razem na górze, bez odchylania się w tył.",
];

const MOVES: Record<string, Move> = {
  squat: {
    id: "squat",
    kind: "squat",
    pose: squat(),
    start: 0,
    steps: [
      { to: 0, ms: 700 },
      { to: 1, ms: 1600, label: "w dół" },
      { to: 1, ms: 250 },
      { to: 0, ms: 1200, label: "w górę" },
    ],
    points: SQUAT_POINTS,
  },
  squatPause: {
    id: "squatPause",
    kind: "squat",
    pose: squat(),
    start: 0,
    steps: [
      { to: 0, ms: 700 },
      { to: 1, ms: 1600, label: "w dół" },
      { to: 1, ms: 2000, label: "pauza 2 s" },
      { to: 0, ms: 1200, label: "w górę" },
    ],
    points: ["2 s w dole bez rozluźnienia, potem mocno w górę.", ...SQUAT_POINTS.slice(0, 3)],
  },
  squatTempo: {
    id: "squatTempo",
    kind: "squat",
    pose: squat(),
    start: 0,
    steps: [
      { to: 0, ms: 700 },
      { to: 1, ms: 3000, label: "3 s w dół" },
      { to: 1, ms: 1000, label: "1 s pauzy" },
      { to: 0, ms: 1000, label: "dynamicznie w górę" },
    ],
    points: ["Tempo 3-1-0: 3 s w dół, 1 s pauzy, w górę bez zwłoki.", ...SQUAT_POINTS.slice(0, 3)],
  },
  squatPins: {
    id: "squatPins",
    kind: "squat",
    pose: squat(),
    start: 0,
    pins: 1,
    steps: [
      { to: 0, ms: 700 },
      { to: 1, ms: 1600, label: "siad na piny" },
      { to: 1, ms: 1200, label: "zatrzymanie" },
      { to: 0, ms: 1200, label: "w górę bez odbicia" },
    ],
    points: [
      "Piny na wysokości zawodniczej głębokości.",
      "Sztanga zatrzymuje się na pinach, bez odbicia, napięcie zostaje.",
      ...SQUAT_POINTS.slice(0, 2),
    ],
  },
  bench: {
    id: "bench",
    kind: "bench",
    bench: true,
    pose: bench(),
    start: 0,
    steps: [
      { to: 0, ms: 700 },
      { to: 1, ms: 1500, label: "w dół" },
      { to: 1, ms: 1000, label: "pauza na klatce" },
      { to: 0, ms: 1100, label: "w górę" },
    ],
    points: ["Pauza: sztanga nieruchomo na klatce, potem wyciskasz.", ...BENCH_POINTS],
  },
  benchTouchAndGo: {
    id: "benchTouchAndGo",
    kind: "bench",
    bench: true,
    pose: bench(),
    start: 0,
    steps: [
      { to: 0, ms: 600 },
      { to: 1, ms: 1300, label: "w dół" },
      { to: 1, ms: 120 },
      { to: 0, ms: 1100, label: "od razu w górę" },
    ],
    points: ["Dotyk klatki i od razu w górę, bez odbijania.", ...BENCH_POINTS],
  },
  benchPause3: {
    id: "benchPause3",
    kind: "bench",
    bench: true,
    pose: bench(),
    start: 0,
    steps: [
      { to: 0, ms: 700 },
      { to: 1, ms: 1500, label: "w dół" },
      { to: 1, ms: 3000, label: "pauza 3 s" },
      { to: 0, ms: 1100, label: "w górę" },
    ],
    points: ["3 s pauzy na klatce: cierpliwość i ustawienie.", ...BENCH_POINTS.slice(0, 3)],
  },
  larsen: {
    id: "larsen",
    kind: "bench",
    bench: true,
    pose: bench({ legsUp: true }),
    start: 0,
    steps: [
      { to: 0, ms: 700 },
      { to: 1, ms: 1500, label: "w dół" },
      { to: 1, ms: 1000, label: "pauza 1 s" },
      { to: 0, ms: 1100, label: "w górę" },
    ],
    points: [
      "Nogi proste w powietrzu: bez napędu z nóg.",
      "Pośladki na ławce przez cały ruch.",
      ...BENCH_POINTS.slice(1, 3),
    ],
  },
  spoto: {
    id: "spoto",
    kind: "bench",
    bench: true,
    pose: bench({ stopAbove: 3 }),
    start: 0,
    steps: [
      { to: 0, ms: 700 },
      { to: 1, ms: 1500, label: "w dół" },
      { to: 1, ms: 1000, label: "stop nad klatką" },
      { to: 0, ms: 1100, label: "w górę" },
    ],
    points: [
      "Zatrzymaj sztangę 1–2 cm nad klatką na 1 s, bez dotykania.",
      ...BENCH_POINTS.slice(0, 3),
    ],
  },
  closeGrip: {
    id: "closeGrip",
    kind: "bench",
    bench: true,
    pose: bench(),
    start: 0,
    steps: [
      { to: 0, ms: 700 },
      { to: 1, ms: 1500, label: "w dół" },
      { to: 1, ms: 1000, label: "pauza 1 s" },
      { to: 0, ms: 1100, label: "w górę" },
    ],
    points: [
      "Chwyt na szerokość barków, łokcie bliżej tułowia.",
      "Pauza 1 s na klatce, potem wyprost tricepsami.",
      ...BENCH_POINTS.slice(0, 2),
    ],
  },
  deadlift: {
    id: "deadlift",
    kind: "hinge",
    pose: deadlift(),
    start: 0,
    steps: [
      { to: 0, ms: 900, label: "ustawienie" },
      { to: 1, ms: 1800, label: "ciąg" },
      { to: 1, ms: 600, label: "wyprost" },
      { to: 0, ms: 1400, label: "odłożenie" },
    ],
    points: DEADLIFT_POINTS,
  },
  deadliftPause: {
    id: "deadliftPause",
    kind: "hinge",
    pose: deadlift(),
    start: 0,
    steps: [
      { to: 0, ms: 900, label: "ustawienie" },
      { to: 0.28, ms: 900, label: "do kolan" },
      { to: 0.28, ms: 2000, label: "pauza 2 s pod kolanem" },
      { to: 1, ms: 1200, label: "dokończ" },
      { to: 1, ms: 500 },
      { to: 0, ms: 1400, label: "odłożenie" },
    ],
    points: [
      "2 s zatrzymania tuż pod kolanem, sztanga przy nogach.",
      ...DEADLIFT_POINTS.slice(1),
    ],
  },
  rdl: {
    id: "rdl",
    kind: "hinge",
    pose: rdl,
    start: 0,
    steps: [
      { to: 0, ms: 800 },
      { to: 1, ms: 2000, label: "biodra w tył" },
      { to: 1, ms: 300 },
      { to: 0, ms: 1400, label: "w górę" },
    ],
    points: [
      "Kolana lekko ugięte i nieruchome, biodra w tył.",
      "Sztanga przy nogach, plecy neutralnie.",
      "W dół do mocnego rozciągnięcia dwugłowych, bez odkładania.",
    ],
  },
};

const BY_NAME: Record<string, string> = {
  Przysiad: "squat",
  "Przysiad z pauzą 2 s": "squatPause",
  "Przysiad tempo 3-1-0": "squatTempo",
  "Przysiad z pinów": "squatPins",
  "Wyciskanie leżąc (pauza)": "bench",
  "Wyciskanie leżąc T&G": "benchTouchAndGo",
  "Wyciskanie z pauzą 3 s": "benchPause3",
  "Larsen press": "larsen",
  "Spoto press": "spoto",
  "Wyciskanie wąskim chwytem": "closeGrip",
  "Martwy ciąg": "deadlift",
  "Martwy ciąg z pauzą pod kolanem": "deadliftPause",
  "Rumuński martwy ciąg (RDL)": "rdl",
};

/** Animacja dla ćwiczenia z planu albo null (np. akcesoria, na razie bez animacji). */
export function moveFor(name: string): Move | null {
  const id = BY_NAME[name];
  return id ? MOVES[id] : null;
}

export function cycleMs(move: Move): number {
  return move.steps.reduce((sum, s) => sum + s.ms, 0);
}

/** Postęp ruchu i opis chwili w czasie `t` (ms, zapętlone). */
export function progressAt(move: Move, t: number): { progress: number; label: string | null } {
  const total = cycleMs(move);
  let time = ((t % total) + total) % total;
  let from = move.start;
  let label: string | null = null;
  for (const step of move.steps) {
    if (time < step.ms) {
      const progress = step.to === from ? from : lerp(from, step.to, time / step.ms);
      return { progress, label: step.label ?? label };
    }
    time -= step.ms;
    from = step.to;
    label = step.label ?? null;
  }
  return { progress: from, label: null };
}
