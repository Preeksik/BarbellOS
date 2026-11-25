/**
 * Ludzik do animacji techniki (25.11.2026): widok z boku, twarzą w prawo.
 *
 * Pozy nie są rysowane klatka po klatce. Liczy je prosta mechanika: kości mają stałą
 * długość, sztanga zostaje nad środkiem stopy, a stawy pośrednie (kolano, biodro, łokieć)
 * wyznacza kinematyka odwrotna dwóch kości. Dzięki temu ruch wygląda fizycznie spójnie
 * w każdym momencie, a warianty (pauza, tempo, piny) to tylko inny przebieg czasu.
 *
 * Jednostki ≈ centymetry, oś y w górę, podłoga na y = 0. To czysta prezentacja: żadnych
 * liczb treningowych tu nie liczymy (AGENTS.md, zasada 2).
 */

export interface Vec {
  x: number;
  y: number;
}

export const BODY = {
  shin: 42,
  thigh: 44,
  torso: 52,
  neck: 9,
  head: 10,
  upperArm: 31,
  forearm: 33, // do środka chwytu, z dłonią
  ankleHeight: 8,
  toe: 18,
  heel: 6,
} as const;

export const PLATE_RADIUS = 22.5; // talerz zawodniczy ma średnicę 45 cm

export interface Pose {
  toe: Vec;
  heel: Vec;
  ankle: Vec;
  knee: Vec;
  hip: Vec;
  shoulder: Vec;
  head: Vec;
  elbow: Vec;
  hand: Vec;
  bar: Vec | null;
}

export const vec = (x: number, y: number): Vec => ({ x, y });
const add = (a: Vec, b: Vec): Vec => vec(a.x + b.x, a.y + b.y);
const scale = (a: Vec, k: number): Vec => vec(a.x * k, a.y * k);
export const dist = (a: Vec, b: Vec): number => Math.hypot(b.x - a.x, b.y - a.y);
const deg = (d: number) => (d * Math.PI) / 180;
/** Kierunek pod kątem `angle` stopni od osi x (przeciwnie do wskazówek zegara). */
const dir = (angle: number): Vec => vec(Math.cos(deg(angle)), Math.sin(deg(angle)));

export const lerp = (a: number, b: number, t: number): number => a + (b - a) * t;

/** Gładkie przejście 0 → 1 (bez szarpnięcia na początku i końcu ruchu). */
export function smooth(t: number): number {
  const c = Math.min(1, Math.max(0, t));
  return c * c * (3 - 2 * c);
}

/**
 * Staw pośredni dwóch kości (np. kolano między kostką a biodrem). `bend` = 1 zgina
 * w lewo od kierunku a → cel, −1 w prawo. Za daleki cel: kości w jednej linii.
 */
export function twoBone(a: Vec, target: Vec, l1: number, l2: number, bend: 1 | -1): Vec {
  const d = Math.min(Math.max(dist(a, target), Math.abs(l1 - l2) + 1e-6), l1 + l2 - 1e-6);
  const base = Math.atan2(target.y - a.y, target.x - a.x);
  const inner = Math.acos((l1 * l1 + d * d - l2 * l2) / (2 * l1 * d));
  const angle = base + bend * inner;
  return add(a, vec(Math.cos(angle) * l1, Math.sin(angle) * l1));
}

/** Stopa na podłodze z kostką w `ankle`. */
function feet(ankle: Vec): Pick<Pose, "toe" | "heel"> {
  return { toe: vec(ankle.x + BODY.toe, 0), heel: vec(ankle.x - BODY.heel, 0) };
}

/** Głowa nad barkami, w przedłużeniu tułowia, lekko do przodu (neutralna szyja). */
function headFrom(hip: Vec, shoulder: Vec, forward = 0.35): Vec {
  const along = scale(vec(shoulder.x - hip.x, shoulder.y - hip.y), 1 / BODY.torso);
  const ahead = vec(along.y, -along.x); // prostopadle, w stronę twarzy
  return add(shoulder, add(scale(along, BODY.neck + BODY.head), scale(ahead, forward * BODY.head)));
}

export const MIDFOOT_X = 100;
const ANKLE = vec(MIDFOOT_X - 6, BODY.ankleHeight);

/**
 * Przysiad ze sztangą na plecach. `depth`: 0 stoisz, 1 pełny dół (biodro poniżej kolana).
 * Kolana idą do przodu, biodro w tył, a pochylenie tułowia wynika z równowagi:
 * sztanga zostaje nad środkiem stopy.
 */
export function squatPose(depth: number, opts: { platform?: number } = {}): Pose {
  const lift = opts.platform ?? 0;
  const ankle = vec(ANKLE.x, ANKLE.y + lift);
  const shin = lerp(4, 40, depth); // od pionu, do przodu
  const knee = add(ankle, scale(vec(Math.sin(deg(shin)), Math.cos(deg(shin))), BODY.shin));
  const thigh = lerp(96, 195, depth); // od osi x: 90 pionowo w górę, 180 poziomo w tył
  const hip = add(knee, scale(dir(thigh), BODY.thigh));
  // Sztanga na górze pleców leży ok. 5 cm za barkiem; ona ma być nad środkiem stopy.
  const barBehind = 5;
  const dx = Math.min(BODY.torso, Math.max(-BODY.torso, MIDFOOT_X + barBehind - hip.x));
  const torsoAngle = Math.acos(dx / BODY.torso);
  const shoulder = add(hip, vec(dx, Math.sin(torsoAngle) * BODY.torso));
  const along = scale(vec(shoulder.x - hip.x, shoulder.y - hip.y), 1 / BODY.torso);
  const back = vec(-along.y, along.x); // prostopadle do tułowia, w stronę pleców
  const bar = add(shoulder, add(scale(back, barBehind), scale(along, -2)));
  const hand = add(bar, scale(back, -1));
  // Ręce na sztandze idą szeroko w bok, poza płaszczyznę widoku: z boku widać łokieć
  // pod barkiem i za nim, a ramię krótsze niż w rzeczywistości.
  const elbow = add(shoulder, add(scale(along, -20), scale(back, 9)));
  return {
    ...feet(ankle),
    ankle,
    knee,
    hip,
    shoulder,
    head: headFrom(hip, shoulder),
    elbow,
    hand,
    bar,
  };
}

/** Wysokość sztangi w rękach, gdy stoisz wyprostowany. */
export const LOCKOUT_BAR_Y =
  BODY.ankleHeight + BODY.shin + BODY.thigh + BODY.torso - BODY.upperArm - BODY.forearm;

/**
 * Martwy ciąg i RDL: sztanga w prostych rękach, na pionowej linii nad środkiem stopy.
 * `barY` to wysokość sztangi; biodro wyznacza kinematyka między kolanem a barkami.
 * `shin` to pochylenie piszczeli od pionu (kolana nad sztangą na starcie, potem w tył).
 */
export function hingePose(barY: number, shin: number, opts: { platform?: number } = {}): Pose {
  const lift = opts.platform ?? 0;
  const ankle = vec(ANKLE.x, ANKLE.y + lift);
  const bar = vec(MIDFOOT_X + 1, barY + lift);
  const knee = add(ankle, scale(vec(Math.sin(deg(shin)), Math.cos(deg(shin))), BODY.shin));
  const shoulderTarget = vec(bar.x + 3, bar.y + BODY.upperArm + BODY.forearm);
  // Biodro za linią kolano → bark (zgięcie w lewo, patrząc od kolana w górę).
  const hip = twoBone(knee, shoulderTarget, BODY.thigh, BODY.torso, 1);
  const along = scale(vec(shoulderTarget.x - hip.x, shoulderTarget.y - hip.y), 1 / dist(hip, shoulderTarget));
  const shoulder = add(hip, scale(along, BODY.torso));
  const hand = vec(bar.x, bar.y);
  const elbow = twoBone(shoulder, hand, BODY.upperArm, BODY.forearm, -1);
  return {
    ...feet(ankle),
    ankle,
    knee,
    hip,
    shoulder,
    head: headFrom(hip, shoulder, 0.6),
    elbow,
    hand,
    bar,
  };
}

export const BENCH = { top: 44, from: 40, to: 168, pad: 8 } as const;

/**
 * Wyciskanie leżąc: barki i biodra na ławce, łuk w odcinku piersiowym, stopy na podłodze
 * (w Larsenie nogi w powietrzu). `depth`: 0 wyprost, 1 sztanga na klatce. `stopAbove`
 * zatrzymuje sztangę kilka cm nad klatką (spoto). Tor sztangi lekko ukośny, jak w zawodach.
 */
export function benchPose(
  depth: number,
  opts: { legsUp?: boolean; stopAbove?: number } = {},
): Pose {
  const bodyY = BENCH.top + BENCH.pad;
  const hip = vec(92, bodyY);
  const shoulder = add(hip, scale(dir(7), BODY.torso)); // łuk: klatka wyżej niż biodra
  const head = vec(shoulder.x + BODY.neck + BODY.head, bodyY + 1);
  const top = vec(shoulder.x - 1, shoulder.y + BODY.upperArm + BODY.forearm - 2);
  const chest = vec(shoulder.x - 13, shoulder.y + 12 + (opts.stopAbove ?? 0));
  const bar = vec(lerp(top.x, chest.x, smooth(depth) ** 0.8), lerp(top.y, chest.y, depth));
  const hand = bar;
  const elbow = twoBone(shoulder, hand, BODY.upperArm, BODY.forearm, 1);
  let ankle: Vec;
  let knee: Vec;
  if (opts.legsUp) {
    // Larsen: nogi proste w powietrzu, bez napędu z nóg.
    ankle = add(hip, scale(dir(188), BODY.thigh + BODY.shin));
    knee = add(hip, scale(dir(188), BODY.thigh));
  } else {
    ankle = vec(hip.x - 40, BODY.ankleHeight);
    knee = twoBone(hip, ankle, BODY.thigh, BODY.shin, -1); // kolano w górze, piszczel pionowo
  }
  const toe = opts.legsUp ? add(ankle, scale(dir(100), BODY.toe)) : vec(ankle.x - BODY.toe, 0);
  const heel = opts.legsUp ? add(ankle, scale(dir(280), BODY.heel)) : vec(ankle.x + BODY.heel, 0);
  return { toe, heel, ankle, knee, hip, shoulder, head, elbow, hand, bar };
}
