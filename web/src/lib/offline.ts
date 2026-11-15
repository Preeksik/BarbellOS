/**
 * Trwała kolejka zapisów offline (dokumentacja 3.6, wymóg twardy z AGENTS.md).
 *
 * 1. Stan TanStack Query jest utrwalany w IndexedDB, więc wstrzymane zapisy przeżywają
 *    ubicie aplikacji przez iOS.
 * 2. Każdy zapis, który może trafić do kolejki, ma `mutationKey` i funkcję zarejestrowaną
 *    tutaj przez `setMutationDefaults`. Po restarcie aplikacji nie istnieje już komponent,
 *    który zapis wywołał, więc funkcja musi być znana globalnie.
 * 3. Po odtworzeniu stanu wywoływane jest `resumeAfterRestore`.
 * 4. Endpointy zapisu są idempotentne (PUT z identyfikatorem nadanym na telefonie).
 */

import { type Mutation, QueryClient } from "@tanstack/react-query";
import type { PersistedClient, Persister } from "@tanstack/react-query-persist-client";
import { del, get, set } from "idb-keyval";
import {
  ApiError,
  type Food,
  type FoodUpdateBody,
  NetworkError,
  type Probe,
  api,
} from "./api";

const IDB_KEY = "barbellos-query-client";
// Zwiększ po zmianie kształtu odpowiedzi API: stara kopia w telefonie zostanie odrzucona
// (razem z kolejką niewysłanych zapisów, więc nie zmieniaj bez potrzeby).
const CACHE_VERSION = "2";
const THIRTY_DAYS_MS = 1000 * 60 * 60 * 24 * 30;

export const persister: Persister = {
  persistClient: (client: PersistedClient) => set(IDB_KEY, client),
  restoreClient: () => get<PersistedClient>(IDB_KEY),
  removeClient: () => del(IDB_KEY),
};

function retryPolicy(failureCount: number, error: unknown): boolean {
  if (error instanceof NetworkError) return true; // czeka w kolejce do powrotu połączenia
  if (error instanceof ApiError && error.status >= 500) return failureCount < 5; // np. zimny start
  return false; // błąd 4xx nie naprawi się sam
}

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: { gcTime: THIRTY_DAYS_MS, staleTime: 30_000, retry: 1 },
    mutations: { retry: retryPolicy, gcTime: THIRTY_DAYS_MS },
  },
});

export const persistOptions = {
  persister,
  // Domyślne 24 h skasowałoby kolejkę po dniu bez otwierania aplikacji.
  maxAge: THIRTY_DAYS_MS,
  buster: CACHE_VERSION,
  dehydrateOptions: {
    // Domyślnie utrwalane są tylko zapisy już wstrzymane. Utrwalamy każdy niedokończony,
    // żeby nie zgubić zapisu, który był w trakcie wysyłki w chwili zamknięcia aplikacji.
    shouldDehydrateMutation: (mutation: Mutation) => mutation.state.status === "pending",
  },
};

/** Wznawia zapisy odtworzone z IndexedDB: wstrzymane oraz przerwane w trakcie wysyłki. */
export async function resumeAfterRestore(): Promise<void> {
  const interrupted = queryClient
    .getMutationCache()
    .getAll()
    .filter((m) => m.state.status === "pending" && !m.state.isPaused);
  await Promise.all(interrupted.map((m) => m.continue().catch(() => undefined)));
  await queryClient.resumePausedMutations();
}

// ---------- rejestr zapisów, które mogą trafić do kolejki ----------

export const mutationKeys = {
  probe: ["probe"] as const,
  foodUpdate: ["food", "update"] as const,
  foodVerify: ["food", "verify"] as const,
};

export interface ProbeInput {
  id: string;
  client_created_at: string;
  note: string;
}

queryClient.setMutationDefaults(mutationKeys.probe, {
  mutationFn: ({ id, ...body }: ProbeInput) => api.put<Probe>(`/api/probe/${id}`, body),
  onSuccess: () => queryClient.invalidateQueries({ queryKey: ["probes"] }),
});

// ---------- produkty ----------

export const foodQueryKey = (barcode: string) => ["food", barcode] as const;

export interface FoodUpdateInput {
  id: number;
  barcode: string;
  body: FoodUpdateBody;
}

export interface FoodVerifyInput {
  id: number;
  barcode: string;
}

queryClient.setMutationDefaults(mutationKeys.foodUpdate, {
  mutationFn: ({ id, body }: FoodUpdateInput) => api.put<Food>(`/api/foods/${id}`, body),
  // Poprawione wartości widać od razu, także bez sieci. Serwer potwierdza je po wysłaniu.
  onMutate: ({ barcode, body }: FoodUpdateInput) => {
    queryClient.setQueryData<Food>(
      foodQueryKey(barcode),
      (old) =>
        old && {
          ...old,
          ...body,
          macro_source: "user",
          verified_at: new Date().toISOString(),
          warnings: [],
        },
    );
  },
  onSuccess: (food: Food, { barcode }: FoodUpdateInput) => {
    queryClient.setQueryData(foodQueryKey(barcode), food);
  },
  // Serwer odrzucił zapis: wracamy do tego, co naprawdę jest w bazie.
  onError: (_error: Error, { barcode }: FoodUpdateInput) =>
    queryClient.invalidateQueries({ queryKey: foodQueryKey(barcode) }),
});

queryClient.setMutationDefaults(mutationKeys.foodVerify, {
  mutationFn: ({ id }: FoodVerifyInput) => api.post<Food>(`/api/foods/${id}/verify`),
  onSuccess: (food: Food, { barcode }: FoodVerifyInput) => {
    queryClient.setQueryData(foodQueryKey(barcode), food);
  },
});
