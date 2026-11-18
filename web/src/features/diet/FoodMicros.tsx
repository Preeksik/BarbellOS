import { useQuery, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { ApiError, type FdcSearch, type Food, type Nutrient, api } from "../../lib/api";
import { SOURCE_LABELS, formatAmount } from "../../lib/micros";
import { storeFood } from "../../lib/offline";
import { formatKcal } from "./macros";

export const NUTRIENTS_QUERY_KEY = ["nutrients"] as const;

/** Słownik nazw i jednostek mikroskładników (zmienia się rzadko). */
export function useNutrients() {
  return useQuery({
    queryKey: NUTRIENTS_QUERY_KEY,
    queryFn: () => api.get<Nutrient[]>("/api/foods/nutrients"),
    staleTime: Number.POSITIVE_INFINITY,
  });
}

/**
 * Witaminy i minerały produktu (etap 6) z dopasowaniem do tabeli USDA.
 * Dopasowanie wymaga sieci (zapytanie do USDA), więc nie trafia do kolejki offline.
 */
export function FoodMicros({ food }: { food: Food }) {
  const nutrients = useNutrients();
  const [matching, setMatching] = useState(false);
  const byId = new Map((nutrients.data ?? []).map((n) => [n.id, n]));
  const micros = [...food.micros].sort(
    (a, b) =>
      (nutrients.data?.findIndex((n) => n.id === a.nutrient_id) ?? 0) -
      (nutrients.data?.findIndex((n) => n.id === b.nutrient_id) ?? 0),
  );

  return (
    <details className="micros">
      <summary>
        Witaminy i minerały ({micros.length} z {nutrients.data?.length ?? 20})
        {food.fdc_description ? " · tabela USDA" : ""}
      </summary>
      {micros.length > 0 ? (
        <table>
          <caption>Na 100 {food.unit}</caption>
          <tbody>
            {micros.map((m) => {
              const n = byId.get(m.nutrient_id);
              return (
                <tr key={m.nutrient_id}>
                  <th scope="row">
                    {n?.name_pl ?? m.nutrient_id}
                    <span className="muted">{SOURCE_LABELS[m.source] ?? m.source}</span>
                  </th>
                  <td>
                    {formatAmount(m.amount_per_100g)} {n?.unit ?? ""}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      ) : (
        <p className="muted">
          Brak danych. Dopasuj produkt do tabeli USDA, żeby liczyć witaminy i minerały.
        </p>
      )}
      {food.fdc_description && (
        <p className="muted">
          Tabela USDA: {food.fdc_description}
          {food.barcode ? " (produkt podobny: wartości przybliżone)" : ""}
        </p>
      )}
      {micros.length > 0 && <Backfill food={food} />}
      {matching ? (
        <FdcMatch food={food} onDone={() => setMatching(false)} />
      ) : (
        <button type="button" onClick={() => setMatching(true)}>
          {food.fdc_id ? "Zmień dopasowanie do tabeli USDA" : "Dopasuj do tabeli USDA"}
        </button>
      )}
    </details>
  );
}

function FdcMatch({ food, onDone }: { food: Food; onDone: () => void }) {
  const [query, setQuery] = useState<string | null>(null); // null = zapytanie od serwera (AI)
  const [text, setText] = useState("");
  const [chosen, setChosen] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const queryClient = useQueryClient();
  const search = useQuery({
    queryKey: ["fdc", food.id, query],
    queryFn: async () => {
      const q = query ? `?q=${encodeURIComponent(query)}` : "";
      const result = await api.get<FdcSearch>(`/api/foods/${food.id}/fdc${q}`);
      setText(result.query);
      setChosen(result.suggested_id);
      return result;
    },
    retry: false,
    staleTime: Number.POSITIVE_INFINITY,
    gcTime: 0, // wyniki tylko na czas wyboru, bez zapisu w pamięci telefonu
  });

  function onSearch(event: FormEvent) {
    event.preventDefault();
    if (text.trim()) setQuery(text.trim());
  }

  async function save(fdcId: number | null) {
    setBusy(true);
    setError(null);
    try {
      const saved =
        fdcId == null
          ? await api.delete(`/api/foods/${food.id}/fdc`).then(() =>
              api.get<Food>(`/api/foods/${food.id}`),
            )
          : await api.put<Food>(`/api/foods/${food.id}/fdc`, { fdc_id: fdcId });
      storeFood(saved);
      void queryClient.invalidateQueries({ queryKey: ["week"] });
      onDone();
    } catch (err) {
      setError(err instanceof ApiError || err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fdc">
      <form className="row" onSubmit={onSearch}>
        <input
          type="search"
          aria-label="Zapytanie do tabeli USDA (po angielsku)"
          placeholder="np. Oats, rolled"
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        <button type="submit" disabled={search.isFetching}>
          Szukaj
        </button>
      </form>
      <p className="muted">
        Tabela USDA jest po angielsku. Wybierz rekord, który najlepiej opisuje produkt; porównaj
        kalorie z Twoimi ({food.per_100.kcal == null ? "brak" : formatKcal(food.per_100.kcal)} kcal/100{" "}
        {food.unit}).
      </p>
      {search.isFetching ? (
        <p className="muted">Szukam w tabelach USDA…</p>
      ) : search.error ? (
        <p className="error">{search.error.message}</p>
      ) : search.data?.candidates.length === 0 ? (
        <p className="muted">Nic nie znaleziono. Spróbuj innych słów po angielsku.</p>
      ) : (
        <ul className="list choices-list">
          {search.data?.candidates.map((c) => (
            <li key={c.fdc_id}>
              <label className={chosen === c.fdc_id ? "choice active" : "choice"}>
                <input
                  type="radio"
                  name="fdc"
                  checked={chosen === c.fdc_id}
                  onChange={() => setChosen(c.fdc_id)}
                />
                <span>
                  <strong>{c.description}</strong>
                  <span className="muted">
                    {c.kcal == null ? "brak kcal" : `${formatKcal(c.kcal)} kcal/100 g`} · składników:{" "}
                    {c.micros_count}
                    {c.fdc_id === search.data?.suggested_id ? " · podpowiedź" : ""}
                  </span>
                </span>
              </label>
            </li>
          ))}
        </ul>
      )}
      {error && <p className="error">{error}</p>}
      <div className="row">
        <button
          type="button"
          className="primary"
          disabled={chosen == null || busy}
          onClick={() => save(chosen)}
        >
          Użyj wybranego
        </button>
        <button type="button" onClick={onDone} disabled={busy}>
          Anuluj
        </button>
      </div>
      {food.fdc_id && (
        <button type="button" className="link" disabled={busy} onClick={() => save(null)}>
          Usuń dopasowanie
        </button>
      )}
    </div>
  );
}

/**
 * Wpisy dodane przed dopasowaniem mają zamrożone wartości bez witamin. Uzupełnienie to
 * świadoma decyzja (dokumentacja 8): kalorie i makro wpisów się nie zmieniają.
 */
function Backfill({ food }: { food: Food }) {
  const [result, setResult] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const queryClient = useQueryClient();

  async function run() {
    setBusy(true);
    try {
      const { updated } = await api.post<{ updated: number }>(
        `/api/foods/${food.id}/micros/backfill`,
      );
      setResult(
        updated === 0
          ? "Wcześniejsze wpisy mają już te dane."
          : `Uzupełniono wpisy: ${updated}. Kalorie i makro się nie zmieniły.`,
      );
      void queryClient.invalidateQueries({ queryKey: ["week"] });
    } catch (err) {
      setResult(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return result ? (
    <p className="muted">{result}</p>
  ) : (
    <button type="button" className="link" disabled={busy} onClick={run}>
      Uzupełnij witaminy we wcześniejszych wpisach tego produktu
    </button>
  );
}
