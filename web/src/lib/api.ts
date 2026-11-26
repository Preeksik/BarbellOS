/** Cienka warstwa nad fetch: ten sam adres co frontend, ciasteczko sesji, czytelne błędy. */

import { reportNetworkFailure } from "./connectivity";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

/** Żądanie nie dotarło do serwera (brak zasięgu, Wi-Fi bez internetu). */
export class NetworkError extends Error {}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  // Plik (np. zdjęcie etykiety) idzie w treści żądania bez opakowania; reszta jako JSON.
  const isFile = body instanceof Blob;
  const contentType = isFile ? body.type || "application/octet-stream" : "application/json";
  let response: Response;
  try {
    response = await fetch(path, {
      method,
      credentials: "same-origin",
      headers: body === undefined ? undefined : { "Content-Type": contentType },
      body: body === undefined ? undefined : isFile ? body : JSON.stringify(body),
    });
  } catch {
    reportNetworkFailure();
    throw new NetworkError("Brak połączenia z serwerem.");
  }
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const data = await response.json();
      if (typeof data?.detail === "string") detail = data.detail;
    } catch {
      /* odpowiedź bez JSON-a: zostaje tekst statusu */
    }
    throw new ApiError(response.status, detail);
  }
  return response.status === 204 ? (undefined as T) : ((await response.json()) as T);
}

export const api = {
  get: <T>(path: string) => request<T>("GET", path),
  post: <T>(path: string, body?: unknown) => request<T>("POST", path, body),
  put: <T>(path: string, body?: unknown) => request<T>("PUT", path, body),
  delete: (path: string) => request<void>("DELETE", path),
};

// ---------- typy odpowiedzi (docelowo generowane z /api/openapi.json) ----------

export interface Session {
  authenticated: boolean;
  auth_required: boolean;
}

export type MacroKey =
  | "kcal"
  | "protein_g"
  | "fat_g"
  | "sat_fat_g"
  | "carbs_g"
  | "sugars_g"
  | "fiber_g"
  | "salt_g";

/** Wartości na 100 g lub 100 ml. `null` to brak danych, nie zero. */
export type Per100 = Record<MacroKey, number | null>;

export interface Food {
  id: number;
  barcode: string | null;
  name: string;
  brand: string | null;
  serving_g: number | null;
  unit: "g" | "ml";
  origin: string;
  macro_source: string;
  source_updated_at: string | null;
  verified_at: string | null;
  per_100: Per100;
  micros: { nutrient_id: string; amount_per_100g: number; source: string }[];
  warnings: string[];
  cached: boolean;
  favorite: boolean;
  /** Rekord tabeli USDA, z którego są mikroskładniki (etap 6). */
  fdc_id: number | null;
  fdc_description: string | null;
}

export interface FoodUpdateBody {
  name: string;
  brand: string | null;
  serving_g: number | null;
  unit: "g" | "ml";
  per_100: Per100;
}

/** Własny produkt dla kodu spoza źródeł. `origin`: wpisany ręcznie albo odczytany z etykiety. */
export interface FoodCreateBody extends FoodUpdateBody {
  origin: "user" | "ai_label";
}

/** Szkic ze zdjęcia etykiety. `null` w wartości oznacza „nie odczytano". */
export interface LabelDraft {
  name: string | null;
  brand: string | null;
  serving_g: number | null;
  unit: "g" | "ml" | null;
  per_100: Per100;
  warnings: string[];
}

export type MealSlot ="breakfast" | "second_breakfast" | "lunch" | "snack" | "dinner";

/** Wpis dziennika. `values` to wartości dla tej porcji, zamrożone w chwili dodania. */
export interface DiaryEntry {
  id: string;
  date: string;
  meal_slot: MealSlot;
  food_id: number | null;
  food_name: string;
  amount: number;
  unit: "g" | "ml";
  values: Per100;
  /** `estimated` = szacunek AI (składnika nie było w bazie); inaczej źródło produktu. */
  macro_source?: string | null;
  source: string;
  ai_run_id?: number | null;
  created_at: string;
}

export type MacroTotals = Record<MacroKey, number>;

/** Suplement na dany dzień (`GET /api/supplements/day/{dzień}`, 23.11.2026). */
export interface SupplementItem {
  id: string;
  name: string;
  dose: string | null;
  taken: boolean;
  /** Dni z rzędu do tego dnia (bez dziś, jeśli jeszcze nie wzięty). */
  streak: number;
  /** Ostatnie 7 dni, od najstarszego. */
  last7: boolean[];
  /** Skład jednej dawki w jednostkach słownika (mg albo µg). */
  micros: { nutrient_id: string; amount: number }[];
}

export interface SupplementDay {
  date: string;
  supplements: SupplementItem[];
  taken_ids: string[];
  yesterday_ids: string[];
}

/** Posiłek z ostatnich dwóch tygodni do skopiowania (`GET /api/diary/recent-meals/{dzień}`). */
export interface RecentMeal {
  date: string;
  meal_slot: MealSlot;
  kcal: number;
  entries: DiaryEntry[];
}

export interface DiaryDay {
  date: string;
  entries: DiaryEntry[];
  totals: MacroTotals;
  by_slot: Partial<Record<MealSlot, MacroTotals>>;
}

// ---------- cele dzienne ----------

/** target: cel, min: co najmniej, max: najwyżej. */
export type GoalKind = "target" | "min" | "max";

export interface Targets {
  date: string;
  /** Od kiedy obowiązują; `null`, gdy celów jeszcze nie ustawiono. */
  date_from: string | null;
  /** `null` = bez celu. */
  goals: Per100;
  kinds: Record<MacroKey, GoalKind>;
}

// ---------- wyszukiwanie ----------

export interface OffHit {
  barcode: string;
  name: string;
  brand: string | null;
  kcal: number | null;
  unit: "g" | "ml";
}

/** Produkt podstawowy z tabel USDA w wyszukiwarce (polska nazwa nadana przez AI). */
export interface GenericHit {
  fdc_id: number;
  name: string;
  description: string;
  kcal: number; // na 100 g
  protein_g: number | null;
  fat_g: number | null;
  carbs_g: number | null;
}

export interface RecentFood {
  food: Food;
  last_amount: number;
  last_slot: MealSlot;
}

// ---------- zapisane posiłki ----------

export interface MealItem {
  food_id: number;
  food_name: string;
  amount: number;
  unit: "g" | "ml";
  per_100: Per100;
}

export interface Meal {
  id: string;
  name: string;
  items: MealItem[];
  totals: MacroTotals;
}

export interface HealthTypeSummary {
  type: string;
  count: number;
  last_starts_at: string | null;
  last_value: number | null;
  last_label: string | null;
  unit: string | null;
  source: string | null;
  last_received_at: string | null;
}

export interface Probe {
  id: string;
  client_created_at: string;
  received_at: string;
  note: string | null;
}

// ---------- profil ----------

export type Sex = "male" | "female";
export type Lifestyle = "sitting" | "mixed" | "standing" | "physical";
export type Goal = "lose" | "maintain" | "gain";

export interface Profile {
  sex: Sex;
  birth_date: string;
  height_cm: number;
  weight_kg: number;
  lifestyle: Lifestyle;
  steps_per_day: number;
  strength_sessions_week: number;
  /** Długość jednej sesji w minutach. */
  strength_minutes: number;
  cardio_minutes_week: number;
  goal: Goal;
  pace_kg_week: number;
  /** `null` = domyślne dla celu. */
  protein_g_per_kg: number | null;
}

/** Propozycja policzona na serwerze (`backend/app/core/profile.py`). */
export interface Plan {
  age: number;
  bmr: number;
  tdee: number;
  /** Z czego składa się zapotrzebowanie: przemiana, tryb życia, kroki… */
  parts: { key: string; label: string; kcal: number; detail: string }[];
  kcal: number;
  adjustment: number;
  pace_kg_week: number;
  protein_g_per_kg: number;
  goals: Per100;
  notes: string[];
  warnings: string[];
}

export interface ProfileResponse {
  profile: Profile | null;
  plan: Plan | null;
}

// ---------- AI w diecie (etap 2) ----------

export type Confidence = "low" | "medium" | "high";

export interface DraftItem {
  name: string;
  category: string;
  grams: number;
  grams_low: number;
  grams_high: number;
  confidence: Confidence;
  /** Produkt z bazy dobrany przez serwer; `null` = szacunek modelu. */
  match: Food | null;
  /** Inne produkty z bazy do wyboru. */
  candidates: Food[];
  /** Szacunek modelu na 100 g (kcal, B, T, W; reszta `null`). */
  estimate_per_100: Per100;
  /** Szacunek mikroskładników na 100 g ({id: ilość}). */
  estimate_micros: Record<string, number>;
  values: Per100;
}

export interface MealDraft {
  ai_run_id: number;
  source: "photo" | "text";
  items: DraftItem[];
  notes: string | null;
  warnings: string[];
}

export interface AiUsage {
  month: string;
  runs: number;
  cost_usd: number;
  unpriced_runs: number;
  by_task: {
    task: string;
    runs: number;
    failed: number;
    input_tokens: number;
    output_tokens: number;
    cost_usd: number;
  }[];
}

// ---------- mikroskładniki i tydzień (etap 6) ----------

export interface Nutrient {
  id: string;
  name_pl: string;
  unit: string;
  group: "vitamin" | "mineral";
  /** Referencyjne spożycie z etykiet UE (RWS); sód: górna granica. */
  rda: number | null;
}

export interface FdcCandidate {
  fdc_id: number;
  description: string;
  data_type: string;
  kcal: number | null;
  micros_count: number;
  score: number;
}

export interface FdcSearch {
  query: string;
  candidates: FdcCandidate[];
  suggested_id: number | null;
}

export interface MicroWeek {
  nutrient_id: string;
  name_pl: string;
  unit: string;
  group: "vitamin" | "mineral";
  rda: number | null;
  /** Średnio na dzień z jedzenia i suplementów. */
  avg_amount: number;
  /** W tym średnio na dzień z odhaczonych suplementów (24.11.2026). */
  supplement_amount: number;
  percent_rda: number | null;
  /** Część kalorii tygodnia z wpisów z danymi z tabel lub etykiet. */
  share_trusted: number;
  share_estimated: number;
  share_missing: number;
}

export interface Week {
  start: string;
  end: string;
  days: { date: string; entries: number; totals: MacroTotals }[];
  logged_days: number;
  average: MacroTotals | null;
  micros: MicroWeek[];
}

// ---------- trening (etap 4) ----------

/** Wpis jednego ćwiczenia sesji (jak w starym pliku planu: jeden na ćwiczenie). */
export interface TrainingEntry {
  kg: number | null;
  reps: number | null;
  rpe: number | null;
  done: boolean;
  ok: "y" | "n" | null;
}

export interface TrainingExercise {
  index: number;
  name: string;
  lift: "S" | "B" | "D" | null;
  kind: "sets" | "single" | "acc" | "att";
  tier: "main" | "var" | "acc";
  sets: number | null;
  reps: string | null;
  percent_tm: number | null;
  rpe: string | null;
  weight_hint: string | null;
  attempt: number | null;
  cue: string | null;
  load: number | null;
  plates: number[] | null;
  entry: TrainingEntry;
  e1rm: number | null;
  last: { kg: number; reps: number | null; rpe: number | null; date: string; gym: string } | null;
}

export type SessionStatus = "none" | "part" | "done";

export interface TrainingSession {
  key: string;
  code: string;
  title: string;
  date: string;
  minutes: number | null;
  days_before_meet: number | null;
  holiday: string | null;
  note: string | null;
  status: SessionStatus;
  gym: string | null;
  bodyweight: number | null;
  log_note: string | null;
  exercises: TrainingExercise[];
  /** Arkusz podejść (test, zawody). Brak w starszej kopii z pamięci telefonu. */
  sheet?: TrainingSheet | null;
}

export type Lift = "S" | "B" | "D";

export interface ThirdHint {
  kind: "failed" | "rules" | "need_rpe" | "limit" | "next";
  kg: number | null;
  rpe: number | null;
}

export interface TrainingSheet {
  context: "test" | "meet";
  lifts: {
    lift: Lift;
    max: number;
    from_singles: boolean;
    fallback_phase: number;
    first: number;
    second: number;
    third: [number, number];
    hint: ThirdHint;
  }[];
  best: Record<Lift, number | null>;
  total: number | null;
  gl: number | null;
  bodyweight: number;
}

export interface TrainingWeek {
  index: number;
  n: number;
  key: string;
  block_name: string;
  focus: string | null;
  start: string;
  end: string;
  repeat_of: number | null;
  phase: number;
  tm: Record<"S" | "B" | "D", number>;
  banner: { phase_name: string; suggestions: { lift: "S" | "B" | "D"; kg: number }[] } | null;
  sessions: TrainingSession[];
  gyms: string[];
}

export interface TrainingWeekSummary {
  index: number;
  n: number;
  key: string;
  block_name: string;
  plate: number | null;
  label: string | null;
  start: string;
  end: string;
  repeat_of: number | null;
  done: number;
  total: number;
  holidays?: string[];
}

export interface TrainingSeason {
  plan_name: string | null;
  headline: string | null;
  countdowns: { days: number; label: string }[];
  position: { week: number; day: number; rest: boolean } | null;
  current_week: number | null;
  weeks: TrainingWeekSummary[];
  /** Opisy części sezonu z pliku planu (np. jesień do testu). */
  groups?: { title: string; text: string; last_week: number | null }[];
}

// Teksty z pliku planu: akapity, listy (z pogrubionym początkiem) i tabele.
export interface NoteBlock {
  type: "p" | "list" | "table";
  text: string | null;
  items: { lead: string | null; text: string }[];
  head: string[];
  rows: string[][];
}

export interface NoteSection {
  title: string | null;
  blocks: NoteBlock[];
}

export interface TrainingMaxes {
  goals_title: string;
  goals_intro: NoteBlock[];
  goals: { label: string; S: number; B: number; D: number; total: number; gl: number; baseline: boolean }[];
  goals_after: NoteSection[];
  tm_intro: NoteBlock[];
  phases: {
    phase: number;
    name: string;
    first_week: number;
    last_week: number;
    start: string;
    total: number;
    lifts: { lift: Lift; value: number; default: number; manual: boolean; suggestion: number | null }[];
  }[];
  points: {
    date: string;
    lift: Lift;
    kg: number;
    rpe: number;
    e1rm: number;
    e1rm_rounded: number;
    kind: "single" | "att";
  }[];
  start_date: string;
  test_date: string | null;
  meet_date: string;
  meet_name: string;
}

export interface AttemptPlan {
  rows: {
    lift: Lift;
    max: number;
    from_singles: boolean;
    fallback_phase: number;
    first: number;
    second: number;
    third: [number, number];
  }[];
  total_first: number;
  total_second: number;
  total_third: [number, number];
  ladders: { lift: Lift; steps: [number, number][]; opener: number }[];
}

export interface StartCard {
  name: string;
  date: string;
  week_index: number | null;
  intro: NoteBlock[];
  after_table: NoteBlock[];
  after_ladder: NoteSection[];
  attempts: AttemptPlan;
}

export interface TrainingStart {
  test: StartCard | null;
  meet: StartCard;
  meet_default: boolean;
  meet_range: [string, string] | null;
  adjustment: string;
  results: {
    label: string;
    S: number | null;
    B: number | null;
    D: number | null;
    total: number | null;
    gl: number | null;
    baseline: boolean;
    empty: boolean;
  }[];
  results_note: NoteBlock[];
}

/** Sprzęt na siłowni: od niego zależą talerze na stronę sztangi. */
export interface TrainingEquipment {
  plates_25: boolean;
  collars: boolean;
  has_plan: boolean;
}

export interface TrainingImportResult {
  plan_name: string;
  weeks: number;
  sessions: number;
  imported_sessions: number;
  skipped: string[];
}
