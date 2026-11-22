import { useMutation, useQuery } from "@tanstack/react-query";
import { type FormEvent, type ReactNode, useEffect, useRef, useState } from "react";
import {
  type DiaryEntry,
  type Food,
  type GenericHit,
  type Meal,
  type MealSlot,
  type OffHit,
  type RecentFood,
  type RecentMeal,
  api,
} from "../../lib/api";
import { MEAL_SLOTS, dayLabel, toIsoDay } from "../../lib/diary";
import { copiedEntries, mealEntries } from "../../lib/meals";
import { formatDecimal } from "../../lib/number";
import {
  type DiaryDeleteInput,
  type DiaryPutInput,
  MEALS_QUERY_KEY,
  type MealDeleteInput,
  mutationKeys,
} from "../../lib/offline";
import type { EntrySource } from "./AddToDay";
import { FoodCard, type FoodRef } from "./FoodCard";
import { FoodEditForm } from "./FoodEditForm";
import { MealAi } from "./MealAi";
import { Scanner } from "./Scanner";
import { formatKcal } from "./macros";

const MIN_QUERY = 2; // jak na serwerze (`core/search.py`)
const TYPING_PAUSE_MS = 250;
// Duża baza produktów pozwala na kilka wyszukiwań na minutę (limit na serwerze), więc
// pytamy ją dopiero po dłuższej pauzie w pisaniu albo od razu po „Szukaj" na klawiaturze.
const WIDE_QUERY = 3;
const WIDE_PAUSE_MS = 900;

type View =
  | { kind: "home" }
  | { kind: "scan" }
  | { kind: "card"; target: FoodRef; source: EntrySource; back: "scan" | "home" }
  | { kind: "new" }
  | { kind: "ai"; mode: "photo" | "text"; text?: string };

/**
 * Dodawanie do posiłku, otwierane przyciskiem „Dodaj" przy posiłku w Diecie:
 * wyszukiwarka, skan kodu, posiłek ze zdjęcia lub opisu (AI), własny produkt,
 * zapisane posiłki, ulubione i ostatnie. Widoki są stanem, nie adresami (AGENTS.md, zasada 11).
 */
export function AddPage({
  day,
  slot,
  onClose,
}: {
  day: string;
  slot: MealSlot;
  onClose: () => void;
}) {
  const [view, setView] = useState<View>({ kind: "home" });
  // Wpisany tekst zostaje po powrocie z karty produktu do listy.
  const [query, setQuery] = useState("");
  const home = () => setView({ kind: "home" });
  const slotLabel = MEAL_SLOTS.find((s) => s.id === slot)?.label ?? "";
  const today = toIsoDay(new Date());

  let body: ReactNode;
  if (view.kind === "scan") {
    body = (
      <>
        <Scanner
          onDetected={(barcode) =>
            setView({
              kind: "card",
              target: { kind: "barcode", barcode },
              source: "scan",
              back: "scan",
            })
          }
        />
        <button type="button" className="wide" onClick={home}>
          Wróć do wyszukiwania
        </button>
      </>
    );
  } else if (view.kind === "card") {
    const target = view.target;
    body = (
      <FoodCard
        // `key`: kolejny produkt zaczyna od czystej karty (bez „Dodano" z poprzedniego).
        key={target.kind === "barcode" ? target.barcode : `id-${target.food.id}`}
        target={target}
        day={day}
        slot={slot}
        source={view.source}
        onBack={() => setView({ kind: view.back })}
        backLabel={view.back === "scan" ? "Skanuj kolejny" : "Dodaj kolejny"}
        onShowDiary={onClose}
      />
    );
  } else if (view.kind === "ai") {
    body = (
      <MealAi
        mode={view.mode}
        initialText={view.text}
        day={day}
        slot={slot}
        onBack={home}
        onShowDiary={onClose}
      />
    );
  } else if (view.kind === "new") {
    body = (
      <FoodEditForm
        food={null}
        barcode={null}
        onDone={home}
        onSaved={(food) =>
          setView({ kind: "card", target: { kind: "food", food }, source: "search", back: "home" })
        }
      />
    );
  } else {
    const open = (food: Food, amount?: number) =>
      setView({ kind: "card", target: { kind: "food", food, amount }, source: "search", back: "home" });
    body = (
      <Home
        day={day}
        slot={slot}
        query={query}
        onQuery={setQuery}
        onOpen={open}
        onOpenBarcode={(barcode) =>
          setView({ kind: "card", target: { kind: "barcode", barcode }, source: "search", back: "home" })
        }
        onScan={() => setView({ kind: "scan" })}
        onAi={(mode, text) => setView({ kind: "ai", mode, text })}
        onNew={() => setView({ kind: "new" })}
      />
    );
  }

  return (
    <>
      <div className="addhead">
        <button type="button" className="back" onClick={view.kind === "home" ? onClose : home}>
          ‹ {view.kind === "home" ? "Dieta" : "Wróć"}
        </button>
        <h1>
          Dodaj do: {slotLabel}
          {day !== today && <span className="muted"> ({dayLabel(day, today).toLowerCase()})</span>}
        </h1>
      </div>
      {body}
    </>
  );
}

function Home({
  day,
  slot,
  query,
  onQuery,
  onOpen,
  onOpenBarcode,
  onScan,
  onAi,
  onNew,
}: {
  day: string;
  slot: MealSlot;
  query: string;
  onQuery: (query: string) => void;
  onOpen: (food: Food, amount?: number) => void;
  onOpenBarcode: (barcode: string) => void;
  onScan: () => void;
  onAi: (mode: "photo" | "text", text?: string) => void;
  onNew: () => void;
}) {
  // „Szukaj" na klawiaturze: od razu pyta dużą bazę i chowa klawiaturę, żeby było widać wyniki.
  const [submitted, setSubmitted] = useState<string | null>(null);
  const input = useRef<HTMLInputElement>(null);
  const searching = query.trim().length >= MIN_QUERY;

  function submit(event: FormEvent) {
    event.preventDefault();
    setSubmitted(query.trim());
    input.current?.blur();
  }

  return (
    <>
      <form className="searchbar" role="search" onSubmit={submit}>
        <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round">
          <circle cx="11" cy="11" r="7" />
          <path d="M20 20l-3.5-3.5" />
        </svg>
        <input
          ref={input}
          type="search"
          enterKeyHint="search"
          placeholder="Szukaj produktu, np. sałata lodowa"
          aria-label="Szukaj produktu"
          value={query}
          onChange={(e) => onQuery(e.target.value)}
        />
      </form>

      {searching ? (
        <SearchResults
          query={query.trim()}
          submitted={submitted}
          onOpen={onOpen}
          onOpenBarcode={onOpenBarcode}
          onNew={onNew}
          onEstimate={(text) => onAi("text", text)}
        />
      ) : (
        <>
          <div className="tiles">
            <button type="button" className="tile scan" onClick={onScan}>
              <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round">
                <path d="M4 7V5a1 1 0 0 1 1-1h2M17 4h2a1 1 0 0 1 1 1v2M20 17v2a1 1 0 0 1-1 1h-2M7 20H5a1 1 0 0 1-1-1v-2" />
                <path d="M8 8v8M11 8v8M14 8v8M17 8v8" />
              </svg>
              Skanuj kod
            </button>
            <button type="button" className="tile ai" onClick={() => onAi("photo")}>
              <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
                <path d="M4 8h3l2-3h6l2 3h3v11H4z" />
                <circle cx="12" cy="13" r="3.5" />
              </svg>
              <span>
                Zdjęcie posiłku <small>AI</small>
              </span>
            </button>
            <button type="button" className="tile ai" onClick={() => onAi("text")}>
              <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
                <path d="M5 19l1-4L16 5l3 3L9 18z" />
                <path d="M14 7l3 3" />
              </svg>
              <span>
                Opisz posiłek <small>AI</small>
              </span>
            </button>
            <button type="button" className="tile own" onClick={onNew}>
              <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round">
                <rect x="4" y="4" width="16" height="16" rx="3" />
                <path d="M12 8v8M8 12h8" />
              </svg>
              Dodaj własny
            </button>
          </div>
          <RecentMeals day={day} slot={slot} />
          <MealList day={day} slot={slot} />
          <FavoriteList onOpen={onOpen} />
          <RecentList onOpen={onOpen} />
        </>
      )}
    </>
  );
}

// ---------- wyszukiwanie ----------

function useDebounced<T>(value: T, delayMs: number): T {
  const [settled, setSettled] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setSettled(value), delayMs);
    return () => clearTimeout(timer);
  }, [value, delayMs]);
  return settled;
}

/** Jedna lista: najpierw Twoje produkty, potem duża baza. Skąd są dane, nie ma znaczenia. */
function SearchResults({
  query,
  submitted,
  onOpen,
  onOpenBarcode,
  onNew,
  onEstimate,
}: {
  query: string;
  submitted: string | null;
  onOpen: (food: Food) => void;
  onOpenBarcode: (barcode: string) => void;
  onNew: () => void;
  onEstimate: (text: string) => void;
}) {
  const settled = useDebounced(query, TYPING_PAUSE_MS);
  const paused = useDebounced(query, WIDE_PAUSE_MS);
  const wide = submitted === query ? query : paused === query ? paused : null;
  const own = useQuery({
    queryKey: ["search", settled],
    queryFn: () =>
      api.get<{ foods: Food[] }>(`/api/foods/search?q=${encodeURIComponent(settled)}`),
    enabled: settled.length >= MIN_QUERY,
    placeholderData: (previous) => previous,
  });
  const big = useQuery({
    queryKey: ["search-off", wide],
    queryFn: () => api.get<OffHit[]>(`/api/foods/search/off?q=${encodeURIComponent(wide!)}`),
    enabled: wide != null && wide.length >= WIDE_QUERY,
    retry: false,
    staleTime: Number.POSITIVE_INFINITY,
    // W trakcie pisania zostają poprzednie wyniki, zamiast znikać do następnej pauzy.
    placeholderData: (previous) => previous,
  });
  // Produkty podstawowe (warzywa, mięso, kasze) z tabel: tłumaczy je serwer, więc też po pauzie.
  const basic = useQuery({
    queryKey: ["search-generic", wide],
    queryFn: () =>
      api.get<GenericHit[]>(`/api/foods/search/generic?q=${encodeURIComponent(wide!)}`),
    enabled: wide != null && wide.length >= WIDE_QUERY,
    retry: false,
    staleTime: Number.POSITIVE_INFINITY,
    placeholderData: (previous) => previous,
  });
  const [opening, setOpening] = useState<number | null>(null);
  const [openError, setOpenError] = useState<string | null>(null);
  const foods = own.data?.foods ?? [];
  const known = new Set(foods.map((food) => food.barcode).filter(Boolean));
  const knownBasic = new Set(foods.filter((f) => !f.barcode).map((f) => f.fdc_id));
  const hits = (big.data ?? []).filter((hit) => !known.has(hit.barcode));
  const basics = (basic.data ?? []).filter((hit) => !knownBasic.has(hit.fdc_id));
  const waitingForBig =
    big.isFetching || basic.isFetching || (wide == null && query.length >= WIDE_QUERY);
  const nothing =
    foods.length === 0 && hits.length === 0 && basics.length === 0 && !own.isPending && !waitingForBig;

  // Wybrany produkt podstawowy zapisuje się w bazie (z witaminami) i otwiera jak każdy inny.
  async function openBasic(hit: GenericHit) {
    setOpening(hit.fdc_id);
    setOpenError(null);
    try {
      onOpen(await api.put<Food>(`/api/foods/generic/${hit.fdc_id}`, { name: hit.name }));
    } catch (err) {
      setOpenError(err instanceof Error ? err.message : String(err));
    } finally {
      setOpening(null);
    }
  }

  return (
    <section className="card">
      {own.error && <p className="error">{own.error.message}</p>}
      {(foods.length > 0 || hits.length > 0 || basics.length > 0) && (
        <ul className="list foods">
          {foods.map((food) => (
            <li key={`own-${food.id}`}>
              <FoodRow food={food} onOpen={() => onOpen(food)} />
            </li>
          ))}
          {basics.map((hit) => (
            <li key={`basic-${hit.fdc_id}`}>
              <button
                type="button"
                className="food"
                disabled={opening != null}
                onClick={() => openBasic(hit)}
              >
                <span className="name">{hit.name}</span>
                <span className="kcal">
                  {opening === hit.fdc_id ? "otwieram…" : `${formatKcal(hit.kcal)} kcal/100 g`}
                </span>
              </button>
            </li>
          ))}
          {hits.map((hit) => (
            <li key={hit.barcode}>
              <button type="button" className="food" onClick={() => onOpenBarcode(hit.barcode)}>
                <span className="name">
                  {hit.name}
                  {hit.brand && <em> · {hit.brand}</em>}
                </span>
                <span className="kcal">
                  {hit.kcal == null ? "–" : formatKcal(hit.kcal)} kcal/100 {hit.unit}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
      {openError && <p className="error">{openError}</p>}
      {waitingForBig && <p className="muted">Szukam w bazie produktów…</p>}
      {big.error && (
        <div className="row added">
          <p className="muted">{big.error.message}</p>
          <button type="button" onClick={() => big.refetch()}>
            Szukaj ponownie
          </button>
        </div>
      )}
      {nothing && !big.error && (
        <p className="muted">Nic nie znaleziono dla „{query}". Spróbuj innej nazwy albo:</p>
      )}
      {/* Warzywa na wagę i dania domowe rzadko są w bazie produktów: AI je oszacuje. */}
      {!own.isPending && !waitingForBig && (
        <button type="button" className="estimate" onClick={() => onEstimate(query)}>
          <span>
            Oszacuj „{query}" <small>AI</small>
          </span>
          <span className="muted">kalorie, makro i witaminy na podstawie nazwy</span>
        </button>
      )}
      {nothing && !big.error && (
        <button type="button" onClick={onNew}>
          Dodaj własny produkt
        </button>
      )}
    </section>
  );
}

// ---------- listy produktów ----------

function FoodRow({ food, amount, onOpen }: { food: Food; amount?: number; onOpen: () => void }) {
  return (
    <button type="button" className="food" onClick={onOpen}>
      <span className="name">
        {food.favorite && <span aria-label="ulubiony">★ </span>}
        {food.name}
        {food.brand && <em> · {food.brand}</em>}
      </span>
      <span className="kcal">
        {amount != null
          ? `${formatDecimal(amount)} ${food.unit}`
          : `${food.per_100.kcal == null ? "–" : formatKcal(food.per_100.kcal)} kcal/100 ${food.unit}`}
      </span>
    </button>
  );
}

function FoodRows({
  foods,
  onOpen,
}: {
  foods: { food: Food; amount?: number }[];
  onOpen: (food: Food, amount?: number) => void;
}) {
  return (
    <ul className="list foods">
      {foods.map(({ food, amount }) => (
        <li key={food.id}>
          <FoodRow food={food} amount={amount} onOpen={() => onOpen(food, amount)} />
        </li>
      ))}
    </ul>
  );
}

function FavoriteList({ onOpen }: { onOpen: (food: Food) => void }) {
  const favorites = useQuery({
    queryKey: ["favorites"],
    queryFn: () => api.get<Food[]>("/api/foods/favorites"),
  });
  if (!favorites.data?.length) return null;
  return (
    <section className="card">
      <h2>Ulubione</h2>
      <FoodRows foods={favorites.data.map((food) => ({ food }))} onOpen={onOpen} />
    </section>
  );
}

function RecentList({ onOpen }: { onOpen: (food: Food, amount?: number) => void }) {
  const recent = useQuery({
    queryKey: ["recent"],
    queryFn: () => api.get<RecentFood[]>("/api/foods/recent"),
  });
  return (
    <section className="card">
      <h2>Ostatnie</h2>
      {recent.error ? (
        <p className="error">{recent.error.message}</p>
      ) : recent.data?.length === 0 ? (
        <p className="muted">Tu pojawią się produkty, które dodasz.</p>
      ) : (
        <FoodRows
          foods={(recent.data ?? []).map((r) => ({ food: r.food, amount: r.last_amount }))}
          onOpen={onOpen}
        />
      )}
    </section>
  );
}

// ---------- poprzednie posiłki ----------

/**
 * Posiłki z ostatnich dwóch tygodni: stuknięcie kopiuje cały posiłek do tego, przy którym
 * stuknięto „Dodaj" (22.11.2026: „wczoraj spaghetti, dziś to samo"). Działa bez sieci, jak
 * każdy wpis; wartości przenosi serwer z oryginalnych wpisów.
 */
function RecentMeals({ day, slot }: { day: string; slot: MealSlot }) {
  const [added, setAdded] = useState<{ label: string; ids: string[] } | null>(null);
  const recent = useQuery({
    queryKey: ["recent-meals", day],
    queryFn: () => api.get<RecentMeal[]>(`/api/diary/recent-meals/${day}`),
  });
  const put = useMutation<DiaryEntry, Error, DiaryPutInput>({ mutationKey: mutationKeys.diaryPut });
  const remove = useMutation<void, Error, DiaryDeleteInput>({
    mutationKey: mutationKeys.diaryDelete,
  });
  const today = toIsoDay(new Date());
  // Bez posiłku, do którego właśnie dodajesz: kopiowanie go do siebie nie ma sensu.
  const meals = (recent.data ?? [])
    .filter((m) => !(m.date === day && m.meal_slot === slot))
    .slice(0, 10);
  if (meals.length === 0) return null;

  const label = (meal: RecentMeal) =>
    `${MEAL_SLOTS.find((s) => s.id === meal.meal_slot)?.label}, ${dayLabel(meal.date, today).toLowerCase()}`;

  function copy(meal: RecentMeal) {
    const copies = copiedEntries(meal, day, slot, new Date(), () => crypto.randomUUID());
    for (const input of copies) put.mutate(input);
    setAdded({ label: label(meal), ids: copies.map((c) => c.entry.id) });
  }

  function undo() {
    if (!added) return;
    for (const id of added.ids) remove.mutate({ id, date: day });
    setAdded(null);
  }

  return (
    <section className="card">
      <h2>Poprzednie posiłki</h2>
      {added && (
        <div className="row added">
          <p className="status ok">Skopiowano: {added.label}</p>
          <button type="button" onClick={undo}>
            Cofnij
          </button>
        </div>
      )}
      <ul className="list meals">
        {meals.map((meal) => (
          <li key={`${meal.date}-${meal.meal_slot}`}>
            <button type="button" className="food" onClick={() => copy(meal)}>
              <span className="name">
                {label(meal)}
                <em> · {meal.entries.map((e) => e.food_name).join(", ")}</em>
              </span>
              <span className="kcal">{formatKcal(meal.kcal)} kcal</span>
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}

// ---------- zapisane posiłki ----------

/** Zapisane posiłki trafiają do posiłku, przy którym stuknięto „Dodaj". */
function MealList({ day, slot }: { day: string; slot: MealSlot }) {
  const [added, setAdded] = useState<{ meal: Meal; entries: DiaryEntry[] } | null>(null);
  const meals = useQuery({
    queryKey: MEALS_QUERY_KEY,
    queryFn: () => api.get<Meal[]>("/api/meals"),
  });
  // Funkcje zapisu są w rejestrze lib/offline.ts: dodanie posiłku działa bez sieci.
  const put = useMutation<DiaryEntry, Error, DiaryPutInput>({ mutationKey: mutationKeys.diaryPut });
  const remove = useMutation<void, Error, DiaryDeleteInput>({
    mutationKey: mutationKeys.diaryDelete,
  });
  const removeMeal = useMutation<void, Error, MealDeleteInput>({
    mutationKey: mutationKeys.mealDelete,
  });

  function add(meal: Meal) {
    const entries = mealEntries(meal, day, slot, new Date(), () => crypto.randomUUID());
    for (const entry of entries) put.mutate({ entry });
    setAdded({ meal, entries });
  }

  function undo() {
    if (!added) return;
    for (const entry of added.entries) remove.mutate({ id: entry.id, date: entry.date });
    setAdded(null);
  }

  function forget(meal: Meal) {
    if (window.confirm(`Usunąć zapisany posiłek „${meal.name}"? Wpisy w Diecie się nie zmienią.`)) {
      removeMeal.mutate({ id: meal.id });
    }
  }

  // Bez zapisanych posiłków karta tylko zajmowałaby miejsce: podpowiedź jest przy posiłkach.
  if (!meals.data?.length && !meals.error) return null;

  return (
    <section className="card">
      <h2>Zapisane posiłki</h2>
      {added && (
        <div className="row added">
          <p className="status ok">
            Dodano „{added.meal.name}" ({added.entries.length}{" "}
            {added.entries.length === 1 ? "produkt" : "produkty"})
          </p>
          <button type="button" onClick={undo}>
            Cofnij
          </button>
        </div>
      )}
      {meals.error ? (
        <p className="error">{meals.error.message}</p>
      ) : (
        <ul className="list meals">
          {meals.data!.map((meal) => (
            <li key={meal.id}>
              <button type="button" className="food" onClick={() => add(meal)}>
                <span className="name">
                  {meal.name}
                  <em> · {meal.items.map((item) => item.food_name).join(", ")}</em>
                </span>
                <span className="kcal">{formatKcal(meal.totals.kcal)} kcal</span>
              </button>
              <button
                type="button"
                className="forget"
                aria-label={`Usuń zapisany posiłek ${meal.name}`}
                onClick={() => forget(meal)}
              >
                ✕
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
