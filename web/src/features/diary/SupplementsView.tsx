import { useMutation, useQuery } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { type SupplementDay, api } from "../../lib/api";
import { dayLabel, shiftDay, toIsoDay } from "../../lib/diary";
import {
  type SupplementDayInput,
  type SupplementDeleteInput,
  type SupplementPutInput,
  type SupplementYesterdayInput,
  mutationKeys,
  supplementsQueryKey,
} from "../../lib/offline";
import { toggled, yesterdayGain } from "../../lib/supplements";

/**
 * Suplementacja w Diecie (23.11.2026): lista suplementów do odhaczania, „To co wczoraj",
 * seria dni i ostatni tydzień przy każdym. Wszystko działa bez sieci (kolejka offline).
 */
export function SupplementsView({ day }: { day: string }) {
  const today = toIsoDay(new Date());
  const [editing, setEditing] = useState(false);
  const supplements = useQuery({
    queryKey: supplementsQueryKey(day),
    queryFn: () => api.get<SupplementDay>(`/api/supplements/day/${day}`),
  });
  const setDay = useMutation<void, Error, SupplementDayInput>({
    mutationKey: mutationKeys.supplementDay,
  });
  const yesterday = useMutation<void, Error, SupplementYesterdayInput>({
    mutationKey: mutationKeys.supplementYesterday,
  });
  const remove = useMutation<void, Error, SupplementDeleteInput>({
    mutationKey: mutationKeys.supplementDelete,
  });

  const data = supplements.data;
  if (!data) {
    return (
      <section className="card">
        {supplements.error ? (
          <p className="error">{supplements.error.message}</p>
        ) : supplements.fetchStatus === "paused" ? (
          <p className="muted">Brak połączenia, a tego dnia nie ma w pamięci telefonu.</p>
        ) : (
          <p className="muted">Wczytuję suplementy…</p>
        )}
      </section>
    );
  }

  const gain = yesterdayGain(data);
  const previous = dayLabel(shiftDay(day, -1), today).toLowerCase();

  return (
    <>
      <section className="card supps">
        <div className="slothead">
          <h2>Suplementy</h2>
          {data.supplements.length > 0 && (
            <span>
              {data.taken_ids.length} <small>z {data.supplements.length}</small>
            </span>
          )}
        </div>

        {data.supplements.length === 0 ? (
          <p className="muted">
            Dodaj to, co bierzesz, np. „Witamina D3, 2000 IU". Potem odhaczasz codziennie albo
            jednym stuknięciem „To co wczoraj".
          </p>
        ) : (
          <>
            <button
              type="button"
              className="primary wide yesterday"
              disabled={gain === 0}
              onClick={() => yesterday.mutate({ date: day })}
            >
              {data.yesterday_ids.length === 0
                ? `Brak odhaczeń: ${previous}`
                : gain === 0
                  ? `To co ${previous}: odhaczone`
                  : `To co ${previous} (+${gain})`}
            </button>
            <ul className="supplist">
              {data.supplements.map((s) => (
                <li key={s.id}>
                  <button
                    type="button"
                    className={s.taken ? "supp on" : "supp"}
                    aria-pressed={s.taken}
                    onClick={() => setDay.mutate({ date: day, takenIds: toggled(data, s.id) })}
                  >
                    <span className="tick" aria-hidden="true">
                      {s.taken && (
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={3}>
                          <path d="M5 12.5l4.5 4.5L19 7" strokeLinecap="round" strokeLinejoin="round" />
                        </svg>
                      )}
                    </span>
                    <span className="name">
                      {s.name}
                      {s.dose && <span className="muted"> {s.dose}</span>}
                    </span>
                    <span className="habit">
                      <span className="dots" aria-label={`Ostatnie 7 dni: ${s.last7.filter(Boolean).length} z 7`}>
                        {s.last7.map((taken, i) => (
                          <i key={i} className={taken ? "on" : ""} />
                        ))}
                      </span>
                      <span className="streak">
                        {s.streak > 0 ? `${s.streak} ${s.streak === 1 ? "dzień" : "dni"} z rzędu` : "bez serii"}
                      </span>
                    </span>
                  </button>
                  {editing && (
                    <button
                      type="button"
                      className="forget"
                      aria-label={`Usuń z listy: ${s.name}`}
                      onClick={() => remove.mutate({ id: s.id })}
                    >
                      ✕
                    </button>
                  )}
                </li>
              ))}
            </ul>
            <button type="button" className="link" onClick={() => setEditing(!editing)}>
              {editing ? "Gotowe" : "Usuń z listy"}
            </button>
          </>
        )}
      </section>
      <AddSupplement />
    </>
  );
}

/** Nowy suplement na liście. Identyfikator nadaje telefon (kolejka offline). */
function AddSupplement() {
  const [name, setName] = useState("");
  const [dose, setDose] = useState("");
  const put = useMutation<void, Error, SupplementPutInput>({
    mutationKey: mutationKeys.supplementPut,
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!name.trim()) return;
    put.mutate({ id: crypto.randomUUID(), name: name.trim(), dose: dose.trim() || null });
    setName("");
    setDose("");
  }

  return (
    <form className="card" onSubmit={submit}>
      <h2>Dodaj suplement</h2>
      <div className="row">
        <label>
          Nazwa
          <input
            value={name}
            maxLength={80}
            placeholder="np. Kreatyna"
            onChange={(e) => setName(e.target.value)}
          />
        </label>
        <label className="dose">
          Dawka
          <input
            value={dose}
            maxLength={40}
            placeholder="np. 5 g"
            onChange={(e) => setDose(e.target.value)}
          />
        </label>
      </div>
      <button type="submit" disabled={!name.trim()}>
        Dodaj do listy
      </button>
    </form>
  );
}
