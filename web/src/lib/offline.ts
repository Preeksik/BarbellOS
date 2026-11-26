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

import {
  type Mutation,
  type Query,
  QueryClient,
  defaultShouldDehydrateQuery,
} from "@tanstack/react-query";
import type { PersistedClient, Persister } from "@tanstack/react-query-persist-client";
import { del, get, set } from "idb-keyval";
import {
  ApiError,
  type DiaryDay,
  type DiaryEntry,
  type Food,
  type FoodCreateBody,
  type FoodUpdateBody,
  type Meal,
  NetworkError,
  type Per100,
  type Probe,
  type Profile,
  type ProfileResponse,
  type SupplementDay,
  type Targets,
  type TrainingEntry,
  type TrainingEquipment,
  type TrainingWeek,
  api,
} from "./api";
import { emptyDay, withEntry, withoutEntry } from "./diary";
import { likeYesterday, withTaken } from "./supplements";

const IDB_KEY = "barbellos-query-client";
// Zwiększ po zmianie kształtu odpowiedzi API: stara kopia w telefonie zostanie odrzucona
// (razem z kolejką niewysłanych zapisów, więc nie zmieniaj bez potrzeby).
// 3: produkt ma pole `favorite` (etap 1, krok 5).
// 4: profil ma tryb życia, kroki i treningi zamiast jednej „aktywności”.
// 5: wpis dziennika ma źródło wartości i powiązanie z wywołaniem AI (etap 2).
// 6: produkt ma dopasowanie do tabeli USDA (etap 6).
const CACHE_VERSION = "7"; // 7: składniki suplementów w tygodniu (24.11.2026)
const DAY_MS = 1000 * 60 * 60 * 24;
const THIRTY_DAYS_MS = 30 * DAY_MS;
// Czas trzymania nieużywanych danych w pamięci. Przeglądarka liczy opóźnienia na 32 bitach:
// powyżej ok. 24,8 dnia licznik się przepełnia i uruchamia natychmiast. Przy 30 dniach
// zeskanowany produkt znikał z pamięci zaraz po zamknięciu karty i bez sieci nie dało się
// go otworzyć ponownie.
export const GC_TIME_MS = 20 * DAY_MS;

export const persister: Persister = {
  persistClient: (client: PersistedClient) => set(IDB_KEY, client),
  restoreClient: () => get<PersistedClient>(IDB_KEY),
  removeClient: () => del(IDB_KEY),
};

function retryPolicy(failureCount: number, error: unknown): boolean {
  if (error instanceof NetworkError) return true; // czeka w kolejce do powrotu połączenia
  if (error instanceof ApiError && error.status >= 500) return failureCount < 5; // np. zimny start
  if (error instanceof ApiError && error.status === 401) {
    // Sesja wygasła, gdy zapis czekał w kolejce. Nie wolno go zgubić: ekran logowania
    // pojawia się po odświeżeniu „me", a zapis ponawia się do skutku po zalogowaniu.
    void queryClient.invalidateQueries({ queryKey: ["me"] });
    return true;
  }
  return false; // błąd 4xx nie naprawi się sam
}

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: { gcTime: GC_TIME_MS, staleTime: 30_000, retry: 1 },
    mutations: { retry: retryPolicy, gcTime: GC_TIME_MS },
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
    // Dane nieodświeżane od 30 dni nie wracają do pamięci telefonu, żeby kopia nie rosła
    // bez końca (każdy zeskanowany produkt i każdy oglądany dzień to osobny wpis).
    shouldDehydrateQuery: (query: Query) =>
      defaultShouldDehydrateQuery(query) && Date.now() - query.state.dataUpdatedAt < THIRTY_DAYS_MS,
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
  foodCreate: ["food", "create"] as const,
  foodCustom: ["food", "custom"] as const,
  foodFavorite: ["food", "favorite"] as const,
  diaryPut: ["diary", "put"] as const,
  diaryDelete: ["diary", "delete"] as const,
  targetsPut: ["targets", "put"] as const,
  mealPut: ["meals", "put"] as const,
  mealDelete: ["meals", "delete"] as const,
  profilePut: ["profile", "put"] as const,
  supplementPut: ["supplements", "put"] as const,
  supplementDelete: ["supplements", "delete"] as const,
  supplementDay: ["supplements", "day"] as const,
  supplementYesterday: ["supplements", "yesterday"] as const,
  trainingEntry: ["training", "entry"] as const,
  trainingSession: ["training", "session"] as const,
  trainingEquipment: ["training", "equipment"] as const,
  trainingTm: ["training", "tm"] as const,
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

/** Produkt otwarty po kodzie kreskowym (skan, wynik z Open Food Facts). */
export const foodQueryKey = (barcode: string) => ["food", barcode] as const;
/** Produkt otwarty z listy (wyszukiwarka, ostatnie, ulubione), także bez kodu. */
export const foodByIdKey = (id: number) => ["food", "id", id] as const;

/** Listy produktów, które trzeba odświeżyć po zmianie produktu. */
const FOOD_LISTS = [["search"], ["recent"], ["favorites"], ["meals"]] as const;

function refreshFoodLists(): void {
  for (const queryKey of FOOD_LISTS) void queryClient.invalidateQueries({ queryKey });
}

/** Zmienia produkt we wszystkich miejscach pamięci, gdzie jest trzymany. */
function updateFood(id: number, barcode: string | null, change: (food: Food) => Food): void {
  const apply = (old: Food | undefined) => old && change(old);
  queryClient.setQueryData<Food>(foodByIdKey(id), apply);
  if (barcode) queryClient.setQueryData<Food>(foodQueryKey(barcode), apply);
}

/** Zapisuje produkt z serwera we wszystkich miejscach pamięci (np. po dopasowaniu USDA). */
export function storeFood(food: Food): void {
  queryClient.setQueryData(foodByIdKey(food.id), food);
  if (food.barcode) queryClient.setQueryData(foodQueryKey(food.barcode), food);
}

export interface FoodUpdateInput {
  id: number;
  barcode: string | null;
  body: FoodUpdateBody;
}

export interface FoodVerifyInput {
  id: number;
  barcode: string | null;
}

queryClient.setMutationDefaults(mutationKeys.foodUpdate, {
  mutationFn: ({ id, body }: FoodUpdateInput) => api.put<Food>(`/api/foods/${id}`, body),
  // Poprawione wartości widać od razu, także bez sieci. Serwer potwierdza je po wysłaniu.
  onMutate: ({ id, barcode, body }: FoodUpdateInput) => {
    updateFood(id, barcode, (old) => ({
      ...old,
      ...body,
      macro_source: "user",
      verified_at: new Date().toISOString(),
      warnings: [],
    }));
  },
  onSuccess: (food: Food) => {
    storeFood(food);
    refreshFoodLists();
  },
  // Serwer odrzucił zapis: wracamy do tego, co naprawdę jest w bazie.
  onError: (_error: Error, { id, barcode }: FoodUpdateInput) => {
    void queryClient.invalidateQueries({ queryKey: foodByIdKey(id) });
    if (barcode) void queryClient.invalidateQueries({ queryKey: foodQueryKey(barcode) });
  },
});

queryClient.setMutationDefaults(mutationKeys.foodVerify, {
  mutationFn: ({ id }: FoodVerifyInput) => api.post<Food>(`/api/foods/${id}/verify`),
  onSuccess: storeFood,
});

export interface FoodCreateInput {
  barcode: string;
  body: FoodCreateBody;
}

// Własny produkt dla kodu, którego nie ma w źródłach. PUT z kodem kreskowym jako kluczem,
// więc zapis ponowiony z kolejki nie tworzy duplikatu. Bez podglądu: produkt dostaje
// identyfikator dopiero na serwerze, a bez niego nie da się go dodać do dnia.
queryClient.setMutationDefaults(mutationKeys.foodCreate, {
  mutationFn: ({ barcode, body }: FoodCreateInput) =>
    api.put<Food>(`/api/foods/barcode/${barcode}`, body),
  onSuccess: (food: Food) => {
    storeFood(food);
    refreshFoodLists();
  },
});

export interface FoodCustomInput {
  /** Identyfikator nadany na telefonie: powtórka z kolejki nie tworzy drugiego produktu. */
  clientId: string;
  body: FoodCreateBody;
}

// Produkt bez kodu kreskowego. Jak wyżej: bez podglądu, bo identyfikator nadaje serwer.
queryClient.setMutationDefaults(mutationKeys.foodCustom, {
  mutationFn: ({ clientId, body }: FoodCustomInput) =>
    api.put<Food>(`/api/foods/custom/${clientId}`, body),
  onSuccess: (food: Food) => {
    storeFood(food);
    refreshFoodLists();
  },
});

export interface FoodFavoriteInput {
  id: number;
  barcode: string | null;
  favorite: boolean;
}

queryClient.setMutationDefaults(mutationKeys.foodFavorite, {
  mutationFn: ({ id, favorite }: FoodFavoriteInput) =>
    api.put<Food>(`/api/foods/${id}/favorite`, { favorite }),
  // Gwiazdka zmienia się od razu, także bez sieci.
  onMutate: ({ id, barcode, favorite }: FoodFavoriteInput) =>
    updateFood(id, barcode, (old) => ({ ...old, favorite })),
  onSuccess: storeFood,
  onSettled: () => queryClient.invalidateQueries({ queryKey: ["favorites"] }),
});

// ---------- cele dzienne ----------

export const targetsQueryKey = (day: string) => ["targets", day] as const;

export interface TargetsPutInput {
  dateFrom: string;
  goals: Per100;
}

queryClient.setMutationDefaults(mutationKeys.targetsPut, {
  mutationFn: ({ dateFrom, goals }: TargetsPutInput) =>
    api.put<Targets>(`/api/targets/${dateFrom}`, { goals }),
  // Nowe cele widać od razu we wszystkich dniach od `dateFrom`, także bez sieci.
  onMutate: ({ dateFrom, goals }: TargetsPutInput) => {
    for (const [queryKey, old] of queryClient.getQueriesData<Targets>({ queryKey: ["targets"] })) {
      if (old && old.date >= dateFrom) {
        queryClient.setQueryData<Targets>(queryKey, { ...old, date_from: dateFrom, goals });
      }
    }
  },
  onSettled: () => queryClient.invalidateQueries({ queryKey: ["targets"] }),
});

// ---------- zapisane posiłki ----------

export const MEALS_QUERY_KEY = ["meals"] as const;

/** Pełny zestaw: serwer dostaje nazwę i skład, telefon trzyma resztę do podglądu. */
// Zapisy dziennika idą jeden po drugim, w kolejności wykonania. Bez tego usunięcie
// wpisu mogłoby dotrzeć do serwera przed jego dodaniem. Zapis posiłku z wpisów też tu
// jest: musi dotrzeć po wpisach, z których bierze produkty.
const DIARY_SCOPE = { id: "diary" };

export interface MealPutInput {
  /** Podgląd na liście do czasu odpowiedzi serwera (puste `items`: bez podglądu). */
  meal: Meal;
  /**
   * Wpisy dziennika, z których serwer bierze produkty i ilości (22.11.2026). Telefon nie zna
   * numeru produktu, który serwer zakłada dla szacunku AI, więc posiłek wskazuje wpisy.
   */
  entryIds?: string[];
}

export interface MealDeleteInput {
  id: string;
}

queryClient.setMutationDefaults(mutationKeys.mealPut, {
  scope: DIARY_SCOPE,
  mutationFn: ({ meal, entryIds }: MealPutInput) =>
    api.put<void>(
      `/api/meals/${meal.id}`,
      entryIds
        ? { name: meal.name, entry_ids: entryIds }
        : { name: meal.name, items: meal.items.map(({ food_id, amount }) => ({ food_id, amount })) },
    ),
  onMutate: ({ meal }: MealPutInput) => {
    if (meal.items.length === 0) return;
    queryClient.setQueryData<Meal[]>(MEALS_QUERY_KEY, (old = []) =>
      [...old.filter((m) => m.id !== meal.id), meal].sort((a, b) => a.name.localeCompare(b.name)),
    );
  },
  onSettled: () => queryClient.invalidateQueries({ queryKey: MEALS_QUERY_KEY }),
});

queryClient.setMutationDefaults(mutationKeys.mealDelete, {
  mutationFn: ({ id }: MealDeleteInput) => api.delete(`/api/meals/${id}`),
  onMutate: ({ id }: MealDeleteInput) =>
    queryClient.setQueryData<Meal[]>(MEALS_QUERY_KEY, (old = []) => old.filter((m) => m.id !== id)),
  onSettled: () => queryClient.invalidateQueries({ queryKey: MEALS_QUERY_KEY }),
});

// ---------- suplementacja (23.11.2026) ----------

export const supplementsQueryKey = (day: string) => ["supplements", day] as const;
const SUPPLEMENT_MUTATIONS = ["supplements"] as const;
// Jedna kolejka: odhaczenie nowego suplementu musi dotrzeć po jego dodaniu.
const SUPPLEMENTS_SCOPE = { id: "supplements" };

export interface SupplementPutInput {
  id: string;
  name: string;
  dose: string | null;
  /** Skład dawki w jednostkach z opakowania; przelicza serwer (np. 2000 IU witaminy D). */
  micros: { nutrient_id: string; amount: number; unit: string }[];
}

export interface SupplementDeleteInput {
  id: string;
}

export interface SupplementDayInput {
  date: string;
  takenIds: string[];
}

export interface SupplementYesterdayInput {
  date: string;
}

/** Zmiana wszystkich zapamiętanych dni (lista suplementów jest wspólna). */
function previewSupplementDays(change: (day: SupplementDay) => SupplementDay): void {
  queryClient.setQueriesData<SupplementDay>({ queryKey: ["supplements"] }, (old) =>
    old ? change(old) : old,
  );
}

function previewSupplementDay(date: string, change: (day: SupplementDay) => SupplementDay): void {
  queryClient.setQueryData<SupplementDay>(supplementsQueryKey(date), (old) =>
    old ? change(old) : old,
  );
}

/** Serię dni i tydzień liczy serwer: pobieramy je po ostatnim zapisie z kolejki. */
function refreshSupplementsAfterLastWrite(): void {
  if (queryClient.isMutating({ mutationKey: SUPPLEMENT_MUTATIONS }) <= 1) {
    void queryClient.invalidateQueries({ queryKey: ["supplements"] });
  }
}

queryClient.setMutationDefaults(mutationKeys.supplementPut, {
  scope: SUPPLEMENTS_SCOPE,
  mutationFn: ({ id, name, dose, micros }: SupplementPutInput) =>
    api.put<void>(`/api/supplements/${id}`, { name, dose, micros }),
  onMutate: ({ id, name, dose }: SupplementPutInput) =>
    previewSupplementDays((day) =>
      day.supplements.some((s) => s.id === id)
        ? { ...day, supplements: day.supplements.map((s) => (s.id === id ? { ...s, name, dose } : s)) }
        : {
            ...day,
            supplements: [
              ...day.supplements,
              {
                id,
                name,
                dose,
                taken: false,
                streak: 0,
                last7: Array(7).fill(false),
                micros: [],
              },
            ],
          },
    ),
  onSettled: refreshSupplementsAfterLastWrite,
});

queryClient.setMutationDefaults(mutationKeys.supplementDelete, {
  scope: SUPPLEMENTS_SCOPE,
  mutationFn: ({ id }: SupplementDeleteInput) => api.delete(`/api/supplements/${id}`),
  onMutate: ({ id }: SupplementDeleteInput) =>
    previewSupplementDays((day) => ({
      ...day,
      supplements: day.supplements.filter((s) => s.id !== id),
      taken_ids: day.taken_ids.filter((sid) => sid !== id),
      yesterday_ids: day.yesterday_ids.filter((sid) => sid !== id),
    })),
  onSettled: refreshSupplementsAfterLastWrite,
});

queryClient.setMutationDefaults(mutationKeys.supplementDay, {
  scope: SUPPLEMENTS_SCOPE,
  mutationFn: ({ date, takenIds }: SupplementDayInput) =>
    api.put<void>(`/api/supplements/day/${date}`, { taken_ids: takenIds }),
  onMutate: ({ date, takenIds }: SupplementDayInput) =>
    previewSupplementDay(date, (day) => withTaken(day, takenIds)),
  onSettled: refreshSupplementsAfterLastWrite,
});

queryClient.setMutationDefaults(mutationKeys.supplementYesterday, {
  scope: SUPPLEMENTS_SCOPE,
  mutationFn: ({ date }: SupplementYesterdayInput) =>
    api.post<void>(`/api/supplements/day/${date}/as-yesterday`),
  onMutate: ({ date }: SupplementYesterdayInput) =>
    previewSupplementDay(date, (day) => withTaken(day, likeYesterday(day))),
  onSettled: refreshSupplementsAfterLastWrite,
});

// ---------- trening (etap 4) ----------

export const trainingSeasonKey = (today: string) => ["training", "season", today] as const;
export const trainingWeekKey = (index: number) => ["training", "week", index] as const;
const TRAINING_MUTATIONS = ["training"] as const;
// Jedna kolejka: wpisy jednej sesji docierają w kolejności wpisywania.
const TRAINING_SCOPE = { id: "training" };

export interface TrainingEntryInput {
  /** Indeks tygodnia w sezonie: który widok podglądać do czasu wysłania. */
  week: number;
  session: string;
  index: number;
  entry: TrainingEntry;
}

export interface TrainingSessionInput {
  week: number;
  session: string;
  gym: string | null;
  bodyweight: number | null;
  note: string | null;
}

/** Wpis widać od razu, także bez sieci; status, e1RM i „ostatnio" liczy serwer. */
function previewTrainingWeek(
  week: number,
  session: string,
  change: (s: TrainingWeek["sessions"][number]) => TrainingWeek["sessions"][number],
): void {
  queryClient.setQueryData<TrainingWeek>(trainingWeekKey(week), (old) =>
    old
      ? { ...old, sessions: old.sessions.map((s) => (s.key === session ? change(s) : s)) }
      : old,
  );
}

function refreshTrainingAfterLastWrite(): void {
  if (queryClient.isMutating({ mutationKey: TRAINING_MUTATIONS }) <= 1) {
    void queryClient.invalidateQueries({ queryKey: ["training"] });
  }
}

queryClient.setMutationDefaults(mutationKeys.trainingEntry, {
  scope: TRAINING_SCOPE,
  mutationFn: ({ session, index, entry }: TrainingEntryInput) =>
    api.put<void>(`/api/training/sessions/${session}/entries/${index}`, entry),
  onMutate: ({ week, session, index, entry }: TrainingEntryInput) =>
    previewTrainingWeek(week, session, (s) => ({
      ...s,
      exercises: s.exercises.map((e) => (e.index === index ? { ...e, entry } : e)),
    })),
  onSettled: refreshTrainingAfterLastWrite,
});

queryClient.setMutationDefaults(mutationKeys.trainingSession, {
  scope: TRAINING_SCOPE,
  mutationFn: ({ session, gym, bodyweight, note }: TrainingSessionInput) =>
    api.put<void>(`/api/training/sessions/${session}`, { gym, bodyweight, note }),
  onMutate: ({ week, session, gym, bodyweight, note }: TrainingSessionInput) =>
    previewTrainingWeek(week, session, (s) => ({ ...s, gym, bodyweight, log_note: note })),
  onSettled: refreshTrainingAfterLastWrite,
});

export const TRAINING_MAXES_KEY = ["training", "maxes"] as const;
export const TRAINING_START_KEY = ["training", "start"] as const;
export const TRAINING_RULES_KEY = ["training", "rules"] as const;

export interface TrainingTmInput {
  phase: number;
  /** TM fazy w całości; brak = wartość z planu. */
  values: { S: number | null; B: number | null; D: number | null };
}

// Nowe TM przeliczają ciężary w całym planie: po wysłaniu odświeża się cały trening.
// Nowe pola odpowiedzi (arkusz, święta, opisy sezonu) są opcjonalne, więc starsza kopia
// w telefonie działa dalej i CACHE_VERSION zostaje (podbicie skasowałoby kolejkę zapisów).
queryClient.setMutationDefaults(mutationKeys.trainingTm, {
  scope: TRAINING_SCOPE,
  mutationFn: ({ phase, values }: TrainingTmInput) =>
    api.put<void>(`/api/training/tm/${phase}`, values),
  onSettled: refreshTrainingAfterLastWrite,
});

export const TRAINING_EQUIPMENT_KEY = ["training", "equipment"] as const;

export interface TrainingEquipmentInput {
  plates_25: boolean;
  collars: boolean;
}

// Talerze przelicza serwer: po wysłaniu odświeżają się tygodnie treningu.
queryClient.setMutationDefaults(mutationKeys.trainingEquipment, {
  scope: TRAINING_SCOPE,
  mutationFn: (body: TrainingEquipmentInput) => api.put<void>("/api/training/equipment", body),
  onMutate: (body: TrainingEquipmentInput) =>
    queryClient.setQueryData<TrainingEquipment>(TRAINING_EQUIPMENT_KEY, (old) =>
      old ? { ...old, ...body } : old,
    ),
  onSettled: refreshTrainingAfterLastWrite,
});

// ---------- profil ----------

export const PROFILE_QUERY_KEY = ["profile"] as const;

export interface ProfilePutInput {
  profile: Profile;
}

// Profil zapisuje się także bez sieci. Plan (kalorie, makro) liczy serwer, więc do czasu
// wysłania ekran pokazuje nowy profil ze starym planem i informację, że plan się przeliczy.
queryClient.setMutationDefaults(mutationKeys.profilePut, {
  mutationFn: ({ profile }: ProfilePutInput) => api.put<ProfileResponse>("/api/profile", profile),
  onMutate: ({ profile }: ProfilePutInput) =>
    queryClient.setQueryData<ProfileResponse>(PROFILE_QUERY_KEY, (old) => ({
      profile,
      plan: old?.plan ?? null,
    })),
  onSuccess: (response: ProfileResponse) => queryClient.setQueryData(PROFILE_QUERY_KEY, response),
  onError: () => queryClient.invalidateQueries({ queryKey: PROFILE_QUERY_KEY }),
});

// ---------- dziennik dnia ----------

export const diaryQueryKey = (date: string) => ["diary", date] as const;

/** Wspólny początek kluczy zapisów dziennika: do liczenia kolejki i zgłaszania błędów. */
export const DIARY_MUTATIONS = ["diary"] as const;


/** Pełny wpis w stanie po zmianie. Serwer dostaje z niego tylko to, co potrzebne. */
export interface DiaryPutInput {
  entry: DiaryEntry;
  /** Składnik z AI bez produktu w bazie: szacunek modelu na 100 g (tylko przy dodaniu). */
  estimate?: { name: string; per_100: Per100; micros_per_100?: Record<string, number> };
  /** Kopia wpisu z innego dnia lub posiłku: serwer przenosi zamrożone wartości z tego wpisu. */
  copyOf?: string;
}

export interface DiaryDeleteInput {
  id: string;
  date: string;
}

/** Zmiana widoczna od razu, także bez sieci. Sumy z serwera zastąpią podgląd po wysłaniu. */
async function previewDay(date: string, change: (day: DiaryDay) => DiaryDay): Promise<void> {
  // Trwające pobieranie dnia mogłoby nadpisać podgląd starszą odpowiedzią serwera.
  await queryClient.cancelQueries({ queryKey: diaryQueryKey(date) });
  queryClient.setQueryData<DiaryDay>(diaryQueryKey(date), (old) => change(old ?? emptyDay(date)));
}

/**
 * Pobiera dziennik z serwera dopiero po ostatnim zapisie z kolejki. Odświeżenie po każdym
 * zapisie pokazałoby na chwilę dzień bez wpisów, które jeszcze czekają na wysłanie.
 * W trakcie `onSettled` kończący się zapis nadal liczy się jako trwający, stąd 1.
 */
function refreshDiaryAfterLastWrite(): void {
  if (queryClient.isMutating({ mutationKey: DIARY_MUTATIONS }) <= 1) {
    void queryClient.invalidateQueries({ queryKey: ["diary"] });
    // „Ostatnie" bierze się z dziennika: bez tego lista pokazywałaby stan sprzed wpisu.
    void queryClient.invalidateQueries({ queryKey: ["recent"] });
    void queryClient.invalidateQueries({ queryKey: ["recent-meals"] });
    void queryClient.invalidateQueries({ queryKey: ["diary-month"] });
    void queryClient.invalidateQueries({ queryKey: ["week"] });
    // Szacunek AI zakłada produkt na serwerze: wyszukiwarka ma go znać od razu.
    void queryClient.invalidateQueries({ queryKey: ["search"] });
  }
}

queryClient.setMutationDefaults(mutationKeys.diaryPut, {
  scope: DIARY_SCOPE,
  mutationFn: ({ entry, estimate, copyOf }: DiaryPutInput) =>
    api.put<DiaryEntry>(`/api/diary/entries/${entry.id}`, {
      date: entry.date,
      meal_slot: entry.meal_slot,
      food_id: entry.food_id,
      amount: entry.amount,
      source: entry.source,
      estimate: estimate ?? null,
      copy_of: copyOf ?? null,
      ai_run_id: entry.ai_run_id ?? null,
    }),
  onMutate: ({ entry }: DiaryPutInput) => previewDay(entry.date, (day) => withEntry(day, entry)),
  onSettled: refreshDiaryAfterLastWrite,
});

queryClient.setMutationDefaults(mutationKeys.diaryDelete, {
  scope: DIARY_SCOPE,
  mutationFn: ({ id }: DiaryDeleteInput) => api.delete(`/api/diary/entries/${id}`),
  onMutate: ({ id, date }: DiaryDeleteInput) => previewDay(date, (day) => withoutEntry(day, id)),
  onSettled: refreshDiaryAfterLastWrite,
});

/** Usuwa z pamięci zapisy dziennika odrzucone przez serwer (po pokazaniu błędu). */
export function dismissDiaryErrors(): void {
  const cache = queryClient.getMutationCache();
  for (const mutation of cache.findAll({ mutationKey: DIARY_MUTATIONS, status: "error" })) {
    cache.remove(mutation);
  }
}
