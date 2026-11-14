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
  let response: Response;
  try {
    response = await fetch(path, {
      method,
      credentials: "same-origin",
      headers: body === undefined ? undefined : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
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
};

// ---------- typy odpowiedzi (docelowo generowane z /api/openapi.json) ----------

export interface Session {
  authenticated: boolean;
  auth_required: boolean;
}

export interface Food {
  id: number;
  barcode: string | null;
  name: string;
  brand: string | null;
  serving_g: number | null;
  origin: string;
  macro_source: string;
  per_100g: Record<string, number | null>;
  micros: { nutrient_id: string; amount_per_100g: number; source: string }[];
  cached: boolean;
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
