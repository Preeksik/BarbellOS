import { useMutation, useQueryClient } from "@tanstack/react-query";
import { type ChangeEvent, type FormEvent, useEffect, useState } from "react";
import { ApiError, type DiaryEntry, type MealDraft, type MealSlot, api } from "../../lib/api";
import {
  type Choice,
  type ItemState,
  chosenFood,
  draftEntries,
  draftTotals,
  foodOptions,
  initialState,
  itemValues,
} from "../../lib/aiDraft";
import { MEAL_SLOTS, dayLabel, defaultSlot, toIsoDay } from "../../lib/diary";
import { shrinkPhoto } from "../../lib/label";
import { INVALID, formatDecimal, parseDecimal } from "../../lib/number";
import { type DiaryPutInput, mutationKeys } from "../../lib/offline";
import { formatGrams, formatKcal } from "./macros";

const CONFIDENCE: Record<string, string> = { low: "niepewne", medium: "", high: "" };

/**
 * Posiłek ze zdjęcia albo z opisu (etap 2). Model proponuje składniki i gramaturę,
 * Ty poprawiasz, a zapis to zwykłe wpisy dziennika (działają także bez sieci).
 * Samo rozpoznanie wymaga sieci: to wywołanie modelu, nie zapis w kolejce.
 */
export function MealAi({
  mode,
  day,
  onBack,
  onShowDiary,
}: {
  mode: "photo" | "text";
  day: string;
  onBack: () => void;
  onShowDiary: () => void;
}) {
  const [draft, setDraft] = useState<MealDraft | null>(null);
  const [photoUrl, setPhotoUrl] = useState<string | null>(null);

  // Podgląd zdjęcia jest adresem w pamięci przeglądarki: zwalniamy go przy wyjściu.
  useEffect(() => () => void (photoUrl && URL.revokeObjectURL(photoUrl)), [photoUrl]);

  if (draft) {
    return (
      <DraftEditor
        draft={draft}
        day={day}
        photoUrl={photoUrl}
        onAgain={() => setDraft(null)}
        onBack={onBack}
        onShowDiary={onShowDiary}
      />
    );
  }
  return (
    <DraftRequest
      mode={mode}
      onBack={onBack}
      onDraft={(next, photo) => {
        setDraft(next);
        setPhotoUrl(photo ? URL.createObjectURL(photo) : null);
      }}
    />
  );
}

function DraftRequest({
  mode,
  onBack,
  onDraft,
}: {
  mode: "photo" | "text";
  onBack: () => void;
  onDraft: (draft: MealDraft, photo: Blob | null) => void;
}) {
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const queryClient = useQueryClient();

  async function run(request: () => Promise<MealDraft>, photo: Blob | null) {
    setBusy(true);
    setError(null);
    try {
      onDraft(await request(), photo);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        void queryClient.invalidateQueries({ queryKey: ["me"] });
      }
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function onPhoto(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    const query = text.trim() ? `?description=${encodeURIComponent(text.trim())}` : "";
    await run(async () => api.post<MealDraft>(`/api/ai/meal/photo${query}`, await shrinkPhoto(file)), file);
  }

  function onText(event: FormEvent) {
    event.preventDefault();
    if (text.trim().length < 3) return setError("Opisz posiłek kilkoma słowami.");
    void run(() => api.post<MealDraft>("/api/ai/meal/text", { text: text.trim() }), null);
  }

  return (
    <form className="card" onSubmit={onText}>
      <h2>{mode === "photo" ? "Zdjęcie posiłku" : "Opisz posiłek"}</h2>
      <p className="muted">
        {mode === "photo"
          ? "Zrób zdjęcie z góry, żeby było widać cały talerz. AI rozpozna składniki i oszacuje gramaturę; wszystko poprawisz przed dodaniem."
          : "Napisz, co zjadłeś, np. „2 jajka sadzone, 2 kromki chleba żytniego z masłem, kawa z mlekiem”. Ilości w gramach będą użyte dokładnie."}
      </p>
      <label>
        {mode === "photo" ? "Opis (opcjonalnie, pomaga AI)" : "Co zjadłeś"}
        <textarea
          rows={mode === "photo" ? 2 : 4}
          maxLength={mode === "photo" ? 500 : 1000}
          placeholder={mode === "photo" ? "np. smażone na oliwie, sos czosnkowy" : ""}
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
      </label>
      {mode === "photo" ? (
        <label className={busy ? "file primary busy" : "file primary"}>
          {busy ? "Analizuję zdjęcie…" : "Zrób zdjęcie"}
          <input type="file" accept="image/*" capture="environment" disabled={busy} onChange={onPhoto} />
        </label>
      ) : (
        <button type="submit" className="primary" disabled={busy}>
          {busy ? "Rozpisuję…" : "Rozpisz na składniki"}
        </button>
      )}
      {error && <p className="error">{error}</p>}
      <button type="button" onClick={onBack} disabled={busy}>
        Wróć
      </button>
    </form>
  );
}

function DraftEditor({
  draft,
  day,
  photoUrl,
  onAgain,
  onBack,
  onShowDiary,
}: {
  draft: MealDraft;
  day: string;
  photoUrl: string | null;
  onAgain: () => void;
  onBack: () => void;
  onShowDiary: () => void;
}) {
  const [states, setStates] = useState<ItemState[]>(() => initialState(draft));
  const [texts, setTexts] = useState<string[]>(() => draft.items.map((i) => formatDecimal(i.grams)));
  const [slot, setSlot] = useState<MealSlot>(() => defaultSlot(new Date().getHours()));
  const [added, setAdded] = useState<number | null>(null);
  // Funkcja zapisu jest w rejestrze lib/offline.ts: dodanie działa bez sieci.
  const put = useMutation<DiaryEntry, Error, DiaryPutInput>({ mutationKey: mutationKeys.diaryPut });

  const totals = draftTotals(draft, states);
  const invalid = states.some((s) => s.include && !(s.grams > 0 && s.grams <= 5000));
  const count = states.filter((s) => s.include && s.grams > 0).length;

  function update(index: number, change: Partial<ItemState>) {
    setStates(states.map((s, i) => (i === index ? { ...s, ...change } : s)));
  }

  function onGrams(index: number, text: string) {
    setTexts(texts.map((t, i) => (i === index ? text : t)));
    const parsed = parseDecimal(text);
    update(index, { grams: parsed === INVALID || parsed == null ? 0 : parsed });
  }

  function save() {
    const inputs = draftEntries(draft, states, day, slot, new Date(), () => crypto.randomUUID());
    for (const input of inputs) put.mutate(input);
    setAdded(inputs.length);
  }

  if (added != null) {
    return (
      <section className="card">
        <p className="status ok">
          Dodano {added} {added === 1 ? "pozycję" : added < 5 ? "pozycje" : "pozycji"} ·{" "}
          {MEAL_SLOTS.find((s) => s.id === slot)?.label} · {formatKcal(totals.kcal)} kcal
        </p>
        <div className="row">
          <button type="button" className="primary" onClick={onShowDiary}>
            Pokaż dziennik
          </button>
          <button type="button" onClick={onBack}>
            Gotowe
          </button>
        </div>
      </section>
    );
  }

  return (
    <section className="card draft">
      <h2>Sprawdź składniki</h2>
      {photoUrl && <img className="mealphoto" src={photoUrl} alt="Zdjęcie posiłku" />}
      {draft.notes && <p className="notice">{draft.notes}</p>}
      {draft.warnings.map((w) => (
        <p key={w} className="notice">
          {w}
        </p>
      ))}

      <ul className="draftitems">
        {draft.items.map((item, index) => {
          const state = states[index];
          const food = chosenFood(item, state.choice);
          const values = itemValues(item, state);
          const options = foodOptions(item);
          return (
            <li key={`${item.name}-${index}`} className={state.include ? "" : "off"}>
              <label className="itemhead">
                <input
                  type="checkbox"
                  checked={state.include}
                  onChange={(e) => update(index, { include: e.target.checked })}
                />
                <strong>{item.name}</strong>
                {CONFIDENCE[item.confidence] && <em>{CONFIDENCE[item.confidence]}</em>}
              </label>
              {state.include && (
                <>
                  <div className="row">
                    <label>
                      Ilość (g)
                      <input
                        inputMode="decimal"
                        value={texts[index]}
                        aria-invalid={!(state.grams > 0 && state.grams <= 5000)}
                        onChange={(e) => onGrams(index, e.target.value)}
                        onFocus={(e) => e.target.select()}
                      />
                      <span className="muted">
                        AI: {formatDecimal(item.grams_low)}–{formatDecimal(item.grams_high)} g
                      </span>
                    </label>
                    <label>
                      Produkt
                      <select
                        value={state.choice.kind === "food" ? String(state.choice.foodId) : "estimate"}
                        onChange={(e) => {
                          const choice: Choice =
                            e.target.value === "estimate"
                              ? { kind: "estimate" }
                              : { kind: "food", foodId: Number(e.target.value) };
                          update(index, { choice });
                        }}
                      >
                        {options.map((f) => (
                          <option key={f.id} value={f.id}>
                            {f.name}
                            {f.brand ? ` · ${f.brand}` : ""}
                          </option>
                        ))}
                        <option value="estimate">
                          Szacunek AI
                          {item.estimate_per_100.kcal != null
                            ? ` (${formatKcal(item.estimate_per_100.kcal)} kcal/100 g)`
                            : ""}
                        </option>
                      </select>
                    </label>
                  </div>
                  <p className="muted">
                    {values.kcal == null ? "brak danych o kaloriach" : `${formatKcal(values.kcal)} kcal`}
                    {" · "}B {formatGrams(values.protein_g)} · T {formatGrams(values.fat_g)} · W{" "}
                    {formatGrams(values.carbs_g)}
                    {food ? "" : " · szacunek AI, bez mikroskładników"}
                  </p>
                </>
              )}
            </li>
          );
        })}
      </ul>

      <div className="slothead">
        <strong>Razem: {formatKcal(totals.kcal)} kcal</strong>
        <span>
          B {formatGrams(totals.protein_g)} · T {formatGrams(totals.fat_g)} · W{" "}
          {formatGrams(totals.carbs_g)}
        </span>
      </div>
      <label>
        Posiłek · {dayLabel(day, toIsoDay(new Date()))}
        <select value={slot} onChange={(e) => setSlot(e.target.value as MealSlot)}>
          {MEAL_SLOTS.map((s) => (
            <option key={s.id} value={s.id}>
              {s.label}
            </option>
          ))}
        </select>
      </label>
      {invalid && <p className="error">Popraw ilości: większe od zera, najwyżej 5000 g.</p>}
      <button type="button" className="primary" disabled={invalid || count === 0} onClick={save}>
        Dodaj do dnia ({count})
      </button>
      <div className="row">
        <button type="button" onClick={onAgain}>
          Spróbuj jeszcze raz
        </button>
        <button type="button" onClick={onBack}>
          Anuluj
        </button>
      </div>
    </section>
  );
}
