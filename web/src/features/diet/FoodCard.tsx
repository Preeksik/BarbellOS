import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { type Food, api } from "../../lib/api";
import { MEAL_SLOTS } from "../../lib/diary";
import { formatDecimal } from "../../lib/number";
import { type FoodVerifyInput, foodQueryKey, mutationKeys } from "../../lib/offline";
import { AddToDay, type Added } from "./AddToDay";
import { FoodEditForm } from "./FoodEditForm";
import { MACRO_ROWS, formatNumber } from "./macros";

/** Produkt po skanie: wartości, weryfikacja, poprawianie według etykiety, dodanie do dnia. */
export function FoodCard({
  barcode,
  day,
  onAgain,
  onShowDiary,
}: {
  barcode: string;
  day: string;
  onAgain: () => void;
  onShowDiary: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [added, setAdded] = useState<Added | null>(null);
  const food = useQuery({
    queryKey: foodQueryKey(barcode),
    queryFn: () => api.get<Food>(`/api/foods/barcode/${barcode}`),
    retry: false,
    staleTime: Number.POSITIVE_INFINITY,
  });
  const verify = useMutation<Food, Error, FoodVerifyInput>({ mutationKey: mutationKeys.foodVerify });

  if (editing && food.data) {
    return <FoodEditForm food={food.data} barcode={barcode} onDone={() => setEditing(false)} />;
  }

  return (
    <section className="card">
      <h2>{food.data?.name ?? barcode}</h2>
      <p className="muted">
        {food.data?.brand ? `${food.data.brand} · ` : ""}EAN {barcode}
      </p>
      {food.isPending && <p className="muted">Szukam produktu…</p>}
      {food.error && <p className="error">{food.error.message}</p>}

      {food.data && (
        <>
          <FoodStatus food={food.data} />
          {/* Nad tabelą: większość skanów to znane produkty, które od razu trafiają do dnia. */}
          {added ? (
            <div className="add">
              <p className="status ok">
                Dodano: {formatDecimal(added.amount)} {food.data.unit} ·{" "}
                {MEAL_SLOTS.find((s) => s.id === added.slot)?.label}
              </p>
              <div className="row">
                <button type="button" className="primary" onClick={onAgain}>
                  Skanuj kolejny
                </button>
                <button type="button" onClick={onShowDiary}>
                  Pokaż dziennik
                </button>
              </div>
            </div>
          ) : (
            <AddToDay food={food.data} day={day} onAdded={setAdded} />
          )}
          <table>
            <caption>Wartości na 100 {food.data.unit}</caption>
            <tbody>
              {MACRO_ROWS.map(({ key, label, unit, sub }) => {
                const value = food.data.per_100[key];
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

          {food.data.warnings.map((warning) => (
            <p key={warning} className="notice">
              {warning}
            </p>
          ))}

          <div className="row">
            {!food.data.verified_at && (
              <button
                type="button"
                disabled={verify.isPending}
                onClick={() => verify.mutate({ id: food.data.id, barcode })}
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
        <button type="button" onClick={onAgain}>
          Skanuj kolejny
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
  const age = food.source_updated_at ? `, dane z ${formatMonth(food.source_updated_at)}` : "";
  return (
    <p className="status todo">
      Niezweryfikowany · Open Food Facts{age}. Porównaj z etykietą.
    </p>
  );
}

function formatDay(iso: string): string {
  return new Date(iso).toLocaleDateString("pl-PL");
}

function formatMonth(iso: string): string {
  return new Date(iso).toLocaleDateString("pl-PL", { month: "2-digit", year: "numeric" });
}
