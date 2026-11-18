import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { type FdcSearch, type Food, api } from "../../lib/api";
import { percent } from "../../lib/micros";
import { storeFood } from "../../lib/offline";
import { formatKcal } from "../diet/macros";

interface Gap {
  food_id: number;
  name: string;
  brand: string | null;
  kcal: number;
  share: number;
  entries: number;
  has_micros: boolean;
}

interface Gaps {
  foods: Gap[];
  share_without_food: number;
}

type Status = "idle" | "busy" | "done" | "skipped" | { error: string };

/**
 * Produkty z tygodnia bez witamin, z podpowiedzią z tabeli USDA i zatwierdzeniem jednym
 * stuknięciem. Zatwierdzenie dopasowuje produkt i uzupełnia jego wpisy z tygodnia:
 * to świadoma decyzja użytkownika (dokumentacja 4.2), kalorie i makro wpisów się nie zmieniają.
 */
export function MicroGaps({ day }: { day: string }) {
  const queryClient = useQueryClient();
  const [status, setStatus] = useState<Record<number, Status>>({});
  const gaps = useQuery({
    queryKey: ["week", day, "gaps"],
    queryFn: () => api.get<Gaps>(`/api/diary/week/${day}/gaps`),
  });

  const foods = (gaps.data?.foods ?? []).filter((g) => status[g.food_id] !== "skipped");
  if (!gaps.data || (foods.length === 0 && gaps.data.share_without_food < 0.01)) return null;

  async function confirm(gap: Gap, fdcId: number | null) {
    setStatus((s) => ({ ...s, [gap.food_id]: "busy" }));
    try {
      if (fdcId != null) {
        storeFood(await api.put<Food>(`/api/foods/${gap.food_id}/fdc`, { fdc_id: fdcId }));
      }
      await api.post(`/api/foods/${gap.food_id}/micros/backfill`);
      setStatus((s) => ({ ...s, [gap.food_id]: "done" }));
    } catch (err) {
      setStatus((s) => ({
        ...s,
        [gap.food_id]: { error: err instanceof Error ? err.message : String(err) },
      }));
    }
  }

  async function confirmAll() {
    for (const gap of foods) {
      if (status[gap.food_id] === "done") continue;
      if (gap.has_micros) {
        await confirm(gap, null);
        continue;
      }
      const search = queryClient.getQueryData<FdcSearch>(["fdc", gap.food_id, null]);
      if (search?.suggested_id != null) await confirm(gap, search.suggested_id);
    }
    void queryClient.invalidateQueries({ queryKey: ["week"] });
  }

  const pending = foods.filter((g) => status[g.food_id] !== "done");
  return (
    <section className="card gaps">
      <h2>Uzupełnij dane o witaminach</h2>
      <p className="muted">
        Te produkty nie mają jeszcze witamin i minerałów. Podpowiedź pochodzi z tabeli USDA;
        sprawdź opis i kalorie, potem zatwierdź. Wpisy z tego tygodnia zostaną uzupełnione
        (kalorie i makro się nie zmienią).
      </p>
      <ul className="list gaplist">
        {foods.map((gap) => (
          <GapRow
            key={gap.food_id}
            gap={gap}
            status={status[gap.food_id] ?? "idle"}
            onConfirm={(fdcId) =>
              confirm(gap, fdcId).then(() =>
                queryClient.invalidateQueries({ queryKey: ["week"] }),
              )
            }
            onSkip={() => setStatus((s) => ({ ...s, [gap.food_id]: "skipped" }))}
          />
        ))}
      </ul>
      {pending.length > 1 && (
        <button type="button" className="primary" onClick={confirmAll}>
          Zatwierdź wszystkie podpowiedzi
        </button>
      )}
      {gaps.data.share_without_food >= 0.01 && (
        <p className="muted">
          {percent(gaps.data.share_without_food)} kalorii to wpisy z AI bez produktu, dodane przed
          18.11.2026: nie mają witamin i nie da się ich uzupełnić z tabeli. Nowe wpisy z AI mają
          szacunek witamin.
        </p>
      )}
    </section>
  );
}

function GapRow({
  gap,
  status,
  onConfirm,
  onSkip,
}: {
  gap: Gap;
  status: Status;
  onConfirm: (fdcId: number | null) => void;
  onSkip: () => void;
}) {
  // Podpowiedź z tabeli: AI tłumaczy nazwę (raz, potem zapamiętana), kod ustala kolejność.
  const search = useQuery({
    queryKey: ["fdc", gap.food_id, null],
    queryFn: () => api.get<FdcSearch>(`/api/foods/${gap.food_id}/fdc`),
    enabled: !gap.has_micros,
    retry: false,
    staleTime: Number.POSITIVE_INFINITY,
    gcTime: 0,
  });
  const suggested = search.data?.candidates.find((c) => c.fdc_id === search.data?.suggested_id);

  return (
    <li className="gap">
      <div className="goalhead">
        <strong>
          {gap.name}
          {gap.brand && <span className="muted"> · {gap.brand}</span>}
        </strong>
        <span className="muted">
          {formatKcal(gap.kcal)} kcal · {percent(gap.share)}
        </span>
      </div>
      {status === "done" ? (
        <p className="status ok">Uzupełnione.</p>
      ) : gap.has_micros ? (
        <div className="row">
          <span className="muted">Produkt ma już dane; brakuje ich we wpisach.</span>
          <button type="button" disabled={status === "busy"} onClick={() => onConfirm(null)}>
            Uzupełnij wpisy
          </button>
        </div>
      ) : search.isFetching ? (
        <p className="muted">Szukam w tabelach USDA…</p>
      ) : search.error ? (
        <p className="error">{search.error.message}</p>
      ) : suggested ? (
        <>
          <p className="muted">
            Tabela USDA: <strong>{suggested.description}</strong> ·{" "}
            {suggested.kcal == null ? "brak kcal" : `${formatKcal(suggested.kcal)} kcal/100 g`} ·
            składników: {suggested.micros_count}
          </p>
          <div className="row">
            <button
              type="button"
              className="primary"
              disabled={status === "busy"}
              onClick={() => onConfirm(suggested.fdc_id)}
            >
              Zatwierdź
            </button>
            <button type="button" disabled={status === "busy"} onClick={onSkip}>
              Pomiń
            </button>
          </div>
        </>
      ) : (
        <p className="muted">
          Brak pewnej podpowiedzi (szukano: „{search.data?.query}”). Dopasuj ręcznie: Dodaj →
          wyszukaj produkt → Witaminy i minerały.
        </p>
      )}
      {typeof status === "object" && <p className="error">{status.error}</p>}
    </li>
  );
}
