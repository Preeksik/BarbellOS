import { useMutation, useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import {
  type DiaryEntry,
  type Food,
  type Meal,
  type MealSlot,
  type OffHit,
  type RecentFood,
  api,
} from "../../lib/api";
import { MEAL_SLOTS, dayLabel, defaultSlot, toIsoDay } from "../../lib/diary";
import { mealEntries } from "../../lib/meals";
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

type View =
  | { kind: "home" }
  | { kind: "scan" }
  | { kind: "card"; target: FoodRef; source: EntrySource; back: "scan" | "home" }
  | { kind: "new" }
  | { kind: "ai"; mode: "photo" | "text" };

/**
 * Dodawanie do dnia: wyszukiwarka, ostatnie, ulubione, zapisane posiłki, skan kodu
 * oraz posiłek ze zdjęcia lub opisu (AI, etap 2).
 * Widoki są stanem, nie adresami (AGENTS.md, zasada 11).
 */
export function AddPage({ day, onShowDiary }: { day: string; onShowDiary: () => void }) {
  const [view, setView] = useState<View>({ kind: "home" });
  // Wpisany tekst zostaje po powrocie z karty produktu do listy.
  const [query, setQuery] = useState("");
  const home = () => setView({ kind: "home" });

  if (view.kind === "scan") {
    return (
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
  }
  if (view.kind === "card") {
    const target = view.target;
    return (
      <FoodCard
        // `key`: kolejny produkt zaczyna od czystej karty (bez „Dodano" z poprzedniego).
        key={target.kind === "barcode" ? target.barcode : `id-${target.food.id}`}
        target={target}
        day={day}
        source={view.source}
        onBack={() => setView({ kind: view.back })}
        backLabel={view.back === "scan" ? "Skanuj kolejny" : "Wróć do listy"}
        onShowDiary={onShowDiary}
      />
    );
  }
  if (view.kind === "ai") {
    return <MealAi mode={view.mode} day={day} onBack={home} onShowDiary={onShowDiary} />;
  }
  if (view.kind === "new") {
    return (
      <FoodEditForm
        food={null}
        barcode={null}
        onDone={home}
        onSaved={(food) =>
          setView({ kind: "card", target: { kind: "food", food }, source: "search", back: "home" })
        }
      />
    );
  }

  const open = (food: Food, amount?: number) =>
    setView({ kind: "card", target: { kind: "food", food, amount }, source: "search", back: "home" });
  const searching = query.trim().length >= MIN_QUERY;

  return (
    <>
      <p className="muted daynote">Dodajesz do dnia: {dayLabel(day, toIsoDay(new Date()))}</p>
      <section className="card">
        <input
          type="search"
          enterKeyHint="search"
          placeholder="Szukaj produktu…"
          aria-label="Szukaj produktu"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <div className="row">
          <button type="button" className="primary" onClick={() => setView({ kind: "scan" })}>
            Skanuj kod
          </button>
          <button type="button" onClick={() => setView({ kind: "new" })}>
            Produkt bez kodu
          </button>
        </div>
        <div className="row">
          <button type="button" onClick={() => setView({ kind: "ai", mode: "photo" })}>
            Zdjęcie posiłku (AI)
          </button>
          <button type="button" onClick={() => setView({ kind: "ai", mode: "text" })}>
            Opisz posiłek (AI)
          </button>
        </div>
      </section>

      {searching ? (
        <SearchResults
          query={query.trim()}
          onOpen={open}
          onOpenBarcode={(barcode) =>
            setView({
              kind: "card",
              target: { kind: "barcode", barcode },
              source: "search",
              back: "home",
            })
          }
        />
      ) : (
        <>
          <MealList day={day} />
          <FavoriteList onOpen={open} />
          <RecentList onOpen={open} />
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

function SearchResults({
  query,
  onOpen,
  onOpenBarcode,
}: {
  query: string;
  onOpen: (food: Food) => void;
  onOpenBarcode: (barcode: string) => void;
}) {
  const settled = useDebounced(query, TYPING_PAUSE_MS);
  // Open Food Facts pozwala na kilka wyszukiwań na minutę, więc tylko na przycisk.
  const [offQuery, setOffQuery] = useState<string | null>(null);
  const own = useQuery({
    queryKey: ["search", settled],
    queryFn: () =>
      api.get<{ foods: Food[] }>(`/api/foods/search?q=${encodeURIComponent(settled)}`),
    enabled: settled.length >= MIN_QUERY,
    placeholderData: (previous) => previous,
  });
  const off = useQuery({
    queryKey: ["search-off", offQuery],
    queryFn: () => api.get<OffHit[]>(`/api/foods/search/off?q=${encodeURIComponent(offQuery!)}`),
    enabled: offQuery != null,
    retry: false,
    staleTime: Number.POSITIVE_INFINITY,
  });
  const foods = own.data?.foods ?? [];

  return (
    <>
      <section className="card">
        <h2>Twoje produkty</h2>
        {own.error ? (
          <p className="error">{own.error.message}</p>
        ) : own.isPending ? (
          <p className="muted">Szukam…</p>
        ) : foods.length === 0 ? (
          <p className="muted">Brak w Twojej bazie. Poszukaj w Open Food Facts poniżej.</p>
        ) : (
          <FoodRows foods={foods.map((food) => ({ food }))} onOpen={onOpen} />
        )}
      </section>

      <section className="card">
        <h2>Open Food Facts</h2>
        {offQuery !== query && (
          <button type="button" onClick={() => setOffQuery(query)}>
            Szukaj „{query}" w Open Food Facts
          </button>
        )}
        {offQuery != null &&
          (off.isFetching ? (
            <p className="muted">Szukam w Open Food Facts…</p>
          ) : off.error ? (
            <p className="error">{off.error.message}</p>
          ) : off.data?.length === 0 ? (
            <p className="muted">Nic nie znaleziono. Spróbuj innych słów albo zeskanuj kod.</p>
          ) : (
            <ul className="list foods">
              {off.data?.map((hit) => (
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
          ))}
        <p className="muted">
          Wartości z Open Food Facts to szkic: po wybraniu porównaj je z etykietą.
        </p>
      </section>
    </>
  );
}

// ---------- listy produktów ----------

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
          <button type="button" className="food" onClick={() => onOpen(food, amount)}>
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
        <p className="muted">Tu pojawią się produkty, które dodasz do dziennika.</p>
      ) : (
        <FoodRows
          foods={(recent.data ?? []).map((r) => ({ food: r.food, amount: r.last_amount }))}
          onOpen={onOpen}
        />
      )}
    </section>
  );
}

// ---------- zapisane posiłki ----------

function MealList({ day }: { day: string }) {
  const [slot, setSlot] = useState<MealSlot>(() => defaultSlot(new Date().getHours()));
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
    if (window.confirm(`Usunąć zapisany posiłek „${meal.name}"? Dziennik się nie zmieni.`)) {
      removeMeal.mutate({ id: meal.id });
    }
  }

  return (
    <section className="card">
      <div className="slothead">
        <h2>Posiłki</h2>
        <select value={slot} aria-label="Dodaj do posiłku" onChange={(e) => setSlot(e.target.value as MealSlot)}>
          {MEAL_SLOTS.map((s) => (
            <option key={s.id} value={s.id}>
              do: {s.label}
            </option>
          ))}
        </select>
      </div>
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
      {meals.data?.length ? (
        <ul className="list meals">
          {meals.data.map((meal) => (
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
      ) : meals.error ? (
        <p className="error">{meals.error.message}</p>
      ) : (
        <p className="muted">
          Zapisz posiłek w dzienniku („Zapisz jako posiłek" przy śniadaniu, obiedzie…), a potem
          dodawaj go tutaj jednym stuknięciem.
        </p>
      )}
    </section>
  );
}
