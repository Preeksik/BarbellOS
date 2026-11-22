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
  avg_amount: number;
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
