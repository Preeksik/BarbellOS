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
  source: string;
  created_at: string;
}

export type MacroTotals = Record<MacroKey, number>;

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
export type Activity = "sedentary" | "light" | "moderate" | "active" | "very_active";
export type Goal = "lose" | "maintain" | "gain";

export interface Profile {
  sex: Sex;
  birth_date: string;
  height_cm: number;
  weight_kg: number;
  activity: Activity;
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
