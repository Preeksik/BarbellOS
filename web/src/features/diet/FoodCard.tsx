import { useMutation, useMutationState, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { ApiError, type Food, type MealSlot, api } from "../../lib/api";
import { MEAL_SLOTS } from "../../lib/diary";
import { formatDecimal } from "../../lib/number";
import {
  type FoodCreateInput,
  type FoodFavoriteInput,
  type FoodVerifyInput,
  foodByIdKey,
  foodQueryKey,
  mutationKeys,
} from "../../lib/offline";
import { AddToDay, type Added, type EntrySource } from "./AddToDay";
import { FoodEditForm } from "./FoodEditForm";
import { FoodMicros } from "./FoodMicros";
import { MACRO_ROWS, formatNumber } from "./macros";

/** Skąd karta bierze produkt: kod kreskowy (skan, wynik z OFF) albo produkt z listy. */
export type FoodRef =
  | { kind: "barcode"; barcode: string }
  | { kind: "food"; food: Food; amount?: number };

/**
 * Karta produktu: wartości, ulubione, weryfikacja, poprawianie według etykiety,
 * dodanie do dnia. Gdy kodu nie ma w żadnym źródle, proponuje dodanie własnego produktu.
 */
export function FoodCard({
  target,
  day,
  source,
  onBack,
  backLabel,
  onShowDiary,
  slot,
}: {
  target: FoodRef;
  day: string;
  source: EntrySource;
  onBack: () => void;
  backLabel: string;
  onShowDiary: () => void;
  slot?: MealSlot;
}) {
  const [editing, setEditing] = useState(false);
  const [added, setAdded] = useState<Added | null>(null);
  const barcode = target.kind === "barcode" ? target.barcode : target.food.barcode;
  const byBarcode = target.kind === "barcode";
  const food = useQuery<Food, Error, Food, readonly unknown[]>({
    queryKey: byBarcode ? foodQueryKey(target.barcode) : foodByIdKey(target.food.id),
    queryFn: () =>
      api.get<Food>(
        byBarcode ? `/api/foods/barcode/${target.barcode}` : `/api/foods/${target.food.id}`,
      ),
    retry: byBarcode ? false : 1,
    staleTime: Number.POSITIVE_INFINITY,
    // Produkt z listy jest od razu na ekranie, także bez sieci.
    initialData: byBarcode ? undefined : target.food,
  });
  const verify = useMutation<Food, Error, FoodVerifyInput>({ mutationKey: mutationKeys.foodVerify });
  const favorite = useMutation<Food, Error, FoodFavoriteInput>({
    mutationKey: mutationKeys.foodFavorite,
  });
  // Kodu nie ma ani u nas, ani w Open Food Facts: produkt można dodać samemu.
  const notFound = food.error instanceof ApiError && food.error.status === 404;
  // Nowy produkt zapisany bez sieci czeka w kolejce i pojawi się po wysłaniu.
  const waiting = useMutationState<FoodCreateInput>({
    filters: { mutationKey: mutationKeys.foodCreate, status: "pending" },
    select: (mutation) => mutation.state.variables as FoodCreateInput,
  }).some((input) => input?.barcode === barcode);

  if (editing && (food.data || notFound)) {
    return (
      <FoodEditForm food={food.data ?? null} barcode={barcode} onDone={() => setEditing(false)} />
    );
  }

  const data = food.data;
  return (
    <section className="card">
      <div className="cardhead">
        <h2>{data?.name ?? barcode}</h2>
        {data && (
          <button
            type="button"
            className={data.favorite ? "star on" : "star"}
            aria-pressed={data.favorite}
            aria-label={data.favorite ? "Usuń z ulubionych" : "Dodaj do ulubionych"}
            onClick={() =>
              favorite.mutate({ id: data.id, barcode: data.barcode, favorite: !data.favorite })
            }
          >
            {data.favorite ? "★" : "☆"}
          </button>
        )}
      </div>
      <p className="muted">
        {[
          data?.brand,
          barcode ? `EAN ${barcode}` : data?.origin === "fdc" ? "produkt podstawowy" : "własny",
        ]
          .filter(Boolean)
          .join(" · ")}
      </p>
      {food.isPending && <p className="muted">Szukam produktu…</p>}
      {food.error && <p className="error">{food.error.message}</p>}
      {notFound &&
        (waiting ? (
          <p className="status todo">Nowy produkt czeka na wysłanie. Pojawi się po powrocie sieci.</p>
        ) : (
          <>
            <p className="muted">
              Możesz dodać go sam: zrób zdjęcie etykiety albo wpisz wartości ręcznie.
            </p>
            <button type="button" className="primary" onClick={() => setEditing(true)}>
              Dodaj produkt
            </button>
          </>
        ))}

      {data && (
        <>
          <FoodStatus food={data} />
          {/* Nad tabelą: większość wyborów to znane produkty, które od razu trafiają do dnia. */}
          {added ? (
            <div className="add">
              <p className="status ok">
                Dodano: {formatDecimal(added.amount)} {data.unit} ·{" "}
                {MEAL_SLOTS.find((s) => s.id === added.slot)?.label}
              </p>
              <div className="row">
                <button type="button" className="primary" onClick={onBack}>
                  {backLabel}
                </button>
                <button type="button" onClick={onShowDiary}>
                  Wróć do diety
                </button>
              </div>
            </div>
          ) : (
            <AddToDay
              food={data}
              day={day}
              source={source}
              initialAmount={target.kind === "food" ? target.amount : undefined}
              initialSlot={slot}
              onAdded={setAdded}
            />
          )}
          <table>
            <caption>Wartości na 100 {data.unit}</caption>
            <tbody>
              {MACRO_ROWS.map(({ key, label, unit, sub }) => {
                const value = data.per_100[key];
                return (
                  <tr key={key}>
                    <th scope="row" className={sub ? "sub" : undefined}>
                      {label}
                    </th>
                    <td>{value == null ? "brak danych" : `${formatNumber(value)} ${unit}`}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>

          <FoodMicros food={data} />

          {data.warnings.map((warning) => (
            <p key={warning} className="notice">
              {warning}
            </p>
          ))}

          <div className="row">
            {/* Produkt podstawowy z tabel nie ma etykiety, z którą można go porównać. */}
            {!data.verified_at && data.origin !== "fdc" && (
              <button
                type="button"
                disabled={verify.isPending}
                onClick={() => verify.mutate({ id: data.id, barcode: data.barcode })}
              >
                Zgadza się z etykietą
              </button>
            )}
            <button type="button" onClick={() => setEditing(true)}>
              Popraw
            </button>
          </div>
          {verify.error && <p className="error">{verify.error.message}</p>}
        </>
      )}

      {!added && (
        <button type="button" onClick={onBack}>
          {backLabel}
        </button>
      )}
    </section>
  );
}

function FoodStatus({ food }: { food: Food }) {
  if (food.verified_at) {
    const how = food.macro_source === "user" ? "Twoje wartości" : "zgodny z etykietą";
    return (
      <p className="status ok">
        Zweryfikowany {formatDay(food.verified_at)} · {how}
      </p>
    );
  }
  if (food.origin === "fdc") {
    // Produkt podstawowy z wyszukiwarki: średnie z tabel, etykiety nie ma z czym porównać.
    return <p className="status ok">Średnie wartości z tabel składu żywności</p>;
  }
  const age = food.source_updated_at ? `, dane z ${formatMonth(food.source_updated_at)}` : "";
  return (
    <p className="status todo">
      Wartości z bazy produktów{age}. Porównaj z etykietą.
    </p>
  );
}

function formatDay(iso: string): string {
  return new Date(iso).toLocaleDateString("pl-PL");
}

function formatMonth(iso: string): string {
  return new Date(iso).toLocaleDateString("pl-PL", { month: "2-digit", year: "numeric" });
}
