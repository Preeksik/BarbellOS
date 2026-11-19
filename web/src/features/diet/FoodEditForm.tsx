import { useMutation, useQueryClient } from "@tanstack/react-query";
import { type ChangeEvent, type FormEvent, useEffect, useState } from "react";
import { ApiError, type Food, type MacroKey } from "../../lib/api";
import { applyLabelDraft, labelKeys, readLabel } from "../../lib/label";
import { INVALID, formatDecimal, parseDecimal } from "../../lib/number";
import {
  type FoodCreateInput,
  type FoodCustomInput,
  type FoodUpdateInput,
  mutationKeys,
} from "../../lib/offline";
import { MACRO_ROWS } from "./macros";

type Texts = Record<MacroKey, string>;

const MACRO_ORDER = MACRO_ROWS.map(({ key }) => key);

// Składnik „w tym…" nie może być większy od składnika, którego jest częścią.
const SUBSETS: [MacroKey, MacroKey, string][] = [
  ["sat_fat_g", "fat_g", "Kwasy nasycone nie mogą przekraczać tłuszczu."],
  ["sugars_g", "carbs_g", "Cukry nie mogą przekraczać węglowodanów."],
];

/** Co wpisało zdjęcie etykiety: podświetlone pola i uwagi z serwera do sprawdzenia. */
interface FromLabel {
  keys: MacroKey[]; // pola nadal w brzmieniu ze zdjęcia (ręczna poprawka zdejmuje podświetlenie)
  count: number; // ile wartości model odczytał
  warnings: string[];
}

/**
 * Formularz produktu według etykiety. Puste pole oznacza brak danych, nie zero.
 *
 * `food` to poprawiany produkt; `null` oznacza nowy produkt: dla kodu, którego nie ma
 * w Open Food Facts, albo (bez `barcode`) produkt bez kodu kreskowego.
 * Zdjęcie etykiety tylko wypełnia pola: zapisuje dopiero „Zapisz".
 */
export function FoodEditForm({
  food,
  barcode,
  onDone,
  onSaved,
}: {
  food: Food | null;
  barcode: string | null;
  onDone: () => void;
  /** Wywoływane z produktem z serwera po udanym zapisie (nie przy zapisie w kolejce). */
  onSaved?: (food: Food) => void;
}) {
  // Identyfikator produktu bez kodu, nadany raz na formularz: powtórka nie tworzy duplikatu.
  const [clientId] = useState(() => crypto.randomUUID());
  const [name, setName] = useState(food?.name ?? "");
  const [brand, setBrand] = useState(food?.brand ?? "");
  const [unit, setUnit] = useState<"g" | "ml">(food?.unit ?? "g");
  const [serving, setServing] = useState<number | null>(food?.serving_g ?? null);
  const [texts, setTexts] = useState<Texts>(
    () =>
      Object.fromEntries(MACRO_ORDER.map((key) => [key, formatDecimal(food?.per_100[key])])) as Texts,
  );
  const [problem, setProblem] = useState<string | null>(null);
  const [reading, setReading] = useState(false);
  const [labelError, setLabelError] = useState<string | null>(null);
  const [fromLabel, setFromLabel] = useState<FromLabel | null>(null);
  const queryClient = useQueryClient();
  // Funkcje zapisu są w rejestrze lib/offline.ts, więc zapis przetrwa brak sieci.
  const update = useMutation<Food, Error, FoodUpdateInput>({ mutationKey: mutationKeys.foodUpdate });
  const create = useMutation<Food, Error, FoodCreateInput>({ mutationKey: mutationKeys.foodCreate });
  const custom = useMutation<Food, Error, FoodCustomInput>({ mutationKey: mutationKeys.foodCustom });
  const saving = update.isPending || create.isPending || custom.isPending;
  const paused = update.isPaused || create.isPaused || custom.isPaused;
  const saveError = update.error ?? create.error ?? custom.error;

  // Bez sieci zapis czeka w kolejce: nie trzymamy użytkownika w formularzu.
  useEffect(() => {
    if (paused) onDone();
  }, [paused, onDone]);

  // Odczyt etykiety to nie zapis do kolejki: wymaga sieci i modelu, więc jest zwykłym
  // wywołaniem. Jako „mutation" trafiłby ze zdjęciem do IndexedDB i do licznika niewysłanych.
  async function onPhoto(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    setReading(true);
    setLabelError(null);
    try {
      const draft = await readLabel(file);
      // Funkcje zamiast wartości: pola mogły się zmienić, gdy model czytał zdjęcie.
      setTexts((current) => applyLabelDraft(current, draft));
      setName((current) => (current.trim() ? current : (draft.name ?? "")));
      setBrand((current) => (current.trim() ? current : (draft.brand ?? "")));
      setServing((current) => current ?? draft.serving_g);
      if (draft.unit) setUnit(draft.unit);
      const keys = labelKeys(draft, MACRO_ORDER);
      setFromLabel({ keys, count: keys.length, warnings: draft.warnings });
      setProblem(null);
    } catch (error) {
      // Sesja wygasła: odświeżenie „me" pokaże ekran logowania.
      if (error instanceof ApiError && error.status === 401) {
        void queryClient.invalidateQueries({ queryKey: ["me"] });
      }
      setLabelError(error instanceof Error ? error.message : String(error));
    } finally {
      setReading(false);
    }
  }

  function onValue(key: MacroKey, text: string) {
    setTexts({ ...texts, [key]: text });
    // Pole poprawione ręcznie nie jest już „ze zdjęcia".
    if (fromLabel?.keys.includes(key)) {
      setFromLabel({ ...fromLabel, keys: fromLabel.keys.filter((k) => k !== key) });
    }
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    const per_100 = {} as Food["per_100"];
    for (const { key, label } of MACRO_ROWS) {
      const parsed = parseDecimal(texts[key]);
      if (parsed === INVALID) return setProblem(`„${label}": wpisz liczbę albo zostaw puste pole.`);
      per_100[key] = parsed;
    }
    for (const [part, whole, message] of SUBSETS) {
      const a = per_100[part];
      const b = per_100[whole];
      if (a != null && b != null && a > b) return setProblem(message);
    }
    if (!name.trim()) return setProblem("Wpisz nazwę produktu.");
    setProblem(null);
    const body = {
      name: name.trim(),
      brand: brand.trim() || null,
      serving_g: serving,
      unit,
      per_100,
    };
    // Z `onSaved` to rodzic decyduje, co pokazać dalej (np. kartę nowego produktu).
    const saved = (result: Food) => (onSaved ? onSaved(result) : onDone());
    const origin = fromLabel ? "ai_label" : "user";
    if (food) {
      update.mutate({ id: food.id, barcode: food.barcode, body }, { onSuccess: saved });
    } else if (barcode) {
      create.mutate({ barcode, body: { ...body, origin } }, { onSuccess: saved });
    } else {
      custom.mutate({ clientId, body: { ...body, origin } }, { onSuccess: saved });
    }
  }

  return (
    <form className="card" onSubmit={submit}>
      <h2>{food ? "Popraw według etykiety" : "Własny produkt"}</h2>
      {!food && (
        <p className="muted">
          {barcode ? `EAN ${barcode}` : "Bez kodu kreskowego (np. danie domowe, produkt na wagę)"}
        </p>
      )}

      <label className={reading ? "file busy" : "file"}>
        {reading ? "Czytam etykietę…" : "Zdjęcie etykiety"}
        <input
          type="file"
          accept="image/*"
          capture="environment"
          disabled={reading}
          onChange={onPhoto}
        />
      </label>
      {labelError && <p className="error">{labelError}</p>}
      {fromLabel ? (
        <p className="status todo">
          Odczytano {fromLabel.count} z {MACRO_ROWS.length} wartości (podświetlone). Porównaj
          je z etykietą i zapisz.
        </p>
      ) : (
        <p className="muted">
          Sfotografuj tabelę wartości odżywczych: pola wypełnią się same. Nic nie zapisze się,
          dopóki nie stukniesz „Zapisz".
        </p>
      )}
      {fromLabel?.warnings.map((warning) => (
        <p key={warning} className="notice">
          {warning}
        </p>
      ))}

      <label>
        Nazwa
        <input value={name} onChange={(e) => setName(e.target.value)} />
      </label>
      <label>
        Marka
        <input value={brand} onChange={(e) => setBrand(e.target.value)} />
      </label>

      <fieldset className="segmented">
        <legend>Wartości na</legend>
        {(["g", "ml"] as const).map((option) => (
          <label key={option} className={unit === option ? "active" : ""}>
            <input
              type="radio"
              name="unit"
              checked={unit === option}
              onChange={() => setUnit(option)}
            />
            100 {option}
          </label>
        ))}
      </fieldset>

      <div className="fields">
        {MACRO_ROWS.map(({ key, label, unit: rowUnit, sub }) => {
          const read = fromLabel?.keys.includes(key);
          return (
            <label key={key} className={`field${sub ? " sub" : ""}${read ? " read" : ""}`}>
              <span>{label}</span>
              <input
                inputMode="decimal"
                autoComplete="off"
                placeholder="brak"
                value={texts[key]}
                onChange={(e) => onValue(key, e.target.value)}
              />
              <span className="muted">{rowUnit}</span>
            </label>
          );
        })}
      </div>
      <p className="muted">Puste pole oznacza, że etykieta nie podaje tej wartości.</p>

      {(problem || saveError) && <p className="error">{problem ?? saveError?.message}</p>}
      <div className="row">
        <button type="button" onClick={onDone}>
          Anuluj
        </button>
        <button type="submit" className="primary" disabled={saving || reading}>
          Zapisz
        </button>
      </div>
    </form>
  );
}
