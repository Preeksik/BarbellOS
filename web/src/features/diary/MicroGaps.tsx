import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { api } from "../../lib/api";
import { percent } from "../../lib/micros";

interface Gap {
  food_id: number;
  name: string;
  brand: string | null;
  kcal: number;
  share: number;
  entries: number;
  has_micros: boolean;
  checked: boolean;
}

interface Gaps {
  foods: Gap[];
  share_without_food: number;
}

interface Autofill {
  filled: string[];
  completed: string[];
  no_match: string[];
  postponed: string[];
}

/**
 * Witaminy z tabel USDA uzupełniane automatycznie (decyzja z 18.11.2026): przy otwarciu
 * tygodnia serwer dopasowuje produkty bez danych i uzupełnia ich wpisy. Ręcznie zostają
 * tylko produkty bez pewnego dopasowania. Nowe wpisy uzupełniają się same w tle.
 */
export function MicroGaps({ day }: { day: string }) {
  const queryClient = useQueryClient();
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<Autofill | null>(null);
  const [error, setError] = useState<string | null>(null);
  const started = useRef<string | null>(null);
  const gaps = useQuery({
    queryKey: ["week", day, "gaps"],
    queryFn: () => api.get<Gaps>(`/api/diary/week/${day}/gaps`),
  });
  // Coś do zrobienia: produkt jeszcze niesprawdzony albo dane są, ale nie we wpisach.
  const todo = (gaps.data?.foods ?? []).some((g) => !g.checked || g.has_micros);

  useEffect(() => {
    if (!todo || started.current === day) return;
    started.current = day; // raz na otwarcie dnia: bez pętli przy odświeżaniu
    setRunning(true);
    setError(null);
    api
      .post<Autofill>(`/api/diary/week/${day}/autofill`)
      .then((r) => {
        setResult(r);
        void queryClient.invalidateQueries({ queryKey: ["week"] });
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)))
      .finally(() => setRunning(false));
  }, [todo, day, queryClient]);

  const manual = (gaps.data?.foods ?? []).filter((g) => g.checked && !g.has_micros);
  const added = [...(result?.filled ?? []), ...(result?.completed ?? [])];
  const orphan = gaps.data?.share_without_food ?? 0;
  if (!running && !error && added.length === 0 && manual.length === 0 && orphan < 0.01) {
    return null;
  }

  return (
    <section className="card gaps">
      <h2>Dane o witaminach</h2>
      {running && <p className="muted">Uzupełniam witaminy z tabel USDA…</p>}
      {error && <p className="error">Uzupełnianie nie powiodło się: {error}</p>}
      {added.length > 0 && <p className="status ok">Uzupełniono: {added.join(", ")}.</p>}
      {result && result.postponed.length > 0 && (
        <p className="muted">
          Bez połączenia z USDA: {result.postponed.join(", ")}. Spróbuję przy następnym otwarciu.
        </p>
      )}
      {manual.length > 0 && (
        // Bez wezwania do ręcznego wyboru (decyzja z 19.11.2026): witaminy to szacunek.
        <p className="muted">
          Bez danych o witaminach: {manual.map((g) => g.name).join(", ")}. Tabele nie mają
          podobnego produktu, więc te pozycje nie liczą się do norm.
        </p>
      )}
      {orphan >= 0.01 && (
        <p className="muted">
          {percent(orphan)} kalorii to wpisy z AI bez produktu, dodane przed 18.11.2026: nie mają
          witamin i nie da się ich uzupełnić z tabeli. Nowe wpisy z AI mają szacunek witamin.
        </p>
      )}
    </section>
  );
}
